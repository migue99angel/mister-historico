// Violation: domain must not import other internal layers.
import type { ScorePort } from '../application/scorePort';

export const zeroScore: ScorePort = { readScore: () => 0 };
