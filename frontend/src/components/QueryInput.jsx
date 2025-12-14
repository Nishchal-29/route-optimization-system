import { Send } from 'lucide-react';

export default function QueryInput({ query, setQuery, onSubmit, loading, disabled }) {
  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      onSubmit();
    }
  };

  return (
    <div className="card">
      <h2 className="text-xl font-semibold mb-4">Enter Logistics Request</h2>
      
      <textarea
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        onKeyPress={handleKeyPress}
        placeholder="E.g., Start from Delhi, visit Mumbai, Bangalore, and Chennai, then end at Kolkata"
        className="input-field min-h-[120px] resize-none"
        disabled={disabled}
      />
      
      <button
        onClick={onSubmit}
        disabled={disabled || !query.trim()}
        className="btn-primary w-full mt-4 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
      >
        {loading ? (
          <>
            <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
            Processing...
          </>
        ) : (
          <>
            <Send className="w-5 h-5" />
            Optimize Route
          </>
        )}
      </button>
    </div>
  );
}