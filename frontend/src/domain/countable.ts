/** Formats a count with the singular or plural form of its noun, e.g. `1 puesto`, `3 puestos`. */
export function countable(count: number, singular: string, plural: string): string {
  return `${String(count)} ${count === 1 ? singular : plural}`;
}
