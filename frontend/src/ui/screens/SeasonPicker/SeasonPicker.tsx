import { useId } from 'react';

import type { SeasonSummaryDto } from '../../../application/ports';
import { useSeasons } from '../../../application/useSeasons';
import { Button, Card, GenericCrest } from '../../design-system';

export interface SeasonPickerProps {
  onSeasonChosen: (seasonId: string) => void;
}

/** Home screen (`/`): the game's pitch and the playable seasons to choose from. */
export function SeasonPicker({ onSeasonChosen }: SeasonPickerProps) {
  const headingId = useId();

  return (
    <main className="mx-auto flex min-h-dvh w-full max-w-md flex-col gap-8 px-gutter py-12">
      <header className="flex flex-col items-center gap-3 text-center">
        <h1 className="font-display text-display font-extrabold tracking-tight">
          Míster Histórico
        </h1>
        <p className="text-title text-ink-muted">¿Lo habrías hecho mejor que el míster?</p>
      </header>

      <section aria-labelledby={headingId} className="flex flex-col gap-4">
        <h2 id={headingId} className="font-display text-headline font-extrabold">
          Elige una temporada
        </h2>
        <SeasonList onSeasonChosen={onSeasonChosen} />
      </section>
    </main>
  );
}

function SeasonList({ onSeasonChosen }: SeasonPickerProps) {
  const seasons = useSeasons();

  if (seasons.isPending) {
    return (
      <p role="status" className="text-ink-muted">
        Cargando temporadas…
      </p>
    );
  }

  if (seasons.isError) {
    return (
      <div role="alert" className="flex flex-col items-start gap-3">
        <p>No hemos podido cargar las temporadas.</p>
        <Button
          variant="secondary"
          loading={seasons.isFetching}
          onClick={() => void seasons.refetch()}
        >
          Reintentar
        </Button>
      </div>
    );
  }

  if (seasons.data.length === 0) {
    return <p className="text-ink-muted">Todavía no hay temporadas disponibles.</p>;
  }

  return (
    <ul className="flex flex-col gap-3">
      {seasons.data.map((season) => (
        <li key={season.id}>
          <SeasonCard season={season} onChoose={onSeasonChosen} />
        </li>
      ))}
    </ul>
  );
}

function SeasonCard({
  season,
  onChoose,
}: {
  season: SeasonSummaryDto;
  onChoose: (seasonId: string) => void;
}) {
  return (
    <Card title={season.clubName} eyebrow={season.seasonLabel} headingLevel={3}>
      <div className="flex items-center gap-3">
        <GenericCrest colors={season.colors} size={48} />
        <p className="min-w-0 flex-1 text-caption text-ink-muted">
          Míster real: {season.historicalManager}
        </p>
        <Button
          aria-label={`Elegir ${season.clubName} ${season.seasonLabel}`}
          onClick={() => {
            onChoose(season.id);
          }}
        >
          Elegir
        </Button>
      </div>
    </Card>
  );
}
