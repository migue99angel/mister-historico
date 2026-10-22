// Violation: ui must not import infrastructure.
import { apiClient } from '../infrastructure/apiClient';

export const leakyScore = apiClient.readScore();
