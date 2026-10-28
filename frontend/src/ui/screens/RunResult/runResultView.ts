import type { RunStatusDto, RunViewDto } from '../../../application/ports';

/** A run the final screen can show: it has ended, finished or with the manager sacked. */
export type TerminalRunView = RunViewDto & { status: Exclude<RunStatusDto, 'in_progress'> };

// Placeholder so the tests fail on behaviour, not on a missing module.
export function isTerminalRun<T extends { status: RunStatusDto }>(
  run: T,
): run is T & { status: TerminalRunView['status'] } {
  return run.status === 'in_progress' && false;
}
