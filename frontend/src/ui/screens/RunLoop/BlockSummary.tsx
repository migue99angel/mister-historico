import { useId, type Ref } from 'react';

import type { BlockSummaryDto, MatchReportDto } from '../../../application/ports';
import type { BlockNarrativeViewModel } from '../../../domain/blockNarrative';
import { formatMatchResult } from '../../../domain/matchResult';
import { Button, Card, MatchLine } from '../../design-system';

export interface BlockSummaryProps {
  summary: BlockSummaryDto;
  narrative: BlockNarrativeViewModel;
  /** The heading takes the focus after a simulation, when the button becomes disabled. */
  visibleDates?: number;
  revealing?: boolean;
  onComplete?: () => void;
  headingRef?: Ref<HTMLHeadingElement>;
}

function userSide(match: MatchReportDto): 'home' | 'away' | undefined {
  if (match.home.isUser) return 'home';
  if (match.away.isUser) return 'away';
  return undefined;
}

/** Results, news and standings of the last block played. */
export function BlockSummary({
  summary,
  narrative,
  headingRef,
  visibleDates = Infinity,
  revealing = false,
  onComplete,
}: BlockSummaryProps) {
  const headingId = useId();
  const sorted = [...summary.results].sort((a, b) =>
    a.date < b.date
      ? -1
      : a.date > b.date
        ? 1
        : a.fixtureId < b.fixtureId
          ? -1
          : a.fixtureId > b.fixtureId
            ? 1
            : 0,
  );
  const dates = [...new Set(sorted.map((match) => match.date))];
  const shownDates = dates.slice(0, visibleDates);
  const visible = sorted.filter((match) => shownDates.includes(match.date));

  return (
    <>
      <section aria-labelledby={headingId} className="flex flex-col gap-2">
        <h2
          id={headingId}
          ref={headingRef}
          tabIndex={-1}
          className="font-display text-title font-bold text-ink"
        >
          Resumen del bloque
        </h2>
        <Card>
          {!revealing && (
            <p className="text-caption font-semibold tracking-wide text-ink-muted uppercase">
              {`${narrative.title} · ${narrative.recordText}`}
            </p>
          )}
          {revealing && (
            <div className="flex flex-col gap-2">
              <p className="text-body">Mostrando los resultados del bloque ya simulado.</p>
              <Button onClick={onComplete}>Mostrar todos</Button>
            </div>
          )}
          <p role="status" aria-live="polite" className="sr-only">
            {revealing
              ? `${String(visible.length)} de ${String(sorted.length)} resultados mostrados.`
              : 'Resumen completo disponible.'}
          </p>
          <ul className="divide-y divide-line">
            {shownDates.map((date) => (
              <li key={date}>
                <h3 className="mt-3 text-caption font-semibold">
                  <time dateTime={date}>{date}</time>
                </h3>
                <ul className="divide-y divide-line">
                  {visible
                    .filter((match) => match.date === date)
                    .map((match) => (
                      <li key={match.fixtureId}>
                        <MatchLine
                          match={formatMatchResult(match)}
                          competitionName={match.competitionName}
                          keyMatchLabel={match.keyMatchLabel}
                          userSide={userSide(match)}
                        />
                      </li>
                    ))}
                </ul>
              </li>
            ))}
          </ul>
          {!revealing && narrative.events.length > 0 && (
            <ul className="mt-3 flex flex-col gap-1 text-body text-ink">
              {narrative.events.map((event) => (
                <li key={event}>{event}</li>
              ))}
            </ul>
          )}
          {!revealing && narrative.injuries.length > 0 && (
            <p className="mt-3 text-caption text-ink-muted">
              {`Parte médico: ${narrative.injuries.join('; ')}.`}
            </p>
          )}
        </Card>
      </section>
    </>
  );
}
