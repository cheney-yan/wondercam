'use client';

import { useState } from 'react';
import { anonymousAuthService } from '@/lib/services/anonymous-auth';
import { getTranslations } from '@/lib/i18n';
import { SupportedLanguage } from '@/app/wondercam/page';

export interface UpgradePromptProps {
  isOpen: boolean;
  onClose: () => void;
  onUpgrade?: () => void;
  trigger?: 'credits-exhausted' | 'manual' | 'low-credits';
  remainingCredits?: number;
  language: SupportedLanguage;
  className?: string;
}

export function UpgradePrompt({
  isOpen,
  onClose,
  onUpgrade,
  trigger = 'credits-exhausted',
  remainingCredits = 0,
  language = 'en',
  className = ''
}: UpgradePromptProps) {
  const [isUpgrading, setIsUpgrading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const t = getTranslations(language);

  const handleUpgrade = async () => {
    try {
      setIsUpgrading(true);
      setError(null);

      // For now, we'll just redirect to a sign-up page or show a registration form
      // In a full implementation, this would handle the upgrade flow
      
      if (onUpgrade) {
        onUpgrade();
      } else {
        // Default behavior - redirect to registration
        window.location.href = '/auth/sign-up';
      }
      
    } catch (error: any) {
      console.error('Upgrade failed:', error);
      setError(error.message || 'Failed to upgrade account');
    } finally {
      setIsUpgrading(false);
    }
  };

  const getPromptTitle = () => {
    switch (trigger) {
      case 'credits-exhausted':
        return t.outOfCreditsTitle;
      case 'low-credits':
        return t.lowOnCreditsTitle;
      case 'manual':
      default:
        return t.upgradeAccountTitle;
    }
  };

  const getPromptMessage = () => {
    switch (trigger) {
      case 'credits-exhausted':
        return t.creditsExhaustedMessage;
      case 'low-credits':
        return t.lowCreditsMessage(remainingCredits);
      case 'manual':
      default:
        return t.manualUpgradeMessage;
    }
  };

  const getBenefits = () => {
    const baseBenefits = t.benefits;

    if (trigger === 'credits-exhausted') {
      return [
        t.instantAccess,
        ...baseBenefits.slice(1)
      ];
    }

    return baseBenefits;
  };

  if (!isOpen) return null;

  return (
    <div className={`fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50 ${className}`}>
      <div className="bg-white rounded-lg shadow-xl max-w-md w-full mx-4 p-6">
        {/* Header */}
        <div className="flex justify-between items-start mb-4">
          <h2 className="text-xl font-bold text-gray-900">
            {getPromptTitle()}
          </h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 text-xl font-bold"
            disabled={isUpgrading}
          >
            ×
          </button>
        </div>

        {/* Message */}
        <p className="text-gray-600 mb-6">
          {getPromptMessage()}
        </p>

        {/* Benefits */}
        <div className="mb-6">
          <h3 className="font-semibold text-gray-900 mb-3">
            {t.whatYouGet}
          </h3>
          <ul className="space-y-2">
            {getBenefits().map((benefit, index) => (
              <li key={index} className="flex items-start">
                <span className="text-green-500 mr-2 mt-0.5">✓</span>
                <span className="text-sm text-gray-700">{benefit}</span>
              </li>
            ))}
          </ul>
        </div>

        {/* Error message */}
        {error && (
          <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded text-red-700 text-sm">
            {error}
          </div>
        )}

        {/* Action buttons */}
        <div className="flex flex-col sm:flex-row gap-3">
          <button
            onClick={handleUpgrade}
            disabled={isUpgrading}
            className="flex-1 bg-blue-600 text-white py-3 px-4 rounded-lg font-semibold hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {isUpgrading ? t.creatingAccount : t.createFreeAccount}
          </button>
          
          <button
            onClick={onClose}
            disabled={isUpgrading}
            className="flex-1 bg-gray-100 text-gray-700 py-3 px-4 rounded-lg font-semibold hover:bg-gray-200 disabled:opacity-50 transition-colors"
          >
            {t.maybeLater}
          </button>
        </div>

        {/* Additional info */}
        <p className="text-xs text-gray-500 text-center mt-4">
          {t.freeAccountInfo}
        </p>
      </div>
    </div>
  );
}

// Compact version for mobile or inline usage
export function CompactUpgradePrompt({ 
  onUpgrade, 
  onDismiss, 
  credits,
  language = 'en',
  className = ''
}: {
  onUpgrade: () => void;
  onDismiss?: () => void;
  credits: number;
  language?: SupportedLanguage;
  className?: string;
}) {
  const t = getTranslations(language);
  const message = credits <= 0
    ? t.compactOutOfCredits
    : t.compactLowCredits(credits);

  return (
    <div className={`bg-gradient-to-r from-blue-50 to-blue-100 border border-blue-200 rounded-lg p-4 ${className}`}>
      <div className="flex items-center justify-between">
        <div className="flex-1">
          <p className="text-sm font-medium text-blue-900">
            {message}
          </p>
        </div>
        <div className="flex items-center space-x-2 ml-4">
          <button
            onClick={onUpgrade}
            className="bg-blue-600 text-white px-4 py-2 rounded text-sm font-medium hover:bg-blue-700 transition-colors"
          >
            {t.upgrade}
          </button>
          {onDismiss && (
            <button
              onClick={onDismiss}
              className="text-blue-600 hover:text-blue-800 text-sm font-medium"
            >
              {t.later}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

// Hook for managing upgrade prompt state
export function useUpgradePrompt() {
  const [isOpen, setIsOpen] = useState(false);
  const [trigger, setTrigger] = useState<UpgradePromptProps['trigger']>('manual');
  const [remainingCredits, setRemainingCredits] = useState(0);

  const showPrompt = (
    promptTrigger: UpgradePromptProps['trigger'] = 'manual',
    credits: number = 0
  ) => {
    setTrigger(promptTrigger);
    setRemainingCredits(credits);
    setIsOpen(true);
  };

  const hidePrompt = () => {
    setIsOpen(false);
  };

  const showCreditsExhausted = () => {
    showPrompt('credits-exhausted', 0);
  };

  const showLowCredits = (credits: number) => {
    showPrompt('low-credits', credits);
  };

  const showManualUpgrade = () => {
    showPrompt('manual', 0);
  };

  return {
    isOpen,
    trigger,
    remainingCredits,
    showPrompt,
    hidePrompt,
    showCreditsExhausted,
    showLowCredits,
    showManualUpgrade
  };
}