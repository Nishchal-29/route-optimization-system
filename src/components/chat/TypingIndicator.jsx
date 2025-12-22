export default function TypingIndicator() {
  return (
    <div className="px-6 pb-2 text-sm text-white/70">
      <div className="flex items-center gap-2">
        <span className="animate-pulse">LogiBOT is thinking</span>
        <span className="flex gap-1">
          <span className="w-1 h-1 bg-white rounded-full animate-bounce" />
          <span className="w-1 h-1 bg-white rounded-full animate-bounce delay-150" />
          <span className="w-1 h-1 bg-white rounded-full animate-bounce delay-300" />
        </span>
      </div>
    </div>
  );
}
