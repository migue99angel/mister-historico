/** Joins class names, skipping the falsy ones left by conditional styles. */
export function cx(...classNames: (string | false | null | undefined)[]): string {
  return classNames.filter(Boolean).join(' ');
}

/** Keyboard focus indicator shared by every interactive component. */
export const FOCUS_RING =
  'focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-gold';
