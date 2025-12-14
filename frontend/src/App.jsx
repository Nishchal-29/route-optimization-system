import { useState } from 'react';
import { Truck, MapPin, Sparkles, Clock, Route, AlertCircle } from 'lucide-react';
import QueryInput from './components/QueryInput';
import LocationsDisplay from './components/LocationsDisplay';
import RouteVisualization from './components/RouteVisualization';
import OptimizationResults from './components/OptimizationResults';
import LoadingState from './components/LoadingState';
import ErrorDisplay from './components/ErrorDisplay';
import { processLogisticsRequest } from './services/api';

function App() {
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [extractedLocations, setExtractedLocations] = useState(null);
  const [optimizationResult, setOptimizationResult] = useState(null);
  const [stage, setStage] = useState('input'); // input, processing, results

  // Example queries
  const exampleQueries = [
    "Start from Delhi, visit Mumbai, Bangalore, and Chennai, then end at Kolkata",
    "I want to travel from delhi to deliver order at pune, jodhpur, banglore, mumbai and jaipur",
    "Begin at Pune, then go to Hyderabad, after that Jaipur, and finally return to Pune",
  ];

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
      
      console.log('Optimization Result:', result.optimized);
    } catch (err) {
      setError(err.message);
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

  const handleExampleClick = (example) => {
    setQuery(example);
  };

  return (
    <div className="min-h-screen pb-20">
      {/* Header */}
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

      <div className="container mx-auto px-6 py-8">
        {/* Main Content Area */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Left Panel - Input & Controls */}
          <div className="lg:col-span-1 space-y-6">
            <QueryInput
              query={query}
              setQuery={setQuery}
              onSubmit={handleSubmit}
              loading={loading}
              disabled={loading}
            />

            {/* Example Queries */}
            {stage === 'input' && (
              <div className="card">
                <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
                  <MapPin className="w-5 h-5 text-primary-500" />
                  Example Queries
                </h3>
                <div className="space-y-2">
                  {exampleQueries.map((example, idx) => (
                    <button
                      key={idx}
                      onClick={() => handleExampleClick(example)}
                      className="w-full text-left p-3 bg-gray-50 hover:bg-primary-50 rounded-lg text-sm transition-colors duration-200 border border-transparent hover:border-primary-200"
                    >
                      {example}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* Locations Display - Pass optimizationResult */}
            {extractedLocations && (
              <LocationsDisplay 
                locations={extractedLocations} 
                optimizedRoute={optimizationResult}
              />
            )}

            {/* Reset Button */}
            {stage === 'results' && (
              <button
                onClick={handleReset}
                className="btn-secondary w-full"
              >
                Start New Request
              </button>
            )}
          </div>

          {/* Right Panel - Visualization & Results */}
          <div className="lg:col-span-2 space-y-6">
            {/* Error Display */}
            {error && <ErrorDisplay error={error} onDismiss={() => setError(null)} />}

            {/* Loading State */}
            {loading && <LoadingState />}

            {/* Results */}
            {stage === 'results' && !loading && (
              <>
                <OptimizationResults result={optimizationResult} />
                <RouteVisualization
                  locations={extractedLocations}
                  optimizedRoute={optimizationResult}
                />
              </>
            )}

            {/* Initial State */}
            {stage === 'input' && !loading && !error && (
              <div className="card text-center py-20">
                <div className="w-24 h-24 bg-primary-100 rounded-full flex items-center justify-center mx-auto mb-6">
                  <Route className="w-12 h-12 text-primary-500" />
                </div>
                <h2 className="text-2xl font-bold text-gray-800 mb-3">
                  Welcome to AI Logistics Optimizer
                </h2>
                <p className="text-gray-600 max-w-md mx-auto mb-6">
                  Enter your delivery request in natural language and let our AI 
                  find the most efficient route for you.
                </p>
                <div className="flex items-center justify-center gap-4 text-sm text-gray-500">
                  <div className="flex items-center gap-2">
                    <Sparkles className="w-4 h-4" />
                    <span>AI-Powered Parsing</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <Clock className="w-4 h-4" />
                    <span>Real-time Optimization</span>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Info Cards */}
        <div className="mt-12 grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="card text-center">
            <div className="w-12 h-12 bg-primary-100 rounded-full flex items-center justify-center mx-auto mb-4">
              <Sparkles className="w-6 h-6 text-primary-500" />
            </div>
            <h3 className="font-semibold text-lg mb-2">AI Understanding</h3>
            <p className="text-gray-600 text-sm">
              Our AI understands natural language and extracts locations with proper sequencing
            </p>
          </div>
          <div className="card text-center">
            <div className="w-12 h-12 bg-primary-100 rounded-full flex items-center justify-center mx-auto mb-4">
              <Route className="w-6 h-6 text-primary-500" />
            </div>
            <h3 className="font-semibold text-lg mb-2">Smart Routing</h3>
            <p className="text-gray-600 text-sm">
              Genetic algorithm optimizes your route for minimum distance and time
            </p>
          </div>
          <div className="card text-center">
            <div className="w-12 h-12 bg-primary-100 rounded-full flex items-center justify-center mx-auto mb-4">
              <Clock className="w-6 h-6 text-primary-500" />
            </div>
            <h3 className="font-semibold text-lg mb-2">Real-time Results</h3>
            <p className="text-gray-600 text-sm">
              Get instant route optimization with detailed distance and time estimates
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;