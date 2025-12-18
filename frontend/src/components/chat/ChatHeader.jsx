import { ArrowLeft, Bot } from 'lucide-react';

export default function ChatHeader() {
  return (
    <div className="flex items-center px-6 py-4 border-b border-white/20">
      
      {/* Back Button */}
      <button
        onClick={() => window.history.back()}
        className="flex items-center gap-2 text-white/80 hover:text-white transition"
      >
        <ArrowLeft className="w-5 h-5" />
        <span className="text-sm">Back</span>
      </button>

      {/* Title */}
      <div className="ml-auto flex items-center gap-2">
        <Bot className="w-5 h-5 text-cyan-400" />
        <span className="font-semibold tracking-wide">
          LogiBOT · Route Intelligence
        </span>
      </div>
    </div>
  );
}
