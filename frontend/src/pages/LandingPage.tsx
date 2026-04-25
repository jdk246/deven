import {
  Activity,
  AlertTriangle,
  Bot,
  CheckCircle,
  Circle,
  Database,
  Shield,
  TrendingUp,
  Users,
} from "lucide-react";
import { useNavigate } from "react-router-dom";

import { Avatar } from "../components/Avatar";
import { GlassCard } from "../components/GlassCard";
import { ScorePill } from "../components/ScorePill";
import { Button } from "../components/ui/button";
import type { Call, KOL, ValidationState } from "../types";

interface LandingPageProps {
  kols: Record<string, KOL>;
  feed: Call[];
  validationStatus: ValidationState;
}

export function LandingPage({
  kols,
  feed,
  validationStatus,
}: LandingPageProps) {
  const navigate = useNavigate();

  const liveCalls =
    feed.slice(0, 4).map((call) => ({
      kol: kols[call.kolId],
      call,
    })) ?? [];

  const features = [
    {
      icon: TrendingUp,
      title: "Multi-Chain Market Tracking",
      description:
        "Track tokens across BNB Chain and Solana, with Base ready to enable when needed.",
      gradient: "from-blue-500 to-cyan-600",
    },
    {
      icon: Users,
      title: "KOL Context Layer",
      description:
        "Monitor curated KOL profiles, recent posts, extracted token mentions, and sentiment without relying on live social credentials.",
      gradient: "from-purple-500 to-violet-600",
    },
    {
      icon: Activity,
      title: "Attention Scoring",
      description:
        "Blend market, social, smart-money, and safety context into a deterministic Attention Score instead of vague hype metrics.",
      gradient: "from-green-500 to-emerald-600",
    },
    {
      icon: Shield,
      title: "Risk Context",
      description:
        "Expose stored audit results, holder concentration, taxes where available, and contract risk signals inside the token view.",
      gradient: "from-red-500 to-orange-600",
    },
    {
      icon: Bot,
      title: "Agent Query Layer",
      description:
        "Ask why something is trending, what looks risky, and whether KOL attention is backed by market data through the TrustTrace assistant.",
      gradient: "from-yellow-500 to-amber-600",
    },
    {
      icon: Database,
      title: "Operational Foundation",
      description:
        "The system already includes validation checks, refresh jobs, deterministic insights, and a production-shaped API surface.",
      gradient: "from-indigo-500 to-purple-600",
    },
  ];

  const howItWorksSteps = [
    {
      number: "01",
      title: "Ingest",
      description: "Pull market, audit, smart-money, and curated social context into one system.",
    },
    {
      number: "02",
      title: "Extract",
      description: "Resolve token mentions conservatively and classify post sentiment.",
    },
    {
      number: "03",
      title: "Score",
      description: "Generate deterministic Attention Scores and token summaries.",
    },
    {
      number: "04",
      title: "Ask",
      description: "Query the agent API for the live state of the dataset.",
    },
  ];

  return (
    <div className="min-h-screen text-white relative z-10">
      <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8 sm:py-12 lg:py-16">
        <div className="text-center mb-8 sm:mb-12">
          <div className="text-sm text-white/60 mb-4 sm:mb-6">
            TrustTrace - validation {validationStatus}
          </div>
          <h1 className="text-3xl sm:text-4xl md:text-5xl lg:text-6xl font-bold mb-4">
            <span className="bg-gradient-to-r from-white to-purple-200 bg-clip-text text-transparent">
              Humans get rugged.
            </span>
            <br />
            <span className="text-white/60">Agents don&apos;t.</span>
          </h1>
          <p className="text-base sm:text-lg text-white/60 max-w-2xl mx-auto mb-6 sm:mb-8 px-4">
            TrustTrace is an agent-backed crypto intelligence stack that combines Binance market
            data, curated KOL context, deterministic scoring, and audit signals into one product
            surface.
          </p>
          <div className="flex flex-col sm:flex-row items-center justify-center gap-3 sm:gap-4 px-4">
            <Button
              onClick={() => navigate("/dashboard")}
              className="bg-gradient-to-r from-purple-500 to-violet-600 hover:from-purple-600 hover:to-violet-700 text-white border-0 shadow-lg shadow-purple-500/30"
            >
              Open dashboard
            </Button>
            <Button
              variant="outline"
              className="bg-white/5 border-white/10 text-white hover:bg-white/10 backdrop-blur-sm"
              onClick={() => {
                const howItWorks = document.getElementById("how-it-works");
                howItWorks?.scrollIntoView({ behavior: "smooth" });
              }}
            >
              See how it works
            </Button>
          </div>
        </div>
      </div>

      <div className="w-full backdrop-blur-xl bg-white/5 border-y border-white/10 py-3 sm:py-4 overflow-hidden mb-8 sm:mb-12 lg:mb-16">
        <div className="flex items-center gap-3 mb-2 sm:mb-3 px-4 sm:px-8">
          <Circle className="w-2.5 h-2.5 text-red-400 fill-red-400 animate-pulse" />
          <span className="text-xs font-semibold text-white/80 uppercase tracking-wide">
            Recent KOL activity
          </span>
        </div>
        <div className="relative flex overflow-x-hidden">
          <div className="flex animate-scroll gap-4 sm:gap-6 px-4 sm:px-8">
            {[...liveCalls, ...liveCalls, ...liveCalls].map((item, index) => {
              if (!item.kol) {
                return null;
              }

              return (
                <div
                  key={`${item.call.id}-${index}`}
                  className="flex items-center gap-2 sm:gap-3 bg-white/5 border border-white/10 rounded-xl px-3 sm:px-4 py-2 sm:py-2.5 hover:bg-white/10 cursor-pointer transition-all duration-300 whitespace-nowrap"
                  onClick={() => navigate(`/kol/${item.kol.id}`)}
                >
                  <Avatar
                    initials={item.kol.initials}
                    size="sm"
                    tier={item.kol.tier}
                    imageUrl={item.kol.avatarUrl}
                  />
                  <div className="min-w-0">
                    <div className="font-semibold text-white text-xs sm:text-sm">{item.kol.name}</div>
                    <div className="text-xs text-white/60 truncate max-w-[190px] sm:max-w-none">
                      {item.call.symbol}: {item.call.snippet}
                    </div>
                  </div>
                  <ScorePill score={item.kol.reliabilityScore} tier={item.kol.tier} size="sm" />
                </div>
              );
            })}
          </div>
        </div>
      </div>

      <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="mb-12 sm:mb-16">
          <div className="text-center mb-6 sm:mb-8">
            <h2 className="text-sm font-semibold text-white/80 uppercase tracking-wide mb-2">
              What&apos;s Here Already
            </h2>
            <p className="text-white/60 max-w-2xl mx-auto px-4">
              This build is connected to working services, not just a static mockup.
            </p>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 sm:gap-6 mb-12 sm:mb-16">
            {features.map((feature) => {
              const Icon = feature.icon;
              return (
                <GlassCard key={feature.title} className="p-6">
                  <div
                    className={`w-12 h-12 rounded-xl bg-gradient-to-br ${feature.gradient} flex items-center justify-center mb-4 shadow-lg`}
                  >
                    <Icon className="w-6 h-6 text-white" />
                  </div>
                  <h3 className="font-semibold text-white mb-2">{feature.title}</h3>
                  <p className="text-sm text-white/60 leading-relaxed">{feature.description}</p>
                </GlassCard>
              );
            })}
          </div>
        </div>

        <div id="how-it-works" className="mt-12 sm:mt-16">
          <div className="text-center mb-6 sm:mb-8">
            <h2 className="text-sm font-semibold text-white/80 uppercase tracking-wide mb-2">
              How It Works
            </h2>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 sm:gap-6">
            {howItWorksSteps.map((step) => (
              <GlassCard key={step.number} className="p-6 text-center">
                <div className="text-3xl font-bold text-purple-400 mb-3">{step.number}</div>
                <div className="font-semibold text-white mb-2">{step.title}</div>
                <div className="text-sm text-white/60">{step.description}</div>
              </GlassCard>
            ))}
          </div>
        </div>

        <div className="mt-12 sm:mt-16 pb-8">
          <GlassCard className="p-6 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
            <div>
              <div className="text-xs font-semibold text-white/60 uppercase tracking-wide mb-1">
                Current state
              </div>
              <div className="text-lg font-semibold text-white">
                Curated KOL context + live market data
              </div>
              <p className="text-sm text-white/60 mt-2">
                The social layer is stable and reproducible for demos, while market, audit, and
                smart-money views stay current.
              </p>
            </div>
            <div className="inline-flex items-center gap-2 px-3 py-2 rounded-lg bg-white/5 border border-white/10">
              <CheckCircle className="w-4 h-4 text-green-400" />
              <span className="text-sm text-white/80">Ready to demo</span>
            </div>
          </GlassCard>
        </div>
      </div>
    </div>
  );
}
