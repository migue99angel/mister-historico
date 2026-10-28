import { BlockProgress, Button, Card, MatchLine, MiniStandings } from '../../design-system';
import { describeRunResult, type TerminalRunView } from './runResultView';

export type { TerminalRunView } from './runResultView';

export interface RunResultProps {
  /** An ended run (`finished` or `sacked`); narrow a `RunViewDto` with `isTerminalRun`. */
  run: TerminalRunView;
  onPlayAgain: () => void;
}

/** Final screen of a run: how it ended, the last block played and a way to play again. */
export function RunResult({ run, onPlayAgain }: RunResultProps) {
  const view = describeRunResult(run);

  return (
    <main className="mx-auto flex min-h-dvh w-full max-w-md flex-col gap-4 px-gutter py-6">
      <h1 className="font-display text-headline font-extrabold text-ink">Final de la partida</h1>
      <BlockProgress progress={view.progress} status={view.status} />
      <p className="text-body text-ink">{view.outcomeText}</p>

      {view.lastBlock ? (
        <Card title="Último bloque" eyebrow={view.lastBlock.eyebrow}>
          <ul className="divide-y divide-line">
            {view.lastBlock.matches.map((item) => (
              <li key={item.key}>
                <MatchLine
                  match={item.match}
                  competitionName={item.competitionName}
                  keyMatchLabel={item.keyMatchLabel}
                  userSide={item.userSide}
                />
              </li>
            ))}
          </ul>
        </Card>
      ) : (
        <p className="text-body text-ink-muted">No hay resumen del último bloque.</p>
      )}

      {view.standings && (
        <Card title={view.standings.title}>
          <MiniStandings
            competitionName={view.standings.competitionName}
            rows={view.standings.rows}
          />
        </Card>
      )}

      <Button fullWidth onClick={onPlayAgain}>
        Jugar otra partida
      </Button>
    </main>
  );
}
