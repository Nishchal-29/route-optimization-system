import os
import requests
import folium
from folium.plugins import HeatMap
from dotenv import load_dotenv
from typing import List, Dict, Tuple, Optional
import time

load_dotenv()
TOMTOM_API_KEY = os.getenv("TOMTOM_API_KEY")
TOMTOM_BASE_URL = "https://api.tomtom.com"
TOMTOM_TRAFFIC_FLOW_VERSION = "4"  

def get_route_bbox(locations: List[Dict]) -> Tuple[float, float, float, float]:
    """Calculate bounding box for a list of locations."""
    if not locations:
        return (0, 0, 0, 0)
    
    lats = [loc['lat'] for loc in locations]
    lons = [loc['lon'] for loc in locations]
    
    buffer = 0.1
    return (
        min(lons) - buffer,
        min(lats) - buffer,
        max(lons) + buffer,
        max(lats) + buffer
    )

def fetch_traffic_flow_segment(lat: float, lon: float, zoom: int = 10) -> Optional[Dict]:
    """Fetch traffic flow data for a specific point using TomTom Traffic Flow Segment Data."""    
    url = f"{TOMTOM_BASE_URL}/traffic/services/{TOMTOM_TRAFFIC_FLOW_VERSION}/flowSegmentData/relative/{zoom}/json"
    
    params = {
        "key": TOMTOM_API_KEY,
        "point": f"{lat},{lon}",
        "unit": "KMPH" 
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"[Traffic] TomTom API error for point ({lat}, {lon}): {e}")
        return None

def fetch_traffic_incidents(bbox: Tuple[float, float, float, float]) -> Optional[Dict]:
    """Fetch traffic incidents (accidents, road closures) in a bounding box."""
    min_lon, min_lat, max_lon, max_lat = bbox
    url = f"{TOMTOM_BASE_URL}/traffic/services/5/incidentDetails"
    
    params = {
        "key": TOMTOM_API_KEY,
        "bbox": f"{min_lon},{min_lat},{max_lon},{max_lat}",
        "fields": "{incidents{type,geometry{type,coordinates},properties{id,iconCategory,magnitudeOfDelay,events{description,code},startTime,endTime}}}",
        "language": "en-US"
    }
    
    try:
        response = requests.get(url, params=params, timeout=10) 
        # if response.status_code == 400:
        #     print(f"TomTom Detail: {response.text}")
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"[Traffic] TomTom Incidents API error: {e}")
        return None

def fetch_incidents_for_route_stops(locations: List[Dict], buffer: float = 0.4) -> Dict:
    """Fetches incidents specifically around each stop on the route."""
    all_combined_incidents = []
    seen_ids = set()
    for loc in locations:
        lat, lon = loc['lat'], loc['lon']
        stop_bbox = (
            lon - buffer, 
            lat - buffer, 
            lon + buffer, 
            lat + buffer  
        )
        
        data = fetch_traffic_incidents(stop_bbox)
        
        if data and 'incidents' in data:
            for incident in data['incidents']:
                incident_id = incident.get('properties', {}).get('id')
                if incident_id not in seen_ids:
                    all_combined_incidents.append(incident)
                    seen_ids.add(incident_id)
        
        time.sleep(0.2)

    return {"incidents": all_combined_incidents}

def analyze_traffic_flow(flow_data: Dict) -> Dict:
    if not flow_data or 'flowSegmentData' not in flow_data:
        return {"congestion_level": "unknown", "coordinates": []}

    segment = flow_data['flowSegmentData']
    current_speed = segment.get('currentSpeed', 0)
    current_travel_time = segment.get('currentTravelTime', 0)
    free_flow_speed = segment.get('freeFlowSpeed', 50)
    free_flow_travel_time = segment.get('freeFlowTravelTime', 0)
    raw_coords = segment.get('coordinates', {}).get('coordinate', [])
    road_coords = [[pt['latitude'], pt['longitude']] for pt in raw_coords]
    
    if free_flow_travel_time > 0: 
        delay_factor = current_travel_time / free_flow_travel_time 
    elif free_flow_speed > 0: 
        delay_factor = free_flow_speed / max(current_speed, 1) 
    else: 
        delay_factor = 0

    speed_ratio = current_speed / max(free_flow_speed, 1)

    if speed_ratio >= 0.8:
        color = "green"
        congestion = "free_flow"
    elif speed_ratio >= 0.6:
        color = "yellow"
        congestion = "light"
    elif speed_ratio >= 0.4:
        color = "orange"
        congestion = "moderate"
    elif speed_ratio >= 0.2:
        color = "red"
        congestion = "heavy"
    else:
        color = "darkred"
        congestion = "severe"

    return {
        "congestion_level": congestion,
        "color": color,
        "current_speed": current_speed,
        "free_flow_speed": free_flow_speed,
        "speed_ratio": speed_ratio,
        "delay_factor": delay_factor,
        "coordinates": road_coords
    }

