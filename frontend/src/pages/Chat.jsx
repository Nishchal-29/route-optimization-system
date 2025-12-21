import { useEffect, useState } from 'react';
import { AlertCircle, CheckCircle, MapPin, TrendingUp, RefreshCw } from 'lucide-react';
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
  const [messages, setMessages] = useState([
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
  ]);
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

  // Poll for status updates every 60 seconds
  const interval = setInterval(loadAgentStatus, 60000);
  return () => clearInterval(interval);
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
      message: "I'm delayed by 15 minutes due to heavy rain"
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
    if (loadingStatus) {
      return (
        <div className="p-4 border-b border-white/20 bg-white/5">
          <div className="animate-pulse flex space-x-4">
            <div className="flex-1 space-y-2">
              <div className="h-4 bg-white/20 rounded w-3/4"></div>
              <div className="h-4 bg-white/20 rounded w-1/2"></div>
            </div>
          </div>
        </div>
      );
    }

    if (!agentStatus || !agentStatus.active) {
      return (
        <div className="p-4 border-b border-white/20 bg-amber-500/10">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 text-amber-300">
              <AlertCircle className="w-5 h-5" />
              <span className="font-semibold">No Active Route</span>
            </div>
            <button
              onClick={handleRefreshStatus}
              className="p-2 hover:bg-white/10 rounded-lg transition-colors"
              title="Refresh Status"
            >
              <RefreshCw className="w-4 h-4 text-white/60" />
            </button>
          </div>
          <p className="text-sm text-white/70 mt-2">
            Create a delivery manifest from the home page to start tracking.
          </p>
        </div>
      );
    }

    const { route_summary, current_location, next_stop, driver } = agentStatus;

    return (
      <div className="p-4 border-b border-white/20 bg-emerald-500/10 space-y-3">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <CheckCircle className="w-5 h-5 text-emerald-400" />
            <span className="font-semibold text-emerald-300">Active Route</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-xs text-white/60">Driver: {driver}</span>
            <button
              onClick={handleRefreshStatus}
              className="p-2 hover:bg-white/10 rounded-lg transition-colors"
              title="Refresh Status"
            >
              <RefreshCw className="w-4 h-4 text-white/60" />
            </button>
          </div>
        </div>

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