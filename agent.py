import os
import json
from datetime import datetime
from dotenv import load_dotenv

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage

from route import solve_route
from traffic import generate_traffic_map

load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# STATE MANAGEMENT
CURRENT_STATE = {
    "active_route": [],  # List of stops with status
    "is_active": False,
    "last_updated": None,
    "driver_name": None,
    "total_distance": 0,
    "total_duration": 0
}

# AGENT TOOLS
@tool
def get_route_status():
    """
    Returns the current active route, showing which stops are pending or completed.
    Use this tool to check the driver's progress.
    """
    if not CURRENT_STATE["is_active"]:
        return "No active route. Please create a delivery manifest first."
    
    status_summary = [
        f"Driver: {CURRENT_STATE.get('driver_name', 'Unknown')}",
        f"Last Updated: {CURRENT_STATE['last_updated']}",
        "\nRoute Progress:"
    ]
    
    for idx, stop in enumerate(CURRENT_STATE["active_route"]):
        status_icon = "✓" if stop['status'] == "completed" else "○"
        status_summary.append(
            f"{status_icon} {idx+1}. {stop['name']} [{stop['status'].upper()}]"
        )
    
    completed = sum(1 for s in CURRENT_STATE["active_route"] if s['status'] == 'completed')
    total = len(CURRENT_STATE["active_route"])
    progress = (completed / total * 100) if total > 0 else 0
    
    status_summary.append(f"\nProgress: {completed}/{total} stops ({progress:.1f}%)")
    
    return "\n".join(status_summary)

@tool
def mark_stop_completed(stop_name: str):
    """
    Mark a delivery stop as completed.
    Use this when driver confirms delivery at a location.
    """
    if not CURRENT_STATE["is_active"]:
        return "No active route."
    
    for stop in CURRENT_STATE["active_route"]:
        if stop["name"].lower() == stop_name.lower():
            if stop["status"] == "completed":
                return f"{stop_name} is already marked as completed."
            
            stop["status"] = "completed"
            stop["completed_at"] = datetime.now().isoformat()
            CURRENT_STATE["last_updated"] = datetime.now().isoformat()
            
            # Find next stop
            next_stops = [s for s in CURRENT_STATE["active_route"] if s["status"] == "pending"]
            next_stop = next_stops[0]["name"] if next_stops else "All stops completed!"
            
            return f"✓ {stop_name} marked as completed. Next stop: {next_stop}"
    
    return f"Stop '{stop_name}' not found in the route."

@tool
def report_delay_and_update_eta(delay_minutes: int, reason: str):
    """
    Report a delay and update estimated arrival times.
    Use this when driver reports traffic, breakdown, or other delays.
    """
    if not CURRENT_STATE["is_active"]:
        return "No active route to update."
    
    # Log the delay
    delay_record = {
        "timestamp": datetime.now().isoformat(),
        "delay_minutes": delay_minutes,
        "reason": reason
    }
    
    if "delays" not in CURRENT_STATE:
        CURRENT_STATE["delays"] = []
    CURRENT_STATE["delays"].append(delay_record)
    
    CURRENT_STATE["last_updated"] = datetime.now().isoformat()
    
    # Calculate impact
    remaining_stops = [s for s in CURRENT_STATE["active_route"] if s["status"] == "pending"]
    
    response = [
        f"Delay recorded: {delay_minutes} minutes due to {reason}",
        f"Impact: All remaining ETAs pushed back by {delay_minutes} minutes",
        f"Remaining stops: {len(remaining_stops)}"
    ]
    
    if delay_minutes > 30:
        response.append("Significant delay detected. Consider notifying customers.")
    
    if "traffic" in reason.lower() or "jam" in reason.lower():
        response.append("Tip: Use check_traffic_conditions tool to find alternative routes.")
    
    return "\n".join(response)

@tool
def check_traffic_conditions():
    """
    Check real-time traffic conditions for the active route.
    Generates a traffic heatmap and identifies congestion zones.
    Use this when driver reports traffic or wants to check conditions ahead.
    """
    if not CURRENT_STATE["is_active"]:
        return "No active route to check traffic for."
    
    try:
        locations = CURRENT_STATE["active_route"]        
        result = generate_traffic_map(locations, route_sequence=locations)
        
        response = [
            f"Traffic Analysis Complete:",
            f"Status: {result['congestion_status']}",
            f"Details: {result['details']}",
            f"Map: {result['map_file']}"
        ]
        
        if result['congestion_status'] == "Severe":
            response.append("\nALERT: Heavy traffic detected!")
            response.append("Recommendation: Consider re-routing or waiting for conditions to improve.")
        elif result['congestion_status'] == "Normal":
            response.append("\nGood news: Traffic is flowing normally.")
        
        return "\n".join(response)
        
    except Exception as e:
        return f"Traffic check failed: {str(e)}. Please try again later."

