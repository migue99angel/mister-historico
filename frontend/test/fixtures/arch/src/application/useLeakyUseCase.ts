// Violation: application must only depend on domain.
import { apiClient } from '../infrastructure/apiClient';

export const useLeakyUseCase = (): number => apiClient.readScore();
