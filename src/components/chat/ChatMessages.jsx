import { useEffect, useRef } from 'react';
import DOMPurify from 'dompurify';

export default function ChatMessages({ messages }) {
  const endRef = useRef(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const createMarkup = (htmlContent) => {
    return {
      __html: DOMPurify.sanitize(htmlContent, {
        ADD_TAGS: ["iframe"], 
        ADD_ATTR: ["src", "width", "height", "style", "frameborder", "allow", "allowfullscreen", "title"]
      })
    };
  };

  return (
    <div className="flex-1 overflow-y-auto px-6 py-4 space-y-4">
      {messages.map((msg) => (
        <div
          key={msg.id}
          className={`flex ${
            msg.role === 'user' ? 'justify-end' : 'justify-start'
          }`}
        >
          <div
            className={`
              max-w-[85%] // Increased width slightly for maps
              px-4 py-3 rounded-2xl
              text-sm leading-relaxed
              whitespace-pre-wrap // <--- CRITICAL: Preserves line breaks (\n)
              ${
                msg.role === 'user'
                  ? 'bg-gradient-to-r from-primary-600 to-secondary-500 text-white'
                  : 'bg-black/60 text-white border border-white/10 shadow-lg backdrop-blur-md' // Darker bg for map contrast
              }
            `}
          >
            {msg.role === 'user' ? (
              msg.content
            ) : (
              <div 
                className="prose prose-invert max-w-none"
                dangerouslySetInnerHTML={createMarkup(msg.content)} 
              />
            )}
          </div>
        </div>
      ))}
      <div ref={endRef} />
    </div>
  );
}