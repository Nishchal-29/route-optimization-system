import os
import requests
import random
import math
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()
ORS_API = os.getenv("ORS_API_KEY")
WEATHER_API = os.getenv("WEATHER_API") 

# CONFIGURATION
POPULATION_SIZE = 60
GENERATIONS = 150
MUTATION_RATE = 0.20

ALPHA = 1.0  # Distance Weight
BETA  = 1.5  # Time Weight (Time is money, and we might wait for weather)
SEQUENCE_PENALTY = 1e6  # Massive penalty for breaking user order

# DATA FETCHING: MATRIX & WEATHER
def get_distance_matrix(locations):
    """
    Fetches Distance and Duration matrices from OpenRouteService.
    locations: List of dicts [{'lat': x, 'lon': y}, ...]
    """
    coords = [[loc['lon'], loc['lat']] for loc in locations]
    
    url = "https://api.openrouteservice.org/v2/matrix/driving-car"
    headers = {
        "Authorization": ORS_API,
        "Content-Type": "application/json"
    }
    body = {
        "locations": coords,
        "metrics": ["distance", "duration"]
    }

    try:
        response = requests.post(url, json=body, headers=headers)
        response.raise_for_status()
        data = response.json()
        return data["distances"], data["durations"]
    except Exception as e:
        print(f"[route.py] Matrix API Error: {e}")
        return [], []

def fetch_weather_forecasts(locations):
    """
    Fetches 5-day/3-hour forecast for all unique locations.
    Returns a dict: { city_index: [forecast_entries] }
    """
    forecasts = {}
    print("[route.py] Fetching weather data for all stops...")
    
    for idx, loc in enumerate(locations):
        try:
            url = "https://api.openweathermap.org/data/2.5/forecast"
            params = {
                "lat": loc['lat'],
                "lon": loc['lon'],
                "appid": WEATHER_API,
                "units": "metric"
            }
            res = requests.get(url, params=params).json()
            
            if "list" in res:
                forecasts[idx] = res["list"]
        except Exception as e:
            print(f"[route.py] Weather API Error for {loc.get('name', idx)}: {e}")
            forecasts[idx] = []
            
    return forecasts

def check_weather_at_time(forecast_list, target_datetime):
    """
    Checks specific weather conditions for a given time.
    Returns: (should_wait_bool, wait_seconds, reason_str)
    """
    if not forecast_list:
        return False, 0, ""

    # 1. Find the best matching forecast slot
    relevant_entry = None
    min_diff = float('inf')

    for entry in forecast_list:
        dt_txt = entry["dt_txt"] # e.g. "2025-12-17 15:00:00"
        forecast_time = datetime.strptime(dt_txt, "%Y-%m-%d %H:%M:%S")
        
        # Calculate time difference
        diff = abs((forecast_time - target_datetime).total_seconds())
        
        if diff < min_diff:
            min_diff = diff
            relevant_entry = entry

    if not relevant_entry or min_diff > 10800: 
        return False, 0, ""
    
    rain_vol = relevant_entry.get("rain", {}).get("3h", 0) or 0
    wind_speed = relevant_entry.get("wind", {}).get("speed", 0) or 0
    visibility = relevant_entry.get("visibility", 10000) or 10000 # Default 10km (clear)
    
    reasons = []
    
    # Threshold: Moderate/Heavy Rain (> 5mm per 3 hours) causes hydroplaning risk
    if rain_vol > 5.0: 
        reasons.append(f"Heavy Rain ({rain_vol}mm)")

    # Threshold: High Wind (> 15 m/s or ~54 km/h) risks toppling high-profile trucks
    if wind_speed > 15.0: 
        reasons.append(f"Gale Winds ({wind_speed}m/s)")
        
    # Threshold: Low Visibility (< 500m) is dangerous for highway driving
    if visibility < 1000:
        reasons.append(f"Fog/Low Visibility ({visibility}m)")

    if reasons:
        # Production Logic: If dangerous, wait 2 hours for conditions to improve
        return True, 7200, ", ".join(reasons)
    
    return False, 0, ""

# GENETIC ALGORITHM CORE
def calculate_route_metrics(route, dist_matrix, dur_matrix, forecasts, start_time):
    """
    Calculates Distance, Duration (including Waits), and generates a Travel Log.
    """
    total_dist = 0
    total_duration = 0
    current_time = start_time
    
    travel_log = [] 
    
    travel_log.append({
        "city_idx": route[0],
        "event": "Depart",
        "time": current_time,
        "note": "Trip Start"
    })

    for i in range(len(route) - 1):
        u = route[i]
        v = route[i+1]
        
        # 1. Travel
        leg_dist = dist_matrix[u][v]
        leg_time = dur_matrix[u][v]
        
        total_dist += leg_dist
        total_duration += leg_time
        current_time += timedelta(seconds=leg_time)
        
        # 2. Check Weather at Arrival (City V)
        should_wait, wait_sec, reason = check_weather_at_time(forecasts.get(v, []), current_time)
        
        if should_wait:
            total_duration += wait_sec
            wait_end_time = current_time + timedelta(seconds=wait_sec)
            
            travel_log.append({
                "city_idx": v,
                "event": "Weather Wait",
                "time": current_time,
                "duration_sec": wait_sec,
                "note": f"Waiting for {reason}"
            })
            
            current_time = wait_end_time 

        # Arrival Log
        travel_log.append({
            "city_idx": v,
            "event": "Arrive",
            "time": current_time,
            "note": "Stop reached"
        })

    return total_dist, total_duration, travel_log

