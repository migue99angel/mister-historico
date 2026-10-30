import { useId, useState, type Ref } from 'react';
import type {
  KeyStarterOfferDto,
  MatchReportDto,
  KeyStarterOutcomeDto,
  SquadMemberDto,
} from '../../../application/ports';
import { Button, Card } from '../../design-system';

const DATE_FORMAT = new Intl.DateTimeFormat('es', {
  day: 'numeric',
  month: 'short',
  year: 'numeric',
  timeZone: 'UTC',
});

function MatchDate({ date }: { date: string }) {
  return <time dateTime={date}>{DATE_FORMAT.format(new Date(`${date}T00:00:00Z`))}</time>;
}

const POSITIONS = { GK: 'Portero', DF: 'Defensa', MF: 'Centrocampista', FW: 'Delantero' };

function capturedCondition(player: SquadMemberDto): string {
  return `${POSITIONS[player.position]} · Media ${String(player.rating)} · Moral ${String(player.morale)} · Físico ${String(player.fitness)} · ${player.injury ? `Lesión: ${String(player.injury.daysOut)} días de baja` : 'Sin lesión'}`;
}

export function KeyStarter({
  offer,
  disabled,
  pending,
  headingRef,
  onConfirm,
}: {
  offer: KeyStarterOfferDto;
  disabled: boolean;
  pending: boolean;
  headingRef: Ref<HTMLHeadingElement>;
  onConfirm: (playerId: string) => void;
}) {
  const headingId = useId();
  const groupId = useId();
  const [choice, setChoice] = useState<string | null>(null);
  const confirmed = offer.candidates.find((p) => p.id === offer.selectedPlayerId);
  return (
    <section aria-labelledby={headingId} className="flex flex-col gap-3">
      <h2
        id={headingId}
        ref={headingRef}
        tabIndex={-1}
        className="font-display text-title font-bold"
      >
        Titular para el partido clave
      </h2>
      <Card>
        <p className="font-semibold">
          {offer.opponent.name} · <MatchDate date={offer.date} />
        </p>
        <p>
          {offer.competitionName} ·{' '}
          {{ home: 'En casa', away: 'Fuera de casa', neutral: 'Campo neutral' }[offer.venue]}
          {offer.keyMatchLabel ? ` · ${offer.keyMatchLabel}` : ''}
        </p>
        <p className="mt-2 text-caption text-ink-muted">
          Estado capturado al inicio del bloque. Elegir titular no garantiza ganar; las lesiones y
          los cambios de plantilla pueden impedir que juegue.
        </p>
        <details open className="mt-3">
          <summary className="min-h-touch cursor-pointer py-2 font-semibold">
            Once previsto al inicio del bloque
          </summary>
          <p className="text-caption text-ink-muted">
            Previsión del servidor; el once real se conocerá después de simular.
          </p>
          <ul className="grid gap-2 py-2 text-caption sm:grid-cols-2">
            {offer.projectedStarters.map((player) => (
              <li key={player.id}>
                <span className="font-semibold">{player.displayName}</span>
                <p>{capturedCondition(player)}</p>
              </li>
            ))}
          </ul>
        </details>
        {confirmed ? (
          <p role="status" className="mt-3 font-semibold">
            Titular confirmado: {confirmed.displayName}
          </p>
        ) : (
          <>
            <fieldset disabled={disabled} className="mt-3 flex min-w-0 flex-col gap-2">
              <legend className="font-semibold">Elige un suplente para que salga de titular</legend>
              {offer.candidates.map((player) => (
                <label
                  key={player.id}
                  className="flex min-h-touch cursor-pointer items-start gap-3 rounded-card border border-line p-3 has-[:checked]:border-ink"
                >
                  <input
                    type="radio"
                    name={groupId}
                    value={player.id}
                    checked={choice === player.id}
                    onChange={() => {
                      setChoice(player.id);
                    }}
                    className="mt-1 shrink-0"
                  />
                  <span className="min-w-0">
                    <span className="font-semibold">{player.displayName}</span>
                    <span className="block text-caption">{capturedCondition(player)}</span>
                  </span>
                </label>
              ))}
            </fieldset>
            <Button
              disabled={disabled || choice === null}
              loading={pending}
              onClick={() => {
                if (choice) onConfirm(choice);
              }}
            >
              Confirmar titular
            </Button>
          </>
        )}
      </Card>
    </section>
  );
}

const ABSENCE = {
  injured: 'No pudo jugar por lesión.',
  not_in_squad: 'Ya no estaba en la plantilla.',
  youth_conflict: 'No pudo jugar por un conflicto de cantera.',
  fixture_not_played: 'El partido no se disputó.',
};

/** Only the server's post-block evidence establishes actual participation. */
export function KeyStarterResult({
  outcome,
  match,
}: {
  outcome: KeyStarterOutcomeDto;
  match: MatchReportDto | undefined;
}) {
  return (
    <section aria-label="Resultado del titular elegido" className="mt-3 border-t border-line pt-3">
      <h3 className="font-semibold">Resultado del titular elegido</h3>
      <p>
        <MatchDate date={outcome.date} /> ·{' '}
        {match
          ? `${match.home.isUser ? match.away.name : match.home.name} · ${match.competitionName}`
          : 'Partido señalado'}
      </p>
      <p>
        {outcome.selectedPlayer?.displayName ?? outcome.playerId}:{' '}
        {outcome.absenceReason === null ? 'Jugó de titular.' : ABSENCE[outcome.absenceReason]}
      </p>
      {outcome.starterIds.length > 0 && (
        <details open>
          <summary className="min-h-touch cursor-pointer py-2 font-semibold">Once real</summary>
          <ul className="grid gap-1 text-caption sm:grid-cols-2">
            {outcome.starterIds.map((id) => (
              <li key={id}>
                {outcome.starters?.find((player) => player.id === id)?.displayName ?? id}
              </li>
            ))}
          </ul>
        </details>
      )}
    </section>
  );
}
