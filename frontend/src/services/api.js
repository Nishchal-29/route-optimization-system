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
export const optimizeRoute = async (parsedLocations) => {
  if (!Array.isArray(parsedLocations) || parsedLocations.length < 2) {
    throw new Error("At least two locations are required.");
  }

  const payload = {
    parsed_locations: parsedLocations.map((loc, index) => ({
      name: loc.name,
      lat: loc.lat,
      lon: loc.lon,
      visit_sequence: loc.visit_sequence ?? index + 1,
    })),
  };

  const response = await api.post("/optimize-route", payload);
  return response.data;
};

/**
 * Full NLP pipeline
 */
export const processLogisticsRequest = async (requestText) => {
  const extracted = await extractSequence(requestText);

  if (
    !extracted?.parsed_locations ||
    extracted.parsed_locations.length < 2
  ) {
    throw new Error("At least two locations are required.");
  }

  const optimized = await optimizeRoute(
    extracted.parsed_locations
  );

  return {
    extracted,
    optimized,
  };
};

/* =====================================================
   MAP FLOW
===================================================== */

/**
 * Optimize route from map-selected locations
 * @param [{ name, lat, lon }]
 */
export const optimizeFromMap = async (locations) => {
  if (!Array.isArray(locations) || locations.length < 2) {
    throw new Error("Select at least two locations.");
  }

  const enrichedLocations = locations.map((loc, index) => ({
    name: loc.name,
    lat: loc.lat,
    lon: loc.lon,
    visit_sequence: index + 1,
  }));

  return optimizeRoute(enrichedLocations);
};

/* =====================================================
   CHAT / EXPLANATION FLOW 🧠🤖
===================================================== */

/**
 * Send message to LogiBOT
 * Used for:
 * - Route explanation
 * - Traffic / weather reasoning
 * - Summary generation
 * - User requested modifications
 */
export const sendChatMessage = async (message, context) => {
  if (!message || typeof message !== "string") {
    throw new Error("Chat message must be a non-empty string.");
  }

  // 🔐 Guarantee valid JSON object (prevents 422)
  const safeContext =
    context && typeof context === "object" && !Array.isArray(context)
      ? context
      : {};

  const response = await api.post("/chat", {
    message,
    context: safeContext,
  });

  return response.data;
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
