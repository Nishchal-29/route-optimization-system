# LogiBot: AI-Powered Multi-City Route Optimization System

## Overview

LogiBot is an intelligent, AI-powered route optimization platform designed for modern logistics and transport companies. It automatically computes the most efficient delivery routes for a single truck carrying shipments to **multiple cities or states**, considering real-world constraints such as **priority deliveries, travel time, distance, weather conditions, traffic conditions and dynamic delays**.

This project was developed as a solution to the *AI/ML Multi-City Route Optimization Challenge for Flipr Hackathon 30.2*, with a strong emphasis on **practical AI usage**, **scalability**, and **real-time adaptability**.

LogiBot eliminates manual route planning by leveraging **AI/ML optimization algorithms**, geospatial intelligence, and conversational AI to deliver a complete end-to-end logistics decision system.

---

## Problem Statement

In real-world logistics:

* A single truck often delivers to **multiple destinations**
* Route planning becomes complex with increasing cities
* Manual planning is inefficient and error-prone
* Weather, traffic, and delays can disrupt schedules

**Goal:**

> Deliver goods across the *maximum number of cities* in the *minimum total travel time*, while respecting priorities and real-world constraints.

---

## Our Solution

LogiBot intelligently analyzes:

* Source city + multiple destination cities
* Delivery priorities
* Distance & travel duration
* Weather at estimated arrival time
* Dynamic delays (traffic, rain, breakdowns, etc.)

Using AI-driven optimization, it generates:

* The **best city visitation sequence**
* **Optimized total distance & duration**
* **Weather-aware alerts**
* **Human-readable AI-generated route summary**

The system continuously adapts to changes through a conversational AI agent interface with integrated tools for checking weather and traffic conditions, re-optimizing routes, handling delays and updating ETAs, checking route status.

---

## Key Features

### 1. Intelligent Route Planning

* City input via **text search or interactive map**
* Automatic geocoding (latitude & longitude extraction)
* AI-based multi-city route optimization
* Supports priority-based deliveries

### 2️. Weather-Aware Routing

* Predicts arrival time per city
* Fetches **weather conditions at ETA**
* Generates weather-based alerts (rain, storms, delays)
* Adjusts routing logic accordingly

### 3️. AI-Powered Route Summary

* Natural language explanation of the route
* Highlights priorities, weather risks, and efficiency
* Easy-to-understand logistics insights

### 4️. Instant Route Manifest

* Generate a complete delivery manifest instantly
* Includes route order, distances, ETAs, and alerts

### 5️. LogiBot: Context-Aware AI Copilot

* A sophisticated agent that doesn't just chat—it has access to execution tools.
* Ask "Where am I?" or "What's next?" to get instant DB-synced progress updates.
* Drivers can report issues naturally (e.g., "I'm stuck in traffic for 20 mins"). The agent parses this, updates the database, and recalculates ETAs for all subsequent stops instantly.
* The agent can dynamically generate and render interactive maps directly in the chat interface.
* Get:

  * Current progress
  * Next stop
  * Remaining distance & time
  * traffic conditions
  * weather conditions
  * reoptimize remaining routes
  * report delays and update ETAs

### 6️. Traffic Intelligence

* Traffic heatmaps for nearby regions
* Congestion-aware insights
* Helps drivers anticipate delays

### 7️. Real-Time Adaptability

* Handles dynamic updates
* Scales with increasing number of cities
* Near real-time recalculation

---

## AI & ML Concepts Used

### Genetic Algorithm (GA) – Core Optimization Engine

The heart of LogiBot’s route optimization is powered by a **Genetic Algorithm (GA)**, chosen for its effectiveness in solving complex, NP-hard optimization problems such as multi-city route planning with constraints.

**Why Genetic Algorithm?**

* Traditional shortest-path algorithms fail when cities, priorities, and constraints increase
* GA efficiently explores a large solution space
* Naturally supports multi-objective optimization

