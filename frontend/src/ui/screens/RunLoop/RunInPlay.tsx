import { useEffect, useId, useRef, useState } from 'react';

import type { DilemmaDto, RunViewDto } from '../../../application/ports';
import { useAdvanceBlock } from '../../../application/useAdvanceBlock';
import { useTakeDecision } from '../../../application/useTakeDecision';
import { toRunViewModel } from '../../../domain/runViewModel';
import { BlockProgress, Button, DilemmaCard } from '../../design-system';
import { BlockSummary } from './BlockSummary';
import { commandFailureMessage, pendingDilemmasHint, type RunLoopCommand } from './feedback';

export interface RunInPlayProps {
  run: RunViewDto;
}

interface DecidedDilemma {
  dilemmaId: string;
  blockNumber: number;
  text: string;
}

type Sending = { command: 'decision'; dilemmaId: string } | { command: 'advance' } | null;

/** Where the focus goes once a successful command re-renders the run. */
type FocusTarget = 'after-decision' | 'after-simulation';

/** The run view while it can be played: block progress, last block and pending dilemmas. */
export function RunInPlay({ run }: RunInPlayProps) {
  const decision = useTakeDecision(run.runId);
  const advance = useAdvanceBlock(run.runId);
  const [choices, setChoices] = useState<Partial<Record<string, string>>>({});
  const [decided, setDecided] = useState<DecidedDilemma[]>([]);
  const [sending, setSending] = useState<Sending>(null);
  const [lastCommand, setLastCommand] = useState<RunLoopCommand | null>(null);
  // Refs: a second tap arrives before React re-renders the loading state.
  const busy = useRef(false);
  const pendingFocus = useRef<FocusTarget | null>(null);
  const dilemmasHeading = useRef<HTMLHeadingElement>(null);
  const summaryHeading = useRef<HTMLHeadingElement>(null);
  const simulateId = useId();
  const hintId = useId();
  const dilemmasHeadingId = useId();

  const viewModel = toRunViewModel(run);
  const inProgress = run.status === 'in_progress';
  const pending = run.pendingDilemmas;
  const decidedInBlock = decided.filter(
    (item) =>
      item.blockNumber === run.block.number &&
      run.decisions.some((made) => made.dilemmaId === item.dilemmaId),
  );
  const failureMessage =
    lastCommand === null
      ? null
      : commandFailureMessage(
          lastCommand,
          lastCommand === 'decision' ? decision.failure : advance.failure,
        );

  useEffect(() => {
    const target = pendingFocus.current;
    if (target === null) return;
    pendingFocus.current = null;
    if (target === 'after-simulation') summaryHeading.current?.focus();
    else if (pending.length > 0) dilemmasHeading.current?.focus();
    else document.getElementById(simulateId)?.focus();
  }, [run.version, pending.length, simulateId]);

  async function sendCommand(
    nextSending: NonNullable<Sending>,
    focusTarget: FocusTarget,
    send: () => Promise<RunViewDto | null>,
  ): Promise<RunViewDto | null> {
    if (busy.current) return null;
    busy.current = true;
    setSending(nextSending);
    setLastCommand(nextSending.command);
    pendingFocus.current = focusTarget;
    try {
      const updated = await send();
      if (!updated) pendingFocus.current = null;
      return updated;
    } finally {
      busy.current = false;
      setSending(null);
    }
  }

  async function confirm(dilemma: DilemmaDto) {
    const optionId = choices[dilemma.id];
    const option = dilemma.options.find((candidate) => candidate.id === optionId);
    if (!option) return;
    const updated = await sendCommand(
      { command: 'decision', dilemmaId: dilemma.id },
      'after-decision',
      () => decision.send({ dilemmaId: dilemma.id, optionId: option.id }),
    );
    if (updated) {
      setDecided((current) => [
        ...current,
        {
          dilemmaId: dilemma.id,
          blockNumber: run.block.number,
          text: `${dilemma.title}: ${option.label}`,
        },
      ]);
    }
  }

  return (
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
          <h2
            id={dilemmasHeadingId}
            ref={dilemmasHeading}
            tabIndex={-1}
            className="mt-2 font-display text-headline font-extrabold"
          >
            Decisiones del bloque
          </h2>
          {decidedInBlock.length > 0 && (
            <ul aria-label="Ya decidido en este bloque" className="flex flex-col gap-1">
              {decidedInBlock.map((item) => (
                <li key={item.dilemmaId} className="text-caption text-ink-muted">
                  {`✓ ${item.text}`}
                </li>
              ))}
            </ul>
          )}
          {pending.map((dilemma, index) => {
            const isSending = sending?.command === 'decision' && sending.dilemmaId === dilemma.id;
            return (
              <div key={dilemma.id} className="flex flex-col gap-2">
                <DilemmaCard
                  dilemma={dilemma}
                  eyebrow={`Dilema ${String(index + 1)} de ${String(pending.length)}`}
                  headingLevel={3}
                  selectedOptionId={choices[dilemma.id] ?? null}
                  disabled={isSending}
                  onSelect={(optionId) => {
                    setChoices((current) => ({ ...current, [dilemma.id]: optionId }));
                  }}
                />
                <Button
                  variant="secondary"
                  disabled={choices[dilemma.id] === undefined || (sending !== null && !isSending)}
                  loading={isSending}
                  onClick={() => {
                    void confirm(dilemma);
                  }}
                >
                  Confirmar decisión<span className="sr-only">{`: ${dilemma.title}`}</span>
                </Button>
              </div>
            );
          })}
        </section>
      )}

      {inProgress && (
        <div className="sticky bottom-0 -mx-gutter border-t border-line bg-canvas/95 px-gutter py-3 backdrop-blur">
          {failureMessage && (
            <p role="alert" className="mb-2 text-center text-body text-loss">
              {failureMessage}
            </p>
          )}
          <Button
            id={simulateId}
            fullWidth
            disabled={pending.length > 0}
            loading={sending?.command === 'advance'}
            aria-describedby={hintId}
            onClick={() => {
              void sendCommand({ command: 'advance' }, 'after-simulation', () => advance.send());
            }}
          >
            {sending?.command === 'advance' ? 'Simulando…' : 'Simular bloque'}
          </Button>
          <p id={hintId} className="mt-1.5 text-center text-caption text-ink-muted">
            {pendingDilemmasHint(pending.length)}
          </p>
        </div>
      )}
    </main>
  );
}
