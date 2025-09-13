'use client';

import { useState } from 'react';
import { SupportedLanguage } from '@/app/wondercam/page';

interface LanguageSelectorProps {
  currentLanguage: SupportedLanguage;
  onLanguageChange: (language: SupportedLanguage) => void;
}

const languages = {
  en: { name: 'English', flag: '🇺🇸' },
  zh: { name: '中文', flag: '🇨🇳' },
  es: { name: 'Español', flag: '🇪🇸' },
  fr: { name: 'Français', flag: '🇫🇷' },
  ja: { name: '日本語', flag: '🇯🇵' }
};

export function LanguageSelector({ currentLanguage, onLanguageChange }: LanguageSelectorProps) {
  const [isOpen, setIsOpen] = useState(false);

  const handleLanguageSelect = (language: SupportedLanguage) => {
    onLanguageChange(language);
    setIsOpen(false);
  };

  return (
    <div className="language-selector relative">
      {/* Current Language Button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center space-x-2 px-3 py-2 bg-gray-800 hover:bg-gray-700 text-white rounded-lg transition-colors"
        title="Change Language"
      >
        <span className="text-lg">{languages[currentLanguage].flag}</span>
        <span className="text-sm hidden sm:block">{languages[currentLanguage].name}</span>
        <span className="text-xs">▼</span>
      </button>

      {/* Language Dropdown */}
      {isOpen && (
        <>
          {/* Backdrop */}
          <div 
            className="fixed inset-0 z-10"
            onClick={() => setIsOpen(false)}
          />
          
          {/* Dropdown Menu */}
          <div className="absolute top-full right-0 mt-2 bg-gray-800 border border-gray-700 rounded-lg shadow-lg z-20 min-w-40">
            {Object.entries(languages).map(([code, lang]) => (
              <button
                key={code}
                onClick={() => handleLanguageSelect(code as SupportedLanguage)}
                className={`w-full text-left px-4 py-2 hover:bg-gray-700 transition-colors flex items-center space-x-3 ${
                  currentLanguage === code ? 'bg-gray-700 text-blue-400' : 'text-white'
                } ${
                  code === 'en' ? 'rounded-t-lg' : code === 'ja' ? 'rounded-b-lg' : ''
                }`}
              >
                <span className="text-lg">{lang.flag}</span>
                <span className="text-sm">{lang.name}</span>
                {currentLanguage === code && (
                  <span className="ml-auto text-blue-400">✓</span>
                )}
              </button>
            ))}
          </div>
        </>
      )}
    </div>
  );
}