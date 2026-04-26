import { useEffect, useMemo, useRef, useState } from "react";
import { MessageCircle, Send, Wrench, X } from "lucide-react";

import { queryAgent } from "../api/trustTrace";
import { useAppData } from "../lib/app-data";
import { GlassCard } from "./GlassCard";
import { Button } from "./ui/button";
import { Input } from "./ui/input";

interface Message {
  id: string;
  type: "user" | "assistant";
  content: string;
  disclaimer?: string;
  evidence?: string[];
  meta?: string;
  loading?: boolean;
}

const SUGGESTIONS = [
  "Which tokens are trending right now?",
  "Which KOLs have the best track record?",
  "Which tokens look risky?",
  "Is the KOL hype backed by market data?",
  "How do you calculate KOL rankings?",
];

export function ChatBot() {
  const { snapshot } = useAppData();
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputValue, setInputValue] = useState("");
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const statusLabel = useMemo(() => {
    if (!snapshot) {
      return "Loading market context";
    }

    return snapshot.agentMode === "openai" ? "AI-assisted analysis" : "Deterministic analysis";
  }, [snapshot]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  useEffect(() => {
    if (!isOpen) {
      return;
    }

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setIsOpen(false);
      }
    }

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen]);

  async function handleSend(prompt = inputValue) {
    const trimmed = prompt.trim();
    if (!trimmed) {
      return;
    }

    const userMessage: Message = {
      id: `user-${Date.now()}`,
      type: "user",
      content: trimmed,
    };
    const pendingMessageId = `assistant-${Date.now() + 1}`;

    setMessages((previous) => [
      ...previous,
      userMessage,
      {
        id: pendingMessageId,
        type: "assistant",
        content: "Thinking...",
        loading: true,
      },
    ]);
    setInputValue("");

    try {
      const response = await queryAgent({
        message: trimmed,
        debug: false,
      });

      const evidence = response.evidence_used
        .slice(0, 4)
        .map((item) => {
          const type = typeof item.type === "string" ? item.type : "evidence";
          const token = typeof item.token === "string" ? item.token : null;
          return token ? `${type}: ${token}` : type;
        });

      setMessages((previous) =>
        previous.map((message) =>
          message.id === pendingMessageId
            ? {
                id: pendingMessageId,
                type: "assistant",
                content: response.answer,
                disclaimer: response.disclaimer,
                evidence,
                meta: `${response.tool_trace.length} tool call${
                  response.tool_trace.length === 1 ? "" : "s"
                }`,
              }
            : message,
        ),
      );
    } catch (error) {
      setMessages((previous) =>
        previous.map((message) =>
          message.id === pendingMessageId
                    ? {
                        id: pendingMessageId,
                        type: "assistant",
                        content:
                          error instanceof Error
                            ? error.message
                    : "The request failed. Check that the TrustTrace API is still running.",
              }
            : message,
        ),
      );
    }
  }

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
    <div className="fixed inset-3 sm:inset-auto sm:bottom-6 sm:right-6 sm:w-[420px] lg:w-[480px] sm:h-[620px] sm:max-h-[calc(100dvh-3rem)] z-50">
      <GlassCard className="h-full overflow-hidden flex flex-col">
        <div className="p-4 border-b border-white/10 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-full bg-gradient-to-br from-purple-500 to-violet-600 flex items-center justify-center shadow-lg shadow-purple-500/50">
              <span className="text-white font-bold text-sm">TT</span>
            </div>
            <div>
              <div className="font-semibold text-white text-sm">TrustTrace Assistant</div>
              <div className="text-xs text-green-400 flex items-center gap-1">
                <div className="w-2 h-2 rounded-full bg-green-400"></div>
                {statusLabel}
              </div>
            </div>
          </div>
          <button
            onClick={() => setIsOpen(false)}
            type="button"
            aria-label="Close chatbot"
            title="Close chatbot"
            className="inline-flex items-center gap-2 rounded-full border border-white/15 bg-white/10 px-3 py-2 text-sm font-medium text-white/85 transition-all hover:bg-white/20 hover:text-white"
          >
            <X className="w-5 h-5" />
            <span>Close</span>
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {messages.length === 0 ? (
            <div className="text-center py-12">
              <div className="w-16 h-16 rounded-full bg-gradient-to-br from-purple-500 to-violet-600 mx-auto mb-4 flex items-center justify-center shadow-lg shadow-purple-500/50">
                <MessageCircle className="w-8 h-8 text-white" />
              </div>
              <h3 className="font-semibold text-white mb-2">Ask TrustTrace</h3>
              <p className="text-sm text-white/60 mb-4">
                Ask about token momentum, risk, KOL activity, or market confirmation.
              </p>
              <div className="space-y-2">
                {SUGGESTIONS.map((suggestion) => (
                  <button
                    key={suggestion}
                    onClick={() => void handleSend(suggestion)}
                    className="w-full px-4 py-2 bg-white/5 border border-white/10 rounded-lg text-sm text-white hover:bg-white/10 transition-colors text-left"
                  >
                    {suggestion}
                  </button>
                ))}
              </div>
            </div>
          ) : null}

          {messages.map((message) => (
            <div
              key={message.id}
              className={`flex ${message.type === "user" ? "justify-end" : "justify-start"}`}
            >
              <div
                className={`max-w-[85%] ${
                  message.type === "user"
                    ? "bg-gradient-to-r from-purple-500 to-violet-600 text-white px-4 py-2 rounded-2xl rounded-tr-sm"
                    : "bg-white/10 text-white px-4 py-3 rounded-2xl rounded-tl-sm backdrop-blur-sm"
                }`}
              >
                <div className="text-sm whitespace-pre-wrap">
                  {message.loading ? "Thinking..." : message.content}
                </div>
                {message.evidence && message.evidence.length > 0 ? (
                  <div className="mt-3 space-y-2">
                    <div className="text-[11px] uppercase tracking-wide text-white/50 flex items-center gap-1">
                      <Wrench className="w-3 h-3" />
                      Evidence used
                    </div>
                    <div className="flex flex-wrap gap-2">
                      {message.evidence.map((entry) => (
                        <span
                          key={entry}
                          className="px-2 py-1 rounded-lg bg-black/20 border border-white/10 text-xs text-white/75"
                        >
                          {entry}
                        </span>
                      ))}
                    </div>
                  </div>
                ) : null}
                {message.meta ? <div className="mt-3 text-xs text-white/50">{message.meta}</div> : null}
                {message.disclaimer ? (
                  <div className="mt-2 text-xs text-white/45">{message.disclaimer}</div>
                ) : null}
              </div>
            </div>
          ))}
          <div ref={messagesEndRef} />
        </div>

        <div className="p-4 border-t border-white/10">
          <div className="flex gap-2">
            <Input
              placeholder="Ask about any token, risk, or KOL trend..."
              value={inputValue}
              onChange={(event) => setInputValue(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Enter") {
                  void handleSend();
                }
              }}
              className="flex-1 bg-black/20 border-white/10 text-white placeholder:text-white/40"
            />
            <Button
              onClick={() => void handleSend()}
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
