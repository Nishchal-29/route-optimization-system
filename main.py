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

# ROUTE PLANNING ENDPOINTS
@app.get("/")
async def root():
    """API root with available endpoints"""
    return {
        "message": "AI Logistics Optimizer API",
        "version": "2.0.0",
        "features": [
            "Natural language route planning",
            "Real-time traffic monitoring",
            "AI driver copilot",
            "Weather-aware optimization"
        ],
        "endpoints": {
            "planning": [
                "POST /extract-sequence - Parse NL to locations",
                "POST /optimize-route - Optimize route with GA",
                "POST /create-manifest - Create new delivery manifest"
            ],
            "agent": [
                "POST /agent/chat - Chat with AI copilot",
                "GET /agent/status - Get current route status"
            ],
            "monitoring": [
                "GET /traffic/map - Get traffic visualization",
                "GET /health - Health check"
            ]
        }
    }

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
        # Prepare readable route string
        route_text = " → ".join([loc.name for loc in data.optimized_route])
        total_stops = len(data.optimized_route)
        weather_text = ""
        if data.weather_alerts:
            weather_text = "Weather alerts: " + ", ".join(data.weather_alerts)

        # Optional: include time violations from full_log
        time_violations = []
        for entry in data.full_log or []:
            if entry.get("event") == "Wait" and entry.get("reason"):
                time_violations.append(f"{entry.get('name', 'Unknown')}: {entry['reason']}")
        time_violation_text = ""
        if time_violations:
            time_violation_text = "Time delays due to: " + "; ".join(time_violations)

        # Gemini prompt
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
    - "I need to deliver from Delhi to Mumbai via Jaipur"
    - "How is the traffic looking right now?"
    - "I'm delayed by 30 minutes due to rain"
    - "What's my current status?"
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

# @app.post("/agent/report-delay")
# async def report_delay(delay: DelayReport):
#     """Report a delay and get agent recommendation"""
#     if not CURRENT_STATE["is_active"]:
#         raise HTTPException(
#             status_code=404,
#             detail="No active route. Create a manifest first."
#         )
    
#     # Use agent to process the delay
#     message = f"I'm delayed by {delay.delay_minutes} minutes due to {delay.reason}"
#     if delay.location:
#         message += f" at {delay.location}"
    
#     agent_response = run_logistics_chat(message)
    
#     return {
#         "status": "success",
#         "delay_recorded": {
#             "minutes": delay.delay_minutes,
#             "reason": delay.reason,
#             "location": delay.location,
#             "timestamp": datetime.now().isoformat()
#         },
#         "agent_recommendation": agent_response
#     }

# @app.post("/agent/check-traffic")
# async def check_traffic_status():
#     """Check real-time traffic for active route"""
#     if not CURRENT_STATE["is_active"]:
#         raise HTTPException(
#             status_code=404,
#             detail="No active route. Create a manifest first."
#         )
    
#     agent_response = run_logistics_chat("Check traffic conditions for my route")
    
#     return {
#         "status": "success",
#         "traffic_check": agent_response,
#         "timestamp": datetime.now().isoformat()
#     }

@app.get("/traffic/map")
async def get_traffic_map(session_id: str = Query(...)):
    """Generate and return traffic visualization map"""
    state = get_session_state(session_id)
    if not state["is_active"]:
        raise HTTPException(status_code=404, detail="No active route found for this session.")
    
    try:
        locations = [{
            "name": s["name"],
            "lat": s["lat"],
            "lon": s["lon"]
        } for s in state["active_route"]]
        result = generate_traffic_map(locations, route_sequence=locations)
        
        return {
            "status": "success",
            "map_file": result["map_file"],
            "congestion_status": result["congestion_status"],
            "details": result["details"],
            "download_url": "/traffic/download-map"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Traffic map generation failed: {str(e)}")

@app.get("/traffic/download-map")
async def download_traffic_map():
    """Download the generated traffic map HTML file"""
    map_file = "traffic_map.html"
    
    if not os.path.exists(map_file):
        raise HTTPException(status_code=404, detail="Traffic map not generated yet")
    
    return FileResponse(
        map_file,
        media_type="text/html",
        filename="traffic_map.html"
    )
  
@app.get("/health")
async def health_check():
    return {"status": "healthy"}