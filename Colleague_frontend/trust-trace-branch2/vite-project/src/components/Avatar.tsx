import { ReliabilityTier } from '../../types';

interface AvatarProps {
  initials: string;
  size?: 'sm' | 'md' | 'lg' | 'xl';
  tier?: ReliabilityTier;
  imageUrl?: string;
}

const sizeClasses = {
  sm: 'w-8 h-8 text-xs',
  md: 'w-10 h-10 text-sm',
  lg: 'w-12 h-12 text-base',
  xl: 'w-16 h-16 text-lg',
};

const tierColors = {
  good: 'bg-gradient-to-br from-green-400 to-emerald-500',
  mixed: 'bg-gradient-to-br from-amber-400 to-orange-500',
  bad: 'bg-gradient-to-br from-red-400 to-rose-500',
};

export function Avatar({ initials, size = 'md', tier, imageUrl }: AvatarProps) {
  const colorClass = tier ? tierColors[tier] : 'bg-gradient-to-br from-gray-600 to-gray-700';

  if (imageUrl) {
    return (
      <div className={`${sizeClasses[size]} rounded-full overflow-hidden ring-2 ring-white/10 shadow-lg`}>
        <img src={imageUrl} alt={initials} className="w-full h-full object-cover" />
      </div>
    );
  }

  return (
    <div className={`${sizeClasses[size]} rounded-full flex items-center justify-center font-semibold text-white ${colorClass} ring-2 ring-white/10 shadow-lg`}>
      {initials}
    </div>
  );
}
