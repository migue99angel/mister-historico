import { ApiError } from '../../../application/apiError';
import type { PlayerPositionDto, SeasonDetailDto } from '../../../application/ports';
import { useSeason } from '../../../application/useSeasons';
import { useStartRun } from '../../../application/useStartRun';
import { Button, Card, GenericCrest } from '../../design-system';

export interface SeasonIntroProps {
  seasonId: string;
  onRunStarted: (runId: string) => void;
  onBackHome: () => void;
}

const POSITION_LABELS: Record<PlayerPositionDto, string> = {
  GK: 'Portero',
  DF: 'Defensa',
  MF: 'Centrocampista',
  FW: 'Delantero',
};

const ratingFormat = new Intl.NumberFormat('es-ES', { maximumFractionDigits: 1 });

const PAGE_CLASSES = 'mx-auto flex min-h-dvh w-full max-w-md flex-col gap-4 px-gutter py-6';

/** Season context (`/equipo/:id`): who you manage, what the board expects, and «Empezar». */
export function SeasonIntro({ seasonId, onRunStarted, onBackHome }: SeasonIntroProps) {
  const season = useSeason(seasonId);

  if (season.isPending) {
    return (
      <main className={PAGE_CLASSES}>
        <p role="status" className="text-ink-muted">
          Cargando la temporada…
        </p>
      </main>
    );
  }

  if (season.isError) {
    if (season.error instanceof ApiError && season.error.status === 404) {
      return (
        <main className={PAGE_CLASSES}>
          <h1 className="font-display text-headline font-extrabold">Temporada no encontrada</h1>
          <p className="text-ink-muted">Esta temporada no existe o ya no se puede jugar.</p>
          <Button onClick={onBackHome}>Volver al inicio</Button>
        </main>
      );
    }
    return (
      <main className={PAGE_CLASSES}>
        <div role="alert" className="flex flex-col items-start gap-3">
          <p>No hemos podido cargar la temporada.</p>
          <Button
            variant="secondary"
            loading={season.isFetching}
            onClick={() => void season.refetch()}
          >
            Reintentar
          </Button>
        </div>
      </main>
    );
  }

  return <SeasonContext season={season.data} onRunStarted={onRunStarted} onBackHome={onBackHome} />;
}

function SeasonContext({
  season,
  onRunStarted,
  onBackHome,
}: {
  season: SeasonDetailDto;
  onRunStarted: (runId: string) => void;
  onBackHome: () => void;
}) {
  const startRun = useStartRun();

  return (
    <main className={PAGE_CLASSES}>
      <header className="flex items-center gap-3">
        <GenericCrest colors={season.colors} size={56} />
        <div className="min-w-0">
          <h1 className="font-display text-headline font-extrabold">{season.clubName}</h1>
          <p className="text-caption text-ink-muted">
            Temporada {season.seasonLabel} · Míster real: {season.historicalManager}
          </p>
        </div>
      </header>

      <p>{season.presentation}</p>

      <Card title="Objetivos de la directiva" tone="highlight">
        <ul className="flex list-disc flex-col gap-1 pl-5">
          {season.boardObjectives.map((objective) => (
            <li key={objective.id}>{objective.description}</li>
          ))}
        </ul>
      </Card>

      <Card title="Plantilla">
        <p className="text-caption text-ink-muted">
          {season.squad.size} jugadores · media {ratingFormat.format(season.squad.averageRating)}
        </p>
        <h3 className="mt-3 font-semibold">Jugadores clave</h3>
        <ul className="mt-1 divide-y divide-line">
          {season.squad.keyPlayers.map((player) => (
            <li key={player.id} className="flex items-baseline justify-between gap-3 py-2">
              <span>{player.displayName}</span>
              <span className="text-caption text-ink-muted">
                {POSITION_LABELS[player.position]} · {player.rating}
              </span>
            </li>
          ))}
        </ul>
      </Card>

      <Card title="La temporada">
        <ul className="flex flex-col gap-1">
          {season.competitions.map((competition) => (
            <li key={competition.id}>{competition.name}</li>
          ))}
        </ul>
        <p className="mt-3 text-caption text-ink-muted">Se juega en {season.blockCount} bloques.</p>
      </Card>

      <div className="sticky bottom-0 -mx-gutter mt-auto flex flex-col gap-2 border-t border-line bg-canvas/95 px-gutter py-3 backdrop-blur">
        {startRun.error && (
          <p role="alert" className="text-center text-loss">
            No hemos podido empezar la partida.
          </p>
        )}
        <Button
          fullWidth
          loading={startRun.isPending}
          onClick={() => {
            startRun.start(season.id, { onStarted: onRunStarted });
          }}
        >
          {startRun.error ? 'Reintentar' : 'Empezar'}
        </Button>
        <Button variant="ghost" fullWidth onClick={onBackHome}>
          Elegir otra temporada
        </Button>
      </div>
    </main>
  );
}
