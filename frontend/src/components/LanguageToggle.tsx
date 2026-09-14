'use client';

import React from 'react';
import { Globe } from 'lucide-react';
import { Language } from '@/lib/i18n';

interface Props {
  currentLang: Language;
  onLanguageChange: (lang: Language) => void;
}

export default function LanguageToggle({ currentLang, onLanguageChange }: Props) {
  return (
    <div
      role="group"
      aria-label="Language selection"
      className="inline-flex items-center bg-slate-900 border border-slate-700 rounded-lg p-0.5 text-xs"
    >
      <Globe className="w-3.5 h-3.5 text-slate-400 ml-2 mr-1" aria-hidden="true" />
      <button
        type="button"
        onClick={() => onLanguageChange('en')}
        className={`px-2.5 py-1 rounded-md font-medium transition cursor-pointer ${
          currentLang === 'en'
            ? 'bg-amber-500 text-slate-950 font-semibold shadow-sm'
            : 'text-slate-300 hover:text-white'
        }`}
        aria-pressed={currentLang === 'en'}
      >
        English
      </button>
      <button
        type="button"
        onClick={() => onLanguageChange('hi')}
        className={`px-2.5 py-1 rounded-md font-medium transition cursor-pointer ${
          currentLang === 'hi'
            ? 'bg-amber-500 text-slate-950 font-semibold shadow-sm'
            : 'text-slate-300 hover:text-white'
        }`}
        aria-pressed={currentLang === 'hi'}
      >
        हिन्दी
      </button>
    </div>
  );
}
