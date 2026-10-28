import {
  describeBlock,
  type BlockNarrativeViewModel,
  type BlockSummaryInput,
} from './blockNarrative';
import {
  describeSeasonProgress,
  type SeasonProgressInput,
  type SeasonProgressViewModel,
} from './seasonProgress';

/** Structural subset of a run view: what the play screen needs to narrate the season. */
export interface RunViewInput extends SeasonProgressInput {
  lastBlockSummary: BlockSummaryInput | null;
}

export interface RunViewModel {
  progress: SeasonProgressViewModel;
  lastBlock: BlockNarrativeViewModel | null;
}

export function toRunViewModel(run: RunViewInput): RunViewModel {
  return {
    progress: describeSeasonProgress(run),
    lastBlock: run.lastBlockSummary ? describeBlock(run.lastBlockSummary) : null,
  };
}
