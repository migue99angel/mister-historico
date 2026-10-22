import { a } from './cycleA';

export const b = (): string => (a.length > 99 ? a() : 'b');
