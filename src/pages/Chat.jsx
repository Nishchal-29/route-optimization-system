import { useEffect, useState } from 'react';
import { ChevronUp, ChevronDown, CheckCircle, MapPin, TrendingUp, RefreshCw } from 'lucide-react';
import ChatHeader from '../components/chat/ChatHeader';
import ChatMessages from '../components/chat/ChatMessages';
import ChatInput from '../components/chat/ChatInput';
import TypingIndicator from '../components/chat/TypingIndicator';

import { sendAgentMessage, getAgentStatus } from '../services/api';
import { useSession } from '../hooks/useSession';

export default function Chat() {
  /* ---------------- AGENT STATE ---------------- */
  const [agentStatus, setAgentStatus] = useState(null);
  const [loadingStatus, setLoadingStatus] = useState(true);

  /* ---------------- CHAT STATE ---------------- */
  const initialMessages = () => {
    const stored = sessionStorage.getItem("chatMessages");
    if (stored) {
      try {
        return JSON.parse(stored);
      } catch {
        sessionStorage.removeItem("chatMessages");
      }
    }
    return [
      {
        id: 1,
        role: 'assistant',
        content:
          'Hello 👋 I am LogiBOT, your AI logistics copilot. I can help you with:\n\n' +
          '• Creating and managing delivery routes\n' +
          '• Checking traffic and weather conditions\n' +
          '• Reporting delays and getting recommendations\n' +
          '• Answering questions about your current route\n\n' +
          'How can I assist you today?'
      }
    ];
  };

  const [messages, setMessages] = useState(initialMessages);
  useEffect(() => {
    sessionStorage.setItem("chatMessages", JSON.stringify(messages));
  }, [messages]);

  const [typing, setTyping] = useState(false);
  const sessionId = useSession();

  /* ---------------- LOAD AGENT STATUS ---------------- */

  const loadAgentStatus = async () => {
    if (!sessionId) return;
    try {
      const status = await getAgentStatus(sessionId);
      setAgentStatus(status.data || status);
    } catch (err) {
      console.error('Failed to load agent status:', err);
      setAgentStatus(null);
    } finally {
      setLoadingStatus(false);
    }
  };

  useEffect(() => {
    if (!sessionId) return;
    loadAgentStatus();
  }, [sessionId]);

  /* ---------------- QUICK ACTIONS ---------------- */
  const quickActions = [
    {
      label: '📊 Check Status',
      message: "What's my current status?"
    },
    {
      label: '🚦 Check Traffic',
      message: 'How is the traffic looking right now?'
    },
    {
      label: '🌧️ Weather Alert',
      message: "How is the weather for the next location in my route?"
    },
    {
      label: '📍 Next Stop',
      message: "What's my next stop and ETA?"
    }
  ];

  const handleQuickAction = (message) => {
    handleSend(message);
  };

  /* ---------------- MANUAL REFRESH ---------------- */
  const handleRefreshStatus = () => {
    setLoadingStatus(true);
    loadAgentStatus();
  };

  /* ---------------- SEND MESSAGE ---------------- */
  const handleSend = async (text) => {
    if (!text.trim()) return;

    const userMsg = {
      id: Date.now(),
      role: 'user',
      content: text
    };

    setMessages((prev) => [...prev, userMsg]);
    setTyping(true);

    try {
      const res = await sendAgentMessage(text, sessionId);

      setMessages((prev) => [
        ...prev,
        {
          id: Date.now() + 1,
          role: 'assistant',
          content: res?.agent_response || res?.reply || 'I received your message.'
        }
      ]);

      // Refresh status if the message might have affected the route
      if (
        text.toLowerCase().includes('delay') ||
        text.toLowerCase().includes('complete') ||
        text.toLowerCase().includes('start') ||
        text.toLowerCase().includes('create')
      ) {
        setTimeout(loadAgentStatus, 1000);
      }
    } catch (err) {
      console.error('Chat error:', err);

      setMessages((prev) => [
        ...prev,
        {
          id: Date.now() + 1,
          role: 'assistant',
          content: '⚠️ Unable to process your message right now. Please try again.'
        }
      ]);
    } finally {
      setTyping(false);
    }
  };

  /* ---------------- STATUS DISPLAY COMPONENT ---------------- */
  const RouteStatusCard = () => {
    // 1. State to track if card is expanded or collapsed
    const [isExpanded, setIsExpanded] = useState(true);

    if (!agentStatus || !agentStatus.active) return null;

    const { driver, route_summary, current_location, next_stop } = agentStatus;

    return (
      <div className="border-b border-white/20 bg-emerald-500/10 transition-all duration-300">
        {/* Header - Always Visible */}
        <div className="p-3 flex items-center justify-between">
          <div className="flex items-center gap-3">
            {/* Toggle Button */}
            <button
              onClick={() => setIsExpanded(!isExpanded)}
              className="p-1.5 hover:bg-white/10 rounded-lg text-emerald-300 transition-colors"
              title={isExpanded ? "Collapse" : "Expand"}
            >
              {isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
            </button>

            <div className="flex items-center gap-2">
              <CheckCircle className="w-5 h-5 text-emerald-400" />
              <span className="font-semibold text-emerald-300">Active Route</span>
              
              {/* Show mini-progress when collapsed */}
              {!isExpanded && (
                <span className="text-xs text-white/60 bg-white/10 px-2 py-0.5 rounded-full ml-2">
                  {route_summary.progress_percentage}% Complete
                </span>
              )}
            </div>
          </div>

          <div className="flex items-center gap-2">
            <span className="text-xs text-white/60 hidden sm:inline">Driver: {driver}</span>
            <button
              onClick={handleRefreshStatus}
              className="p-2 hover:bg-white/10 rounded-lg transition-colors"
              title="Refresh Status"
            >
              <RefreshCw className="w-4 h-4 text-white/60" />
            </button>
          </div>
        </div>

        {/* Collapsible Content */}
        {isExpanded && (
          <div className="px-4 pb-4 space-y-3 animate-in slide-in-from-top-2 duration-200">
            {/* Progress Bar */}
            <div className="space-y-1">
              <div className="flex justify-between text-sm">
                <span className="text-white/80">Progress</span>
                <span className="text-white/80 font-semibold">
                  {route_summary.progress_percentage}%
                </span>
              </div>
              <div className="w-full bg-white/20 rounded-full h-2">
                <div
                  className="bg-emerald-400 h-2 rounded-full transition-all duration-500"
                  style={{ width: `${route_summary.progress_percentage}%` }}
                />
              </div>
              <div className="flex justify-between text-xs text-white/60">
                <span>{route_summary.completed} completed</span>
                <span>{route_summary.pending} pending</span>
              </div>
            </div>

            {/* Current & Next Location */}
            <div className="grid grid-cols-2 gap-3 text-sm">
              <div className="bg-white/10 rounded-lg p-2">
                <div className="flex items-center gap-1 text-white/60 mb-1">
                  <MapPin className="w-3 h-3" />
                  <span className="text-xs">Current</span>
                </div>
                <div className="font-semibold text-white truncate">
                  {current_location}
                </div>
              </div>
              <div className="bg-white/10 rounded-lg p-2">
                <div className="flex items-center gap-1 text-white/60 mb-1">
                  <TrendingUp className="w-3 h-3" />
                  <span className="text-xs">Next Stop</span>
                </div>
                <div className="font-semibold text-white truncate">
                  {next_stop}
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    );
};

  /* ---------------- UI ---------------- */
  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-gray-900 via-purple-900 to-gray-900 p-4">
      <div
        className="
          w-full max-w-4xl h-[85vh]
          rounded-3xl
          bg-white/10 backdrop-blur-2xl
          border border-white/20
          shadow-2xl
          flex flex-col
          text-white
          overflow-hidden
        "
      >
        {/* Header */}
        <ChatHeader />

        {/* Route Status Card */}
        <RouteStatusCard />

        {/* Quick Actions */}
        {agentStatus?.active && (
          <div className="p-3 border-b border-white/10 bg-white/5">
            <div className="flex gap-2 overflow-x-auto pb-2 scrollbar-hide">
              {quickActions.map((action, idx) => (
                <button
                  key={idx}
                  onClick={() => handleQuickAction(action.message)}
                  className="
                    px-3 py-1.5 
                    bg-white/10 hover:bg-white/20 
                    rounded-full 
                    text-xs font-medium 
                    whitespace-nowrap
                    transition-all
                    border border-white/20
                    hover:scale-105
                  "
                  disabled={typing}
                >
                  {action.label}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Chat Messages */}
        <div className="flex-1 overflow-y-auto p-4 space-y-3">
          <ChatMessages messages={messages} />
          {typing && <TypingIndicator />}
        </div>

        {/* Input */}
        <div className="p-4 border-t border-white/20 bg-white/5">
          <ChatInput 
            onSend={handleSend} 
            disabled={typing}
            placeholder={
              agentStatus?.active 
                ? "Ask about your route, report issues, or request help..."
                : "Create a route first, or ask me anything..."
            }
          />
        </div>
      </div>
    </div>
  );
}