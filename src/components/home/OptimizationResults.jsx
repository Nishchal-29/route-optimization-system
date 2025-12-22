import { Route, Clock, Navigation, TrendingDown, AlertTriangle } from 'lucide-react';

export default function OptimizationResults({ result }) {
  if (!result) return null;
  // Extract route sequence from optimized_route array
  const routeSequence = Array.isArray(result.optimized_route)
  ? result.optimized_route
  : result.route_sequence || result.routeSequence || result.route || [];

  return (
    <div className="space-y-6">
      {/* Metrics Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="card bg-gradient-to-br from-primary-500 to-primary-600 text-white">
          <div className="flex items-center justify-between mb-2">
            <p className="text-primary-100 text-sm font-medium">Total Distance</p>
            <Navigation className="w-5 h-5 text-primary-200" />
          </div>
          <p className="text-3xl font-bold">{result.total_distance_km} km</p>
          <p className="text-primary-200 text-xs mt-2">Optimized route distance</p>
        </div>

        <div className="card bg-gradient-to-br from-secondary-500 to-purple-600 text-white">
          <div className="flex items-center justify-between mb-2">
            <p className="text-purple-100 text-sm font-medium">Estimated Time</p>
            <Clock className="w-5 h-5 text-purple-200" />
          </div>
          <p className="text-3xl font-bold">{result.total_duration_hours} hours</p>
          <p className="text-purple-200 text-xs mt-2">Including stops</p>
        </div>
      </div>

      {/* Optimized Route Sequence */}
      <div className="card">
        <div className="flex items-center gap-2 mb-6">
          <div className="w-10 h-10 bg-primary-100 rounded-lg flex items-center justify-center">
            <TrendingDown className="w-5 h-5 text-primary-600" />
          </div>
          <div>
            <h3 className="text-xl font-bold text-gray-800">Optimized Route</h3>
            <p className="text-sm text-gray-500">AI-recommended delivery sequence</p>
          </div>
        </div>

        {routeSequence.length > 0 ? (
          <div className="space-y-3">
            {routeSequence.map((location, idx) => (
              <div key={idx} className="relative">
                <div className="flex items-center gap-4 p-4 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors duration-200">
                  <div className="flex items-center justify-center w-10 h-10 bg-primary-500 text-white rounded-full font-bold flex-shrink-0">
                    {idx + 1}
                  </div>
                  <div className="flex-1">
                    <p className="font-semibold text-gray-800 capitalize">{location}</p>
                    {idx < routeSequence.length - 1 && (
                      <p className="text-xs text-gray-500 mt-1">
                        Next: <span className="capitalize">{routeSequence[idx + 1]}</span>
                      </p>
                    )}
                  </div>
                  {idx === 0 && (
                    <span className="px-3 py-1 bg-green-100 text-green-700 text-xs font-semibold rounded-full">
                      Start
                    </span>
                  )}
                  {idx === routeSequence.length - 1 && (
                    <span className="px-3 py-1 bg-red-100 text-red-700 text-xs font-semibold rounded-full">
                      End
                    </span>
                  )}
                </div>
                {idx < routeSequence.length - 1 && (
                  <div className="absolute left-9 top-[60px] w-0.5 h-3 bg-primary-300" />
                )}
              </div>
            ))}
          </div>
        ) : (
          <div className="text-center py-8 text-gray-500">
            <Route className="w-12 h-12 mx-auto mb-3 opacity-50" />
            <p>No route sequence available</p>
          </div>
        )}

      </div>
    </div>
  );
}