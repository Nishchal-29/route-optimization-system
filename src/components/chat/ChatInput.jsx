import { useState } from 'react';
import { Send } from 'lucide-react';

export default function ChatInput({ onSend, disabled = false, placeholder = "Type your message..." }) {
  const [input, setInput] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();
    if (input.trim() && !disabled) {
      onSend(input.trim());
      setInput('');
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="flex gap-2">
      <input
        type="text"
        value={input}
        onChange={(e) => setInput(e.target.value)}
        onKeyPress={handleKeyPress}
        placeholder={placeholder}
        disabled={disabled}
        className="
          flex-1 
          px-4 py-3 
          bg-white/10 
          border border-white/20 
          rounded-xl 
          text-white 
          placeholder-white/50
          focus:outline-none 
          focus:ring-2 
          focus:ring-primary-500/50
          disabled:opacity-50 
          disabled:cursor-not-allowed
        "
      />
      <button
        type="submit"
        disabled={disabled || !input.trim()}
        className="
          px-6 py-3 
          bg-primary-500 
          hover:bg-primary-600 
          text-white 
          rounded-xl 
          transition-colors
          disabled:opacity-50 
          disabled:cursor-not-allowed
          flex items-center gap-2
        "
      >
        <Send className="w-4 h-4" />
        <span className="hidden sm:inline">Send</span>
      </button>
    </form>
  );
}
