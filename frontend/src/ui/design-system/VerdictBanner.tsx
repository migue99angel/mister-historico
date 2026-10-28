import { useId } from 'react';

import { cx } from './styles';

/** The four endings of the glossary's `Verdict`. */
export type VerdictKind = 'surpassed' | 'matched' | 'below' | 'sacked';

export interface VerdictBannerProps {
  kind: VerdictKind;
  /** «Superaste a…», «Igualaste la historia», «Te quedaste por debajo»… */
  title: string;
  description?: string | undefined;
  /** Manager score (0-100); omitted while there is none. */
  score?: number | null | undefined;
  headingLevel?: 1 | 2 | 3 | 4;
}

const KIND_STYLES: Record<VerdictKind, { banner: string; icon: string; iconPath: string }> = {
  surpassed: {
    banner: 'border-gold bg-gold text-on-gold',
    icon: 'bg-on-gold text-gold',
    iconPath: 'M8 4h8v4a4 4 0 0 1-8 0V4Zm4 8v5m-4 3h8M8 6H5v1a3 3 0 0 0 3 3m8-4h3v1a3 3 0 0 1-3 3',
  },
  matched: {
    banner: 'border-accent bg-accent text-on-accent',
    icon: 'bg-on-accent text-accent',
    iconPath: 'M6 9h12M6 15h12',
  },
  below: {
    banner: 'border-line bg-surface-raised text-ink',
    icon: 'bg-surface text-ink-muted',
    iconPath: 'M12 5v14m-6-6 6 6 6-6',
  },
  sacked: {
    banner: 'border-loss bg-surface-raised text-ink',
    icon: 'bg-loss text-on-accent',
    iconPath: 'M7 7l10 10M17 7 7 17',
  },
};

export function VerdictBanner({
  kind,
  title,
  description,
  score,
  headingLevel = 2,
}: VerdictBannerProps) {
  const titleId = useId();
  const styles = KIND_STYLES[kind];
  const Heading = `h${String(headingLevel)}` as 'h1' | 'h2' | 'h3' | 'h4';

  return (
    <section
      aria-labelledby={titleId}
      className={cx('rounded-card border-2 px-gutter py-6 text-center', styles.banner)}
    >
      <span
        aria-hidden="true"
        className={cx('mx-auto mb-3 grid size-12 place-items-center rounded-full', styles.icon)}
      >
        <svg viewBox="0 0 24 24" className="size-7" fill="none" stroke="currentColor">
          <path d={styles.iconPath} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      </span>
      <p className="text-caption font-semibold tracking-widest uppercase">Veredicto</p>
      <Heading id={titleId} className="mt-1 font-display text-headline font-extrabold text-balance">
        {title}
      </Heading>
      {description && <p className="mt-2 text-body text-pretty">{description}</p>}
      {score !== undefined && score !== null && (
        <div className="mt-4">
          <p className="text-caption font-semibold tracking-wide uppercase">
            Puntuación del míster
          </p>
          <p className="font-display font-extrabold tabular-nums">
            <span className="text-display">{score}</span>
            <span className="text-title">/100</span>
          </p>
        </div>
      )}
    </section>
  );
}
