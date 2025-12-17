import { useState } from 'react';
import { Truck, MapPin, Sparkles, Clock, Route } from 'lucide-react';

import QueryInput from './components/QueryInput';
import LocationsDisplay from './components/LocationsDisplay';
import RouteVisualization from './components/RouteVisualization';
import OptimizationResults from './components/OptimizationResults';
import LoadingState from './components/LoadingState';
import ErrorDisplay from './components/ErrorDisplay';
import MapSelectionModal from './components/MapSelectionModal';

import { processLogisticsRequest, optimizeRoute } from './services/api';

function App() {
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

  /* ---------------- TEXT BASED FLOW ---------------- */

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
    } catch (err) {
      setError(err.message || 'Something went wrong');
      setStage('input');
    } finally {
      setLoading(false);
    }
  };

  /* ---------------- MAP BASED FLOW (CORRECT) ---------------- */

  const handleMapOptimization = async (locations) => {
    // 1️⃣ Close map immediately
    setShowMap(false);

    // 2️⃣ Trigger loading UI
    setLoading(true);
    setError(null);
    setStage('processing');
    setExtractedLocations(null);
    setOptimizationResult(null);

    try {
      // 3️⃣ Call SAME optimize endpoint
      const optimized = await optimizeRoute(locations);

      setExtractedLocations(locations);
      setOptimizationResult(optimized);
      setStage('results');
    } catch (err) {
      setError(err.message || 'Route optimization failed');
      setStage('input');
    } finally {
      setLoading(false);
    }
  };

  const handleReset = () => {
    setQuery('');
    setExtractedLocations(null);
    setOptimizationResult(null);
    setError(null);
    setStage('input');
  };

  return (
    <div className="min-h-screen pb-20">
      {/* ---------------- HEADER ---------------- */}
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

      {/* ---------------- MAIN ---------------- */}
      <div className="container mx-auto px-6 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">

          {/* -------- LEFT PANEL -------- */}
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

          {/* -------- RIGHT PANEL -------- */}
          <div className="lg:col-span-2 space-y-6">
            {error && (
              <ErrorDisplay error={error} onDismiss={() => setError(null)} />
            )}

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
                <h2 className="text-2xl font-bold mb-2">
                  Smart Logistics Routing
                </h2>
                <p className="text-gray-600">
                  Enter a request or select cities directly from the map.
                </p>
              </div>
            )}
          </div>
        </div>

        {/* -------- INFO CARDS -------- */}
        <div className="mt-12 grid grid-cols-1 md:grid-cols-3 gap-6">
          {[
            { icon: Sparkles, title: "AI Parsing", text: "Understands natural language" },
            { icon: Route, title: "Genetic Optimization", text: "Finds best possible route" },
            { icon: Clock, title: "Fast Results", text: "Near real-time computation" },
          ].map((item, i) => (
            <div key={i} className="card text-center">
              <item.icon className="w-10 h-10 mx-auto text-primary-500 mb-3" />
              <h3 className="font-semibold">{item.title}</h3>
              <p className="text-sm text-gray-600">{item.text}</p>
            </div>
          ))}
        </div>
      </div>

      {/* ---------------- MAP MODAL ---------------- */}
      {showMap && (
        <MapSelectionModal
          onClose={() => setShowMap(false)}
          onOptimize={handleMapOptimization}
        />
      )}
    </div>
  );
}

export default App;
