import axios from "axios";
const API_BASE_URL =
  import.meta.env.VITE_API_URL || "http://localhost:8000";

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    "Content-Type": "application/json",
  },
  timeout: 60000,
});

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

export const extractSequence = async (requestText) => {
  const response = await api.post("/extract-sequence", {
    request_text: requestText,
  });

  return response.data;
};

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
  return response.json();
};

export const getAgentStatus = async (sessionId) => {
  const response = await api.get("/agent/status", {
    params: { session_id: sessionId }
  });
  return response.data;
};

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

export const getRouteSummary = async (optimizedResult, locations) => {
  try {
    if (!optimizedResult?.optimized_route || !Array.isArray(locations)) {
      throw new Error("Invalid route data for summary");
    }

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

export const healthCheck = async () => {
  try {
    const res = await api.get("/health");
    return res.data;
  } catch {
    return { status: "offline" };
  }
};

export default api;