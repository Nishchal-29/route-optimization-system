import os
import json
import requests
from typing import List, Optional, Dict, Any
from datetime import datetime
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from dotenv import load_dotenv
import google.generativeai as genai

from route import solve_route
from traffic import generate_traffic_map
from agent import run_logistics_chat, CURRENT_STATE

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
    session_id: Optional[str] = Field(default="default_session")

class RouteManifest(BaseModel):
    """Request to create a new delivery manifest"""
    locations: List[LocationPoint]
    driver_name: Optional[str] = "Driver_001"
    start_time: Optional[str] = datetime.now().isoformat()

class DelayReport(BaseModel):
    """Report a delay on active route"""
    delay_minutes: int
    reason: str
    location: Optional[str] = None
    
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
                "GET /agent/status - Get current route status",
                "POST /agent/report-delay - Report delay",
                "POST /agent/check-traffic - Check traffic conditions"
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

@app.post("/optimize-route")
async def optimize_route(data: RouteResponse):
    """Optimize route using genetic algorithm with weather awareness"""
    if not data.parsed_locations:
        raise HTTPException(
            status_code=400,
            detail="No locations provided for route optimization"
        )

    locations_list = [loc.dict() for loc in data.parsed_locations]
    result = solve_route(locations_list)
    
    if result.get("status") == "error":
        raise HTTPException(status_code=500, detail=result.get("message"))
    
    return result

@app.post("/create-manifest")
async def create_manifest(manifest: RouteManifest):
    """Create a new delivery manifest and initialize the agent state"""
    try:
        locations_list = [loc.dict() for loc in manifest.locations]        
        result = solve_route(locations_list)
        
        if result.get("status") == "error":
            raise HTTPException(status_code=500, detail=result.get("message"))        
        route_names = result["optimized_route"]
        full_route_objects = []
        
        full_route_objects.append({"name": route_names[0], "status": "completed"})
        
        for name in route_names[1:]:
            matching_loc = next(
                (loc for loc in locations_list if loc["name"].lower() == name.lower()), 
                None
            )
            if matching_loc:
                full_route_objects.append({
                    **matching_loc,
                    # "eta": result["full_log"],
                    "status": "pending"
                })
        
        # Update global state
        CURRENT_STATE["active_route"] = full_route_objects
        CURRENT_STATE["is_active"] = True
        CURRENT_STATE["last_updated"] = datetime.now().isoformat()
        CURRENT_STATE["driver_name"] = manifest.driver_name
        
        return {
            "status": "success",
            "message": f"Manifest created for {manifest.driver_name}",
            "route": {
                "optimized_sequence": route_names,
                "total_distance_km": result.get("total_distance_km"),
                "total_duration_hours": result.get("total_duration_hours"),
                "weather_alerts": result.get("weather_alerts", [])
            },
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
        response = run_logistics_chat(message.message)
        
        return {
            "status": "success",
            "user_message": message.message,
            "agent_response": response,
            "session_id": message.session_id,
            "timestamp": datetime.now().isoformat(),
            "active_route": CURRENT_STATE["is_active"]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent error: {str(e)}")

@app.get("/agent/status")
async def get_agent_status():
    """Get current route status from agent state"""
    if not CURRENT_STATE["is_active"]:
        return {
            "status": "no_active_route",
            "message": "No active delivery route. Create a manifest first.",
            "active": False
        }
    
    pending_stops = [
        stop for stop in CURRENT_STATE["active_route"] 
        if stop["status"] == "pending"
    ]
    
    completed_stops = [
        stop for stop in CURRENT_STATE["active_route"] 
        if stop["status"] == "completed"
    ]
    
    return {
        "status": "active",
        "active": True,
        "driver": CURRENT_STATE.get("driver_name", "Unknown"),
        "last_updated": CURRENT_STATE["last_updated"],
        "route_summary": {
            "total_stops": len(CURRENT_STATE["active_route"]),
            "completed": len(completed_stops),
            "pending": len(pending_stops),
            "progress_percentage": round(
                (len(completed_stops) / len(CURRENT_STATE["active_route"])) * 100, 2
            ) if CURRENT_STATE["active_route"] else 0
        },
        "current_location": completed_stops[-1]["name"] if completed_stops else CURRENT_STATE["active_route"][0]["name"],
        "next_stop": pending_stops[0]["name"] if pending_stops else "Route Complete",
        "pending_stops": [stop["name"] for stop in pending_stops],
        "completed_stops": [stop["name"] for stop in completed_stops]
    }

@app.post("/agent/report-delay")
async def report_delay(delay: DelayReport):
    """Report a delay and get agent recommendation"""
    if not CURRENT_STATE["is_active"]:
        raise HTTPException(
            status_code=404,
            detail="No active route. Create a manifest first."
        )
    
    # Use agent to process the delay
    message = f"I'm delayed by {delay.delay_minutes} minutes due to {delay.reason}"
    if delay.location:
        message += f" at {delay.location}"
    
    agent_response = run_logistics_chat(message)
    
    return {
        "status": "success",
        "delay_recorded": {
            "minutes": delay.delay_minutes,
            "reason": delay.reason,
            "location": delay.location,
            "timestamp": datetime.now().isoformat()
        },
        "agent_recommendation": agent_response
    }

@app.post("/agent/check-traffic")
async def check_traffic_status():
    """Check real-time traffic for active route"""
    if not CURRENT_STATE["is_active"]:
        raise HTTPException(
            status_code=404,
            detail="No active route. Create a manifest first."
        )
    
    # Use agent's traffic checking tool
    agent_response = run_logistics_chat("Check traffic conditions for my route")
    
    return {
        "status": "success",
        "traffic_check": agent_response,
        "timestamp": datetime.now().isoformat()
    }

# TRAFFIC & MONITORING ENDPOINTS
@app.get("/traffic/map")
async def get_traffic_map():
    """Generate and return traffic visualization map"""
    if not CURRENT_STATE["is_active"]:
        raise HTTPException(
            status_code=404,
            detail="No active route to visualize. Create a manifest first."
        )
    
    try:
        locations = CURRENT_STATE["active_route"]
        result = generate_traffic_map(locations, route_sequence=locations)
        
        return {
            "status": "success",
            "map_file": result["map_file"],
            "congestion_status": result["congestion_status"],
            "details": result["details"],
            "download_url": f"/traffic/download-map"
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
