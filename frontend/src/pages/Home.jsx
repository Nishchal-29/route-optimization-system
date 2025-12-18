import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Truck, MapPin, Sparkles, Clock, Route } from 'lucide-react';

import QueryInput from '../components/home/QueryInput';
import LocationsDisplay from '../components/home/LocationsDisplay';
import RouteVisualization from '../components/home/RouteVisualization';
import OptimizationResults from '../components/home/OptimizationResults';
import LoadingState from '../components/home/LoadingState';
import ErrorDisplay from '../components/home/ErrorDisplay';
import MapSelectionModal from '../components/home/MapSelectionModal';
import ChatNavButton from '../components/home/ChatNavButton';

import { processLogisticsRequest, optimizeRoute } from '../services/api';

function Home() {
  const navigate = useNavigate();

  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const [extractedLocations, setExtractedLocations] = useState(null);
  const [optimizationResult, setOptimizationResult] = useState(null);

  const [stage, setStage] = useState('input'); // input | processing | results
  const [showMap, setShowMap] = useState(false);

  const exampleQueries = [
    "Start from Delhi, visit Mumbai, Bangalore, and Chennai, then end at Kolkata",
    "I want to travel from delhi to deliver order at pune, jodhpur, banglore, mumbai and jaipur",
    "Begin at Pune, then go to Hyderabad, after that Jaipur, and finally return to Pune",
  ];

  // --------------------------------------------------
  // RESTORE DATA FROM SESSION STORAGE ON REFRESH ONLY
  // --------------------------------------------------
  useEffect(() => {
    const storedContext = sessionStorage.getItem("chatContext");

    if (storedContext) {
      try {
        const parsed = JSON.parse(storedContext);

        if (parsed?.locations && parsed?.optimizedRoute) {
          setExtractedLocations(parsed.locations);
          setOptimizationResult(parsed.optimizedRoute);
          setStage('results');
        }
      } catch (err) {
        console.error("Invalid session storage data", err);
        sessionStorage.removeItem("chatContext");
      }
    }
  }, []);

  // --------------------------------------------------
  // TEXT BASED FLOW
  // --------------------------------------------------
  const handleSubmit = async () => {
    if (!query.trim()) {
      setError('Please enter a logistics request');
      return;
    }

    setLoading(true);
    setError(null);
    setStage('processing');
    setExtractedLocations(null);
    setOptimizationResult(null);

    try {
      const result = await processLogisticsRequest(query);

      setExtractedLocations(result.extracted.parsed_locations);
      setOptimizationResult(result.optimized);
      setStage('results');

      const chatContext = {
        locations: result.extracted.parsed_locations,
        optimizedRoute: result.optimized
      };

      sessionStorage.setItem("chatContext", JSON.stringify(chatContext));

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
    setShowMap(false);
    setLoading(true);
    setError(null);
    setStage('processing');
    setExtractedLocations(null);
    setOptimizationResult(null);

    try {
      const optimized = await optimizeRoute(locations);

      setExtractedLocations(locations);
      setOptimizationResult(optimized);
      setStage('results');

      const chatContext = {
        locations,
        optimizedRoute: optimized
      };

      sessionStorage.setItem("chatContext", JSON.stringify(chatContext));

    } catch (err) {
      setError(err.message || 'Route optimization failed');
      setStage('input');
    } finally {
      setLoading(false);
    }
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

    sessionStorage.removeItem("chatContext");
  };

  // --------------------------------------------------
  // NAVIGATION TO CHAT PAGE
  // --------------------------------------------------
  const openChatPage = () => {
    navigate('/chat');
  };

  return (
    <div className="min-h-screen pb-20">

      {/* HEADER */}
      <header className="bg-gradient-to-r from-primary-600 to-secondary-500 text-white shadow-2xl">
        <div className="container mx-auto px-6 py-8">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className="bg-white/20 p-3 rounded-xl backdrop-blur-sm">
                <Truck className="w-8 h-8" />
              </div>
              <div>
                <h1 className="text-3xl font-bold">AI Logistics Optimizer</h1>
                <p className="text-primary-100 mt-1">
                  Intelligent Multi-City Route Planning with ML
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
                    className="w-full text-left p-3 mb-2 bg-gray-50 rounded-lg hover:bg-primary-50"
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
              <button onClick={handleReset} className="btn-secondary w-full">
                Start New Request
              </button>
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
              </>
            )}

            {stage === 'input' && !loading && (
              <div className="card text-center py-20">
                <Route className="w-16 h-16 mx-auto text-primary-500 mb-4" />
                <h2 className="text-2xl font-bold">Smart Logistics Routing</h2>
                <p className="text-gray-600">
                  Enter a request or select cities directly from the map.
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
