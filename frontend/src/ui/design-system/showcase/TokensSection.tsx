import { useId, type ReactNode } from 'react';

import { contrastRatio } from '../color';
import { colors, spacing, textPairs, typeScale, type ColorToken } from '../tokens';

// Literal class names so Tailwind generates them.
const TYPE_CLASSES: Record<string, string> = {
  display: 'text-display',
  headline: 'text-headline',
  title: 'text-title',
  body: 'text-body',
  caption: 'text-caption',
};

const BASE_SPACING_STEPS = [1, 2, 3, 4, 6, 8];

function ratio(foreground: ColorToken, background: ColorToken): string {
  return `${contrastRatio(colors[foreground], colors[background]).toFixed(1)}:1`;
}

function remToPx(rem: string): number {
  return parseFloat(rem) * 16;
}

function TokenGroup({ title, children }: { title: string; children: ReactNode }) {
  const titleId = useId();
  return (
    <section aria-labelledby={titleId} className="rounded-card border border-line p-gutter">
      <h3 id={titleId} className="mb-4 font-display text-title font-bold">
        {title}
      </h3>
      {children}
    </section>
  );
}

export function TokensSection() {
  return (
    <div className="flex flex-col gap-6">
      <TokenGroup title="Paleta">
        <ul className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
          {(Object.entries(colors) as [ColorToken, string][]).map(([name, value]) => (
            <li key={name} className="overflow-hidden rounded-control border border-line">
              <div aria-hidden="true" className="h-14" style={{ backgroundColor: value }} />
              <div className="bg-surface px-3 py-2">
                <p className="text-caption font-semibold">
                  <code>{name}</code>
                </p>
                <p className="text-caption text-ink-muted">
                  <code>{value}</code>
                </p>
              </div>
            </li>
          ))}
        </ul>
        <h4 className="mt-6 mb-2 text-body font-bold">Pares de texto (WCAG AA ≥ 4,5:1)</h4>
        <ul className="grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-4">
          {textPairs.map(({ foreground, background }) => (
            <li
              key={`${foreground}-${background}`}
              className="flex items-center justify-between gap-2 rounded-control border border-line px-3 py-2 text-caption"
              style={{ backgroundColor: colors[background], color: colors[foreground] }}
            >
              <span>
                {foreground} / {background}
              </span>
              <span className="font-bold tabular-nums">{ratio(foreground, background)}</span>
            </li>
          ))}
        </ul>
      </TokenGroup>

      <TokenGroup title="Escala tipográfica">
        <ul className="flex flex-col gap-4">
          {typeScale.map((step) => (
            <li key={step.token} className="border-b border-line pb-3 last:border-b-0">
              <p className="text-caption text-ink-muted">
                <code className="font-semibold text-ink">{step.token}</code> · {step.size} /{' '}
                {step.lineHeight} · {step.usage}
              </p>
              <p
                className={`${TYPE_CLASSES[step.token] ?? ''} ${step.token === 'display' || step.token === 'headline' ? 'font-display font-extrabold' : ''}`}
              >
                Test FC gana la Liga Test
              </p>
            </li>
          ))}
        </ul>
      </TokenGroup>

      <TokenGroup title="Espaciado">
        <ul className="flex flex-col gap-3">
          {(Object.entries(spacing) as [string, string][]).map(([name, value]) => (
            <li key={name} className="flex items-center gap-3">
              <span
                aria-hidden="true"
                className="shrink-0 rounded-sm bg-accent"
                style={{ width: value, height: value }}
              />
              <p className="text-caption">
                <code className="font-semibold">{name}</code> · {value} · {remToPx(value)} px
                {name === 'touch' && ' · mínimo de cualquier objetivo táctil'}
                {name === 'gutter' && ' · margen lateral en móvil'}
              </p>
            </li>
          ))}
          {BASE_SPACING_STEPS.map((step) => (
            <li key={step} className="flex items-center gap-3">
              <span
                aria-hidden="true"
                className="h-3 shrink-0 rounded-sm bg-ink-muted"
                style={{ width: `${String(step * 4)}px` }}
              />
              <p className="text-caption text-ink-muted">
                Escala base de Tailwind · <code>{step}</code> · {step * 4} px
              </p>
            </li>
          ))}
        </ul>
      </TokenGroup>
    </div>
  );
}
