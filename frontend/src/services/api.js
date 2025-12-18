import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 60000,
});

// Request interceptor for logging
api.interceptors.request.use(
  (config) => {
    console.log('API Request:', config.method.toUpperCase(), config.url);
    return config;
  },
  (error) => {
    console.error('Request Error:', error);
    return Promise.reject(error);
  }
);

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => {
    console.log('API Response:', response.status, response.config.url);
    return response;
  },
  (error) => {
    if (error.response) {
      console.error('Response Error:', error.response.status, error.response.data);
    } else if (error.request) {
      console.error('Network Error:', error.message);
    } else {
      console.error('Error:', error.message);
    }
    return Promise.reject(error);
  }
);

/**
 * Extract sequence from natural language query
 * @param {string} requestText - Natural language logistics request
 * @returns {Promise} - Parsed locations with coordinates and sequence
 */
export const extractSequence = async (requestText) => {
  try {
    const response = await api.post('/extract-sequence', {
      request_text: requestText,
    });
    return response.data;
  } catch (error) {
    throw new Error(
      error.response?.data?.detail || 
      'Failed to extract locations from your request. Please try again.'
    );
  }
};

/**
 * Optimize route using genetic algorithm
 * @param {Array} parsedLocations - Array of location objects with lat, lon, sequence
 * @returns {Promise} - Optimized route with distance, time, and sequence
 */
export const optimizeRoute = async (parsedLocations) => {
  try {
    const response = await api.post('/optimize-route', {
      parsed_locations: parsedLocations,
    });
    return response.data;
  } catch (error) {
    throw new Error(
      error.response?.data?.detail || 
      'Failed to optimize route. Please check your input and try again.'
    );
  }
};

/**
 * Complete flow: Extract + Optimize
 * @param {string} requestText - Natural language logistics request
 * @returns {Promise} - Complete optimization result
 */
export const processLogisticsRequest = async (requestText) => {
  try {
    // Step 1: Extract sequence
    const extractedData = await extractSequence(requestText);
    
    if (!extractedData.parsed_locations || extractedData.parsed_locations.length === 0) {
      throw new Error('No locations found in your request. Please provide city names.');
    }
    
    // Step 2: Optimize route
    const optimizedRoute = await optimizeRoute(extractedData.parsed_locations);
    
    return {
      extracted: extractedData,
      optimized: optimizedRoute,
    };
  } catch (error) {
    throw error;
  }
};

/**
 * Health check endpoint
 * @returns {Promise} - API health status
 */
export const healthCheck = async () => {
  try {
    const response = await api.get('/health');
    return response.data;
  } catch (error) {
    return { status: 'offline', error: error.message };
  }
};

export default api;