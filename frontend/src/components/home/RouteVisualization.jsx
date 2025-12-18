import { useEffect } from 'react';
import { MapContainer, TileLayer, Marker, Popup, Polyline, useMap } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';

// Fix for default marker icons in React-Leaflet
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon-2x.png',
  iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png',
});

// Create custom numbered marker icons
const createNumberedIcon = (number, isStart = false, isEnd = false) => {
  let color = '#667eea';
  if (isStart) color = '#10b981';
  if (isEnd) color = '#ef4444';

  return L.divIcon({
    className: 'custom-div-icon',
    html: `
      <div style="
        background-color: ${color};
        width: 32px;
        height: 32px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        color: white;
        font-weight: bold;
        font-size: 14px;
        border: 3px solid white;
        box-shadow: 0 2px 8px rgba(0,0,0,0.3);
      ">
        ${number}
      </div>
    `,
    iconSize: [32, 32],
    iconAnchor: [16, 32],
  });
};

// Component to fit map bounds
function MapBoundsHandler({ locations }) {
  const map = useMap();

  useEffect(() => {
    if (locations && locations.length > 0) {
      const bounds = locations.map(loc => [loc.lat, loc.lon]);
      map.fitBounds(bounds, { padding: [50, 50] });
    }
  }, [locations, map]);

  return null;
}

export default function RouteVisualization({ locations, optimizedRoute }) {
  if (!locations || locations.length === 0) return null;

  // Handle your API response format - optimized_route contains the ordered locations
  let displayLocations = [];
  
  if (optimizedRoute?.optimized_route && Array.isArray(optimizedRoute.optimized_route)) {
    // Use the optimized_route array directly as it contains full location objects
    displayLocations = optimizedRoute.optimized_route;
  } else if (optimizedRoute?.route_sequence || optimizedRoute?.routeSequence) {
    // Fallback: map route sequence to location objects
    const routeSequence = optimizedRoute.route_sequence || optimizedRoute.routeSequence;
    displayLocations = routeSequence.map(cityName => 
      locations.find(loc => loc.name.toLowerCase() === cityName.toLowerCase())
    ).filter(Boolean);
  } else {
    // Last resort: use original locations sorted by visit_sequence
    displayLocations = [...locations].sort((a, b) => a.visit_sequence - b.visit_sequence);
  }

  // Create polyline coordinates
  const polylinePositions = displayLocations.map(loc => [loc.lat, loc.lon]);

  // Calculate center for initial map view
  const center = displayLocations.length > 0 
    ? [displayLocations[0].lat, displayLocations[0].lon]
    : [20.5937, 78.9629]; // India center as fallback

  return (
    <div className="card">
      <h3 className="text-xl font-bold mb-4">Route Visualization</h3>
      
      <div className="rounded-lg overflow-hidden shadow-lg border-2 border-gray-200" style={{ height: '500px' }}>
        <MapContainer
          center={center}
          zoom={5}
          style={{ height: '100%', width: '100%' }}
          scrollWheelZoom={true}
        >
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />
          
          {/* Markers for each location */}
          {displayLocations.map((location, idx) => {
            const isStart = idx === 0;
            const isEnd = idx === displayLocations.length - 1;
            
            return (
              <Marker
                key={idx}
                position={[location.lat, location.lon]}
                icon={createNumberedIcon(idx + 1, isStart, isEnd)}
              >
                <Popup>
                  <div className="text-center">
                    <p className="font-bold text-lg capitalize">{location.name}</p>
                    <p className="text-sm text-gray-600">Stop #{idx + 1}</p>
                    <p className="text-xs text-gray-500 mt-1">
                      {location.lat.toFixed(4)}, {location.lon.toFixed(4)}
                    </p>
                    {location.original_sequence_req && (
                      <p className="text-xs text-gray-500 mt-1">
                        Original Order: {location.original_sequence_req}
                      </p>
                    )}
                    {isStart && (
                      <span className="inline-block mt-2 px-2 py-1 bg-green-100 text-green-700 text-xs font-semibold rounded">
                        Starting Point
                      </span>
                    )}
                    {isEnd && (
                      <span className="inline-block mt-2 px-2 py-1 bg-red-100 text-red-700 text-xs font-semibold rounded">
                        Final Destination
                      </span>
                    )}
                  </div>
                </Popup>
              </Marker>
            );
          })}
          
          {/* Polyline connecting all locations */}
          {polylinePositions.length > 1 && (
            <Polyline
              positions={polylinePositions}
              color="#667eea"
              weight={3}
              opacity={0.7}
              dashArray="10, 10"
            />
          )}
          
          {/* Auto-fit bounds */}
          <MapBoundsHandler locations={displayLocations} />
        </MapContainer>
      </div>

      {/* Legend */}
      <div className="mt-4 flex items-center justify-center gap-6 text-sm">
        <div className="flex items-center gap-2">
          <div className="w-6 h-6 bg-green-500 rounded-full border-2 border-white shadow" />
          <span className="text-gray-600">Start</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-6 h-6 bg-primary-500 rounded-full border-2 border-white shadow" />
          <span className="text-gray-600">Waypoints</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-6 h-6 bg-red-500 rounded-full border-2 border-white shadow" />
          <span className="text-gray-600">End</span>
        </div>
      </div>

      {/* Route Summary */}
      {displayLocations.length > 0 && (
        <div className="mt-4 p-3 bg-gray-50 rounded-lg text-sm text-gray-600">
          <p className="font-semibold text-gray-800 mb-1">Route Summary:</p>
          <p className="capitalize">
            {displayLocations.map(loc => loc.name).join(' → ')}
          </p>
        </div>
      )}
    </div>
  );
}