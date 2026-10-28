import type { TerminalRunView } from './runResultView';

export type { TerminalRunView } from './runResultView';

export interface RunResultProps {
  run: TerminalRunView;
  onPlayAgain: () => void;
}

// Placeholder so the tests fail on behaviour, not on a missing module.
export function RunResult(props: RunResultProps) {
  return <main data-run={props.run.runId} />;
}