**GA Representation**

* **Chromosome**: A complete delivery route (ordered list of cities)
* **Gene**: A single city within the route

**Fitness Function**
The fitness score is computed using a weighted combination of:

* Total travel distance
* Total travel time
* Priority penalties (high-priority cities visited late)
* Weather risk penalties

**Genetic Operations**

* **Selection**: Tournament / fitness-based selection
* **Crossover**: Order-based crossover to preserve valid routes
* **Mutation**: Random city swaps to maintain diversity
* **Elitism**: Best routes preserved across generations

**Termination Criteria**

* Fixed number of generations OR
* No significant improvement in fitness score

This GA-based approach ensures LogiBot generates **near-optimal, scalable, and adaptive delivery routes** even as the number of cities increases.

### Additional AI Components

* Priority-based constraint handling
* ETA prediction logic
* Weather-aware decision modeling
* LLM-powered conversational AI agent for dynamic updates

> This system goes beyond static rules and uses **evolutionary intelligence** for real-world logistics optimization.

---

## System Architecture (High-Level)

1. **Frontend UI**

   * City selection (text/map)
   * Route visualization
   * Traffic heatmaps
   * Chating interface for our Agentic AI

2. **Backend Services**

   * Geocoding & distance matrix
   * Weather & ETA computation
   * Optimization engine

3. **AI Layer**

   * Route optimization logic
   * Conversational AI agent (LogiBot)
   * AI-generated summaries

4. **External APIs**

   * Maps & distance APIs
   * Weather APIs

---

## Tech Stack

### Frontend

* Framework: React.js (Vite)
* Styling: Tailwind CSS, Lucide React (Icons)
* State Management: React Hooks (useState, useEffect), Custom Hooks (useSession)
* Security: DOMPurify (for safe HTML/Map rendering)
* HTTP Client: Native Fetch API

### Backend

* Framework: FastAPI (Python)
* Server: Uvicorn
* Validation: Pydantic
* Database: Supabase (PostgreSQL) with supabase-py client
* Architecture: RESTful API with Session Persistence

### AI / ML

* LLM Engine: Google Gemini 2.5 Flash
* Agent Framework: LangChain (Custom Tools & Reasoning Loop)
* Core Algorithm: Genetic Algorithm (GA) with Custom Mutation/Crossover logic for TSP
* Heuristics: Weather-based penalty functions

### Geospatial & External APIs

* Traffic Intelligence: TomTom Traffic API (Flow Segments & Incidents)
* Mapping: Folium (Python-based interactive map generation)
* Routing & Geocoding: OpenRouteService (ORS) Matrix API
* Weather: OpenWeatherMap API (5-day/3-hour forecast)

---

## Getting Started (Local Setup)

```bash
# Clone the repository
git clone https://github.com/your-usernam/logibot

# Start the backend server
uvicorn main:app --reload

# Go to frontend directory
cd frontend

# Install dependencies
npm install  

# Run development server
npm run dev  
```

## Live Deployment

🔗 **Deployed Website:**

> https://route-optimization-frontend-16zh.onrender.com

---

## Demo Video (Mandatory)

**Live Demo Walkthrough:**

> https://drive.google.com/file/d/1QuUI0nkZcowPWTJgDHKHihrkP_daNXwy/view?usp=sharing

The demo showcases:

* City selection & route optimization
* AI based Route Summary generation
* Manifest generation
* LogiBot conversational updates

---

## Scalability & Future Enhancements

* Multi-truck optimization
* Cost-based optimization (fuel, tolls)
* Driver shift & rest constraints
* Live GPS tracking integration
* Reinforcement Learning-based route learning

---

## Acknowledgements

* Logistics optimization research
* Open-source AI tools
* Map data providers : Open Route Service
* Weather data providers : Open Weather Map
* Traffic Data providers : TomTom Service

---

> **LogiBot** – *Deliver smarter, faster, and safer with AI-powered logistics intelligence.*
