import { useState } from 'react';
import { Send } from 'lucide-react';

export default function ChatInput({ onSend, disabled }) {
  const [text, setText] = useState('');

  const handleSend = () => {
    if (!text.trim() || disabled) return;
    onSend(text);
    setText('');
  };

  return (
    <div className="px-6 py-4 border-t border-white/20 flex gap-3">
      <input
        value={text}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={(e) => e.key === 'Enter' && handleSend()}
        disabled={disabled}
        placeholder="Ask about traffic, weather, priorities or suggest changes..."
        className="
          flex-1 px-4 py-3 rounded-xl
          bg-black/30 text-white placeholder-white/50
          border border-white/10
          outline-none
          focus:border-cyan-400
          disabled:opacity-50
        "
      />

      <button
        onClick={handleSend}
        disabled={disabled}
        className="
          px-4 rounded-xl
          bg-cyan-500 text-black
          hover:bg-cyan-400
          disabled:opacity-50
          flex items-center justify-center
        "
      >
        <Send className="w-5 h-5" />
      </button>
    </div>
  );
}
