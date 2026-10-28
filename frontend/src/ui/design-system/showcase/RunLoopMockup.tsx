import { useEffect, useId, useState } from 'react';

import { BlockProgress } from '../BlockProgress';
import { Button } from '../Button';
import { Card } from '../Card';
import { DilemmaCard } from '../DilemmaCard';
import { MatchLine } from '../MatchLine';
import { MiniStandings } from '../MiniStandings';
import { ClubHeader } from './ClubHeader';
import { PhoneFrame } from './PhoneFrame';
import {
  dilemmas,
  lastBlockMatches,
  LEAGUE,
  progressStates,
  standingsAfterAugust,
} from './sampleData';

const SIMULATION_DEMO_MS = 1500;

/** Block loop screen (T4.5) with synthetic data: summary, standings and dilemmas. */
export function RunLoopMockup() {
  const hintId = useId();
  const [choices, setChoices] = useState<Record<string, string>>({});
  const [simulating, setSimulating] = useState(false);
  const pending = dilemmas.filter((dilemma) => !(dilemma.id in choices)).length;

  useEffect(() => {
    if (!simulating) return;
    const timer = setTimeout(() => {
      setSimulating(false);
      setChoices({});
    }, SIMULATION_DEMO_MS);
    return () => {
      clearTimeout(timer);
    };
  }, [simulating]);

  return (
    <PhoneFrame
      title="Bucle de bloques"
      description="Resumen del último bloque, clasificación y dilemas del siguiente. Elige una opción en cada dilema para simular."
    >
      <ClubHeader />
      <div className="flex flex-col gap-4 px-gutter py-4">
        <BlockProgress progress={progressStates.loop} />

        <Card title="Resumen del bloque" eyebrow="Agosto · 3V 1E 1D" headingLevel={4}>
          <ul className="divide-y divide-line">
            {lastBlockMatches.map((sample) => (
              <li key={`${sample.match.homeName}-${sample.match.awayName}`}>
                <MatchLine
                  match={sample.match}
                  competitionName={sample.competitionName}
                  keyMatchLabel={sample.keyMatchLabel}
                  userSide={sample.userSide}
                />
              </li>
            ))}
          </ul>
          <p className="mt-3 text-caption text-ink-muted">
            Parte médico: Nico Prueba, baja 12 días.
          </p>
        </Card>

        <Card title="Clasificación" headingLevel={4}>
          <MiniStandings competitionName={LEAGUE} rows={standingsAfterAugust} />
        </Card>

        <h4 className="mt-2 font-display text-headline font-extrabold">Decisiones del bloque</h4>
        {dilemmas.map((dilemma, index) => (
          <DilemmaCard
            key={dilemma.id}
            dilemma={dilemma}
            eyebrow={`Dilema ${String(index + 1)} de ${String(dilemmas.length)}`}
            headingLevel={5}
            selectedOptionId={choices[dilemma.id] ?? null}
            disabled={simulating}
            onSelect={(optionId) => {
              setChoices((current) => ({ ...current, [dilemma.id]: optionId }));
            }}
          />
        ))}
      </div>
      <div className="sticky bottom-0 rounded-b-[1.75rem] border-t border-line bg-canvas/95 px-gutter py-3 backdrop-blur">
        <Button
          fullWidth
          disabled={pending > 0}
          loading={simulating}
          aria-describedby={hintId}
          onClick={() => {
            setSimulating(true);
          }}
        >
          {simulating ? 'Simulando…' : 'Simular bloque'}
        </Button>
        <p id={hintId} className="mt-1.5 text-center text-caption text-ink-muted">
          {pending > 0
            ? `Te ${pending === 1 ? 'queda 1 dilema' : `quedan ${String(pending)} dilemas`} por decidir.`
            : 'Todo decidido: simula el bloque.'}
        </p>
      </div>
    </PhoneFrame>
  );
}
