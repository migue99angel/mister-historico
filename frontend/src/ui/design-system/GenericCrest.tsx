import { useId } from 'react';

import { crestDesign, type CrestPattern, type CrestShape } from './crestDesign';
import type { TeamColors } from './viewModels';

export interface GenericCrestProps {
  colors: TeamColors;
  /** Club name for screen readers; omit it when the name is already shown next to the crest. */
  label?: string | undefined;
  size?: number;
}

// Every path is drawn on a 48 × 48 canvas; patterns are clipped to the shape.
const SHAPE_PATHS: Record<CrestShape, string> = {
  shield: 'M6 4h36v20c0 12.5-8.2 19.6-18 22C14.2 43.6 6 36.5 6 24Z',
  round: 'M24 4a20 20 0 1 1 0 40a20 20 0 1 1 0-40Z',
  peaked: 'M24 3l18 7v14c0 11-7.5 18.5-18 21C13.5 42.5 6 35 6 24V10Z',
};

const PATTERN_PATHS: Record<CrestPattern, string> = {
  band: 'M0 18h48v12H0Z',
  stripes: 'M9 0h6v48H9ZM21 0h6v48h-6ZM33 0h6v48h-6Z',
  halves: 'M24 0h24v48H24Z',
  sash: 'M0 38 38 0h10v10L10 48H0Z',
  chevron: 'M0 14l24 14 24-14v10L24 38 0 24Z',
  quarters: 'M0 0h24v24H0ZM24 24h24v24H24Z',
  hoops: 'M0 8h48v6H0ZM0 21h48v6H0ZM0 34h48v6H0Z',
  pale: 'M18 0h12v48H18Z',
};

/** A crest drawn only from the club colours: never a real badge (brief §14). */
export function GenericCrest({ colors, label, size = 40 }: GenericCrestProps) {
  const clipId = useId();
  const design = crestDesign(colors);
  const shape = SHAPE_PATHS[design.shape];

  return (
    <svg
      viewBox="0 0 48 48"
      width={size}
      height={size}
      className="shrink-0"
      {...(label === undefined
        ? { 'aria-hidden': true }
        : { role: 'img', 'aria-label': `Escudo genérico de ${label}` })}
    >
      <defs>
        <clipPath id={clipId}>
          <path d={shape} />
        </clipPath>
      </defs>
      <g clipPath={`url(#${clipId})`}>
        <rect width="48" height="48" fill={design.field} />
        <path d={PATTERN_PATHS[design.pattern]} fill={design.charge} />
      </g>
      <path d={shape} fill="none" stroke={design.charge} strokeWidth="2" />
    </svg>
  );
}
