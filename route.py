import os
import requests
import random
from datetime import datetime, timedelta
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor, as_completed

load_dotenv()
ORS_API = os.getenv("ORS_API_KEY")
WEATHER_API = os.getenv("WEATHER_API")

# CONFIGURATION
POPULATION_SIZE = 60
GENERATIONS = 150
MUTATION_RATE = 0.20
ALPHA = 1.0
BETA = 1.5
SEQUENCE_PENALTY = 1000000

# DISTANCE MATRIX
def get_distance_matrix(locations):
    coords = [[loc['lon'], loc['lat']] for loc in locations]
    url = "https://api.openrouteservice.org/v2/matrix/driving-car"
    headers = {"Authorization": ORS_API, "Content-Type": "application/json"}
    body = {"locations": coords, "metrics": ["distance", "duration"]}

    try:
        r = requests.post(url, json=body, headers=headers, timeout=15)
        r.raise_for_status()
        data = r.json()
        return data["distances"], data["durations"]
    except Exception as e:
        print(f"[route.py] Matrix API Error: {e}")
        return [], []

# WEATHER FETCH (THREADED)
def _fetch_weather(idx, loc):
    try:
        url = "https://api.openweathermap.org/data/2.5/forecast"
        params = {
            "lat": loc["lat"],
            "lon": loc["lon"],
            "appid": WEATHER_API,
            "units": "metric"
        }
        r = requests.get(url, params=params, timeout=10).json()
        entries = r.get("list", [])
        for e in entries:
            e["_dt"] = datetime.strptime(e["dt_txt"], "%Y-%m-%d %H:%M:%S")
        return idx, entries
    except:
        return idx, []

def fetch_weather_forecasts(locations):
    forecasts = {}
    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = [pool.submit(_fetch_weather, i, loc) for i, loc in enumerate(locations)]
        for f in as_completed(futures):
            idx, data = f.result()
            forecasts[idx] = data
    return forecasts

# WEATHER CHECK
def check_weather_at_time(forecast_list, target_datetime):
    if not forecast_list:
        return False, 0, ""

    best = None
    min_diff = float("inf")

    for e in forecast_list:
        diff = abs((e["_dt"] - target_datetime).total_seconds())
        if diff < min_diff:
            min_diff = diff
            best = e

    if not best or min_diff > 10800:
        return False, 0, ""

    rain = best.get("rain", {}).get("3h", 0) or 0
    wind = best.get("wind", {}).get("speed", 0) or 0
    vis = best.get("visibility", 10000) or 10000

    reasons = []
    if rain > 5.0:
        reasons.append(f"Heavy Rain ({rain}mm)")
    if wind > 15.0:
        reasons.append(f"Gale Winds ({wind}m/s)")
    if vis < 1000:
        reasons.append(f"Fog/Low Visibility ({vis}m)")

    if reasons:
        return True, 7200, ", ".join(reasons)

    return False, 0, ""

def get_single_stop_weather(lat, lon, location_name, eta_iso=None):
    """
    Fetches fresh weather for a specific location and time.
    Used by the Agent to check the next stop.
    """
    if eta_iso:
        try:
            target_time = datetime.fromisoformat(eta_iso)
        except ValueError:
            target_time = datetime.now()
    else:
        target_time = datetime.now()

    if target_time.tzinfo is not None:
        target_time = target_time.replace(tzinfo=None)
    _, entries = _fetch_weather(0, {"lat": lat, "lon": lon})
    
    if not entries:
        return f"Could not fetch weather data for {location_name}."

    best_match = None
    min_diff = float("inf")

    for entry in entries:
        diff = abs((entry["_dt"] - target_time).total_seconds())
        if diff < min_diff:
            min_diff = diff
            best_match = entry

    if best_match:
        desc = best_match.get("weather", [{}])[0].get("description", "Unknown").capitalize()
        temp = best_match.get("main", {}).get("temp", "N/A")
        wind = best_match.get("wind", {}).get("speed", 0)
        rain = best_match.get("rain", {}).get("3h", 0)        
        arrival_str = target_time.strftime("%H:%M")
        summary = [
            f"**Weather for {location_name}** (Arrival ~{arrival_str})",
            f"Condition: {desc}",
            f"Temp: {temp}°C",
            f"Wind: {wind} m/s"
        ]
        
        if rain > 0:
            summary.append(f"Rain: {rain}mm (Take caution)")
        
        return "\n".join(summary)
    
    return f"No close forecast found for {location_name} at {target_time}."

