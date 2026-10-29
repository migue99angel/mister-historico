import { useEffect, useState } from 'react';

const REDUCED_MOTION = '(prefers-reduced-motion: reduce)';
const MAX_DURATION_MS = 4500;
const DATE_INTERVAL_MS = 700;

/** Ephemeral presentation state: only the successful local advance starts a reveal. */
export function useBlockReveal(version: number, dateCount: number) {
  const [sequence, setSequence] = useState<{ version: number; visible: number } | null>(null);
  const revealing =
    sequence !== null && sequence.version === version && sequence.visible < dateCount;
  const sequenceVersion = sequence?.version;

  useEffect(() => {
    if (!revealing) return;
    const media = motionPreference();
    const interval = Math.min(DATE_INTERVAL_MS, MAX_DURATION_MS / dateCount);
    const timers = Array.from({ length: dateCount }, (_, index) =>
      window.setTimeout(
        () => {
          setSequence({ version, visible: index + 1 });
        },
        interval * (index + 1),
      ),
    );
    const onMotionChange = () => {
      if (media?.matches) setSequence(null);
    };
    media?.addEventListener('change', onMotionChange);
    return () => {
      timers.forEach((timer) => {
        window.clearTimeout(timer);
      });
      media?.removeEventListener('change', onMotionChange);
    };
  }, [revealing, sequenceVersion, version, dateCount]);

  return {
    revealing,
    visibleDates: revealing ? sequence.visible : dateCount,
    start(nextVersion: number, dates: number) {
      if (dates === 0 || motionPreference()?.matches) return;
      setSequence({ version: nextVersion, visible: 0 });
    },
    complete() {
      setSequence(null);
    },
  };
}

function motionPreference(): MediaQueryList | null {
  return typeof window.matchMedia === 'function' ? window.matchMedia(REDUCED_MOTION) : null;
}
