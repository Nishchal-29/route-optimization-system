import { useState } from "react";
import {
  MapContainer,
  TileLayer,
  Marker,
  Popup,
  useMapEvents,
} from "react-leaflet";
import "leaflet/dist/leaflet.css";
import L from "leaflet";
import { X } from "lucide-react";

/* ---------------- FIX LEAFLET ICONS ---------------- */
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconUrl:
    "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon.png",
  shadowUrl:
    "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png",
});

/* ---------------- MAP CLICK HANDLER ---------------- */
function MapClickHandler({ onAdd }) {
  useMapEvents({
    click(e) {
      onAdd(e.latlng);
    },
  });
  return null;
}

/* ---------------- REVERSE GEOCODING ---------------- */
async function reverseGeocode(lat, lon) {
  const res = await fetch(
    `https://nominatim.openstreetmap.org/reverse?format=jsonv2&lat=${lat}&lon=${lon}`
  );
  const data = await res.json();

  return (
    data.address?.city ||
    data.address?.town ||
    data.address?.village ||
    data.address?.state ||
    "Unknown"
  );
}

/* ---------------- MODAL ---------------- */
export default function MapSelectionModal({ onClose, onOptimize }) {
  const [locations, setLocations] = useState([]);
  const [loading, setLoading] = useState(false);

  async function handleAddLocation({ lat, lng }) {
    const name = await reverseGeocode(lat, lng);

    setLocations((prev) => [
      ...prev,
      {
        id: crypto.randomUUID(),
        name,
        lat,
        lon: lng,
      },
    ]);
  }

  function removeLocation(id) {
    setLocations((prev) => prev.filter((l) => l.id !== id));
  }

  function handleOptimize() {
    if (locations.length < 2) return;
    setLoading(true);
    onOptimize(locations);
  }

  return (
    <div className="fixed inset-0 z-50 bg-black/50 flex items-center justify-center">
      <div className="bg-white w-[90%] h-[90%] rounded-xl shadow-xl relative flex flex-col">

        {/* HEADER */}
        <div className="flex justify-between items-center p-4 border-b">
          <h2 className="text-lg font-semibold">Select Cities from Map</h2>
          <button onClick={onClose}>
            <X />
          </button>
        </div>

        {/* MAP */}
        <div className="flex-1">
          <MapContainer
            center={[20.5937, 78.9629]}
            zoom={5}
            className="h-full w-full"
          >
            <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
            <MapClickHandler onAdd={handleAddLocation} />

            {locations.map((loc, i) => (
              <Marker key={loc.id} position={[loc.lat, loc.lon]}>
                <Popup>
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-medium">
                      {i + 1}. {loc.name}
                    </span>
                    <button
                      onClick={() => removeLocation(loc.id)}
                      className="text-red-600 hover:text-red-800"
                    >
                      ❌
                    </button>
                  </div>
                </Popup>
              </Marker>
            ))}
          </MapContainer>
        </div>

        {/* FOOTER */}
        <div className="p-4 border-t flex justify-between items-center gap-4">
          <div className="flex gap-2 flex-wrap text-sm">
            {locations.length === 0 && (
              <span className="text-gray-500">
                Click on map to add cities
              </span>
            )}

            {locations.map((l, i) => (
              <span
                key={l.id}
                className="bg-gray-100 px-2 py-1 rounded-full flex items-center gap-1"
              >
                {i + 1}. {l.name}
                <button
                  onClick={() => removeLocation(l.id)}
                  className="text-red-500 hover:text-red-700"
                >
                  <X size={12} />
                </button>
              </span>
            ))}
          </div>

          <button
            onClick={handleOptimize}
            disabled={loading || locations.length < 2}
            className="btn-primary disabled:opacity-50"
          >
            {loading ? "Optimizing..." : "Optimize Route"}
          </button>
        </div>

      </div>
    </div>
  );
}
