// ChatNavButton.jsx
import { Map } from 'lucide-react';

export default function ChatNavButton({ onClick }) {
  return (
    <div className="fixed bottom-6 right-6 z-50 group">
      {/* Hover Text */}
      <div
        className="
          absolute right-16 top-1/2 -translate-y-1/2
          whitespace-nowrap
          bg-black/80 backdrop-blur-md
          text-white text-sm font-medium
          px-4 py-2 rounded-full
          opacity-0 scale-95
          group-hover:opacity-100 group-hover:scale-100
          transition-all duration-300
          shadow-lg
        "
      >
        🤖 Chat with our <span className="font-semibold">LogiBOT</span>
      </div>

      {/* Circular Button */}
      <button
        onClick={onClick} // <-- use the prop here
        className="
          w-14 h-14
          rounded-full
          bg-primary-600
          text-white
          shadow-xl
          flex items-center justify-center
          hover:bg-primary-700
          transition-all
          z-50
        "
        aria-label="Open Chat"
      >
        <Map className="w-6 h-6" />
      </button>
    </div>
  );
}
