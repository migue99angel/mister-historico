// Violation: circular dependency (cycleA <-> cycleB).
import { b } from './cycleB';

export const a = (): string => `a${b()}`;
