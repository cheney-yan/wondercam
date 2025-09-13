'use client';

import { useState, useEffect } from 'react';
import { creditService } from '@/lib/services/credit-service';
import { anonymousAuthService } from '@/lib/services/anonymous-auth';

export interface CreditDisplayProps {
  position?: 'header' | 'floating' | 'modal';
  showUpgradePrompt?: boolean;
  onUpgradeClick?: () => void;
  className?: string;
  onLowCredits?: (credits: number) => void;
}

export function CreditDisplay({ 
  position = 'header', 
  showUpgradePrompt = false,
  onUpgradeClick,
  className = '',
  onLowCredits
}: CreditDisplayProps) {
  const [credits, setCredits] = useState<number>(0);
  const [isAnonymous, setIsAnonymous] = useState(true);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadCredits = async () => {
    try {
      setIsLoading(true);
      setError(null);
      
      const [currentCredits, anonymous] = await Promise.all([
        creditService.getCurrentCredits(),
        anonymousAuthService.isAnonymous()
      ]);
      
      setCredits(currentCredits);
      setIsAnonymous(anonymous);
      
      // Notify parent if credits are low
      if (currentCredits <= 2 && onLowCredits) {
        onLowCredits(currentCredits);
      }
      
    } catch (error: any) {
      console.error('Failed to load credits:', error);
      setError(error.message);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadCredits();
    
    // Refresh credits every 30 seconds
    const interval = setInterval(loadCredits, 30000);
    
    return () => clearInterval(interval);
  }, []);

  const getCreditColor = () => {
    if (credits <= 0) return 'text-red-500';
    if (credits <= 2) return 'text-orange-500';
    if (credits <= 5) return 'text-yellow-500';
    return 'text-green-500';
  };

  const getCreditIcon = () => {
    if (credits <= 0) return '🚫';
    if (credits <= 2) return '⚠️';
    return '⚡';
  };

  const shouldShowUpgrade = isAnonymous && credits <= 3;

  if (error) {
    return (
      <div className={`credit-display-error ${className}`}>
        <button
          onClick={loadCredits}
          className="text-xs text-red-500 hover:text-red-600"
          title="Retry loading credits"
        >
          ⚠️ Retry
        </button>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className={`credit-display-loading ${className}`}>
        <div className="flex items-center space-x-1">
          <div className="animate-pulse">
            <div className="h-4 w-12 bg-gray-300 rounded"></div>
          </div>
        </div>
      </div>
    );
  }

  // Don't show credit display for registered users
  if (!isAnonymous) {
    return null;
  }

  return (
    <div className={`credit-display flex items-center space-x-2 ${className}`}>
      {/* Anonymous User Icon with Credits */}
      <div className="flex items-center space-x-1">
        {/* Anonymous user icon */}
        <div 
          className="w-5 h-5 rounded-full bg-gray-600 flex items-center justify-center text-xs text-white"
          title="Anonymous User"
        >
          👤
        </div>
        
        {/* Credit count */}
        <div className={`font-medium text-sm ${getCreditColor()}`}>
          <span className="mr-1">{getCreditIcon()}</span>
          <span>{credits}</span>
        </div>
      </div>

      {/* Upgrade prompt button */}
      {shouldShowUpgrade && onUpgradeClick && (
        <button
          onClick={onUpgradeClick}
          className="text-xs bg-blue-500 text-white px-2 py-1 rounded hover:bg-blue-600 transition-colors"
          title="Get more credits by creating an account"
        >
          Get More
        </button>
      )}
      
      {/* Zero credits warning */}
      {credits <= 0 && (
        <div className="text-xs text-red-500 font-medium">
          No credits left
        </div>
      )}
    </div>
  );
}

// Simplified version for use in tight spaces like mobile headers
export function CompactCreditDisplay({ 
  className = '', 
  onUpgradeClick 
}: { 
  className?: string; 
  onUpgradeClick?: () => void; 
}) {
  const [credits, setCredits] = useState<number>(0);
  const [isAnonymous, setIsAnonymous] = useState(true);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const loadCredits = async () => {
      try {
        const [currentCredits, anonymous] = await Promise.all([
          creditService.getCurrentCredits(),
          anonymousAuthService.isAnonymous()
        ]);
        
        setCredits(currentCredits);
        setIsAnonymous(anonymous);
      } catch (error) {
        console.error('Failed to load credits:', error);
      } finally {
        setIsLoading(false);
      }
    };

    loadCredits();
  }, []);

  if (isLoading || !isAnonymous) return null;

  const getCreditColor = () => {
    if (credits <= 0) return 'text-red-400';
    if (credits <= 2) return 'text-orange-400';
    return 'text-green-400';
  };

  return (
    <div className={`flex items-center space-x-1 ${className}`}>
      <div className="w-4 h-4 rounded-full bg-gray-600 flex items-center justify-center text-xs">
        👤
      </div>
      <span className={`text-xs font-medium ${getCreditColor()}`}>
        {credits}
      </span>
      {credits <= 2 && onUpgradeClick && (
        <button
          onClick={onUpgradeClick}
          className="text-xs text-blue-400 hover:text-blue-300"
          title="Upgrade"
        >
          +
        </button>
      )}
    </div>
  );
}

// Hook for other components to use
export function useCreditDisplay() {
  const [credits, setCredits] = useState<number>(0);
  const [isAnonymous, setIsAnonymous] = useState(false);
  const [isLoading, setIsLoading] = useState(true);

  const refresh = async () => {
    try {
      setIsLoading(true);
      const [currentCredits, anonymous] = await Promise.all([
        creditService.getCurrentCredits(),
        anonymousAuthService.isAnonymous()
      ]);
      
      setCredits(currentCredits);
      setIsAnonymous(anonymous);
    } catch (error) {
      console.error('Failed to refresh credits:', error);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    refresh();
  }, []);

  return {
    credits,
    isAnonymous,
    isLoading,
    refresh,
    canPerformAction: (cost: number) => credits >= cost,
    isLowOnCredits: credits <= 2,
    hasNoCredits: credits <= 0
  };
}