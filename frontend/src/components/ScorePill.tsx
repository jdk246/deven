import { ReliabilityTier } from "../types";

interface ScorePillProps {
  score: number;
  tier: ReliabilityTier;
  size?: 'sm' | 'md' | 'lg';
}

const tierColors = {
  good: 'text-green-400',
  mixed: 'text-amber-400',
  bad: 'text-red-400',
};

const tierBg = {
  good: 'bg-green-500/20 border-green-500/30',
  mixed: 'bg-amber-500/20 border-amber-500/30',
  bad: 'bg-red-500/20 border-red-500/30',
};

const sizeClasses = {
  sm: 'text-xs px-2 py-1',
  md: 'text-sm px-3 py-1.5',
  lg: 'text-base px-4 py-2',
};

export function ScorePill({ score, tier, size = 'md' }: ScorePillProps) {
  return (
    <span className={`inline-flex items-center rounded-lg font-semibold border backdrop-blur-sm ${tierColors[tier]} ${tierBg[tier]} ${sizeClasses[size]}`}>
      {score}%
    </span>
  );
}
