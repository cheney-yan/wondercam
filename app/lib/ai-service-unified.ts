/**
 * Unified AI Service for WonderCam
 * Since you've switched to V2 API, this exports the V2 service as the unified service
 */

import { aiServiceV2 } from './ai-service-v2';

// Export V2 service as the unified service
export const unifiedAIService = aiServiceV2;

// Re-export all V2 types for compatibility
export * from './ai-service-v2';