/**
 * Routing Debug Component
 * Shows the actual URLs being constructed for API routing
 */

'use client';

import { useState } from 'react';

export function RoutingDebug() {
  const [isVisible, setIsVisible] = useState(false);

  const backendHost = process.env.NEXT_PUBLIC_BACKEND_API_HOST || '';
  const normalizedHost = backendHost.replace(/\/$/, '');

  const routeExamples = {
    'V1Beta Health': `/v1beta/models/gemini-2.5-flash:generateContent`,
    'V2 Health': `/v2/health`,
    'V2 Capabilities': `/v2/capabilities`,
    'V2 Chat': `/v2/chat`
  };

  const constructedUrls = Object.entries(routeExamples).map(([name, path]) => ({
    name,
    frontend: path,
    backend: `${normalizedHost}${path}`,
    original: `${backendHost}${path}` // Show what it would be without normalization
  }));

  if (!isVisible) {
    return (
      <button
        onClick={() => setIsVisible(true)}
        className="fixed bottom-4 left-4 z-50 px-3 py-1 bg-gray-800/70 text-white text-xs rounded-full hover:bg-gray-700/70 transition-colors"
      >
        Debug Routes
      </button>
    );
  }

  return (
    <div className="fixed bottom-4 left-4 z-50 bg-black/90 backdrop-blur-md border border-gray-700 rounded-lg p-4 max-w-2xl text-white text-xs font-mono">
      <div className="flex justify-between items-center mb-3">
        <h3 className="text-sm font-bold">API Routing Debug</h3>
        <button
          onClick={() => setIsVisible(false)}
          className="text-gray-400 hover:text-white"
        >
          ✕
        </button>
      </div>

      <div className="space-y-3">
        <div>
          <div className="text-gray-400 mb-1">Environment:</div>
          <div className="text-green-400">NEXT_PUBLIC_BACKEND_API_HOST = "{backendHost}"</div>
          <div className="text-blue-400">Normalized = "{normalizedHost}"</div>
        </div>

        <div>
          <div className="text-gray-400 mb-2">Route Mapping:</div>
          {constructedUrls.map(({ name, frontend, backend, original }) => (
            <div key={name} className="mb-2 p-2 bg-gray-800/50 rounded">
              <div className="text-yellow-400 font-bold">{name}</div>
              <div className="text-gray-300">Frontend: {frontend}</div>
              <div className="text-green-400">→ Backend: {backend}</div>
              {original !== backend && (
                <div className="text-red-400">⚠️ Was: {original}</div>
              )}
            </div>
          ))}
        </div>

        <div className="border-t border-gray-600 pt-2">
          <div className="text-gray-400 mb-1">Test Commands:</div>
          <div className="space-y-1 text-xs">
            <div>curl {normalizedHost}/v2/health</div>
            <div>curl {normalizedHost}/v2/capabilities</div>
          </div>
        </div>
      </div>
    </div>
  );
}