def collect_traffic_data_for_route(locations: List[Dict]) -> Tuple[List, Dict]:
    """Collect traffic data for all segments in a route."""
    heatmap_data = []
    segment_analyses = []
    total_delays = 0
    severe_segments = 0    
    for i, location in enumerate(locations):
        flow_data = fetch_traffic_flow_segment(location['lat'], location['lon'])
        
        if flow_data:
            analysis = analyze_traffic_flow(flow_data)
            intensity = 1 - analysis['speed_ratio']
            heatmap_data.append([
                location['lat'],
                location['lon'],
                intensity
            ])
            
            if analysis['congestion_level'] in ['heavy', 'severe']:
                severe_segments += 1
            
            total_delays += analysis['delay_factor']
            
            segment_analyses.append({
                "location": location['name'],
                "congestion": analysis['congestion_level'],
                "current_speed": analysis['current_speed'],
                "delay_factor": round(analysis['delay_factor'], 2)
            })
        
        time.sleep(0.2)
    
    avg_delay = total_delays / len(locations) if locations else 0
    
    if severe_segments > len(locations) * 0.3:
        overall_status = "Severe"
    elif severe_segments > len(locations) * 0.15:
        overall_status = "Moderate"
    else:
        overall_status = "Normal"
    
    analysis_summary = {
        "overall_status": overall_status,
        "total_segments": len(locations),
        "severe_segments": severe_segments,
        "average_delay_factor": round(avg_delay, 2),
        "segment_details": segment_analyses
    }
    
    return heatmap_data, analysis_summary

def draw_local_road_traffic(m, center_lat, center_lon, radius_km=1.2):
    """Draws traffic road segments around a point using TomTom Flow API"""
    steps = 4
    offset = radius_km / 111.0

    lat_points = [
        center_lat - offset + i * (2 * offset / steps)
        for i in range(steps + 1)
    ]
    lon_points = [
        center_lon - offset + i * (2 * offset / steps)
        for i in range(steps + 1)
    ]

    seen_segments = set()

    for lat in lat_points:
        for lon in lon_points:
            data = fetch_traffic_flow_segment(lat, lon)
            if not data:
                continue

            analysis = analyze_traffic_flow(data)
            coords = analysis["coordinates"]
            if len(coords) < 2:
                continue

            segment_id = str(coords[0])
            if segment_id in seen_segments:
                continue

            folium.PolyLine(
                locations=coords,
                color=analysis["color"],
                weight=6,
                opacity=0.9,
                tooltip=f"{analysis['current_speed']} km/h"
            ).add_to(m)

            seen_segments.add(segment_id)

            time.sleep(0.2)

