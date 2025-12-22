import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Truck, MapPin, Sparkles, Route, MessageSquare } from 'lucide-react';

import QueryInput from '../components/home/QueryInput';
import LocationsDisplay from '../components/home/LocationsDisplay';
import RouteVisualization from '../components/home/RouteVisualization';
import OptimizationResults from '../components/home/OptimizationResults';
import LoadingState from '../components/home/LoadingState';
import ErrorDisplay from '../components/home/ErrorDisplay';
import MapSelectionModal from '../components/home/MapSelectionModal';
import ChatNavButton from '../components/home/ChatNavButton';
import RouteSummary from '../components/home/RouteSummary';

import { processLogisticsRequest, optimizeRoute, createManifest, optimizeFromMap, getRouteSummary } from '../services/api';
import { useSession } from '../hooks/useSession';

function Home() {
  const navigate = useNavigate();
  const sessionId = useSession();

  const [routeSummary, setRouteSummary] = useState(null);
  const [summaryLoading, setSummaryLoading] = useState(false);

  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const [extractedLocations, setExtractedLocations] = useState(null);
  const [optimizationResult, setOptimizationResult] = useState(null);
  const [manifestCreated, setManifestCreated] = useState(false);

  const [stage, setStage] = useState('input'); // input | processing | results
  const [showMap, setShowMap] = useState(false);

  const exampleQueries = [
    "Start from Delhi, visit Mumbai, Bangalore, and Chennai, then end at Kolkata",
    "I want to travel from delhi to deliver order at pune, jodhpur, banglore, mumbai and jaipur",
    "Begin at Pune, then go to Hyderabad, after that Jaipur, and finally return to Pune",
    "I want to travel to Mumbai from Delhi via Banglore"
  ];

  // --------------------------------------------------
  // RESTORE DATA FROM SESSION STORAGE ON REFRESH ONLY
  // --------------------------------------------------
  useEffect(() => {
    const storedContext = sessionStorage.getItem("routeContext");

    if (storedContext) {
      try {
        const parsed = JSON.parse(storedContext);

        if (parsed?.locations && parsed?.optimizedRoute) {
          setExtractedLocations(parsed.locations);
          setOptimizationResult(parsed.optimizedRoute);
          setManifestCreated(parsed.manifestCreated || false);
          setStage('results');
        }
      } catch (err) {
        console.error("Invalid session storage data", err);
        sessionStorage.removeItem("routeContext");
      }
    }
  }, []);

  // -------------------------------
  // FETCH ROUTE SUMMARY FROM BACKEND
  // -------------------------------
  const fetchRouteSummary = async (optimizedRoute, locations) => {
    setSummaryLoading(true);
    setRouteSummary(null);

    try {
      const response = await getRouteSummary(optimizedRoute, locations); 

      if (response?.summary) {
        setRouteSummary(response.summary);
        saveToSession(locations, optimizedRoute, manifestCreated, response.summary);
      } else {
        setRouteSummary("No summary available.");
        saveToSession(locations, optimizedRoute, manifestCreated, "No summary available.");
      }

    } catch (err) {
      console.error("Failed to fetch route summary from backend:", err);
      setRouteSummary("Failed to fetch summary.");
    } finally {
      setSummaryLoading(false);
    }
  };


  // --------------------------------------------------
  // TEXT BASED FLOW
  // --------------------------------------------------
  const handleSubmit = async () => {
    if (!query.trim()) {
      setError('Please enter a logistics request');
      return;
    }

    if (!sessionId) { 
      setError('Initializing session... please wait.');
      return;
    }

    setLoading(true);
    setError(null);
    setStage('processing');
    setExtractedLocations(null);
    setOptimizationResult(null);
    setManifestCreated(false);

    try {
      const result = await processLogisticsRequest(query, sessionId);

      setExtractedLocations(result.extracted.parsed_locations);
      setOptimizationResult(result.optimized);
      setStage('results');

      fetchRouteSummary(result.optimized, result.extracted.parsed_locations);
      // Save to session storage
      saveToSession(result.extracted.parsed_locations, result.optimized, false, routeSummary);

    } catch (err) {
      setError(err.message || 'Something went wrong');
      setStage('input');
    } finally {
      setLoading(false);
    }
  };

  // --------------------------------------------------
  // MAP BASED FLOW
  // --------------------------------------------------
  const handleMapOptimization = async (locations) => {
    if (!sessionId) { 
        setError('Initializing session... please wait.');
        return;
    }
    setShowMap(false);
    setLoading(true);
    setError(null);
    setStage('processing');
    setExtractedLocations(null);
    setOptimizationResult(null);
    setManifestCreated(false);

    try {
      const optimized = await optimizeFromMap(locations, sessionId);

      setExtractedLocations(locations);
      setOptimizationResult(optimized);
      setStage('results');

      fetchRouteSummary(optimized, locations);

      // Save to session storage
      saveToSession(locations, optimized, false, routeSummary);

    } catch (err) {
      setError(err.message || 'Route optimization failed');
      setStage('input');
    } finally {
      setLoading(false);
    }
  };

  // --------------------------------------------------
  // CREATE MANIFEST & ACTIVATE AGENT
  // --------------------------------------------------
  const handleCreateManifest = async () => {
    if (!optimizationResult || !optimizationResult.route_id) {
      setError('No optimized route found. Please optimize first.');
      return;
    }

    if (!sessionId) {
      setError('Initializing session... please try again in a moment.');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const manifest = await createManifest(optimizationResult.route_id, "Driver_001", sessionId);

      // Update optimization result with manifest info
      const updatedResult = {
        ...optimizationResult,
        manifest_id: manifest.manifest_id,
        driver: manifest.driver,
        created_at: manifest.created_at,
      };

      setOptimizationResult(updatedResult);
      setManifestCreated(true);

      // Save to session with manifest flag
      saveToSession(extractedLocations, updatedResult, true, routeSummary);

      // Show success message
      setError(null);
      
    } catch (err) {
      setError(err.message || 'Failed to create manifest');
    } finally {
      setLoading(false);
    }
  };

  // --------------------------------------------------
  // SAVE TO SESSION STORAGE
  // --------------------------------------------------
  const saveToSession = (locations, optimized, manifestCreated, routeSummary) => {
    const context = {
      locations,
      optimizedRoute: optimized,
      manifestCreated,
      routeSummary,
      timestamp: new Date().toISOString(),
    };
    sessionStorage.setItem("routeContext", JSON.stringify(context));
  };

  // --------------------------------------------------
  // RESET FLOW
  // --------------------------------------------------
  const handleReset = () => {
    setQuery('');
    setExtractedLocations(null);
    setOptimizationResult(null);
    setError(null);
    setStage('input');
    setManifestCreated(false);

    sessionStorage.removeItem("routeContext");
  };

  // --------------------------------------------------
  // NAVIGATION TO CHAT PAGE
  // --------------------------------------------------
  const openChatPage = () => {
    navigate('/chat');
  };

  return (
    <div className="min-h-screen pb-20 bg-gradient-to-br from-gray-50 to-blue-50">

      {/* HEADER */}
      <header className="bg-gradient-to-r from-primary-600 to-secondary-500 text-white shadow-2xl">
        <div className="container mx-auto px-6 py-8">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className="bg-white/20 p-3 rounded-xl backdrop-blur-sm">
                <Truck className="w-8 h-8" />
              </div>
              <div>
                <h1 className="text-3xl font-bold">AI-Powered Multi-City Route Optimizer</h1>
                <p className="text-primary-100 mt-1">
                  Intelligent Multi-City Route Planning with AI Agent
                </p>
              </div>
            </div>

            <div className="hidden md:flex items-center gap-6 text-sm">
              <div className="flex items-center gap-2">
                <Sparkles className="w-5 h-5" />
                <span>AI-Powered</span>
              </div>
              <div className="flex items-center gap-2">
                <Route className="w-5 h-5" />
                <span>Smart Routing</span>
              </div>
              <div className="flex items-center gap-2">
                <MessageSquare className="w-5 h-5" />
                <span>AI Copilot</span>
              </div>
            </div>
          </div>
        </div>
      </header>

      {/* MAIN */}
      <div className="container mx-auto px-6 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">

          {/* LEFT PANEL */}
          <div className="space-y-6">
            <QueryInput
              query={query}
              setQuery={setQuery}
              onSubmit={handleSubmit}
              onSelectFromMap={() => setShowMap(true)}
              loading={loading}
            />

            {stage === 'input' && (
              <div className="card">
                <h3 className="font-semibold mb-4 flex items-center gap-2">
                  <MapPin className="w-5 h-5 text-primary-500" />
                  Example Queries
                </h3>

                {exampleQueries.map((ex, i) => (
                  <button
                    key={i}
                    onClick={() => setQuery(ex)}
                    className="w-full text-left p-3 mb-2 bg-gray-50 rounded-lg hover:bg-primary-50 transition-colors"
                  >
                    {ex}
                  </button>
                ))}
              </div>
            )}

            {extractedLocations && (
              <LocationsDisplay
                locations={extractedLocations}
                optimizedRoute={optimizationResult}
              />
            )}

            {stage === 'results' && (
              <RouteSummary
                summary={routeSummary}
                loading={summaryLoading}
              />
            )}

            {stage === 'results' && (
              <div className="space-y-3">
                {!manifestCreated ? (
                  <button 
                    onClick={handleCreateManifest} 
                    className="btn-primary w-full flex items-center justify-center gap-2"
                    disabled={loading}
                  >
                    <Truck className="w-4 h-4" />
                    Create Delivery Manifest
                  </button>
                ) : (
                  <div className="card bg-emerald-50 border-emerald-200">
                    <div className="flex items-center gap-2 text-emerald-700 mb-2">
                      <Sparkles className="w-5 h-5" />
                      <span className="font-semibold">Manifest Created!</span>
                    </div>
                    <p className="text-sm text-emerald-600">
                      Your route is now active. Chat with LogiBOT for real-time assistance.
                    </p>
                  </div>
                )}
                
                <button onClick={handleReset} className="btn-secondary w-full">
                  Start New Request
                </button>
              </div>
            )}
          </div>

          {/* RIGHT PANEL */}
          <div className="lg:col-span-2 space-y-6">
            {error && <ErrorDisplay error={error} onDismiss={() => setError(null)} />}
            {loading && <LoadingState />}

            {stage === 'results' && !loading && (
              <>
                <OptimizationResults result={optimizationResult} />
                <RouteVisualization
                  locations={extractedLocations}
                  optimizedRoute={optimizationResult}
                />
                
                {manifestCreated && (
                  <div className="card bg-gradient-to-r from-purple-50 to-blue-50 border-purple-200">
                    <div className="flex items-center justify-between">
                      <div>
                        <h3 className="font-semibold text-lg text-purple-900 mb-1">
                          🤖 AI Copilot Ready
                        </h3>
                        <p className="text-sm text-purple-700">
                          Your route is being monitored. Get traffic updates, weather alerts, and real-time assistance.
                        </p>
                      </div>
                      <button
                        onClick={openChatPage}
                        className="btn-primary flex items-center gap-2"
                      >
                        <MessageSquare className="w-4 h-4" />
                        Chat Now
                      </button>
                    </div>
                  </div>
                )}
              </>
            )}

            {stage === 'input' && !loading && (
              <div className="card text-center py-20">
                <Route className="w-16 h-16 mx-auto text-primary-500 mb-4" />
                <h2 className="text-2xl font-bold text-gray-800">Smart Logistics Routing</h2>
                <p className="text-gray-600 mt-2">
                  Enter a request or select cities directly from the map to get started.
                </p>
                <p className="text-sm text-gray-500 mt-4">
                  💡 After optimization, create a manifest to activate AI copilot features
                </p>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* MAP MODAL */}
      {showMap && (
        <MapSelectionModal
          onClose={() => setShowMap(false)}
          onOptimize={handleMapOptimization}
        />
      )}

      {/* CHAT BUTTON */}
      <ChatNavButton onClick={openChatPage} />
    </div>
  );
}

export default Home;