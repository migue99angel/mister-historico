export interface RunLoopProps {
  runId: string;
  onRunEnded: (runId: string) => void;
}

export function RunLoop(props: RunLoopProps) {
  void props;
  return null;
}
