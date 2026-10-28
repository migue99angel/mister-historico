import { useId, type Ref } from 'react';

import type { BlockSummaryDto, MatchReportDto } from '../../../application/ports';
import type { BlockNarrativeViewModel } from '../../../domain/blockNarrative';
import { formatMatchResult } from '../../../domain/matchResult';
import { describePositionChange } from '../../../domain/standings';
import { Card, MatchLine, MiniStandings, type MiniStandingsRow } from '../../design-system';

export interface BlockSummaryProps {
  summary: BlockSummaryDto;
  narrative: BlockNarrativeViewModel;
  /** The heading takes the focus after a simulation, when the button becomes disabled. */
  headingRef?: Ref<HTMLHeadingElement>;
}

function userSide(match: MatchReportDto): 'home' | 'away' | undefined {
  if (match.home.isUser) return 'home';
  if (match.away.isUser) return 'away';
  return undefined;
}

/** Results, news and standings of the last block played. */
export function BlockSummary({ summary, narrative, headingRef }: BlockSummaryProps) {
  const headingId = useId();

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
          <p className="text-caption font-semibold tracking-wide text-ink-muted uppercase">
            {`${narrative.title} · ${narrative.recordText}`}
          </p>
          <ul className="divide-y divide-line">
            {summary.results.map((match) => (
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
          {narrative.events.length > 0 && (
            <ul className="mt-3 flex flex-col gap-1 text-body text-ink">
              {narrative.events.map((event) => (
                <li key={event}>{event}</li>
              ))}
            </ul>
          )}
          {narrative.injuries.length > 0 && (
            <p className="mt-3 text-caption text-ink-muted">
              {`Parte médico: ${narrative.injuries.join('; ')}.`}
            </p>
          )}
        </Card>
      </section>

      {summary.standings.length > 0 && (
        <Card title="Clasificación" headingLevel={2}>
          <div className="flex flex-col gap-4">
            {summary.standings.map((table) => (
              <MiniStandings
                key={[table.competitionId, table.stageId, table.groupId].join('/')}
                competitionName={table.competitionName}
                rows={table.rows.map((row): MiniStandingsRow => ({
                  position: row.position,
                  teamName: row.team.name,
                  played: row.played,
                  points: row.points,
                  isUser: row.team.isUser,
                  change: describePositionChange(row),
                }))}
              />
            ))}
          </div>
        </Card>
      )}
    </>
  );
}
