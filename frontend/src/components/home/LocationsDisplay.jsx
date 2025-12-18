import { MapPin, CheckCircle } from 'lucide-react';

export default function LocationsDisplay({ locations, optimizedRoute }) {
  if (!locations || locations.length === 0) return null;

  // Determine if we should show optimized order or original order
  let displayLocations = [];
  let isOptimized = false;

  if (optimizedRoute?.optimized_route && Array.isArray(optimizedRoute.optimized_route)) {
    // Show optimized route order
    displayLocations = optimizedRoute.optimized_route;
    isOptimized = true;
  } else {
    // Show original detected order
    displayLocations = [...locations].sort((a, b) => a.visit_sequence - b.visit_sequence);
  }

  return (
    <div className="card">
      <div className="flex items-center gap-2 mb-4">
        <CheckCircle className="w-5 h-5 text-green-500" />
        <h3 className="text-lg font-semibold">
          {isOptimized ? 'Optimized Order' : 'Detected Locations'}
        </h3>
      </div>
      
      <div className="space-y-2">
        {displayLocations.map((location, idx) => (
          <div
            key={idx}
            className={`flex items-start gap-3 p-3 rounded-lg border ${
              isOptimized 
                ? 'bg-gradient-to-r from-green-50 to-transparent border-green-200' 
                : 'bg-gradient-to-r from-primary-50 to-transparent border-primary-100'
            }`}
          >
            <div className={`w-8 h-8 text-white rounded-full flex items-center justify-center font-bold text-sm flex-shrink-0 ${
              isOptimized ? 'bg-green-500' : 'bg-primary-500'
            }`}>
              {idx + 1}
            </div>
            <div className="flex-1 min-w-0">
              <p className="font-semibold text-gray-800 capitalize">
                {location.name}
              </p>
              <div className="flex items-center gap-1 text-xs text-gray-500 mt-1">
                <MapPin className="w-3 h-3" />
                <span>
                  {location.lat.toFixed(4)}, {location.lon.toFixed(4)}
                </span>
              </div>
              {location.original_sequence_req && isOptimized && (
                <div className="mt-1">
                  <span className="text-xs text-gray-500">
                    Original position: {location.original_sequence_req}
                  </span>
                </div>
              )}
            </div>
            {idx === 0 && (
              <span className="px-2 py-1 bg-green-100 text-green-700 text-xs font-semibold rounded-full">
                Start
              </span>
            )}
            {idx === displayLocations.length - 1 && idx !== 0 && (
              <span className="px-2 py-1 bg-red-100 text-red-700 text-xs font-semibold rounded-full">
                End
              </span>
            )}
          </div>
        ))}
      </div>
      
      <div className={`mt-4 p-3 rounded-lg border ${
        isOptimized 
          ? 'bg-green-50 border-green-100' 
          : 'bg-blue-50 border-blue-100'
      }`}>
        <p className={`text-sm ${isOptimized ? 'text-green-800' : 'text-blue-800'}`}>
          {isOptimized 
            ? `✓ Showing optimized route with ${displayLocations.length} stops` 
            : `✓ Found ${locations.length} location${locations.length !== 1 ? 's' : ''} in your request`
          }
        </p>
      </div>
    </div>
  );
}