def generate_traffic_map(locations: List[Dict], route_sequence: Optional[List[Dict]] = None) -> Dict:
    """Generate an interactive HTML map with traffic conditions."""
    if not locations:
        return {
            "map_file": None,
            "congestion_status": "unknown",
            "details": "No locations provided"
        }
        
    avg_lat = sum(loc['lat'] for loc in locations) / len(locations)
    avg_lon = sum(loc['lon'] for loc in locations) / len(locations)
    bbox = get_route_bbox(locations)
    
    heatmap_data, analysis_summary = collect_traffic_data_for_route(locations)
    incidents_data = fetch_incidents_for_route_stops(locations, buffer=0.4)    
    
    m = folium.Map(
        location=[avg_lat, avg_lon],
        zoom_start=10,
        tiles='CartoDB dark_matter'
    )
    
    for loc in locations:
        draw_local_road_traffic(
            m,
            loc["lat"],
            loc["lon"],
            radius_km=1.2
        )
    
    if heatmap_data:
        HeatMap(
            heatmap_data,
            min_opacity=0.3,
            max_opacity=0.8,
            radius=15,
            blur=20,
            gradient={
                0.0: 'green',    # Free flow
                0.25: 'yellow',  # Light traffic
                0.5: 'orange',   # Moderate traffic
                0.75: 'red',     # Heavy traffic
                1.0: 'darkred'   # Severe congestion
            }
        ).add_to(m)
    
    for i, loc in enumerate(locations):
        if i < len(analysis_summary['segment_details']):
            segment = analysis_summary['segment_details'][i]
            congestion = segment['congestion']
            
            if congestion in ['severe', 'heavy']:
                marker_color = 'red'
                icon = 'exclamation-triangle'
            elif congestion == 'moderate':
                marker_color = 'orange'
                icon = 'exclamation-circle'
            else:
                marker_color = 'green'
                icon = 'check-circle'
            
            popup_html = f"""
            <div style='min-width: 200px'>
                <h4><b>{loc['name']}</b></h4>
                <p><b>Status:</b> {congestion.upper()}</p>
                <p><b>Current Speed:</b> {segment['current_speed']} km/h</p>
                <p><b>Delay Factor:</b> {segment['delay_factor']}x</p>
            </div>
            """
        else:
            marker_color = 'blue'
            icon = 'info-sign'
            popup_html = f"<b>{loc['name']}</b><br>Stop #{i+1}"
        
        folium.Marker(
            location=[loc['lat'], loc['lon']],
            popup=folium.Popup(popup_html, max_width=250),
            icon=folium.Icon(
                color=marker_color,
                icon=icon,
                prefix='fa'
            ),
            tooltip=f"{i+1}. {loc['name']}"
        ).add_to(m)
    
    if route_sequence:
        points = [[loc['lat'], loc['lon']] for loc in route_sequence]
        folium.PolyLine(
            points,
            color='white',
            weight=2,
            opacity=0.4,
            dash_array='5, 10',
            popup='Planned Route'
        ).add_to(m)
    
    if incidents_data and 'incidents' in incidents_data:
        incident_count = 0
        for incident in incidents_data['incidents']:
            try:
                props = incident.get('properties', {})
                geometry = incident.get('geometry', {})
                
                if geometry.get('type') == 'Point':
                    coords = geometry.get('coordinates', [])
                    if len(coords) >= 2:
                        incident_lat, incident_lon = coords[1], coords[0]                        
                        icon_category = props.get('iconCategory', 0)
                        magnitude = props.get('magnitudeOfDelay', 0)
                        
                        if icon_category in [1, 2, 3]:  # Accident
                            icon = 'car-crash'
                            color = 'red'
                        elif icon_category in [4, 5]:  # Road closure
                            icon = 'ban'
                            color = 'darkred'
                        else:
                            icon = 'exclamation'
                            color = 'orange'
                        
                        events = props.get('events', [])
                        description = events[0].get('description', 'Traffic incident') if events else 'Traffic incident'
                        
                        folium.Marker(
                            location=[incident_lat, incident_lon],
                            popup=f"<b>INCIDENT</b><br>{description}<br>Delay: {magnitude} min",
                            icon=folium.Icon(color=color, icon=icon, prefix='fa'),
                            tooltip="Traffic Incident"
                        ).add_to(m)
                        
                        incident_count += 1
            except Exception as e:
                print(f"[Traffic] Error processing incident: {e}")
                continue        
    
    legend_html = '''
    <div style="position: fixed; 
                bottom: 50px; left: 50px; width: 220px; height: auto; 
                background-color: white; z-index:9999; font-size:14px;
                border:2px solid grey; border-radius: 5px; padding: 10px">
        <p style="margin:0; font-weight:bold; text-align:center">Traffic Status Legend</p>
        <hr style="margin: 5px 0">
        <p style="margin:3px 0"><span style="color:green">●</span> Free Flow / Light</p>
        <p style="margin:3px 0"><span style="color:orange">●</span> Moderate Traffic</p>
        <p style="margin:3px 0"><span style="color:red">●</span> Heavy Congestion</p>
        <p style="margin:3px 0"><span style="color:darkred">●</span> Severe / Blocked</p>
        <hr style="margin: 5px 0">
        <p style="margin:0; font-size:11px; color:grey">Data: TomTom Traffic API</p>
    </div>
    '''
    m.get_root().html.add_child(folium.Element(legend_html))
    
    output_file = "traffic_map.html"
    m.save(output_file)
    
    print(f"[Traffic] Map saved to {output_file}")
    
    return {
        "map_file": output_file,
        "congestion_status": analysis_summary['overall_status'],
        "details": f"Generated map with {len(heatmap_data)} traffic data points. "
                  f"{analysis_summary['severe_segments']}/{analysis_summary['total_segments']} segments with heavy traffic.",
        "analysis": analysis_summary
    }

def check_traffic_for_segment(start_loc: Dict, end_loc: Dict) -> Dict:
    """Check traffic conditions for a specific route segment."""
    mid_lat = (start_loc['lat'] + end_loc['lat']) / 2
    mid_lon = (start_loc['lon'] + end_loc['lon']) / 2
    
    flow_data = fetch_traffic_flow_segment(mid_lat, mid_lon)
    
    if not flow_data:
        return {
            "status": "unknown",
            "message": "Could not fetch traffic data",
            "from": start_loc['name'],
            "to": end_loc['name']
        }
    
    analysis = analyze_traffic_flow(flow_data)
    
    return {
        "status": "success",
        "from": start_loc['name'],
        "to": end_loc['name'],
        "congestion_level": analysis['congestion_level'],
        "current_speed": analysis['current_speed'],
        "free_flow_speed": analysis['free_flow_speed'],
        "delay_factor": analysis['delay_factor'],
        "recommendation": get_traffic_recommendation(analysis)
    }

def get_traffic_recommendation(analysis: Dict) -> str:
    """Generate traffic recommendation based on analysis."""
    congestion = analysis['congestion_level']
    delay_factor = analysis['delay_factor']
    
    if congestion == 'severe':
        return "Severe congestion. Consider alternative route or wait for conditions to improve."
    elif congestion == 'heavy':
        return f"Heavy traffic. Expected delay: {int((delay_factor - 1) * 60)} minutes. Alternative route recommended."
    elif congestion == 'moderate':
        return f"Moderate traffic. Minor delays expected (~{int((delay_factor - 1) * 30)} min). Proceed with caution."
    elif congestion == 'light':
        return "Light traffic. Proceed as planned."
    else:
        return "Clear roads. Good driving conditions."