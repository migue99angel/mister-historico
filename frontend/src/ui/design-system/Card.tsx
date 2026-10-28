import { useId, type ReactNode } from 'react';

import { cx } from './styles';

export type CardTone = 'default' | 'highlight';

export interface CardProps {
  /** Names the card as a region; without a title the card is a plain container. */
  title?: string;
  headingLevel?: 2 | 3 | 4;
  eyebrow?: string;
  tone?: CardTone;
  children: ReactNode;
}

const TONE_CLASSES: Record<CardTone, string> = {
  default: 'border-line bg-surface',
  highlight: 'border-accent/60 bg-surface-raised',
};

export function Card({ title, headingLevel = 2, eyebrow, tone = 'default', children }: CardProps) {
  const titleId = useId();
  const className = cx('rounded-card border p-gutter', TONE_CLASSES[tone]);

  if (title === undefined) return <div className={className}>{children}</div>;

  const Heading = `h${String(headingLevel)}` as 'h2' | 'h3' | 'h4';
  return (
    <section aria-labelledby={titleId} className={className}>
      <header className="mb-3">
        {eyebrow && (
          <p className="text-caption font-semibold tracking-wide text-ink-muted uppercase">
            {eyebrow}
          </p>
        )}
        <Heading id={titleId} className="font-display text-title font-bold text-ink">
          {title}
        </Heading>
      </header>
      {children}
    </section>
  );
}
