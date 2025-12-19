# ========================= main.py =========================
import os
import json
import requests
from typing import List
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
import google.generativeai as genai
from route import solve_route  # Your route optimization logic

# ==========================================================
# ENV SETUP
# ==========================================================
load_dotenv()

ORS_API_KEY = os.getenv("ORS_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not ORS_API_KEY or not GEMINI_API_KEY:
    raise RuntimeError("Missing API keys")

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-2.5-flash")

# ==========================================================
# FASTAPI APP
# ==========================================================
app = FastAPI(title="AI Logistics Route Optimizer")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==========================================================
# MODELS
# ==========================================================
class LogisticsQuery(BaseModel):
    request_text: str

class LocationPoint(BaseModel):
    name: str
    lat: float
    lon: float
    visit_sequence: int

class RouteResponse(BaseModel):
    parsed_locations: List[LocationPoint]

class ChatData(BaseModel):
    message: str
    context: dict = {}  

# ==========================================================
# GEOCODING
# ==========================================================
def geocode_city(city: str):
    try:
        r = requests.get(
            "https://api.openrouteservice.org/geocode/search",
            params={"api_key": ORS_API_KEY, "text": city},
            timeout=10
        )
        if r.status_code == 200 and r.json().get("features"):
            lon, lat = r.json()["features"][0]["geometry"]["coordinates"]
            return lat, lon
    except Exception as e:
        print(f"Geocoding failed for {city}: {e}")
    return None, None

# ==========================================================
# LLM PARSING
# ==========================================================
def parse_logistics_intent(text: str):
    prompt = f"""
Extract logistics routing intent.

Return ONLY a valid JSON array.
Each object MUST have:
- location_name (string)
- visit_sequence (integer)

Rules:
- Start city → visit_sequence = 1
- Ordered cities → increasing numbers
- Unordered → same number
- End city → highest number

User query:
{text}
"""
    try:
        res = model.generate_content(prompt)

        if not getattr(res, "text", None):
            return []

        raw = res.text.strip()
        if raw.startswith("```"):
            raw = raw.replace("```json", "").replace("```", "").strip()

        data = json.loads(raw)
        normalized = []

        for item in data:
            location = item.get("location_name") or item.get("city") or item.get("name")
            visit_sequence = item.get("visit_sequence") or item.get("order")

            if location is None or visit_sequence is None:
                continue

            normalized.append({
                "location_name": str(location),
                "visit_sequence": int(visit_sequence)
            })

        return normalized

    except Exception as e:
        print("LLM parse failed")
        print("ERROR:", e)
        return []

# ==========================================================
# API ENDPOINTS
# ==========================================================
@app.post("/extract-sequence", response_model=RouteResponse)
async def extract_sequence(query: LogisticsQuery):
    parsed = parse_logistics_intent(query.request_text)

    if not parsed:
        raise HTTPException(
            status_code=400,
            detail="Failed to parse locations from text"
        )

    locations = []
    for p in parsed:
        lat, lon = geocode_city(p["location_name"])
        if lat is None or lon is None:
            print(f"Skipping {p['location_name']} due to failed geocoding")
            continue

        locations.append(LocationPoint(
            name=p["location_name"],
            lat=lat,
            lon=lon,
            visit_sequence=p["visit_sequence"]
        ))

    if not locations:
        raise HTTPException(
            status_code=400,
            detail="No valid locations found after geocoding"
        )

    locations.sort(key=lambda x: x.visit_sequence)
    return RouteResponse(parsed_locations=locations)

@app.post("/optimize-route")
async def optimize_route(data: RouteResponse):
    if not data.parsed_locations:
        raise HTTPException(
            status_code=400,
            detail="No locations provided for route optimization"
        )

    result = solve_route([loc.dict() for loc in data.parsed_locations])

    if "total_distance_km" not in result:
        result["total_distance_km"] = "N/A"
    if "total_duration_min" not in result:
        result["total_duration_min"] = "N/A"

    return result

@app.post("/chat")
async def chat(data: ChatData):
    if not data.message:
        raise HTTPException(
            status_code=400,
            detail="No message provided."
        )

    # ---------------- CONTEXT HANDLING ----------------
    context_block = "No route context available."

    if isinstance(data.context, dict) and data.context:
        try:
            locations = data.context.get("locations", [])
            optimized = data.context.get("optimizedRoute", {})

            context_block = f"""
ROUTE DATA:
- Locations (in order):
{json.dumps(locations, indent=2)}

- Optimized Route Details:
{json.dumps(optimized, indent=2)}
"""
        except Exception as e:
            print("Context parsing failed:", e)
            context_block = "Context was provided but could not be parsed."

    # ---------------- PROMPT ----------------
    prompt = f"""
You are **LogiBOT**, an expert AI assistant for logistics route optimization.

Your tasks:
- Explain WHY the route was formed
- Consider traffic, distance, sequencing, constraints
- Answer clearly and practically
- If user requests changes, explain what would change and why

{context_block}

USER QUESTION:
{data.message}

RULES:
- Be concise but insightful
- Use bullet points if helpful
- Do NOT hallucinate missing data
"""

    # ---------------- LLM CALL ----------------
    try:
        res = model.generate_content(prompt)
        reply_text = getattr(res, "text", None)

        if not reply_text:
            reply_text = "I couldn't generate a meaningful response."

    except Exception as e:
        print("Chat LLM failed:", e)
        reply_text = "⚠️ Error generating explanation. Please try again."

    return {
        "reply": reply_text
    }


# ==========================================================
# HEALTH CHECK
# ==========================================================
@app.get("/health")
async def health_check():
    return {"status": "online"}
