import type {
  AdvanceBlockRequestDto,
  RunViewDto,
  SeasonDetailDto,
  SeasonListDto,
  StartRunRequestDto,
  StartRunResponseDto,
  TakeDecisionRequestDto,
} from '../../application/ports';
import type { components } from './generated/schema';

type Equal<Left, Right> = [Left] extends [Right] ? ([Right] extends [Left] ? true : false) : false;
type Assert<Condition extends true> = Condition;

/** Bidirectional type equality prevents the application DTOs drifting from OpenAPI. */
export type HttpGameApiContractChecks = [
  Assert<Equal<SeasonListDto, components['schemas']['SeasonList']>>,
  Assert<Equal<SeasonDetailDto, components['schemas']['SeasonDetail']>>,
  Assert<Equal<StartRunRequestDto, components['schemas']['StartRunRequest']>>,
  Assert<Equal<StartRunResponseDto, components['schemas']['StartRunResponse']>>,
  Assert<Equal<RunViewDto, components['schemas']['RunView']>>,
  Assert<Equal<TakeDecisionRequestDto, components['schemas']['TakeDecisionRequest']>>,
  Assert<Equal<AdvanceBlockRequestDto, components['schemas']['AdvanceBlockRequest']>>,
];