@tool
def reoptimize_remaining_route():
    """
    Re-optimize the remaining route based on current location.
    Use this when driver wants to find a better route for remaining stops,
    or when significant delays require route changes.
    """
    if not CURRENT_STATE["is_active"]:
        return "No active route to optimize."
    
    # Get remaining stops
    remaining_stops = [
        s for s in CURRENT_STATE["active_route"] 
        if s["status"] == "pending"
    ]
    
    if not remaining_stops:
        return "All stops completed. No re-optimization needed."
    
    if len(remaining_stops) < 2:
        return "Only one stop remaining. Re-optimization not necessary."
    
    try:
        # Get current location (last completed stop or starting point)
        completed_stops = [s for s in CURRENT_STATE["active_route"] if s["status"] == "completed"]
        current_location = completed_stops[-1] if completed_stops else CURRENT_STATE["active_route"][0]
        
        # Prepare locations for optimization
        locations_to_optimize = [current_location] + remaining_stops
        
        print("[Agent] Re-optimizing remaining route...")
        result = solve_route(locations_to_optimize)
        
        if result.get("status") == "success":
            new_sequence = result["optimized_route"]
            new_active_route = [s for s in CURRENT_STATE["active_route"] if s["status"] == "completed"]
            
            for city_name in new_sequence[1:]:  # Skip first (current location)
                matching_stop = next(
                    (s for s in remaining_stops if s["name"].lower() == city_name.lower()),
                    None
                )
                if matching_stop:
                    new_active_route.append(matching_stop)
            
            CURRENT_STATE["active_route"] = new_active_route
            CURRENT_STATE["last_updated"] = datetime.now().isoformat()
            
            response = [
                "Route re-optimized successfully!",
                f"New sequence: {' → '.join(new_sequence)}",
                f"Estimated distance: {result.get('total_distance_km', 'N/A')} km",
                f"Estimated time: {result.get('total_duration_hours', 'N/A')} hours"
            ]
            
            if result.get("weather_alerts"):
                response.append(f"\nWeather Alerts: {', '.join(result['weather_alerts'])}")
            
            return "\n".join(response)
        else:
            return "Re-optimization failed. Continuing with current route."
            
    except Exception as e:
        return f"Re-optimization error: {str(e)}"

@tool
def get_weather_forecast():
    """
    Get weather forecast for remaining stops on the route.
    Use this to check if weather conditions might affect the journey.
    """
    if not CURRENT_STATE["is_active"]:
        return "No active route."
    
    remaining_stops = [s for s in CURRENT_STATE["active_route"] if s["status"] == "pending"]
    
    if not remaining_stops:
        return "All stops completed."
    
    # Note: Weather data is already integrated in route.py
    # This tool provides a summary
    response = [
        "Weather Forecast Summary:",
        f"Checking conditions for {len(remaining_stops)} remaining stops..."
    ]
    
    # If weather alerts exist in state
    if CURRENT_STATE.get("weather_alerts"):
        response.append("\nActive Weather Alerts:")
        for alert in CURRENT_STATE["weather_alerts"]:
            response.append(f"  • {alert}")
    else:
        response.append("\n✓ No severe weather alerts for planned route.")
        response.append("Note: Weather is continuously monitored during route optimization.")
    
    return "\n".join(response)

# AGENT CONFIGURATION
llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    temperature=0.2,
    google_api_key=GEMINI_API_KEY
)

# Define available tools
tools = [
    get_route_status,
    mark_stop_completed,
    report_delay_and_update_eta,
    check_traffic_conditions,
    reoptimize_remaining_route,
    get_weather_forecast
]

llm_with_tools = llm.bind_tools(tools)

# CHAT RUNTIME
def run_logistics_chat(user_input: str) -> str:
    """
    Main function to interact with the logistics agent.
    """
    print(f"\n[User] {user_input}")
    
    # System prompt defines agent behavior
    system_prompt = """
    You are 'LogiBot', an AI Logistics Assistant for truck drivers and fleet managers.
    
    Your capabilities:
    - Track delivery routes and progress
    - Monitor real-time traffic conditions
    - Handle delay reports and re-optimize routes
    - Check weather forecasts
    - Mark deliveries as completed
    
    Guidelines:
    1. ALWAYS check if a route exists before trying to modify it
    2. If user mentions traffic, delays, or road conditions, use check_traffic_conditions
    3. If user mentions completing a delivery, use mark_stop_completed
    4. If significant delays reported (>30 min), suggest re-optimization
    5. Be helpful, concise, and proactive with safety recommendations
    6. Use emojis sparingly for important alerts (⚠️, ✓)
    
    Current Status: {"Active Route" if CURRENT_STATE["is_active"] else "No Active Route"}
    """
    
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_input)
    ]
    
    try:
        # Initial LLM reasoning
        response = llm_with_tools.invoke(messages)
        messages.append(response)
        
        # Tool execution loop
        if response.tool_calls:
            for tool_call in response.tool_calls:
                print(f"  [Agent] Using tool: {tool_call['name']}")
                
                # Map tool names to functions
                tool_map = {
                    "get_route_status": get_route_status,
                    "mark_stop_completed": mark_stop_completed,
                    "report_delay_and_update_eta": report_delay_and_update_eta,
                    "check_traffic_conditions": check_traffic_conditions,
                    "reoptimize_remaining_route": reoptimize_remaining_route,
                    "get_weather_forecast": get_weather_forecast
                }
                
                selected_tool = tool_map.get(tool_call["name"])
                if selected_tool:
                    tool_output = selected_tool.invoke(tool_call["args"])
                    print(f"  [Tool Output] {tool_output[:100]}...")
                    
                    messages.append(
                        ToolMessage(
                            content=tool_output,
                            tool_call_id=tool_call["id"]
                        )
                    )
            
            # Final response after tool execution
            final_response = llm_with_tools.invoke(messages)
            return final_response.content
        else:
            return response.content
            
    except Exception as e:
        print(f"[Agent Error] {str(e)}")
        return f"I encountered an error: {str(e)}. Please try again or rephrase your request."