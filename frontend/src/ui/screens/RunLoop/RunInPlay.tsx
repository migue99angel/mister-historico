import { useEffect, useId, useRef, useState } from 'react';

import type { DilemmaDto, RunViewDto, TeamRefDto } from '../../../application/ports';
import { useAdvanceBlock } from '../../../application/useAdvanceBlock';
import { useTakeDecision } from '../../../application/useTakeDecision';
import { describeDecisionChanges } from '../../../domain/decisionFeedback';
import { toRunViewModel } from '../../../domain/runViewModel';
import { BlockProgress, Button, DilemmaCard, GenericCrest } from '../../design-system';
import { BlockSummary } from './BlockSummary';
import { TeamPanel } from './TeamPanel';
import { commandFailureMessage, pendingDilemmasHint, type RunLoopCommand } from './feedback';

export interface RunInPlayProps {
  run: RunViewDto;
  /** True while a newer view is loading (e.g. after a 409): the simulation waits for it. */
  isRefreshing: boolean;
}

/** Confirms each decision before allowing the block to be simulated. */
export function RunInPlay({ run, isRefreshing }: RunInPlayProps) {
  const decision = useTakeDecision(run.runId);
  const advance = useAdvanceBlock(run.runId);
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
  const uncertain = failedStep === 'decision' && decision.failure?.kind === 'failed';
  const locked = submitting || isRefreshing || uncertain;
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
          failedStep === 'decision' ? decision.failure : advance.failure,
        );

  useEffect(() => {
    const summaryVersion = focusSummaryFromVersion.current;
    if (summaryVersion !== null && run.version >= summaryVersion) {
      focusSummaryFromVersion.current = null;
      summaryHeading.current?.focus();
    }
    if (focusConfirmation.current && confirmationHeading.current) {
      focusConfirmation.current = false;
      confirmationHeading.current.focus();
    }
    if (focusFailure.current) {
      focusFailure.current = false;
      failureAlert.current?.focus();
    }
  }, [run.version, focusRequest, showConfirmation]);

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

  async function simulateBlock() {
    if (busy.current || isRefreshing || !inProgress || pending.length > 0) return;
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
                  identifican la causa de cada cambio. Un cambio cero indica que el valor publicado
                  se mantiene.
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

        <TeamPanel run={run} />

        {run.decisions.length > 0 && (
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

        {inProgress && (
          <section aria-labelledby={dilemmasHeadingId} className="flex flex-col gap-4">
            <h2 id={dilemmasHeadingId} className="mt-2 font-display text-headline font-extrabold">
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
            {uncertain && attempted && (
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
            <Button
              fullWidth
              disabled={pending.length > 0 || isRefreshing}
              loading={submitting && advance.isPending}
              aria-describedby={hintId}
              onClick={() => {
                void simulateBlock();
              }}
            >
              {submitting && advance.isPending ? 'Simulando…' : 'Simular bloque'}
            </Button>
            <p id={hintId} className="mt-1.5 text-center text-caption text-ink-muted">
              {pendingDilemmasHint(pending.length)}
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
