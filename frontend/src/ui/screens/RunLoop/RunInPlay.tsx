import { useEffect, useId, useRef, useState } from 'react';

import type { DilemmaDto, RunViewDto, TeamRefDto } from '../../../application/ports';
import { useAdvanceBlock } from '../../../application/useAdvanceBlock';
import {
  useSelectKeyStarter,
  type KeyStarterChoice,
} from '../../../application/useSelectKeyStarter';
import { useTakeDecision } from '../../../application/useTakeDecision';
import { describeDecisionChanges } from '../../../domain/decisionFeedback';
import { toRunViewModel } from '../../../domain/runViewModel';
import { BlockProgress, Button, DilemmaCard, GenericCrest } from '../../design-system';
import { BlockSummary } from './BlockSummary';
import { CoachLayout } from './CoachLayout';
import { KeyStarter, KeyStarterResult } from './KeyStarter';
import { useBlockReveal } from './useBlockReveal';
import { commandFailureMessage, pendingDilemmasHint, type RunLoopCommand } from './feedback';

export interface RunInPlayProps {
  run: RunViewDto;
  /** True while a newer view is loading (e.g. after a 409): the simulation waits for it. */
  isRefreshing: boolean;
  onRunEnded: (runId: string) => void;
}

/** Confirms each decision before allowing the block to be simulated. */
export function RunInPlay({ run, isRefreshing, onRunEnded }: RunInPlayProps) {
  const reveal = useBlockReveal(
    run.version,
    new Set(run.lastBlockSummary?.results.map((match) => match.date)).size,
  );
  const notified = useRef(false);
  const decisionsHeading = useRef<HTMLHeadingElement>(null);
  const focusDecisions = useRef(false);
  const wasRevealing = useRef(false);
  const decision = useTakeDecision(run.runId);
  const advance = useAdvanceBlock(run.runId);
  const starter = useSelectKeyStarter(run.runId);
  const [starterAttempt, setStarterAttempt] = useState<KeyStarterChoice | null>(null);
  const starterHeading = useRef<HTMLHeadingElement>(null);
  const focusStarter = useRef(false);
  const [choices, setChoices] = useState<Partial<Record<string, string>>>({});
  const [submitting, setSubmitting] = useState(false);
  const [confirmed, setConfirmed] = useState<{
    dilemmaId: string;
    optionId: string;
    title: string;
    label: string;
    version: number;
  } | null>(null);
  const [attempted, setAttempted] = useState<{ dilemma: DilemmaDto; optionId: string } | null>(
    null,
  );
  const confirmationHeading = useRef<HTMLHeadingElement>(null);
  const focusConfirmation = useRef(false);
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
  const uncertain =
    (failedStep === 'decision' && decision.failure?.kind === 'failed') ||
    (failedStep === 'starter' && starter.failure?.kind === 'failed');
  const advanceUncertain = failedStep === 'advance' && advance.failure?.kind === 'failed';
  const locked = submitting || isRefreshing || uncertain || advanceUncertain;
  const transition = decision.transition;
  const showConfirmation = confirmed !== null && confirmed.version === run.version && !isRefreshing;
  const changes =
    showConfirmation && transition && !transition.retried
      ? describeDecisionChanges(transition.before, transition.after, confirmed)
      : null;
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
          failedStep === 'decision'
            ? decision.failure
            : failedStep === 'starter'
              ? starter.failure
              : advance.failure,
        );

  useEffect(() => {
    if (run.status !== 'in_progress' && !submitting && !reveal.revealing && !notified.current) {
      notified.current = true;
      onRunEnded(run.runId);
    }
  }, [run.status, run.runId, submitting, reveal.revealing, onRunEnded]);

  useEffect(() => {
    if (
      wasRevealing.current &&
      !reveal.revealing &&
      (document.activeElement === document.body ||
        document.activeElement === summaryHeading.current)
    ) {
      summaryHeading.current?.focus();
      // The mobile panel returns before this heading and can push retained focus offscreen.
      if (typeof summaryHeading.current?.scrollIntoView === 'function') {
        summaryHeading.current.scrollIntoView({ block: 'nearest' });
      }
    }
    wasRevealing.current = reveal.revealing;
    if (focusDecisions.current && !reveal.revealing) {
      focusDecisions.current = false;
      decisionsHeading.current?.focus();
    }
    const summaryVersion = focusSummaryFromVersion.current;
    if (summaryVersion !== null && run.version >= summaryVersion) {
      focusSummaryFromVersion.current = null;
      summaryHeading.current?.focus();
    }
    if (focusConfirmation.current && confirmationHeading.current) {
      focusConfirmation.current = false;
      confirmationHeading.current.focus();
    }
    if (focusStarter.current && starterHeading.current) {
      focusStarter.current = false;
      starterHeading.current.focus();
    }
    if (focusFailure.current) {
      focusFailure.current = false;
      failureAlert.current?.focus();
    }
  }, [run.version, focusRequest, showConfirmation, reveal.revealing]);

  function reportFailure(step: RunLoopCommand) {
    setFailedStep(step);
    focusFailure.current = true;
    setFocusRequest((request) => request + 1);
  }

  async function confirmDecision(dilemma: DilemmaDto, optionId: string | null) {
    if (busy.current || isRefreshing || !inProgress || optionId === null) return;
    busy.current = true;
    setSubmitting(true);
    setConfirmed(null);
    setAttempted({ dilemma, optionId });
    setFailedStep(null);
    try {
      const decided = await decision.send({ dilemmaId: dilemma.id, optionId });
      if (!decided) {
        reportFailure('decision');
        return;
      }
      setConfirmed({
        dilemmaId: dilemma.id,
        optionId,
        title: dilemma.title,
        label: dilemma.options.find((option) => option.id === optionId)?.label ?? optionId,
        version: decided.version,
      });
      focusConfirmation.current = true;
      setFocusRequest((request) => request + 1);
    } finally {
      busy.current = false;
      setSubmitting(false);
    }
  }

  async function confirmStarter(choice: KeyStarterChoice) {
    if (busy.current || isRefreshing || !inProgress) return;
    busy.current = true;
    setSubmitting(true);
    setStarterAttempt(choice);
    setFailedStep(null);
    setConfirmed(null);
    try {
      const selected = await starter.send(choice);
      if (!selected) {
        reportFailure('starter');
        return;
      }
      focusStarter.current = true;
      setFocusRequest((request) => request + 1);
    } finally {
      busy.current = false;
      setSubmitting(false);
    }
  }

  async function simulateBlock() {
    if (
      busy.current ||
      uncertain ||
      reveal.revealing ||
      isRefreshing ||
      !inProgress ||
      pending.length > 0
    )
      return;
    busy.current = true;
    setSubmitting(true);
    setConfirmed(null);
    setFailedStep(null);
    try {
      const simulated = await advance.send();
      if (!simulated) {
        reportFailure('advance');
        return;
      }
      reveal.start(
        simulated.version,
        new Set(simulated.lastBlockSummary?.results.map((match) => match.date)).size,
      );
      focusSummaryFromVersion.current = simulated.version;
      setFocusRequest((request) => request + 1);
    } finally {
      busy.current = false;
      setSubmitting(false);
    }
  }

  return (
    <>
      {userTeam && (
        <header
          aria-label="Tu equipo"
          className="mx-auto flex w-full max-w-6xl items-center gap-3 border-b border-line px-gutter py-3"
        >
          <GenericCrest colors={userTeam.colors} size={36} />
          <p className="min-w-0 font-display text-title [overflow-wrap:anywhere] leading-tight font-bold">
            {userTeam.name}
          </p>
        </header>
      )}
      <main className="mx-auto flex w-full max-w-6xl flex-col gap-4 px-gutter py-4 [overflow-wrap:anywhere]">
        <h1 className="sr-only">Partida</h1>
        {!reveal.revealing && <BlockProgress progress={viewModel.progress} status={run.status} />}

        <CoachLayout
          run={run}
          revealing={reveal.revealing}
          onDecisions={inProgress ? () => decisionsHeading.current?.focus() : undefined}
        >
          {run.lastBlockSummary && viewModel.lastBlock && (
            <BlockSummary
              summary={run.lastBlockSummary}
              narrative={viewModel.lastBlock}
              headingRef={summaryHeading}
              visibleDates={reveal.visibleDates}
              revealing={reveal.revealing}
              onDecisions={
                inProgress
                  ? () => {
                      focusDecisions.current = true;
                      reveal.complete();
                    }
                  : undefined
              }
              onComplete={() => {
                reveal.complete();
              }}
            />
          )}

          {!reveal.revealing && run.lastBlockSummary?.keyStarterOutcome && (
            <KeyStarterResult
              outcome={run.lastBlockSummary.keyStarterOutcome}
              match={run.lastBlockSummary.results.find(
                (match) => match.fixtureId === run.lastBlockSummary?.keyStarterOutcome?.fixtureId,
              )}
            />
          )}

          {inProgress && !reveal.revealing && run.keyStarter && (
            <KeyStarter
              key={`${run.keyStarter.blockId}/${run.keyStarter.fixtureId}`}
              offer={run.keyStarter}
              disabled={locked}
              pending={starter.isPending}
              headingRef={starterHeading}
              onConfirm={(playerId) => {
                if (run.keyStarter)
                  void confirmStarter({ fixtureId: run.keyStarter.fixtureId, playerId });
              }}
            />
          )}

          {showConfirmation && (
            <section
              aria-label="Última decisión"
              aria-live="polite"
              className="flex flex-col gap-2 rounded-card border border-line p-4"
            >
              <h2
                ref={confirmationHeading}
                tabIndex={-1}
                className="font-display text-title font-bold"
              >
                {changes === null ? 'Estado actualizado' : 'Decisión confirmada'}
              </h2>
              {changes !== null ? (
                <>
                  <p>{`${confirmed.title}: ${confirmed.label}`}</p>
                  <ul className="text-body">
                    {changes.map((change) => (
                      <li key={change}>{change}</li>
                    ))}
                  </ul>
                  <p className="text-caption text-ink-muted">
                    Diferencias visibles entre el estado anterior y la respuesta a esta decisión. El
                    físico medio también depende de la composición de la plantilla; estos valores no
                    identifican la causa de cada cambio. Un cambio cero indica que el valor
                    publicado se mantiene.
                  </p>
                </>
              ) : (
                <p>
                  No podemos aislar los cambios de esta confirmación. Consulta el estado actualizado
                  del equipo.
                </p>
              )}
              <p className="text-caption text-ink-muted">
                Este detalle es temporal; tras recargar puedes consultar el estado y las decisiones
                confirmadas.
              </p>
            </section>
          )}

          {!reveal.revealing && run.decisions.length > 0 && (
            <section aria-label="Decisiones confirmadas">
              <details>
                <summary className="min-h-touch cursor-pointer py-3 font-semibold">
                  Ver decisiones confirmadas
                </summary>
                <ul className="text-body">
                  {run.decisions.map((made) => (
                    <li key={`${String(made.blockNumber)}/${made.dilemmaId}`}>
                      {`Bloque ${String(made.blockNumber)} · ${made.dilemmaId.replaceAll('-', ' ')} · ${made.optionId.replaceAll('-', ' ')}`}
                    </li>
                  ))}
                </ul>
              </details>
            </section>
          )}

          {inProgress && !reveal.revealing && (
            <section aria-labelledby={dilemmasHeadingId} className="flex flex-col gap-4">
              <h2
                ref={decisionsHeading}
                tabIndex={-1}
                id={dilemmasHeadingId}
                className="mt-2 font-display text-headline font-extrabold"
              >
                Decisiones del bloque
              </h2>
              {pending.map((dilemma, index) => (
                <div key={dilemma.id} className="flex flex-col gap-2">
                  <DilemmaCard
                    dilemma={dilemma}
                    eyebrow={`Dilema ${String(decidedInBlock + index + 1)} de ${String(dilemmasInBlock)}`}
                    headingLevel={3}
                    selectedOptionId={chosenOptionId(dilemma)}
                    disabled={locked}
                    onSelect={(optionId) => {
                      setChoices((current) => ({ ...current, [dilemma.id]: optionId }));
                    }}
                  />
                  <Button
                    loading={decision.isPending && attempted?.dilemma.id === dilemma.id}
                    disabled={locked || chosenOptionId(dilemma) === null}
                    aria-label={`Confirmar: ${dilemma.title}`}
                    onClick={() => {
                      void confirmDecision(dilemma, chosenOptionId(dilemma));
                    }}
                  >
                    Confirmar decisión
                  </Button>
                </div>
              ))}
            </section>
          )}

          {inProgress && !reveal.revealing && (
            <div className="border-t border-line bg-canvas py-3">
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
              {uncertain && failedStep === 'decision' && attempted && (
                <Button
                  fullWidth
                  disabled={submitting || isRefreshing}
                  onClick={() => {
                    void confirmDecision(attempted.dilemma, attempted.optionId);
                  }}
                >
                  Reintentar confirmación
                </Button>
              )}
              {uncertain && failedStep === 'starter' && starterAttempt && (
                <Button
                  fullWidth
                  disabled={submitting || isRefreshing}
                  onClick={() => {
                    void confirmStarter(starterAttempt);
                  }}
                >
                  Reintentar titular
                </Button>
              )}
              <Button
                fullWidth
                disabled={pending.length > 0 || submitting || isRefreshing || uncertain}
                loading={submitting && advance.isPending}
                aria-describedby={hintId}
                onClick={() => {
                  void simulateBlock();
                }}
              >
                {submitting && advance.isPending
                  ? 'Simulando…'
                  : run.keyStarter && !run.keyStarter.selectedPlayerId
                    ? 'Simular bloque sin elegir titular'
                    : 'Simular bloque'}
              </Button>
              <p id={hintId} className="mt-1.5 text-center text-caption text-ink-muted">
                {pendingDilemmasHint(pending.length)}
              </p>
            </div>
          )}
        </CoachLayout>
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