def check_sequence_violations(route, constraints):
    """
    Ensures user's requested order is respected.
    """
    violations = 0
    # Map index in original list -> required sequence number
    seq_map = {i: meta.get('visit_sequence', 2) for i, meta in enumerate(constraints)}
    
    # Check every pair
    for i in range(len(route)):
        for j in range(i + 1, len(route)):
            idx_a = route[i]
            idx_b = route[j]
            
            seq_a = seq_map.get(idx_a, 2)
            seq_b = seq_map.get(idx_b, 2)
            
            # If A is strictly higher sequence than B, but A comes first -> Violation
            if seq_a > seq_b:
                violations += 1
    return violations

def cost_function(route, dist_matrix, dur_matrix, forecasts, constraints, start_time):
    # Calculate physical metrics (including weather waits)
    dist, time_with_waits, _ = calculate_route_metrics(route, dist_matrix, dur_matrix, forecasts, start_time)
    
    # Calculate constraints
    seq_violations = check_sequence_violations(route, constraints)
    
    # Total Cost
    # Note: We penalize time heavily so it avoids waiting unless distance detour is huge
    cost = (ALPHA * dist) + (BETA * time_with_waits) + (seq_violations * SEQUENCE_PENALTY)
    return cost

# GA HELPERS
def create_initial_population(num_cities, source_index=0):
    population = []
    remaining = list(range(num_cities))
    remaining.remove(source_index)

    for _ in range(POPULATION_SIZE):
        random.shuffle(remaining)
        population.append([source_index] + remaining[:])
    return population

def tournament_selection(population, dist_mat, dur_mat, forecasts, constraints, start_time):
    selected = random.sample(population, 3)
    selected.sort(key=lambda r: cost_function(r, dist_mat, dur_mat, forecasts, constraints, start_time))
    return selected[0]

def crossover(parent1, parent2):
    # Order Crossover (OX1) to preserve cities
    p1 = parent1[1:]
    p2 = parent2[1:]
    n = len(p1)
    a, b = sorted(random.sample(range(n), 2))
    
    child_p = [None] * n
    child_p[a:b] = p1[a:b]
    
    idx = b
    for item in p2:
        if item not in child_p:
            if idx >= n: idx = 0
            child_p[idx] = item
            idx += 1
            
    return [parent1[0]] + child_p

def mutate(route):
    if random.random() < MUTATION_RATE:
        idx_range = range(1, len(route))
        if len(idx_range) >= 2:
            a, b = random.sample(idx_range, 2)
            route[a], route[b] = route[b], route[a]
    return route

# Main GA route optimization function
def solve_route(locations_data):
    """
    Main function called by the Agent.
    locations_data: List of dicts [{'name', 'lat', 'lon', 'visit_sequence'}]
    """
    if not locations_data or len(locations_data) < 2:
        return {"status": "error", "message": "Need at least 2 locations."}

    # 1. Fetch Static Data
    dist_matrix, dur_matrix = get_distance_matrix(locations_data)
    if not dist_matrix:
        return {"status": "error", "message": "Failed to fetch Matrix API."}

    forecasts = fetch_weather_forecasts(locations_data)
    
    # 2. Setup GA
    start_time = datetime.now()
    population = create_initial_population(len(locations_data))
    
    global_best = None
    global_best_cost = float('inf')

    # 3. Evolution Loop
    for gen in range(GENERATIONS):
        new_pop = []
        
        # Elitism
        population.sort(key=lambda r: cost_function(r, dist_matrix, dur_matrix, forecasts, locations_data, start_time))
        new_pop.extend(population[:2])
        
        while len(new_pop) < POPULATION_SIZE:
            p1 = tournament_selection(population, dist_matrix, dur_matrix, forecasts, locations_data, start_time)
            p2 = tournament_selection(population, dist_matrix, dur_matrix, forecasts, locations_data, start_time)
            child = mutate(crossover(p1, p2))
            new_pop.append(child)
            
        population = new_pop
        
        # Track Best
        curr_best = population[0]
        curr_cost = cost_function(curr_best, dist_matrix, dur_matrix, forecasts, locations_data, start_time)
        if curr_cost < global_best_cost:
            global_best = curr_best
            global_best_cost = curr_cost

    # 4. Final Calculation & Formatting
    final_dist, final_sec, travel_log = calculate_route_metrics(
        global_best, dist_matrix, dur_matrix, forecasts, start_time
    )
    
    # Format the route for the Agent
    optimized_route_names = []
    weather_alerts = []
    
    for event in travel_log:
        city_name = locations_data[event['city_idx']]['name']
        
        if event['event'] == 'Weather Wait':
            weather_alerts.append(f"Wait at {city_name} for {int(event['duration_sec']/3600)}h due to {event['note']}")
        
        if event['event'] == 'Arrive':
             # Only add unique cities to the list path
            if not optimized_route_names or optimized_route_names[-1] != city_name:
                optimized_route_names.append(city_name)
    
    # Insert Source at start if missing
    source_name = locations_data[global_best[0]]['name']
    if optimized_route_names[0] != source_name:
        optimized_route_names.insert(0, source_name)

    return {
        "status": "success",
        "total_distance_km": round(final_dist / 1000, 2),
        "total_duration_hours": round(final_sec / 3600, 2),
        "optimized_route": optimized_route_names,
        "weather_alerts": weather_alerts,
        "full_log": travel_log  
    }