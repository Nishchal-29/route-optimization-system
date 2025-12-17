# ========================= route.py =========================
import os
import requests
import random
from dotenv import load_dotenv
from datetime import datetime, timedelta

# ==========================================================
# ENV
# ==========================================================
load_dotenv()
ORS_API = os.getenv("ORS_API_KEY")
WEATHER_API = os.getenv("WEATHER_API")

if not ORS_API:
    raise RuntimeError("Missing ORS_API_KEY in .env")
if not WEATHER_API:
    print("Warning: WEATHER_API not found, weather windows will be skipped")

# ==========================================================
# GA CONFIG
# ==========================================================
POPULATION_SIZE = 60
GENERATIONS = 200
MUTATION_RATE = 0.2

ALPHA = 1.0
BETA = 1.0
PRIORITY_WEIGHT = 1000
TIME_WINDOW_PENALTY = 1e7

# ==========================================================
# ORS MATRIX
# ==========================================================
def get_distance_matrix(locations):
    coords = [[l["lon"], l["lat"]] for l in locations]
    try:
        r = requests.post(
            "https://api.openrouteservice.org/v2/matrix/driving-car",
            headers={"Authorization": ORS_API},
            json={"locations": coords, "metrics": ["distance", "duration"]},
            timeout=15
        ).json()
        return r.get("distances"), r.get("durations")
    except Exception as e:
        print("Error fetching distance matrix:", e)
        n = len(locations)
        return [[0]*n for _ in range(n)], [[0]*n for _ in range(n)]

# ==========================================================
# WEATHER WINDOWS
# ==========================================================
def build_forbidden_windows(locations):
    forbidden = {}
    if not WEATHER_API:
        return forbidden

    trip_start = datetime.utcnow()
    for idx, loc in enumerate(locations):
        try:
            res = requests.get(
                "https://api.openweathermap.org/data/2.5/forecast",
                params={
                    "lat": loc["lat"],
                    "lon": loc["lon"],
                    "appid": WEATHER_API,
                    "units": "metric"
                },
                timeout=10
            ).json()

            for entry in res.get("list", []):
                reasons = []
                if entry.get("rain", {}).get("3h", 0) > 1:
                    reasons.append("Heavy Rain")
                if entry["wind"]["speed"] > 8:
                    reasons.append("High Wind")
                if entry.get("visibility", 10000) < 3000:
                    reasons.append("Low Visibility")

                if reasons:
                    t = datetime.strptime(entry["dt_txt"], "%Y-%m-%d %H:%M:%S")
                    sec = int((t - trip_start).total_seconds())
                    forbidden[idx] = {
                        "start": sec,
                        "end": sec + 3 * 3600,
                        "reasons": reasons
                    }
                    break
        except Exception as e:
            print(f"Weather API failed for {loc['name']}: {e}")
    return forbidden

# ==========================================================
# COST + FITNESS
# ==========================================================
def route_distance(route, dist):
    return sum(dist[route[i]][route[i+1]] for i in range(len(route)-1))

def route_duration(route, dur):
    return sum(dur[route[i]][route[i+1]] for i in range(len(route)-1))

def priority_penalty(route, locations):
    return sum(locations[c]["visit_sequence"] * i for i, c in enumerate(route))

def violates_time_window(route, dur, windows):
    time = 0
    penalty = 0
    violations = []

    for i in range(len(route)-1):
        time += dur[route[i]][route[i+1]]
        idx = route[i+1]
        if idx in windows:
            w = windows[idx]
            if w["start"] <= time <= w["end"]:
                penalty += w["end"] - time
                violations.append({
                    "city_index": idx,
                    "arrival_time_sec": int(time),
                    "reasons": w["reasons"]
                })
    return penalty, violations

def cost(route, dist, dur, locations, windows):
    return (
        ALPHA * route_distance(route, dist)
        + BETA * route_duration(route, dur)
        + PRIORITY_WEIGHT * priority_penalty(route, locations)
        + TIME_WINDOW_PENALTY * violates_time_window(route, dur, windows)[0]
    )

def fitness(route, dist, dur, locations, windows):
    return 1 / (cost(route, dist, dur, locations, windows) + 1)

# ==========================================================
# GA OPERATORS
# ==========================================================
def create_initial_population(n):
    pop = []
    for _ in range(POPULATION_SIZE):
        route = [0] + random.sample(range(1, n), n - 1)
        pop.append(route)
    return pop

def tournament_selection(pop, dist, dur, locations, windows, k=3):
    selected = random.sample(pop, k)
    selected.sort(key=lambda r: cost(r, dist, dur, locations, windows))
    return selected[0]

def crossover(parent1, parent2):
    p1 = parent1[1:]
    p2 = parent2[1:]
    n = len(p1)

    a, b = sorted(random.sample(range(n), 2))
    child = [None] * n
    child[a:b] = p1[a:b]

    idx = b
    for x in p2:
        if x not in child:
            if idx >= n:
                idx = 0
            child[idx] = x
            idx += 1

    return [0] + child

def mutate(route):
    if random.random() < MUTATION_RATE:
        i, j = random.sample(range(1, len(route)), 2)
        route[i], route[j] = route[j], route[i]
    return route

# ==========================================================
# MAIN SOLVER
# ==========================================================
def solve_route(locations):
    if not locations:
        return {"status": "error", "message": "No locations provided"}

    dist, dur = get_distance_matrix(locations)
    windows = build_forbidden_windows(locations)

    population = create_initial_population(len(locations))
    best = None
    best_cost = float("inf")

    for _ in range(GENERATIONS):
        new_pop = []

        # Elitism
        population.sort(key=lambda r: cost(r, dist, dur, locations, windows))
        new_pop.extend(population[:2])

        while len(new_pop) < POPULATION_SIZE:
            p1 = tournament_selection(population, dist, dur, locations, windows)
            p2 = tournament_selection(population, dist, dur, locations, windows)
            child = mutate(crossover(p1, p2))
            new_pop.append(child)

        population = new_pop
        current_best = population[0]
        c_cost = cost(current_best, dist, dur, locations, windows)
        if c_cost < best_cost:
            best = current_best
            best_cost = c_cost

    _, violations = violates_time_window(best, dur, windows)

    optimized_route = [
        {
            "order": i + 1,
            "name": locations[c]["name"],
            "lat": locations[c]["lat"],
            "lon": locations[c]["lon"],
            "visit_sequence": locations[c]["visit_sequence"]
        }
        for i, c in enumerate(best)
    ]

    total_distance = route_distance(best, dist)
    total_duration = route_duration(best, dur)

    return {
        "status": "success",
        "optimized_route": optimized_route,
        "time_window_violations": violations,
        "total_distance_km": round(total_distance / 1000, 2) if total_distance else "N/A",
        "total_duration_min": round(total_duration / 60, 2) if total_duration else "N/A"
    }