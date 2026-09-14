'use client';

import React, { useState } from 'react';
import { AlertCircle, ChevronDown, ChevronUp, ShieldAlert } from 'lucide-react';
import { Language, translations } from '@/lib/i18n';

interface Props {
  lang?: Language;
}

export default function LegalDisclaimer({ lang = 'en' }: Props) {
  const [expanded, setExpanded] = useState(false);
  const t = translations[lang];

  return (
    <div
      role="region"
      aria-label="Legal safety disclaimer"
      className="bg-amber-950/40 border-b border-amber-500/30 text-amber-200 px-4 py-2 text-xs md:text-sm"
    >
      <div className="max-w-7xl mx-auto flex flex-col md:flex-row items-start md:items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <ShieldAlert className="w-4 h-4 text-amber-400 shrink-0" aria-hidden="true" />
          <span className="font-semibold text-amber-300">
            {lang === 'hi' ? 'महत्वपूर्ण कानूनी सूचना:' : 'LEGAL NOTICE:'}
          </span>
          <span>{t.legal_disclaimer_short}</span>
        </div>

        <button
          type="button"
          onClick={() => setExpanded(!expanded)}
          className="inline-flex items-center gap-1 text-amber-400 hover:text-amber-300 font-medium underline underline-offset-2 ml-6 md:ml-0 cursor-pointer"
          aria-expanded={expanded}
          aria-controls="full-disclaimer-text"
        >
          {expanded ? (
            <>
              {lang === 'hi' ? 'कम देखें' : 'Show less'} <ChevronUp className="w-3.5 h-3.5" />
            </>
          ) : (
            <>
              {lang === 'hi' ? 'पूरा अस्वीकरण पढ़ें' : 'Read full disclaimer'} <ChevronDown className="w-3.5 h-3.5" />
            </>
          )}
        </button>
      </div>

      {expanded && (
        <div
          id="full-disclaimer-text"
          className="max-w-7xl mx-auto mt-2 pt-2 border-t border-amber-500/20 text-amber-200/90 leading-relaxed"
        >
          <p className="mb-1">{t.legal_disclaimer_long}</p>
          <p className="text-[11px] text-amber-300/80">
            {lang === 'hi'
              ? 'सिस्टम प्रतिबंध: न्याय रक्षक कभी भी स्वायत्त रूप से अदालत में केस दर्ज नहीं करता, न ही कोई कानूनी नोटिस भेजता है या विपक्षी दल से संपर्क करता है।'
              : 'System Boundaries: Nyaya Rakshak never performs autonomous case filing, legal notice dispatch, document signing, or communication with opposing parties.'}
          </p>
        </div>
      )}
    </div>
  );
}
