import { useState, useRef, useEffect } from 'react';
import { X, Send, MessageCircle, TrendingUp, TrendingDown } from 'lucide-react';
import { GlassCard } from './GlassCard';
import { Avatar } from './Avatar';
import { ScorePill } from './ScorePill';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { mockAssets, mockKOLs } from '../data/mockData';

interface Message {
  id: string;
  type: 'user' | 'assistant';
  content: string;
  data?: any;
}

export function ChatBot() {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputValue, setInputValue] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSend = () => {
    if (!inputValue.trim()) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      type: 'user',
      content: inputValue,
    };

    setMessages(prev => [...prev, userMessage]);

    setTimeout(() => {
      const assistantMessage = generateResponse(inputValue);
      setMessages(prev => [...prev, assistantMessage]);
    }, 500);

    setInputValue('');
  };

  const generateResponse = (query: string): Message => {
    const lowerQuery = query.toLowerCase();

    if (lowerQuery.includes('bitcoin') || lowerQuery.includes('btc')) {
      if (lowerQuery.includes('who') || lowerQuery.includes('calling')) {
        return {
          id: (Date.now() + 1).toString(),
          type: 'assistant',
          content: "Two reliable KOLs have called BTC bullish in the last 24h:",
          data: {
            type: 'kol-calls',
            kols: [
              { id: 'willy-woo', call: 'Strong accumulation', score: 81 },
              { id: 'michael-saylor', call: '5,000 more BTC bought', score: 87 },
            ],
          },
        };
      }

      return {
        id: (Date.now() + 1).toString(),
        type: 'assistant',
        content: "Here's the live picture for Bitcoin:",
        data: {
          type: 'asset-card',
          asset: 'BTC',
        },
      };
    }

    if (lowerQuery.includes('ethereum') || lowerQuery.includes('eth')) {
      return {
        id: (Date.now() + 1).toString(),
        type: 'assistant',
        content: "Here's the live picture for Ethereum:",
        data: {
          type: 'asset-card',
          asset: 'ETH',
        },
      };
    }

    if (lowerQuery.includes('kol') || lowerQuery.includes('reliable') || lowerQuery.includes('trust')) {
      return {
        id: (Date.now() + 1).toString(),
        type: 'assistant',
        content: "Top 3 most reliable KOLs right now are Willy Woo (81%), Michael Saylor (87%), and Raoul Pal (76%). All have verified wallets and strong track records.",
      };
    }

    return {
      id: (Date.now() + 1).toString(),
      type: 'assistant',
      content: "I can help you track KOL calls, check asset prices, verify wallet holdings, and analyze market sentiment. Try asking: 'How is Bitcoin doing?' or 'Who's calling Ethereum?'",
    };
  };

  const renderMessageData = (data: any) => {
    if (!data) return null;

    if (data.type === 'asset-card') {
      const asset = mockAssets[data.asset];
      if (!asset) return null;

      const isPositive = asset.change24h > 0;

      return (
        <GlassCard className="p-4 my-2 bg-white/10">
          <div className="grid grid-cols-2 gap-3 text-sm mb-3">
            <div>
              <div className="text-white/60 text-xs mb-1">Price</div>
              <div className="font-semibold text-white">${asset.price.toLocaleString()}</div>
            </div>
            <div>
              <div className="text-white/60 text-xs mb-1">30d change</div>
              <div className={`font-semibold ${isPositive ? 'text-green-400' : 'text-red-400'}`}>
                {isPositive ? '+' : ''}{asset.change24h}%
              </div>
            </div>
            <div>
              <div className="text-white/60 text-xs mb-1">24h volume</div>
              <div className="font-semibold text-white">{asset.volume24h}</div>
            </div>
            <div>
              <div className="text-white/60 text-xs mb-1">Trend</div>
              <div className="font-semibold text-green-400">Strong uptrend</div>
            </div>
          </div>
          <p className="text-xs text-white/70 leading-relaxed">
            Quick read: momentum is strong, volume is rising, and on-chain accumulation is happening.
            Multiple high-accuracy KOLs are bullish.
          </p>
        </GlassCard>
      );
    }

    if (data.type === 'kol-calls') {
      return (
        <div className="my-2 space-y-2">
          {data.kols.map((item: any) => {
            const kol = mockKOLs[item.id];
            if (!kol) return null;

            return (
              <GlassCard key={item.id} className="p-3 bg-white/10">
                <div className="flex items-center gap-3">
                  <Avatar initials={kol.initials} size="sm" tier={kol.tier} />
                  <div className="flex-1">
                    <div className="font-semibold text-white text-sm">{kol.name}</div>
                    <div className="text-xs text-white/60">"{item.call}"</div>
                  </div>
                  <ScorePill score={item.score} tier={kol.tier} size="sm" />
                </div>
              </GlassCard>
            );
          })}
          <p className="text-xs text-white/70 mt-2">
            Saylor's wallet shows verified holdings of 252,220 BTC. He's putting money where his mouth is.
          </p>
        </div>
      );
    }

    return null;
  };

  if (!isOpen) {
    return (
      <button
        onClick={() => setIsOpen(true)}
        className="fixed bottom-4 right-4 sm:bottom-6 sm:right-6 w-12 h-12 sm:w-14 sm:h-14 bg-gradient-to-r from-purple-500 to-violet-600 rounded-full shadow-lg shadow-purple-500/50 flex items-center justify-center hover:shadow-purple-500/70 transition-all duration-300 z-50"
      >
        <MessageCircle className="w-5 h-5 sm:w-6 sm:h-6 text-white" />
      </button>
    );
  }

  return (
    <div className="fixed bottom-0 right-0 sm:bottom-6 sm:right-6 w-full h-full sm:w-[420px] lg:w-[480px] sm:h-[600px] z-50">
      <GlassCard className="h-full flex flex-col">
        <div className="p-4 border-b border-white/10 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-full bg-gradient-to-br from-purple-500 to-violet-600 flex items-center justify-center shadow-lg shadow-purple-500/50">
              <span className="text-white font-bold text-sm">TT</span>
            </div>
            <div>
              <div className="font-semibold text-white text-sm">TrustTrace Assistant</div>
              <div className="text-xs text-green-400 flex items-center gap-1">
                <div className="w-2 h-2 rounded-full bg-green-400"></div>
                Live data via Binance
              </div>
            </div>
          </div>
          <button
            onClick={() => setIsOpen(false)}
            className="text-white/60 hover:text-white transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {messages.length === 0 && (
            <div className="text-center py-12">
              <div className="w-16 h-16 rounded-full bg-gradient-to-br from-purple-500 to-violet-600 mx-auto mb-4 flex items-center justify-center shadow-lg shadow-purple-500/50">
                <MessageCircle className="w-8 h-8 text-white" />
              </div>
              <h3 className="font-semibold text-white mb-2">Start a conversation</h3>
              <p className="text-sm text-white/60 mb-4">
                Ask me about any asset, KOL, or market trend
              </p>
              <div className="space-y-2">
                <button
                  onClick={() => {
                    setInputValue('How is Bitcoin doing today?');
                    handleSend();
                  }}
                  className="w-full px-4 py-2 bg-white/5 border border-white/10 rounded-lg text-sm text-white hover:bg-white/10 transition-colors"
                >
                  How is Bitcoin doing today?
                </button>
                <button
                  onClick={() => {
                    setInputValue("Who's calling Bitcoin right now?");
                    handleSend();
                  }}
                  className="w-full px-4 py-2 bg-white/5 border border-white/10 rounded-lg text-sm text-white hover:bg-white/10 transition-colors"
                >
                  Who's calling Bitcoin right now?
                </button>
              </div>
            </div>
          )}

          {messages.map((message) => (
            <div
              key={message.id}
              className={`flex ${message.type === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              <div
                className={`max-w-[80%] ${
                  message.type === 'user'
                    ? 'bg-gradient-to-r from-purple-500 to-violet-600 text-white px-4 py-2 rounded-2xl rounded-tr-sm'
                    : 'bg-white/10 text-white px-4 py-2 rounded-2xl rounded-tl-sm backdrop-blur-sm'
                }`}
              >
                <div className="text-sm">{message.content}</div>
                {renderMessageData(message.data)}
              </div>
            </div>
          ))}
          <div ref={messagesEndRef} />
        </div>

        <div className="p-4 border-t border-white/10">
          <div className="flex gap-2">
            <Input
              placeholder="Ask anything about any asset..."
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') handleSend();
              }}
              className="flex-1 bg-black/20 border-white/10 text-white placeholder:text-white/40"
            />
            <Button
              onClick={handleSend}
              className="bg-gradient-to-r from-purple-500 to-violet-600 hover:from-purple-600 hover:to-violet-700 text-white border-0 shadow-lg shadow-purple-500/30"
            >
              <Send className="w-4 h-4" />
            </Button>
          </div>
        </div>
      </GlassCard>
    </div>
  );
}
