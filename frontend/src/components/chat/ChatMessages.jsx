import { useEffect, useRef } from 'react';

export default function ChatMessages({ messages }) {
  const endRef = useRef(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

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
              max-w-[75%]
              px-4 py-3 rounded-2xl
              text-sm leading-relaxed
              ${
                msg.role === 'user'
                  ? 'bg-gradient-to-r from-primary-600 to-secondary-500 text-white'
                  : 'bg-black/40 text-white border border-white/10'
              }
            `}
          >
            {msg.content}
          </div>
        </div>
      ))}
      <div ref={endRef} />
    </div>
  );
}
