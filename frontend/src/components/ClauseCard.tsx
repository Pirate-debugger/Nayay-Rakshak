'use client';

import React, { useState } from 'react';
import { ChevronDown, ChevronUp, Cpu, FileText, Lightbulb } from 'lucide-react';
import RiskPill from './RiskPill';
import StructuredClauseModal from './StructuredClauseModal';
import { useLanguage } from './AppShell';
import { extractSingleClause } from '@/lib/api';
import { ClauseItem, StructuredClauseRecord } from '@/lib/types';
import { Language } from '@/lib/i18n';

interface Props {
  clause: ClauseItem;
  lang?: Language;
}

export default function ClauseCard({ clause, lang: propLang }: Props) {
  const { lang: ctxLang, simpleMode } = useLanguage();
  const lang = propLang || ctxLang;
  const [showOriginal, setShowOriginal] = useState(false);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [loadingStructured, setLoadingStructured] = useState(false);
  const [structuredRecord, setStructuredRecord] = useState<StructuredClauseRecord | null>(null);

  const handleOpenStructured = async () => {
    if (structuredRecord) {
      setIsModalOpen(true);
      return;
    }

    try {
      setLoadingStructured(true);
      const res = await extractSingleClause(clause.original_text, clause.title, clause.category);
      setStructuredRecord(res);
      setIsModalOpen(true);
    } catch (err: any) {
      alert(err.message || 'Failed to extract structured clause facts');
    } finally {
      setLoadingStructured(false);
    }
  };

  return (
    <article
      className="glass-panel p-5 transition border hover:border-slate-700 space-y-3"
      aria-labelledby={`clause-title-${clause.clause_id}`}
    >
      <div className="flex flex-wrap items-start justify-between gap-2 border-b border-slate-800 pb-3">
        <div>
          <div className="flex items-center gap-2">
            {!simpleMode && (
              <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-400">
                {clause.clause_id}
              </span>
            )}
            <span className="text-xs text-amber-400/90 font-medium">
              {clause.category}
            </span>
            <span className="text-xs text-slate-500">
              • Page {clause.page_number}
            </span>
          </div>
          <h3
            id={`clause-title-${clause.clause_id}`}
            className="text-base font-semibold text-white mt-1"
          >
            {clause.title}
          </h3>
        </div>

        <RiskPill severity={clause.risk_level} lang={lang} />
      </div>

      {/* Dual Plain Language Explanations */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pt-1">
        <div className="bg-slate-900/60 p-3 rounded-lg border border-slate-800/80">
          <h4 className="text-xs font-semibold text-slate-400 mb-1 flex items-center gap-1.5">
            <span>Plain English Meaning</span>
          </h4>
          <p className={`${simpleMode ? 'text-base text-slate-100' : 'text-sm text-slate-200'} leading-relaxed`}>
            {clause.plain_english}
          </p>
        </div>

        <div className="bg-slate-900/60 p-3 rounded-lg border border-slate-800/80">
          <h4 className="text-xs font-semibold text-amber-400/80 mb-1 flex items-center gap-1.5">
            <span>साधारण हिंदी में अर्थ (Hindi)</span>
          </h4>
          <p className={`${simpleMode ? 'text-base text-amber-50' : 'text-sm text-amber-100/90'} leading-relaxed font-sans`}>
            {clause.plain_hindi}
          </p>
        </div>
      </div>

      {/* Practical Action Tip */}
      {clause.recommendations && (
        <div className="flex items-start gap-2 text-xs bg-blue-950/30 border border-blue-500/20 text-blue-200 p-2.5 rounded-lg">
          <Lightbulb className="w-4 h-4 text-blue-400 shrink-0 mt-0.5" aria-hidden="true" />
          <div>
            <strong className="text-blue-300">
              {lang === 'hi' ? 'नागरिक सुझाव: ' : 'Citizen Tip: '}
            </strong>
            <span className={simpleMode ? 'text-sm text-slate-200' : ''}>{clause.recommendations}</span>
          </div>
        </div>
      )}

      {/* Original Contract Text Accordion & Structured Intelligence Trigger */}
      <div className="pt-2 flex flex-wrap items-center justify-between gap-3 border-t border-slate-800/80">
        <button
          type="button"
          onClick={() => setShowOriginal(!showOriginal)}
          className="inline-flex items-center gap-1 text-xs text-slate-400 hover:text-slate-300 font-medium cursor-pointer"
          aria-expanded={showOriginal}
        >
          <FileText className="w-3.5 h-3.5" aria-hidden="true" />
          <span>
            {showOriginal
              ? (lang === 'hi' ? 'मूल कानूनी पाठ छिपाएं' : 'Hide original legal text')
              : (lang === 'hi' ? 'मूल दस्तावेज़ पाठ देखें' : 'View original verbatim clause text')}
          </span>
          {showOriginal ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
        </button>

        {!simpleMode && (
          <button
            type="button"
            onClick={handleOpenStructured}
            disabled={loadingStructured}
            className="inline-flex items-center gap-1.5 text-xs font-semibold text-amber-400 hover:text-amber-300 bg-amber-950/40 hover:bg-amber-900/50 border border-amber-500/30 px-3 py-1.5 rounded-lg transition cursor-pointer disabled:opacity-50"
          >
            <Cpu className="w-3.5 h-3.5" />
            <span>
              {loadingStructured
                ? (lang === 'hi' ? 'तथ्य निकाले जा रहे हैं...' : 'Extracting Facts...')
                : (lang === 'hi' ? 'क्लॉज इंटेलिजेंस व तथ्य' : 'Clause Intelligence & Facts')}
            </span>
          </button>
        )}
      </div>

      {showOriginal && (
        <div className="mt-2 p-3 rounded-lg bg-slate-950/80 border border-slate-800 text-xs text-slate-300 font-mono whitespace-pre-wrap leading-relaxed">
          {clause.original_text}
        </div>
      )}

      {structuredRecord && (
        <StructuredClauseModal
          clause={structuredRecord}
          isOpen={isModalOpen}
          onClose={() => setIsModalOpen(false)}
          lang={lang}
        />
      )}
    </article>
  );
}

