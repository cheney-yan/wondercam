/**
 * API Status Indicator Component
 * Shows current API version and health status
 */

'use client';

import { useState, useEffect } from 'react';
import { unifiedAIService } from '@/lib/ai-service-unified';

interface APIStatus {
  version: 'v1beta' | 'v2';
  health: {
    v1: boolean;
    v2: boolean;
    current: string;
  };
  capabilities?: any;
}

// Helper function to render features from different API formats
const renderFeatures = (features: any) => {
  if (Array.isArray(features)) {
    // V1 format: array of strings
    return features.map((feature: string, index: number) => (
      <div key={index} className="text-green-400">• {feature}</div>
    ));
  } else if (features && typeof features === 'object') {
    // V2 format: object with boolean values
    return Object.entries(features)
      .filter(([, value]) => value === true)
      .map(([key], index) => (
        <div key={index} className="text-green-400">• {key}</div>
      ));
  }
  return null;
};

export function APIStatusIndicator() {
  const [status, setStatus] = useState<APIStatus | null>(null);
  const [isVisible, setIsVisible] = useState(false);

  useEffect(() => {
    const updateStatus = async () => {
      try {
        const [health, capabilities] = await Promise.all([
          unifiedAIService.healthCheck(),
          unifiedAIService.getCapabilities().catch(() => null)
        ]);

        setStatus({
          version: unifiedAIService.getCurrentAPIVersion(),
          health,
          capabilities
        });
      } catch (error) {
        console.warn('Failed to update API status:', error);
      }
    };

    updateStatus();
    
    // Update status every 30 seconds
    const interval = setInterval(updateStatus, 30000);
    return () => clearInterval(interval);
  }, []);

  if (!status) return null;

  const isHealthy = status.health[status.version === 'v2' ? 'v2' : 'v1'];
  const statusColor = isHealthy ? 'text-green-400' : 'text-red-400';
  const statusDot = isHealthy ? 'bg-green-400' : 'bg-red-400';

  return (
    <div className="fixed top-4 left-4 z-50">
      <button
        onClick={() => setIsVisible(!isVisible)}
        className={`flex items-center space-x-2 px-3 py-1 rounded-full bg-black/70 backdrop-blur-sm border border-gray-700 hover:border-gray-600 transition-colors ${statusColor}`}
      >
        <div className={`w-2 h-2 rounded-full ${statusDot}`}></div>
        <span className="text-xs font-mono">{status.version}</span>
      </button>

      {isVisible && (
        <div className="absolute top-10 left-0 bg-black/90 backdrop-blur-md border border-gray-700 rounded-lg p-4 min-w-[300px] text-white text-xs font-mono">
          <div className="space-y-2">
            <div className="flex justify-between">
              <span>API Version:</span>
              <span className={statusColor}>{status.version}</span>
            </div>
            
            <div className="flex justify-between">
              <span>Status:</span>
              <span className={statusColor}>
                {isHealthy ? 'Healthy' : 'Unhealthy'}
              </span>
            </div>

            <div className="border-t border-gray-600 pt-2">
              <div className="text-gray-400 mb-1">Health Check:</div>
              <div className="flex justify-between text-xs">
                <span>V1Beta:</span>
                <span className={status.health.v1 ? 'text-green-400' : 'text-red-400'}>
                  {status.health.v1 ? '✓' : '✗'}
                </span>
              </div>
              <div className="flex justify-between text-xs">
                <span>V2:</span>
                <span className={status.health.v2 ? 'text-green-400' : 'text-red-400'}>
                  {status.health.v2 ? '✓' : '✗'}
                </span>
              </div>
            </div>

            {status.capabilities && (
              <div className="border-t border-gray-600 pt-2">
                <div className="text-gray-400 mb-1">Features:</div>
                <div className="text-xs space-y-1">
                  {renderFeatures(status.capabilities.features)}
                </div>
              </div>
            )}

            <div className="border-t border-gray-600 pt-2">
              <div className="text-gray-400 mb-1">Environment:</div>
              <div className="text-xs space-y-1">
                <div>USE_V2_API: {process.env.NEXT_PUBLIC_USE_V2_API || 'false'}</div>
                <div>V2_FALLBACK: {process.env.NEXT_PUBLIC_V2_API_FALLBACK || 'false'}</div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}