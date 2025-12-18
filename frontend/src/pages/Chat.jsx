import { useEffect, useState } from 'react';
import ChatHeader from '../components/chat/ChatHeader';
import ChatMessages from '../components/chat/ChatMessages';
import ChatInput from '../components/chat/ChatInput';
import TypingIndicator from '../components/chat/TypingIndicator';
import LocationsDisplay from '../components/home/LocationsDisplay';
import { sendChatMessage } from '../services/api';

export default function Chat() {
  /* ---------------- ROUTE CONTEXT ---------------- */
  const [context, setContext] = useState(null);

  /* ---------------- CHAT STATE ---------------- */
  const [messages, setMessages] = useState([
    {
      id: 1,
      role: 'assistant',
      content:
        'Hello 👋 I am LogiBOT. I can explain why this route was formed (traffic, weather, priorities) and help you modify it.'
    }
  ]);
  const [typing, setTyping] = useState(false);

  /* ---------------- LOAD CONTEXT FROM LOCAL STORAGE ---------------- */
  useEffect(() => {
    const stored = sessionStorage.getItem('chatContext');

    if (stored) {
      try {
        setContext(JSON.parse(stored));
      } catch (err) {
        console.error('Invalid chatContext in localStorage');
      }
    }
  }, []);

  /* ---------------- SEND MESSAGE ---------------- */
  const handleSend = async (text) => {
  if (!text.trim() || !context) return;

  const userMsg = {
    id: Date.now(),
    role: 'user',
    content: text
  };

  setMessages((prev) => [...prev, userMsg]);
  setTyping(true);

  try {
    const res = await sendChatMessage(text, context);

    setMessages((prev) => [
      ...prev,
      {
        id: Date.now() + 1,
        role: 'assistant',
        content:
          res?.reply ||
          'Here is the explanation based on traffic, weather, and route constraints.'
      }
    ]);
  } catch (err) {
    console.error("Chat error:", err);

    setMessages((prev) => [
      ...prev,
      {
        id: Date.now() + 1,
        role: 'assistant',
        content: '⚠️ Unable to fetch explanation right now.'
      }
    ]);
  } finally {
    setTyping(false);
  }
};


  /* ---------------- UI ---------------- */
  return (
    <div className="min-h-screen flex items-center justify-center bg-black/60">
      <div
        className="
          w-[90%] max-w-4xl h-[80vh]
          rounded-3xl
          bg-white/10 backdrop-blur-2xl
          border border-white/20
          shadow-2xl
          flex flex-col
          text-white
        "
      >
        {/* Header */}
        <ChatHeader />

        {/* -------- CURRENT ROUTE (FROM LOCAL STORAGE) -------- */}
        {context?.locations && context?.optimizedRoute && (
          <div className="p-4 border-b border-white/20 max-h-44 overflow-auto">
            <h3 className="font-semibold mb-2 text-white/90">
              📍 Current Optimized Route
            </h3>

            <LocationsDisplay
              locations={context.locations}
              optimizedRoute={context.optimizedRoute}
            />
          </div>
        )}

        {/* -------- CHAT MESSAGES -------- */}
        <div className="flex-1 overflow-y-auto p-4 space-y-3">
          <ChatMessages messages={messages} />
          {typing && <TypingIndicator />}
        </div>

        {/* -------- INPUT -------- */}
        <div className="p-4 border-t border-white/20">
          <ChatInput onSend={handleSend} disabled={typing || !context} />
        </div>
      </div>
    </div>
  );
}
