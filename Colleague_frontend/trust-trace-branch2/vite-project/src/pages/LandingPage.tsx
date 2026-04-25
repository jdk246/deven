import { Circle, Shield, TrendingUp, Eye, Zap, CheckCircle, AlertTriangle } from 'lucide-react';
import { KOL } from '../../types';
import { Avatar } from '../components/Avatar';
import { ScorePill } from '../components/ScorePill';
import { GlassCard } from '../components/GlassCard';
import { Button } from '../components/ui/button';
import { useNavigate } from 'react-router-dom';

interface LandingPageProps {
  kols: Record<string, KOL>;
}

export function LandingPage({ kols }: LandingPageProps) {
  const navigate = useNavigate();
  const liveCalls = [
    { kol: kols['willy-woo'], call: 'Bullish on BTC: accumulation signal', score: 81, change: 'up' },
    { kol: kols['zachary-bull'], call: 'Calling $MOONX: honeypot detected', score: 31, change: 'down' },
    { kol: kols['robert-kiyosaki'], call: 'Gold to $5,000 - no wallet found', score: 62, change: 'neutral' },
  ];

  const features = [
    {
      icon: Eye,
      title: 'Real-Time Tracking',
      description: 'Monitor every call from top crypto KOLs across Twitter and social media platforms. Never miss a signal.',
      gradient: 'from-blue-500 to-cyan-600',
    },
    {
      icon: Shield,
      title: 'On-Chain Verification',
      description: 'Cross-reference claims with actual wallet holdings via Arkham Intelligence. Know who puts money where their mouth is.',
      gradient: 'from-purple-500 to-violet-600',
    },
    {
      icon: TrendingUp,
      title: 'Historical Scoring',
      description: 'AI-powered reliability scores based on past accuracy. See who actually delivers alpha and who is just hype.',
      gradient: 'from-green-500 to-emerald-600',
    },
    {
      icon: AlertTriangle,
      title: 'Rug Pull Detection',
      description: 'Automated token security audits flag honeypots and scams before you get burned. Stay protected from bad actors.',
      gradient: 'from-red-500 to-orange-600',
    },
    {
      icon: Zap,
      title: 'AI Assistant',
      description: 'Chat with your personal crypto intelligence agent. Ask questions, get insights, make informed decisions instantly.',
      gradient: 'from-yellow-500 to-amber-600',
    },
    {
      icon: CheckCircle,
      title: 'Built for Retail',
      description: 'Level the playing field. Access institutional-grade intelligence tools without the institutional budget.',
      gradient: 'from-indigo-500 to-purple-600',
    },
  ];

  const howItWorksSteps = [
    {
      number: '01',
      title: 'Track',
      description: 'Every call from top KOLs across crypto',
    },
    {
      number: '02',
      title: 'Verify',
      description: 'On-chain wallet check via Arkham',
    },
    {
      number: '03',
      title: 'Score',
      description: 'Reliability based on past accuracy',
    },
    {
      number: '04',
      title: 'Decide',
      description: 'Form your bias with real data',
    },
  ];

  return (
    <div className="min-h-screen text-white relative z-10">
      <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8 sm:py-12 lg:py-16">
        <div className="text-center mb-8 sm:mb-12">
          <div className="text-sm text-white/60 mb-4 sm:mb-6">TrustTrace</div>
          <h1 className="text-3xl sm:text-4xl md:text-5xl lg:text-6xl font-bold mb-4">
            <span className="bg-gradient-to-r from-white to-purple-200 bg-clip-text text-transparent">
              Humans get rugged.
            </span>
            <br />
            <span className="text-white/60">Agents don't.</span>
          </h1>
          <p className="text-base sm:text-lg text-white/60 max-w-2xl mx-auto mb-6 sm:mb-8 px-4">
            An AI agent that tracks every KOL call, scores their reliability,
            and verifies their wallets on-chain. Built for retail.
          </p>
          <div className="flex flex-col sm:flex-row items-center justify-center gap-3 sm:gap-4 px-4">
            <Button
              onClick={() => navigate('/dashboard')}
              className="bg-gradient-to-r from-purple-500 to-violet-600 hover:from-purple-600 hover:to-violet-700 text-white border-0 shadow-lg shadow-purple-500/30"
            >
              Open the agent
            </Button>
            <Button
              variant="outline"
              className="bg-white/5 border-white/10 text-white hover:bg-white/10 backdrop-blur-sm"
              onClick={() => {
                const howItWorks = document.getElementById('how-it-works');
                howItWorks?.scrollIntoView({ behavior: 'smooth' });
              }}
            >
              See how it works
            </Button>
          </div>
        </div>
      </div>

      {/* Live Tracking Banner */}
      <div className="w-full backdrop-blur-xl bg-white/5 border-y border-white/10 py-3 sm:py-4 overflow-hidden mb-8 sm:mb-12 lg:mb-16">
        <div className="flex items-center gap-3 mb-2 sm:mb-3 px-4 sm:px-8">
          <Circle className="w-2.5 h-2.5 text-red-400 fill-red-400 animate-pulse" />
          <span className="text-xs font-semibold text-white/80 uppercase tracking-wide">
            Live — Tracking Now
          </span>
        </div>
        <div className="relative flex overflow-x-hidden">
          <div className="flex animate-scroll gap-4 sm:gap-6 px-4 sm:px-8">
            {[...liveCalls, ...liveCalls, ...liveCalls].map((item, index) => {
              if (!item.kol) return null;
              return (
                <div
                  key={index}
                  className="flex items-center gap-2 sm:gap-3 bg-white/5 border border-white/10 rounded-xl px-3 sm:px-4 py-2 sm:py-2.5 hover:bg-white/10 cursor-pointer transition-all duration-300 whitespace-nowrap"
                  onClick={() => navigate(`/kol/${item.kol.id}`)}
                >
                  <Avatar initials={item.kol.initials} size="sm" tier={item.kol.tier} imageUrl={item.kol.avatarUrl} />
                  <div className="min-w-0">
                    <div className="font-semibold text-white text-xs sm:text-sm">{item.kol.name}</div>
                    <div className="text-xs text-white/60 truncate max-w-[150px] sm:max-w-none">{item.call}</div>
                  </div>
                  <ScorePill score={item.score} tier={item.kol.tier} size="sm" />
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
              Why TrustTrace?
            </h2>
            <p className="text-white/60 max-w-2xl mx-auto px-4">
              Stop relying on blind faith. Get the tools you need to separate signal from noise in crypto.
            </p>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 sm:gap-6 mb-12 sm:mb-16">
            {features.map((feature) => {
              const Icon = feature.icon;
              return (
                <GlassCard key={feature.title} className="p-6">
                  <div className={`w-12 h-12 rounded-xl bg-gradient-to-br ${feature.gradient} flex items-center justify-center mb-4 shadow-lg`}>
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
      </div>
    </div>
  );
}
