import { useQuery, type UseQueryResult } from '@tanstack/react-query';

import type { SeasonDetailDto, SeasonSummaryDto } from './ports';

export function useSeasons(): UseQueryResult<SeasonSummaryDto[]> {
  return useQuery({ queryKey: ['todo'], queryFn: () => Promise.resolve([]) });
}

export function useSeason(seasonId: string): UseQueryResult<SeasonDetailDto> {
  return useQuery({
    queryKey: ['todo', seasonId],
    queryFn: () => Promise.reject(new Error('todo')),
  });
}
