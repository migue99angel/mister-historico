import { useEffect, useId, useRef, useState } from 'react';

import type { DilemmaDto, RunViewDto, TeamRefDto } from '../../../application/ports';
import { useAdvanceBlock } from '../../../application/useAdvanceBlock';
import { useTakeDecision } from '../../../application/useTakeDecision';
import { toRunViewModel } from '../../../domain/runViewModel';
import { BlockProgress, Button, DilemmaCard, GenericCrest } from '../../design-system';
import { BlockSummary } from './BlockSummary';
import { commandFailureMessage, pendingDilemmasHint, type RunLoopCommand } from './feedback';

export interface RunInPlayProps {
  run: RunViewDto;
  /** True while a newer view is loading (e.g. after a 409): the simulation waits for it. */
  isRefreshing: boolean;
}

/**
 * The run view while it can be played. The player chooses an option in every pending dilemma
 * (nothing is sent yet) and «Simular bloque» sends the decisions one by one, each against the
 * version the previous one returned, and then simulates the block.
 */
export function RunInPlay({ run, isRefreshing }: RunInPlayProps) {
  const decision = useTakeDecision(run.runId);
  const advance = useAdvanceBlock(run.runId);
  const [choices, setChoices] = useState<Partial<Record<string, string>>>({});
  const [simulating, setSimulating] = useState(false);
  const [failedStep, setFailedStep] = useState<RunLoopCommand | null>(null);
  const [focusRequest, setFocusRequest] = useState(0);
  // Refs: a second tap arrives before React re-renders the loading state.
  const busy = useRef(false);
  // Focus targets, applied once the view they need has rendered (see the effect below).
  const focusSummaryFromVersion = useRef<number | null>(null);
  const focusFailure = useRef(false);
  const summaryHeading = useRef<HTMLHeadingElement>(null);
  const failureAlert = useRef<HTMLParagraphElement>(null);
  const hintId = useId();
  const dilemmasHeadingId = useId();

  const viewModel = toRunViewModel(run);
  const userTeam = findUserTeam(run);
  const inProgress = run.status === 'in_progress';
  const pending = run.pendingDilemmas;
  const chosenOptionId = (dilemma: DilemmaDto): string | null =>
    dilemma.options.find((option) => option.id === choices[dilemma.id])?.id ?? null;
  const unchosen = pending.filter((dilemma) => chosenOptionId(dilemma) === null).length;
  // Dilemmas keep their place in the block while earlier ones are decided.
  const decidedInBlock = run.decisions.filter(
    (made) => made.blockNumber === run.block.number,
  ).length;
  const dilemmasInBlock = decidedInBlock + pending.length;
  const failureMessage =
    failedStep === null
      ? null
      : commandFailureMessage(
          failedStep,
          failedStep === 'decision' ? decision.failure : advance.failure,
        );

  useEffect(() => {
    const summaryVersion = focusSummaryFromVersion.current;
    if (summaryVersion !== null && run.version >= summaryVersion) {
      focusSummaryFromVersion.current = null;
      summaryHeading.current?.focus();
    }
    if (focusFailure.current) {
      focusFailure.current = false;
      failureAlert.current?.focus();
    }
  }, [run.version, focusRequest]);

  function stopSeries(step: RunLoopCommand) {
    setFailedStep(step);
    focusFailure.current = true;
    setFocusRequest((request) => request + 1);
  }

  async function simulateBlock() {
    const steps = pending.map((dilemma) => ({
      dilemmaId: dilemma.id,
      optionId: chosenOptionId(dilemma),
    }));
    if (busy.current || steps.some((step) => step.optionId === null)) return;
    busy.current = true;
    setSimulating(true);
    setFailedStep(null);
    try {
      for (const { dilemmaId, optionId } of steps) {
        if (optionId === null) return;
        const decided = await decision.send({ dilemmaId, optionId });
        if (!decided) {
          stopSeries('decision');
          return;
        }
      }
      const simulated = await advance.send();
      if (!simulated) {
        stopSeries('advance');
        return;
      }
      // After a simulation the button is disabled by the next block's dilemmas.
      focusSummaryFromVersion.current = simulated.version;
      setFocusRequest((request) => request + 1);
    } finally {
      busy.current = false;
      setSimulating(false);
    }
  }

  return (
    <>
      {userTeam && (
        <header
          aria-label="Tu equipo"
          className="mx-auto flex w-full max-w-md items-center gap-3 border-b border-line px-gutter py-3"
        >
          <GenericCrest colors={userTeam.colors} size={36} />
          <p className="min-w-0 font-display text-title leading-tight font-bold">{userTeam.name}</p>
        </header>
      )}
      <main className="mx-auto flex w-full max-w-md flex-col gap-4 px-gutter pt-4">
        <h1 className="sr-only">Partida</h1>
        <BlockProgress progress={viewModel.progress} status={run.status} />

        {run.lastBlockSummary && viewModel.lastBlock && (
          <BlockSummary
            summary={run.lastBlockSummary}
            narrative={viewModel.lastBlock}
            headingRef={summaryHeading}
          />
        )}

        {inProgress && (
          <section aria-labelledby={dilemmasHeadingId} className="flex flex-col gap-4">
            <h2 id={dilemmasHeadingId} className="mt-2 font-display text-headline font-extrabold">
              Decisiones del bloque
            </h2>
            {pending.map((dilemma, index) => (
              <DilemmaCard
                key={dilemma.id}
                dilemma={dilemma}
                eyebrow={`Dilema ${String(decidedInBlock + index + 1)} de ${String(dilemmasInBlock)}`}
                headingLevel={3}
                selectedOptionId={chosenOptionId(dilemma)}
                disabled={simulating}
                onSelect={(optionId) => {
                  setChoices((current) => ({ ...current, [dilemma.id]: optionId }));
                }}
              />
            ))}
          </section>
        )}

        {inProgress && (
          <div className="sticky bottom-0 -mx-gutter border-t border-line bg-canvas/95 px-gutter py-3 backdrop-blur">
            {failureMessage && (
              <p
                ref={failureAlert}
                role="alert"
                tabIndex={-1}
                className="mb-2 text-center text-body text-loss"
              >
                {failureMessage}
              </p>
            )}
            <Button
              fullWidth
              disabled={unchosen > 0 || isRefreshing}
              loading={simulating}
              aria-describedby={hintId}
              onClick={() => {
                void simulateBlock();
              }}
            >
              {simulating ? 'Simulando…' : 'Simular bloque'}
            </Button>
            <p id={hintId} className="mt-1.5 text-center text-caption text-ink-muted">
              {pendingDilemmasHint(unchosen)}
            </p>
          </div>
        )}
      </main>
    </>
  );
}

/** The player's club as the last block summary names it; none before the first block. */
function findUserTeam(run: RunViewDto): TeamRefDto | null {
  const summary = run.lastBlockSummary;
  if (!summary) return null;
  const teams = [
    ...summary.results.flatMap((match) => [match.home, match.away]),
    ...summary.standings.flatMap((table) => table.rows.map((row) => row.team)),
  ];
  return teams.find((team) => team.isUser) ?? null;
}
