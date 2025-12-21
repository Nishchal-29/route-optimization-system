import os
import json
import requests
from typing import List, Optional, Dict, Any
from datetime import datetime
from fastapi import FastAPI, HTTPException, BackgroundTasks, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from dotenv import load_dotenv
import google.generativeai as genai

from route import solve_route
from traffic import generate_traffic_map
from agent import run_logistics_chat
from db import get_session_state, create_new_route_db, activate_route_db

load_dotenv()
ORS_API_KEY = os.getenv("ORS_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
TOMTOM_API_KEY = os.getenv("TOMTOM_API_KEY")

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-2.5-flash')

app = FastAPI(
    title="AI Logistics Optimizer with Driver Copilot",
    description="Production-ready logistics optimization with AI agent",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class LogisticsQuery(BaseModel):
    request_text: str 

class LocationPoint(BaseModel):
    name: str
    lat: float
    lon: float
    visit_sequence: int 

class RouteResponse(BaseModel):
    parsed_locations: List[LocationPoint]

class ChatMessage(BaseModel):
    message: str
    session_id: str = Field(..., description="Unique session ID for the driver/user")

class RouteManifest(BaseModel):
    """Request to create a new delivery manifest"""
    session_id: str = Field(..., description="Bind this route to a specific session")
    # locations: List[LocationPoint]
    route_id: int = Field(..., description="The ID returned by /optimize-route")
    driver_name: Optional[str] = "Driver_001"
    start_time: Optional[str] = datetime.now().isoformat()

class DelayReport(BaseModel):
    """Report a delay on active route"""
    session_id: str
    delay_minutes: int
    reason: str
    location: Optional[str] = None

class OptimizedRouteSummaryRequest(BaseModel):
    """Request to summarize an optimized route"""
    optimized_route: List[LocationPoint]
    total_distance_km: float
    total_duration_hours: float
    weather_alerts: Optional[List[str]] = []
    full_log: Optional[List[Dict[str, Any]]] = []
    
def get_coords_from_ors(location_name: str):
    """Geocode location using OpenRouteService"""
    try:
        url = f"https://api.openrouteservice.org/geocode/search?api_key={ORS_API_KEY}&text={location_name}"
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            data = r.json()
            if data['features']:
                coords = data['features'][0]['geometry']['coordinates']
                return coords[1], coords[0]  # lat, lon
    except Exception as e:
        print(f"Geocoding error: {e}")
    return None, None

def parse_logistics_intent(text: str):
    """Extract locations and sequence from natural language"""
    prompt = f"""
    You are a Logistics Dispatcher. Analyze this request: "{text}"
    
    Task:
    1. Identify all locations.
    2. Determine the VISITING ORDER / SEQUENCE.
       - Source City: Always assign visit_sequence = 1.
       - Fixed Destination (e.g. "end at Mumbai"): Assign highest sequence (e.g., 10).
       - Intermediate Stops:
         * If the user says "then", "after", "first", "second": Assign increasing sequence numbers (2, 3, 4...).
         * If the user just lists cities ("visit A, B, and C"): Assign the SAME sequence number to all of them (e.g., all are 2).
    
    Return a raw JSON array. Each object must have:
    - "location_name": str
    - "visit_sequence": int (1-based index)
    
    Do not use markdown. Return only JSON.
    """
    
    try:
        response = model.generate_content(prompt)
        clean_text = response.text.replace("```json", "").replace("```", "").strip()
        return json.loads(clean_text)
    except Exception as e:
        print(f"LLM Parsing failed: {e}")
        return []

@app.post("/extract-sequence", response_model=RouteResponse)
async def extract_sequence(query: LogisticsQuery):
    """Extract locations and sequence from natural language query"""
    extracted_data = parse_logistics_intent(query.request_text)
    if not extracted_data:
        raise HTTPException(status_code=400, detail="No locations found in text.")

    final_locations = []
    
    for item in extracted_data:
        lat, lon = get_coords_from_ors(item["location_name"])
        
        if lat and lon:
            final_locations.append(LocationPoint(
                name=item["location_name"],
                lat=lat,
                lon=lon,
                visit_sequence=item.get("visit_sequence", 999),
            ))
            
    final_locations.sort(key=lambda x: x.visit_sequence)
    return RouteResponse(parsed_locations=final_locations)

@app.post("/route/summary")
async def route_summary(data: OptimizedRouteSummaryRequest):
    """
    Summarize an optimized route using Gemini AI.
    Includes weather/time violations for better driver advice.
    """
    try:
        if not data.optimized_route or len(data.optimized_route) < 2:
            raise HTTPException(status_code=400, detail="At least two locations required for summary.")

        route_text = " → ".join([loc.name for loc in data.optimized_route])
        total_stops = len(data.optimized_route)
        weather_text = ""
        if data.weather_alerts:
            weather_text = "Weather alerts: " + ", ".join(data.weather_alerts)

        time_violations = []
        for entry in data.full_log or []:
            if entry.get("event") == "Wait" and entry.get("reason"):
                time_violations.append(f"{entry.get('name', 'Unknown')}: {entry['reason']}")
        time_violation_text = ""
        if time_violations:
            time_violation_text = "Time delays due to: " + "; ".join(time_violations)

        prompt = f"""
        You are an AI Logistics Assistant. Summarize the following delivery route for the driver:

        Route: {route_text}
        Total stops: {total_stops}
        Total distance: {data.total_distance_km} km
        Total duration: {data.total_duration_hours} hours

        {weather_text}
        {time_violation_text}

        Generate a clear, concise summary with driving advice, sequence of stops, and any important notes and also keep in mind the weather conditions given to you.
        Warn the driver according to the details of the wether conditions about the source cities.
        Return plain text, no JSON or markdown.
        """
        response = model.generate_content(prompt)
        summary_text = response.text.strip()
        return {
            "status": "success",
            "summary": summary_text
        }

    except Exception as e:
        print(f"[route/summary ERROR] {e}")
        raise HTTPException(status_code=500, detail=f"Route summary generation failed: {str(e)}")


@app.post("/optimize-route")
async def optimize_route(data: RouteResponse, session_id: str = Query(..., description="Bind optimization to session")):
    """Optimize route using genetic algorithm with weather awareness"""
    try:
        if not data.parsed_locations:
            raise HTTPException(
                status_code=400,
                detail="No locations provided for route optimization"
            )

        locations_list = [loc.dict() for loc in data.parsed_locations]
        result = solve_route(locations_list)
        
        if result.get("status") == "error":
            raise HTTPException(status_code=500, detail=result.get("message"))
        
        if "full_log" in result:
            for entry in result["full_log"]:
                if "time" in entry and isinstance(entry["time"], datetime):
                    entry["time"] = entry["time"].isoformat()
        
        optimized_stops_data = []
        stop_events = [
            event for event in result["full_log"] 
            if event["event"] in ["Depart", "Arrive"]
        ]
        route_names = result["optimized_route"]
        
        if len(stop_events) != len(route_names):
            print(f"Warning: Log length {len(stop_events)} != Route length {len(route_names)}")
        
        for i, name in enumerate(route_names):
            original = next((loc for loc in locations_list if loc["name"] == name), None)
            eta_iso = None
            if i < len(stop_events):
                raw_time = stop_events[i]["time"]
                if isinstance(raw_time, datetime):
                    eta_iso = raw_time.isoformat()
                else:
                    eta_iso = raw_time
                    
            if original:
                optimized_stops_data.append({
                    "name": name,
                    "lat": original["lat"],
                    "lon": original["lon"],
                    "visit_sequence": i + 1,
                    "status": "completed" if i == 0 else "pending",
                    "eta": eta_iso
                })

        route_id = create_new_route_db(
            session_id=session_id,
            driver_name="Driver_001",
            stops_data=optimized_stops_data,
            status="draft"
        )

        return {
            **result, 
            "route_id": route_id, 
            "message": "Route optimized and saved as draft."
        }
    except Exception as e:
        print(f"[optimize-route ERROR] {e}")
        raise HTTPException(status_code=500, detail=f"Optimize route failed: {str(e)}")

@app.post("/create-manifest")
async def create_manifest(manifest: RouteManifest):
    """Create a new delivery manifest and initialize the agent state"""
    try:
        result = activate_route_db(manifest.route_id, manifest.driver_name)
        
        if not result:
            raise HTTPException(
                status_code=404, 
                detail=f"Route ID {manifest.route_id} not found. Please optimize the route first."
            )
        
        return {
            "status": "success",
            "message": f"Manifest created for Session {manifest.session_id}",
            "route_id": manifest.route_id,
            "manifest_id": f"MF_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "driver": manifest.driver_name,
            "created_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create manifest: {str(e)}")

# AI AGENT ENDPOINTS
@app.post("/agent/chat")
async def agent_chat(message: ChatMessage):
    """
    Chat with AI logistics copilot
    
    Examples:
    - "How is the traffic looking right now?"
    - "I'm delayed by 30 minutes due to rain"
    - "What's my current status?"
    - "Any weather alerts on my route?"
    - "How long will it take to reach the next stop?"
    """
    try:
        response = run_logistics_chat(user_input=message.message, session_id=message.session_id)
        
        return {
            "status": "success",
            "user_message": message.message,
            "agent_response": response,
            "session_id": message.session_id,
            "timestamp": datetime.now().isoformat(),
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent error: {str(e)}")

@app.get("/agent/status")
async def get_agent_status(session_id: str = Query(..., description="Session ID to fetch status for")):
    """Get current route status from agent state"""
    state = get_session_state(session_id)
    if not state["is_active"]:
        return {"status": "no_active_route", "active": False}
    
    stops = state["active_route"]
    pending = [s for s in stops if s["status"] == "pending"]
    completed = [s for s in stops if s["status"] == "completed"]
    
    return {
        "status": "active",
        "active": True,
        "driver": state["driver_name"],
        "last_updated": state["last_updated"],
        "route_summary": {
            "total_stops": len(stops),
            "completed": len(completed),
            "pending": len(pending),
            "progress_percentage": round(
                (len(completed) / len(stops)) * 100, 2
            ) if stops else 0
        },
        "current_location": completed[-1]["name"] if completed else stops[0]["name"],
        "next_stop": pending[0]["name"] if pending else "Route Complete",
        "pending_stops": [stop["name"] for stop in pending],
        "completed_stops": [stop["name"] for stop in completed],
        "route_details": stops
    }
    
@app.get("/traffic/view-map/{filename}")
async def view_traffic_map(filename: str):
    """Serve a specific generated traffic map"""
    if not filename.endswith(".html") or "/" in filename or "\\" in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")
        
    file_path = filename
    
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Map not found")
    
    return FileResponse(file_path, media_type="text/html")
  
@app.get("/health")
async def health_check():
    return {"status": "healthy"}