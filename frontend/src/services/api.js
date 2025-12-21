import axios from "axios";

/* =====================================================
   API INSTANCE
===================================================== */

const API_BASE_URL =
  import.meta.env.VITE_API_URL || "http://localhost:8000";

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    "Content-Type": "application/json",
  },
  timeout: 60000,
});

/* =====================================================
   INTERCEPTORS
===================================================== */

api.interceptors.request.use(
  (config) => {
    console.log(
      "API Request:",
      config.method?.toUpperCase(),
      config.url,
      config.data || ""
    );
    return config;
  },
  (error) => Promise.reject(error)
);

api.interceptors.response.use(
  (response) => {
    console.log(
      "API Response:",
      response.status,
      response.config.url
    );
    return response;
  },
  (error) => {
    if (error.response) {
      console.error(
        "API Error:",
        error.response.status,
        error.response.data
      );
    } else {
      console.error("Network Error:", error.message);
    }
    return Promise.reject(error);
  }
);

/* =====================================================
   NLP FLOW
===================================================== */

/**
 * Extract locations & visit order from natural language
 */
export const extractSequence = async (requestText) => {
  const response = await api.post("/extract-sequence", {
    request_text: requestText,
  });

  return response.data;
};

/**
 * Optimize route (used by NLP + MAP)
 */
export const optimizeRoute = async (parsedLocations, sessionId) => {
  if (!Array.isArray(parsedLocations) || parsedLocations.length < 2) {
    throw new Error("At least two locations are required.");
  }

  const response = await fetch(`${API_BASE_URL}/optimize-route?session_id=${sessionId}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ parsed_locations: parsedLocations }),
  });
  return response.json();
};

/**
 * Full NLP pipeline
 */
export const processLogisticsRequest = async (requestText, sessionId) => {
  const extractRes = await fetch(`${API_BASE_URL}/extract-sequence`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ request_text: requestText })
    });
  const extracted = await extractRes.json();

  if (
    !extracted?.parsed_locations ||
    extracted.parsed_locations.length < 2
  ) {
    throw new Error("At least two locations are required.");
  }

  const optimizeRes = await fetch(`${API_BASE_URL}/optimize-route?session_id=${sessionId}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(extracted) 
  });
  const optimized = await optimizeRes.json();

  return { extracted, optimized };
};

/* =====================================================
   MAP FLOW
===================================================== */

/**
 * Optimize route from map-selected locations
 * @param [{ name, lat, lon }]
 */
export const optimizeFromMap = async (locations, session_id) => {
  if (!Array.isArray(locations) || locations.length < 2) {
    throw new Error("Select at least two locations.");
  }

  const enrichedLocations = locations.map((loc, index) => ({
    name: loc.name,
    lat: loc.lat,
    lon: loc.lon,
    visit_sequence: index + 1,
  }));

  return optimizeRoute(enrichedLocations, session_id);
};

/* =====================================================
   MANIFEST & AGENT FLOW 🚛🤖
===================================================== */

/**
 * Create a new delivery manifest
 * This initializes the agent state with an active route
 */
export const createManifest = async (routeId, driverName, sessionId) => {
  const response = await fetch(`${API_BASE_URL}/create-manifest`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      route_id: routeId, 
      driver_name: driverName,
      session_id: sessionId
    }),
  });
  // ... check response ...
  return response.json();
};

/**
 * Get current agent/route status
 */
export const getAgentStatus = async (sessionId) => {
  const response = await api.get("/agent/status", {
    params: { session_id: sessionId }
  });
  return response.data;
};

/**
 * Report a delay to the agent
 */
// export const reportDelay = async (delayMinutes, reason, location = null) => {
//   const payload = {
//     delay_minutes: delayMinutes,
//     reason,
//     location,
//   };

//   const response = await api.post("/agent/report-delay", payload);
//   return response.data;
// };

/**
 * Check traffic conditions via agent
 */
// export const checkTraffic = async () => {
//   const response = await api.post("/agent/check-traffic");
//   return response.data;
// };

/**
 * Get traffic map visualization
 */
export const getTrafficMap = async () => {
  const response = await api.get("/traffic/map");
  return response.data;
};

/**
 * Download traffic map HTML
 */
export const downloadTrafficMap = () => {
  return `${API_BASE_URL}/traffic/download-map`;
};

/* =====================================================
   CHAT / AI AGENT FLOW 🧠🤖
===================================================== */

/**
 * Send message to AI Agent (LogiBOT)
 * This is the main agent chat endpoint that handles:
 * - Route explanations
 * - Traffic/weather reasoning
 * - Delay reports
 * - Status queries
 * - Natural language commands
 */
export const sendAgentMessage = async (message, sessionId) => {
  if (!message || typeof message !== "string") {
    throw new Error("Chat message must be a non-empty string.");
  }

  const payload = {
    message: message.trim(),
    session_id: sessionId,
  };

  const response = await api.post("/agent/chat", payload);
  return response.data;
};

/* =====================================================
   ROUTE SUMMARY
===================================================== */

/**
 * Fetch summarized route from backend
 * @param {Object} optimizedRoute - Optimized route object returned by backend
 * @param {Array} locations - Array of location objects [{name, lat, lon, visit_sequence}]
 */
export const getRouteSummary = async (optimizedResult, locations) => {
  try {
    if (!optimizedResult?.optimized_route || !Array.isArray(locations)) {
      throw new Error("Invalid route data for summary");
    }

    // Rebuild ordered route with lat/lon
    const orderedRoute = optimizedResult.optimized_route.map((name, index) => {
      const loc = locations.find(l => l.name === name);

      if (!loc) {
        throw new Error(`Location not found for ${name}`);
      }

      return {
        name: loc.name,
        lat: loc.lat,
        lon: loc.lon,
        visit_sequence: index + 1
      };
    });

    const payload = {
      optimized_route: orderedRoute,
      total_distance_km: optimizedResult.total_distance_km || 0,
      total_duration_hours: optimizedResult.total_duration_hours || 0,
      weather_alerts: optimizedResult.weather_alerts || [],
      full_log: optimizedResult.full_log || []
    };

    const response = await api.post("/route/summary", payload);
    return response.data;

  } catch (error) {
    console.error("API Error - getRouteSummary:", error);
    throw error;
  }
};


/* =====================================================
   HEALTH CHECK
===================================================== */

export const healthCheck = async () => {
  try {
    const res = await api.get("/health");
    return res.data;
  } catch {
    return { status: "offline" };
  }
};

export default api;