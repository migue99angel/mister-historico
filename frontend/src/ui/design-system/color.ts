const HEX_COLOUR = /^#([0-9a-f]{3}|[0-9a-f]{6})$/i;

/** Expands `#abc` to `#aabbcc` and lower-cases it; throws on anything else. */
export function normaliseHex(colour: string): string {
  if (!HEX_COLOUR.test(colour)) throw new Error(`Not a hex colour: ${colour}`);
  const digits = colour.slice(1).toLowerCase();
  const full =
    digits.length === 3
      ? digits
          .split('')
          .map((digit) => digit + digit)
          .join('')
      : digits;
  return `#${full}`;
}

function channelLuminance(value: number): number {
  const srgb = value / 255;
  return srgb <= 0.04045 ? srgb / 12.92 : ((srgb + 0.055) / 1.055) ** 2.4;
}

/** WCAG 2.x relative luminance, from 0 (black) to 1 (white). */
export function relativeLuminance(colour: string): number {
  const hex = normaliseHex(colour);
  const [red, green, blue] = [1, 3, 5].map((start) =>
    channelLuminance(parseInt(hex.slice(start, start + 2), 16)),
  ) as [number, number, number];
  return 0.2126 * red + 0.7152 * green + 0.0722 * blue;
}

/** WCAG 2.x contrast ratio between two colours, from 1 to 21. */
export function contrastRatio(first: string, second: string): number {
  const [lighter, darker] = [relativeLuminance(first), relativeLuminance(second)].sort(
    (a, b) => b - a,
  ) as [number, number];
  return (lighter + 0.05) / (darker + 0.05);
}
