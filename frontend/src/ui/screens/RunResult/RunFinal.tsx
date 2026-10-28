export interface RunFinalProps {
  runId: string;
  onPlayAgain: () => void;
}

// Placeholder so the tests fail on behaviour, not on a missing module.
export function RunFinal(props: RunFinalProps) {
  return <main data-run={props.runId} />;
}
