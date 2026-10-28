import { useQuery, type UseQueryResult } from '@tanstack/react-query';

import { useGameApi } from './gameApi';
import type { SeasonDetailDto, SeasonSummaryDto } from './ports';

/** Query key of the season list; every season query starts with `'seasons'`. */
export const seasonsQueryKey = ['seasons', 'list'] as const;

/** Query key of one season's context (`GET /seasons/{seasonId}`). */
export function seasonQueryKey(seasonId: string) {
  return ['seasons', 'detail', seasonId] as const;
}

/** Playable seasons for the season picker. Rejects with `ApiError`. */
export function useSeasons(): UseQueryResult<SeasonSummaryDto[]> {
  const gameApi = useGameApi();
  return useQuery({
    queryKey: seasonsQueryKey,
    queryFn: async () => (await gameApi.listSeasons()).items,
  });
}

/** Context of one season before a run starts. An unknown season rejects with a 404 `ApiError`. */
export function useSeason(seasonId: string): UseQueryResult<SeasonDetailDto> {
  const gameApi = useGameApi();
  return useQuery({
    queryKey: seasonQueryKey(seasonId),
    queryFn: () => gameApi.getSeason(seasonId),
  });
}
