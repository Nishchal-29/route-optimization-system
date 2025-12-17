import os
from dotenv import load_dotenv
import requests
import pandas as pd
import random
import math
from datetime import datetime,timedelta

def print_matrix(title, matrix, labels):
    print(f"\n{title}")
    print("".ljust(12), *[c.ljust(12) for c in labels])
    for label, row in zip(labels, matrix):
        print(label.ljust(12), *[str(round(v, 2)).ljust(12) for v in row])

def violates_time_window(route, duration_matrix, forbidden_windows):
    current_time = 0
    penalty = 0
    violations = []

    for i in range(len(route) - 1):
        city = route[i]
        next_city = route[i + 1]
        current_time += duration_matrix[city][next_city]

        if city in forbidden_windows:
            window = forbidden_windows[city]
            if window["start"] <= current_time <= window["end"]:
                penalty += (window["end"] - current_time)
                violations.append({
                    "city": city,
                    "arrival_time_sec": int(current_time),
                    "window": (window["start"], window["end"]),
                    "reasons": window["reasons"]
                })

    return penalty, violations


load_dotenv()
ORS_API = os.getenv("ORS_API_KEY")
WEATHER_API = os.getenv("WEATHER_API")

cities = ["Delhi","Mumbai","Kolkata","Bengaluru","Guwahati","Chennai","Jaipur","Hyderabad","Pune","Ahmedabad","Lucknow"]

lat_coord=[]
lon_coord=[]
for sity in cities:
    res = requests.get(f"https://api.openrouteservice.org/geocode/search?api_key={ORS_API}&text={sity}")
    da = res.json()
    first = da["features"][0]
    coords = first["geometry"]["coordinates"]  
    lat_coord.append(coords[1])
    lon_coord.append(coords[0])

locations = list(zip(lon_coord, lat_coord))  

forbidden_windows = {}
trip_start = datetime.utcnow()

for idx, (lon, lat) in enumerate(locations):
    res = requests.get(
        "https://api.openweathermap.org/data/2.5/forecast",
        params={
            "lat": lat,
            "lon": lon,
            "appid": WEATHER_API,
            "units": "metric"
        }
    ).json()

    for entry in res["list"]:
        reasons = []

        rain = entry.get("rain", {}).get("3h", 0)
        if rain > 1:
            reasons.append(f"Heavy Rain ({rain} mm)")

        wind = entry["wind"]["speed"]
        if wind > 8:
            reasons.append(f"High Wind ({wind} m/s)")

        visibility = entry.get("visibility", 10000)
        if visibility < 3000:
            reasons.append("Low Visibility")

        main_weather = entry["weather"][0]["main"]
        if main_weather in ["Rain", "Thunderstorm", "Snow"]:
            reasons.append(main_weather)

        if reasons:
            t = datetime.strptime(entry["dt_txt"], "%Y-%m-%d %H:%M:%S")
            seconds_from_start = int((t - trip_start).total_seconds())

            forbidden_windows[idx] = {
                "start": seconds_from_start,
                "end": seconds_from_start + 3*3600,
                "reasons": reasons
            }
            break

print("\n🚫 FORBIDDEN TIME WINDOWS (Weather-based)\n")

for idx, window in forbidden_windows.items():
    start_time = trip_start + timedelta(seconds=window["start"])
    end_time   = trip_start + timedelta(seconds=window["end"])

    print(f"City        : {cities[idx]}")
    print(f"Forbidden  : {start_time.strftime('%Y-%m-%d %H:%M')} "
          f"→ {end_time.strftime('%Y-%m-%d %H:%M')}")
    print(f"Reasons    : {', '.join(window['reasons'])}")
    print("-" * 50)


url = "https://api.openrouteservice.org/v2/matrix/driving-car"

headers = {
    "Authorization": ORS_API,
    "Content-Type": "application/json"
}

body = {
    "locations": locations,
    "metrics": ["distance", "duration"]
}

response = requests.post(url, json=body, headers=headers)
res = response.json()

print_matrix("DISTANCE MATRIX (meters)", res["distances"], cities)
print_matrix("DURATION MATRIX (seconds)", res["durations"], cities)


# ======================================================================
# ========================= GENETIC ALGORITHM ===========================
# ======================================================================

POPULATION_SIZE = 60
GENERATIONS = 200
MUTATION_RATE = 0.20

SOURCE_INDEX = 0   
TIME_WINDOW_PENALTY=1e7
ALPHA = 1.0
BETA  = 1.0

# ===================== PRIORITY SETTINGS =====================  # <<< PRIORITY >>>

# Higher number = higher priority
city_priority = {
    0: 5,  # Delhi
    1: 4,  # Mumbai
    2: 2,  # Kolkata
    3: 4,  # Bengaluru
    4: 1,  # Guwahati
    5: 3,  # Chennai
    6: 3,  # Jaipur
    7: 3,  # Hyderabad
    8: 2,  # Pune
    9: 3,  # Ahmedabad
    10:2   # Lucknow
}

PRIORITY_WEIGHT = 1000  # <<< PRIORITY >>>

