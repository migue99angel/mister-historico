import { useId, type Ref } from 'react';

import type { BlockSummaryDto, MatchReportDto } from '../../../application/ports';
import type { BlockNarrativeViewModel } from '../../../domain/blockNarrative';
import { formatMatchResult } from '../../../domain/matchResult';
import { Button, Card, MatchLine } from '../../design-system';

export interface BlockSummaryProps {
  summary: BlockSummaryDto;
  narrative: BlockNarrativeViewModel;
  visibleDates?: number;
  revealing?: boolean;
  onComplete?: () => void;
  /** Focus target after simulation or skipping the reveal. */
  headingRef?: Ref<HTMLHeadingElement>;
}

function userSide(match: MatchReportDto): 'home' | 'away' | undefined {
  if (match.home.isUser) return 'home';
  if (match.away.isUser) return 'away';
  return undefined;
}

/** Results and closing narrative of the last block played. */
export function BlockSummary({
  summary,
  narrative,
  headingRef,
  visibleDates = Infinity,
  revealing = false,
  onComplete,
}: BlockSummaryProps) {
  const headingId = useId();
  const groups = groupResults(summary.results);
  const visibleGroups = groups.slice(0, visibleDates);
  const visibleCount = visibleGroups.reduce((count, group) => count + group.matches.length, 0);

  return (
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
            ? `${String(visibleCount)} de ${String(summary.results.length)} resultados mostrados.`
            : 'Resumen completo disponible.'}
        </p>
        <ul className="divide-y divide-line">
          {visibleGroups.map(({ date, matches }) => (
            <li key={date}>
              <h3 className="mt-3 text-caption font-semibold">
                <time dateTime={date}>{date}</time>
              </h3>
              <ul className="divide-y divide-line">
                {matches.map((match) => (
                  <li key={match.fixtureId}>
                    <MatchLine
                      match={formatMatchResult(match)}
                      competitionName={match.competitionName}
                      keyMatchLabel={
                        match.keyMatchLabel ?? (match.isKeyMatch ? 'Partido clave' : null)
                      }
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
  );
}

/** ISO dates have no kick-off times: equal dates are revealed together. */
function groupResults(results: readonly MatchReportDto[]) {
  const sorted = [...results].sort(
    (a, b) => compare(a.date, b.date) || compare(a.fixtureId, b.fixtureId),
  );
  const groups = new Map<string, MatchReportDto[]>();
  for (const match of sorted) {
    const matches = groups.get(match.date) ?? [];
    matches.push(match);
    groups.set(match.date, matches);
  }
  return [...groups].map(([date, matches]) => ({ date, matches }));
}

function compare(a: string, b: string): number {
  return a < b ? -1 : a > b ? 1 : 0;
}
