'use client';

import React from 'react';
import { Sparkles, FileText } from 'lucide-react';
import { Language } from '@/lib/i18n';

interface Props {
  simpleMode: boolean;
  onSimpleModeChange: (val: boolean) => void;
  lang?: Language;
}

export default function SimpleModeToggle({ simpleMode, onSimpleModeChange, lang = 'en' }: Props) {
  return (
    <div
      role="group"
      aria-label={lang === 'hi' ? 'दस्तावेज़ प्रस्तुति मोड' : 'Document reading mode'}
      className="inline-flex items-center bg-slate-900 border border-slate-700 rounded-lg p-0.5 text-xs"
    >
      <button
        type="button"
        onClick={() => onSimpleModeChange(true)}
        className={`px-2.5 py-1 rounded-md font-medium transition cursor-pointer flex items-center gap-1 ${
          simpleMode
            ? 'bg-emerald-600 text-white font-semibold shadow-sm'
            : 'text-slate-300 hover:text-white'
        }`}
        aria-pressed={simpleMode}
        title={lang === 'hi' ? 'सरल भाषा व स्पष्ट व्याख्या' : 'Plain language without complex legal jargon'}
      >
        <Sparkles className="w-3 h-3" aria-hidden="true" />
        <span>{lang === 'hi' ? 'सरल मोड' : 'Simple Mode'}</span>
      </button>
      <button
        type="button"
        onClick={() => onSimpleModeChange(false)}
        className={`px-2.5 py-1 rounded-md font-medium transition cursor-pointer flex items-center gap-1 ${
          !simpleMode
            ? 'bg-slate-800 text-white font-semibold shadow-sm'
            : 'text-slate-400 hover:text-white'
        }`}
        aria-pressed={!simpleMode}
        title={lang === 'hi' ? 'पूर्ण कानूनी विवरण व संदर्भ' : 'Full legal citations, tokens, and statutory cross-references'}
      >
        <FileText className="w-3 h-3" aria-hidden="true" />
        <span>{lang === 'hi' ? 'विस्तृत मोड' : 'Detailed'}</span>
      </button>
    </div>
  );
}