# ROUTE METRICS
def calculate_route_metrics(route, dist_matrix, dur_matrix, forecasts, start_time):
    total_dist = 0
    total_time = 0
    current_time = start_time
    travel_log = []

    travel_log.append({"city_idx": route[0], "event": "Depart", "time": current_time, "note": "Trip Start"})

    for i in range(len(route) - 1):
        u, v = route[i], route[i + 1]

        d = dist_matrix[u][v]
        t = dur_matrix[u][v]

        total_dist += d
        total_time += t
        current_time += timedelta(seconds=t)

        wait, wsec, reason = check_weather_at_time(forecasts.get(v, []), current_time)
        if wait:
            total_time += wsec
            travel_log.append({
                "city_idx": v,
                "event": "Weather Wait",
                "time": current_time,
                "duration_sec": wsec,
                "note": f"Waiting for {reason}"
            })
            current_time += timedelta(seconds=wsec)

        travel_log.append({"city_idx": v, "event": "Arrive", "time": current_time, "note": "Stop reached"})

    return total_dist, total_time, travel_log

# SEQUENCE CHECK
def check_sequence_violations(route, constraints):
    seq = {i: c.get("visit_sequence", 2) for i, c in enumerate(constraints)}
    violations = 0
    for i in range(len(route)):
        for j in range(i + 1, len(route)):
            if seq[route[i]] > seq[route[j]]:
                violations += 1
    return violations

# COST CACHE
cost_cache = {}
def cost_function(route, dist_matrix, dur_matrix, forecasts, constraints, start_time):
    key = tuple(route)
    if key in cost_cache:
        return cost_cache[key]

    dist, t, _ = calculate_route_metrics(route, dist_matrix, dur_matrix, forecasts, start_time)
    violations = check_sequence_violations(route, constraints)

    cost = (ALPHA * dist) + (BETA * t) + (violations * SEQUENCE_PENALTY)
    cost_cache[key] = cost
    return cost

def create_initial_population(n, src=0):
    base = list(range(n))
    base.remove(src)
    return [[src] + random.sample(base, len(base)) for _ in range(POPULATION_SIZE)]

def tournament_selection(pop, *args):
    cand = random.sample(pop, 3)
    cand.sort(key=lambda r: cost_function(r, *args))
    return cand[0]

def crossover(p1, p2):
    a, b = sorted(random.sample(range(1, len(p1)), 2))
    child = [None] * len(p1)
    child[0] = p1[0]
    child[a:b] = p1[a:b]
    fill = [x for x in p2 if x not in child]
    idx = 1
    for x in fill:
        while child[idx] is not None:
            idx += 1
        child[idx] = x
    return child

def mutate(route):
    if random.random() < MUTATION_RATE:
        a, b = random.sample(range(1, len(route)), 2)
        route[a], route[b] = route[b], route[a]
    return route

def solve_route(locations_data):
    if len(locations_data) < 2:
        return {"status": "error", "message": "Need at least 2 locations."}

    dist_matrix, dur_matrix = get_distance_matrix(locations_data)
    if not dist_matrix:
        return {"status": "error", "message": "Failed to fetch Matrix API."}

    forecasts = fetch_weather_forecasts(locations_data)
    start_time = datetime.now()
    population = create_initial_population(len(locations_data))

    best = None
    best_cost = float("inf")

    for _ in range(GENERATIONS):
        population.sort(key=lambda r: cost_function(
            r, dist_matrix, dur_matrix, forecasts, locations_data, start_time
        ))
        new_pop = population[:2]

        while len(new_pop) < POPULATION_SIZE:
            p1 = tournament_selection(population, dist_matrix, dur_matrix, forecasts, locations_data, start_time)
            p2 = tournament_selection(population, dist_matrix, dur_matrix, forecasts, locations_data, start_time)
            new_pop.append(mutate(crossover(p1, p2)))

        population = new_pop

        if cost_function(population[0], dist_matrix, dur_matrix, forecasts, locations_data, start_time) < best_cost:
            best = population[0]
            best_cost = cost_function(best, dist_matrix, dur_matrix, forecasts, locations_data, start_time)

    dist, sec, log = calculate_route_metrics(best, dist_matrix, dur_matrix, forecasts, start_time)

    route_names = []
    alerts = []

    for e in log:
        name = locations_data[e["city_idx"]]["name"]
        if e["event"] == "Weather Wait":
            alerts.append(f"Wait at {name} for {int(e['duration_sec']/3600)}h due to {e['note']}")
        if e["event"] == "Arrive" and (not route_names or route_names[-1] != name):
            route_names.append(name)

    if route_names[0] != locations_data[best[0]]["name"]:
        route_names.insert(0, locations_data[best[0]]["name"])

    return {
        "status": "success",
        "total_distance_km": round(dist / 1000, 2),
        "total_duration_hours": round(sec / 3600, 2),
        "optimized_route": route_names,
        "weather_alerts": alerts,
        "full_log": log
    }