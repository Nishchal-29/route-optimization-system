import os
from datetime import datetime, timedelta
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()
url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(url, key)

def get_session_state(session_id: str):
    """Fetches the active route for a specific session."""
    response = supabase.table("active_routes") \
        .select("*") \
        .eq("session_id", session_id) \
        .eq("status", "active") \
        .order("created_at", desc=True) \
        .limit(1) \
        .execute()
    
    if not response.data:
        return {"is_active": False, "active_route": []}
    
    route_data = response.data[0]
    route_id = route_data["id"]
    
    stops_response = supabase.table("stops") \
        .select("*") \
        .eq("route_id", route_id) \
        .order("visit_sequence") \
        .execute()
        
    return {
        "is_active": True,
        "route_id": route_id,
        "driver_name": route_data.get("driver_name"),
        "active_route": stops_response.data,
        "last_updated": route_data.get("last_updated")
    }

def create_new_route_db(session_id: str, driver_name: str, stops_data: list, status: str = "draft"):
    """Creates a new route in the DB."""
    route_res = supabase.table("active_routes").insert({
        "session_id": session_id,
        "driver_name": driver_name,
        "status": status,
        "last_updated": datetime.now().isoformat()
    }).execute()
    route_id = route_res.data[0]["id"]
    
    formatted_stops = []
    for stop in stops_data:
        formatted_stops.append({
            "route_id": route_id,
            "name": stop["name"],
            "lat": stop["lat"],
            "lon": stop["lon"],
            "visit_sequence": stop.get("visit_sequence", 0),
            "status": stop.get("status", "pending"),
            "eta": stop.get("eta")
        })
        
    supabase.table("stops").insert(formatted_stops).execute()
    return route_id

def mark_stop_complete_db(stop_id: int):
    """Updates stop status to completed"""
    supabase.table("stops").update({
        "status": "completed",
        "completed_at": datetime.now().isoformat()
    }).eq("id", stop_id).execute()
    
def activate_route_db(route_id: int, driver_name: str):
    """
    Flips a route from 'draft' to 'active'.
    """
    res = supabase.table("active_routes").update({
        "status": "active",
        "driver_name": driver_name,
        "last_updated": datetime.now().isoformat()
    }).eq("id", route_id).execute()
    
    if not res.data:
        return None
    
    return res.data

def update_etas_db(route_id: int, delay_minutes: int):
    """
    Fetches pending stops for a route and adds the delay to their existing ETAs.
    """
    response = supabase.table("stops") \
        .select("*") \
        .eq("route_id", route_id) \
        .eq("status", "pending") \
        .execute()
    
    updated_count = 0
    for stop in response.data:
        if stop.get("eta"):
            try:
                current_eta = datetime.fromisoformat(stop["eta"])
                new_eta = current_eta + timedelta(minutes=delay_minutes)                
                supabase.table("stops").update({
                    "eta": new_eta.isoformat()
                }).eq("id", stop["id"]).execute()
                
                updated_count += 1
            except ValueError:
                continue 

    return updated_count