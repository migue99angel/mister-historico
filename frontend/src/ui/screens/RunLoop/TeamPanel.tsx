import { useId } from 'react';

import type { RunViewDto } from '../../../application/ports';
import { injuryLabel, PRIORITY_LABELS, TACTIC_LABELS } from '../../../domain/decisionFeedback';
import { describePositionChange } from '../../../domain/standings';
import { MiniStandings } from '../../design-system';

const POSITIONS = { GK: 'Portero', DF: 'Defensa', MF: 'Centrocampista', FW: 'Delantero' };

/** Current published state, reusable independently of the decision flow. */
export function TeamPanel({ run }: { run: RunViewDto }) {
  const headingId = useId();
  const injured = run.squad.players.filter((player) => player.injury !== null);
  return (
    <section
      aria-labelledby={headingId}
      className="flex flex-col gap-3 rounded-card border border-line p-4 [overflow-wrap:anywhere] [&_table]:table-fixed"
    >
      <h2 id={headingId} className="font-display text-title font-bold">
        Estado del equipo
      </h2>
      <ul className="text-body">
        <li>{`Moral: ${String(run.state.morale)}`}</li>
        <li>{`Confianza de la directiva: ${String(run.state.boardConfidence)}`}</li>
        <li>{`Físico medio: ${String(run.state.fitness)}`}</li>
      </ul>
      <details>
        <summary className="min-h-touch cursor-pointer py-3 font-semibold">
          Estado y lesiones
        </summary>
        <p className="text-caption text-ink-muted">
          El físico medio puede variar al cambiar la composición de la plantilla. La media nominal
          no representa la fuerza del once que juega.
        </p>
        <p className="text-body">{`Táctica: ${TACTIC_LABELS[run.tactic.style] ?? run.tactic.style} · ${run.tactic.system}`}</p>
        <div>
          <h3 className="font-semibold">Lesiones actuales</h3>
          {injured.length === 0 ? (
            <p className="text-body">Sin lesiones publicadas.</p>
          ) : (
            <ul className="text-body">
              {injured.map((player) => (
                <li key={player.id}>{`${player.displayName}: ${injuryLabel(player.injury)}`}</li>
              ))}
            </ul>
          )}
        </div>
        {run.competitionPriorities.length > 0 && (
          <div>
            <h3 className="font-semibold">Prioridades de competición</h3>
            <ul className="text-body">
              {run.competitionPriorities.map((priority) => (
                <li key={priority.competitionId}>
                  {`${run.lastBlockSummary?.standings.find((table) => table.competitionId === priority.competitionId)?.competitionName ?? priority.competitionId.replaceAll('-', ' ')}: ${PRIORITY_LABELS[priority.priority] ?? priority.priority}`}
                </li>
              ))}
            </ul>
          </div>
        )}
      </details>
      <details>
        <summary className="min-h-touch cursor-pointer py-3 font-semibold">{`Plantilla (${String(run.squad.size)})`}</summary>
        <p className="text-caption text-ink-muted">{`Media nominal de la plantilla: ${String(run.squad.averageRating)}`}</p>
        <ul className="divide-y divide-line text-body">
          {run.squad.players.map((player) => (
            <li key={player.id} className="py-2">
              <p className="font-semibold">
                {player.displayName}
                {player.key ? ' · Jugador clave' : ''}
              </p>
              <p>{`${POSITIONS[player.position]} · ${String(player.age)} años · Valoración: ${String(player.rating)}`}</p>
              <p>{`Moral: ${String(player.morale)} · Físico: ${String(player.fitness)} · ${injuryLabel(player.injury)}`}</p>
            </li>
          ))}
        </ul>
      </details>
      <details>
        <summary className="min-h-touch cursor-pointer py-3 font-semibold">Clasificación</summary>
        <div className="flex flex-col gap-3">
          {run.lastBlockSummary && run.lastBlockSummary.standings.length > 0 ? (
            <>
              <p className="text-caption text-ink-muted">{`Última clasificación publicada: ${run.lastBlockSummary.label}.`}</p>
              {run.lastBlockSummary.standings.map((table) => (
                <MiniStandings
                  key={[table.competitionId, table.stageId, table.groupId].join('/')}
                  competitionName={table.competitionName}
                  rows={table.rows.map((row) => ({
                    position: row.position,
                    teamName: row.team.name,
                    played: row.played,
                    points: row.points,
                    isUser: row.team.isUser,
                    change: describePositionChange(row),
                  }))}
                />
              ))}
            </>
          ) : (
            <p className="text-body text-ink-muted">
              La clasificación estará disponible al cerrar el primer bloque.
            </p>
          )}
        </div>
      </details>
    </section>
  );
}