# ===============================================================

def route_distance(route, distance_matrix):
    return sum(distance_matrix[route[i]][route[i+1]] for i in range(len(route)-1))

def route_duration(route, duration_matrix):
    return sum(duration_matrix[route[i]][route[i+1]] for i in range(len(route)-1))

# -------------------------------
# PRIORITY PENALTY
# -------------------------------
def priority_penalty(route):   # <<< PRIORITY >>>
    penalty = 0
    for position, city in enumerate(route):
        penalty += city_priority.get(city, 1) * position
    return penalty

# -------------------------------
# COMBINED COST FUNCTION
# -------------------------------
def cost(route, distance_matrix, duration_matrix):
    dist = route_distance(route, distance_matrix)
    time = route_duration(route, duration_matrix)
    p_penalty = priority_penalty(route)
    tw_penalty, _ = violates_time_window(route, duration_matrix, forbidden_windows)
    return ALPHA * dist + BETA * time + PRIORITY_WEIGHT * p_penalty + TIME_WINDOW_PENALTY*tw_penalty

def fitness(route, distance_matrix, duration_matrix):
    return 1 / (cost(route, distance_matrix, duration_matrix) + 1)

# -------------------------------
# INITIAL POPULATION
# -------------------------------
def create_initial_population(num_cities):
    population = []
    remaining = list(range(num_cities))
    remaining.remove(SOURCE_INDEX)

    for _ in range(POPULATION_SIZE):
        random.shuffle(remaining)
        population.append([SOURCE_INDEX] + remaining[:])

    return population

# -------------------------------
# TOURNAMENT SELECTION
# -------------------------------
def tournament_selection(population, dist_matrix, dur_matrix, k=3):
    selected = random.sample(population, k)
    selected.sort(key=lambda r: cost(r, dist_matrix, dur_matrix))
    return selected[0]

# -------------------------------
# ORDER CROSSOVER
# -------------------------------
def crossover(parent1, parent2):
    p1 = parent1[1:]
    p2 = parent2[1:]

    n = len(p1)
    a, b = sorted(random.sample(range(n), 2))

    child = [None]*n
    child[a:b] = p1[a:b]

    idx = b
    for x in p2:
        if x not in child:
            if idx >= n:
                idx = 0
            child[idx] = x
            idx += 1

    return [SOURCE_INDEX] + child

# -------------------------------
# MUTATION
# -------------------------------
def mutate(route):
    if random.random() < MUTATION_RATE:
        a, b = random.sample(range(1, len(route)), 2)
        route[a], route[b] = route[b], route[a]
    return route

# -------------------------------
# MAIN GA (GLOBAL BEST)
# -------------------------------
def genetic_algorithm(distance_matrix, duration_matrix, labels):
    population = create_initial_population(len(labels))

    global_best = None
    global_best_cost = float('inf')

    for gen in range(GENERATIONS):
        new_pop = []

        for _ in range(POPULATION_SIZE):
            p1 = tournament_selection(population, distance_matrix, duration_matrix)
            p2 = tournament_selection(population, distance_matrix, duration_matrix)
            child = mutate(crossover(p1, p2))
            new_pop.append(child)

        population = new_pop

        current_best = min(population, key=lambda r: cost(r, distance_matrix, duration_matrix))
        current_cost = cost(current_best, distance_matrix, duration_matrix)

        if current_cost < global_best_cost:
            global_best = current_best
            global_best_cost = current_cost

        print(
            f"Gen {gen+1}: "
            f"Dist={route_distance(current_best, distance_matrix)/1000:.2f} km, "
            f"Time={route_duration(current_best, duration_matrix)/3600:.2f} hr"
        )

    return global_best

# -------------------------------
# RUN
# -------------------------------
distance_matrix = res["distances"]
duration_matrix = res["durations"]

best_route = genetic_algorithm(distance_matrix,duration_matrix,cities)

print("\nBEST ROUTE:")
current_time_sec = 0

for i in range(len(best_route) - 1):
    curr_idx = best_route[i]
    next_idx = best_route[i + 1]
    travel_sec = duration_matrix[curr_idx][next_idx]
    current_time_sec += travel_sec
    arrival_datetime = trip_start + timedelta(seconds=current_time_sec)
    print(
        f"{cities[curr_idx]} → {cities[next_idx]} | "
        f"Arrival Time: {arrival_datetime.strftime('%I:%M %p')} | "
        f"Date: {arrival_datetime.strftime('%d-%m-%y')}"
    )

tw_penalty, violations = violates_time_window(best_route, duration_matrix, forbidden_windows)

print("\nTIME WINDOW VIOLATIONS (for frontend):")
for v in violations:
    print(
        f"{cities[v['city']]} | "
        f"Arrival: {v['arrival_time_sec']/3600:.2f} hr | "
        f"Reasons: {', '.join(v['reasons'])}"
    )

print("\nFinal Distance:", route_distance(best_route,distance_matrix)/1000, "km")
print("Final Duration:", route_duration(best_route,duration_matrix)/3600, "hours") 