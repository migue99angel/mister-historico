export interface SeasonIntroProps {
  seasonId: string;
  onRunStarted: (runId: string) => void;
  onBackHome: () => void;
}

export function SeasonIntro(_props: SeasonIntroProps) {
  return <main />;
}
