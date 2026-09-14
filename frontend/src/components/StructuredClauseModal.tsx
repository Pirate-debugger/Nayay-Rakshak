'use client';

import React, { useState } from 'react';
import {
  AlertTriangle,
  Bookmark,
  Calendar,
  CheckCircle,
  Clock,
  Copy,
  Cpu,
  Database,
  DollarSign,
  FileCode,
  Lock,
  Percent,
  Scale,
  ShieldCheck,
  X,
} from 'lucide-react';
import { StructuredClauseRecord } from '@/lib/types';
import { Language } from '@/lib/i18n';

interface Props {
  clause: StructuredClauseRecord;
  isOpen: boolean;
  onClose: () => void;
  lang?: Language;
}

export default function StructuredClauseModal({
  clause,
  isOpen,
  onClose,
  lang = 'en',
}: Props) {
  const [activeTab, setActiveTab] = useState<'structured' | 'deterministic' | 'json'>('structured');
  const [copied, setCopied] = useState(false);
  const modalRef = React.useRef<HTMLDivElement>(null);
  const closeButtonRef = React.useRef<HTMLButtonElement>(null);
  const triggerRef = React.useRef<HTMLElement | null>(null);

  React.useEffect(() => {
    if (isOpen) {
      triggerRef.current = document.activeElement as HTMLElement;
      // Focus close button on open
      const timer = setTimeout(() => closeButtonRef.current?.focus(), 50);

      const handleKeyDown = (e: KeyboardEvent) => {
        if (e.key === 'Escape') {
          e.preventDefault();
          onClose();
          return;
        }

        if (e.key === 'Tab' && modalRef.current) {
          const focusableElements = modalRef.current.querySelectorAll<HTMLElement>(
            'button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])'
          );
          if (focusableElements.length === 0) return;

          const first = focusableElements[0];
          const last = focusableElements[focusableElements.length - 1];

          if (e.shiftKey && document.activeElement === first) {
            e.preventDefault();
            last.focus();
          } else if (!e.shiftKey && document.activeElement === last) {
            e.preventDefault();
            first.focus();
          }
        }
      };

      window.addEventListener('keydown', handleKeyDown);
      return () => {
        clearTimeout(timer);
        window.removeEventListener('keydown', handleKeyDown);
        triggerRef.current?.focus();
      };
    }
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const copyJson = () => {
    navigator.clipboard.writeText(JSON.stringify(clause, null, 2));
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const df = clause.deterministic_facts;
  const si = clause.structured_interpretation;

  return (
    <div
      ref={modalRef}
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm overflow-y-auto"
      role="dialog"
      aria-modal="true"
      aria-labelledby="modal-clause-title"
    >
      <div className="relative w-full max-w-4xl bg-slate-900 border border-slate-700 rounded-2xl shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
        {/* Header */}
        <div className="flex items-center justify-between p-5 border-b border-slate-800 bg-slate-950/60">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-amber-500/10 border border-amber-500/30 flex items-center justify-center text-amber-400">
              <Cpu className="w-5 h-5" aria-hidden="true" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-mono text-xs px-2 py-0.5 rounded bg-slate-800 text-amber-400">
                  {clause.clause_id}
                </span>
                <span className="text-xs text-slate-400">
                  {clause.section ? `Section ${clause.section} • ` : ''}Page {clause.page}
                </span>
                <span className="text-xs px-2 py-0.5 rounded-full bg-blue-950/80 text-blue-300 border border-blue-500/30">
                  {clause.clause_type}
                </span>
              </div>
              <h2 id="modal-clause-title" className="text-lg font-bold text-white mt-1">
                {clause.title}
              </h2>
            </div>
          </div>

          <button
            ref={closeButtonRef}
            type="button"
            onClick={onClose}
            className="p-2 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition focus-visible:ring-2 focus-visible:ring-amber-400"
            aria-label={lang === 'hi' ? 'मोडल बंद करें (Esc)' : 'Close modal (Esc)'}
          >
            <X className="w-5 h-5" aria-hidden="true" />
          </button>
        </div>

        {/* Immutability & Confidence Bar */}
        <div className="px-5 py-2.5 bg-slate-950 border-b border-slate-800/80 flex flex-wrap items-center justify-between gap-3 text-xs">
          <div className="flex items-center gap-2 text-emerald-400">
            <Lock className="w-4 h-4" aria-hidden="true" />
            <span className="font-medium">
              {lang === 'hi'
                ? 'अपरिवर्तनीय तथ्य सुरक्षा: AI तथ्यों को बदल नहीं सकता'
                : 'Deterministic Immutability: AI Silently Overwriting Facts is Strictly Blocked'}
            </span>
          </div>

          <div className="flex items-center gap-4 text-slate-400 font-mono text-[11px]">
            <span>
              Extraction Conf: <strong className="text-white">{(clause.extraction_confidence * 100).toFixed(0)}%</strong>
            </span>
            <span>
              Interpretation Conf: <strong className="text-white">{(clause.interpretation_confidence * 100).toFixed(0)}%</strong>
            </span>
          </div>
        </div>

        {/* Tab Navigation */}
        <div
          role="tablist"
          aria-label={lang === 'hi' ? 'धारा विश्लेषण टैब' : 'Clause analysis tabs'}
          className="flex border-b border-slate-800 px-5 pt-2 bg-slate-900/90 gap-4 text-xs font-medium"
        >
          <button
            role="tab"
            aria-selected={activeTab === 'structured'}
            type="button"
            onClick={() => setActiveTab('structured')}
            className={`pb-2.5 border-b-2 transition flex items-center gap-1.5 focus-visible:ring-2 focus-visible:ring-amber-400 ${
              activeTab === 'structured'
                ? 'border-amber-400 text-amber-400 font-bold'
                : 'border-transparent text-slate-400 hover:text-white'
            }`}
          >
            <Scale className="w-4 h-4" aria-hidden="true" />
            <span>{lang === 'hi' ? 'अर्थ और व्याख्या' : 'Semantic Interpretation'}</span>
          </button>

          <button
            role="tab"
            aria-selected={activeTab === 'deterministic'}
            type="button"
            onClick={() => setActiveTab('deterministic')}
            className={`pb-2.5 border-b-2 transition flex items-center gap-1.5 focus-visible:ring-2 focus-visible:ring-amber-400 ${
              activeTab === 'deterministic'
                ? 'border-amber-400 text-amber-400 font-bold'
                : 'border-transparent text-slate-400 hover:text-white'
            }`}
          >
            <Database className="w-4 h-4" aria-hidden="true" />
            <span>
              {lang === 'hi' ? 'तथ्य' : 'Deterministic Facts'} ({df.currencies.length + df.dates.length + df.durations.length + df.percentages.length})
            </span>
          </button>

          <button
            role="tab"
            aria-selected={activeTab === 'json'}
            type="button"
            onClick={() => setActiveTab('json')}
            className={`pb-2.5 border-b-2 transition flex items-center gap-1.5 focus-visible:ring-2 focus-visible:ring-amber-400 ${
              activeTab === 'json'
                ? 'border-amber-400 text-amber-400 font-bold'
                : 'border-transparent text-slate-400 hover:text-white'
            }`}
          >
            <FileCode className="w-4 h-4" aria-hidden="true" />
            <span>{lang === 'hi' ? 'कच्चा JSON' : 'Structured JSON'}</span>
          </button>
        </div>

        {/* Content Body */}
        <div
          role="tabpanel"
          tabIndex={0}
          aria-label={
            activeTab === 'structured'
              ? 'Semantic Interpretation Panel'
              : activeTab === 'deterministic'
              ? 'Deterministic Facts Panel'
              : 'Structured JSON Panel'
          }
          className="p-5 overflow-y-auto space-y-5 text-xs text-slate-300 focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-amber-500/50"
        >
          {activeTab === 'structured' && (
            <div className="space-y-4">
              {/* Statutory Conflict Flag */}
              {clause.statutory_conflict_flag && (
                <div className="p-3.5 rounded-xl bg-red-950/40 border border-red-500/30 flex items-start gap-3">
                  <AlertTriangle className="w-5 h-5 text-red-400 shrink-0 mt-0.5" />
                  <div>
                    <h4 className="font-bold text-red-300 text-sm">
                      Potential Statutory Conflict Flagged
                    </h4>
                    <p className="text-red-200/90 mt-1">
                      {clause.potential_violates_statute || 'Clause terms appear disproportionately one-sided under applicable Indian statutory standards.'}
                    </p>
                  </div>
                </div>
              )}

              {/* Plain Language Explanations */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                <div className="p-3.5 rounded-xl bg-slate-950/60 border border-slate-800">
                  <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider block mb-1">
                    Simplified Meaning
                  </span>
                  <p className="text-slate-200 text-xs leading-relaxed">
                    {clause.simplified_explanation}
                  </p>
                </div>

                {clause.plain_hindi && (
                  <div className="p-3.5 rounded-xl bg-slate-950/60 border border-slate-800">
                    <span className="text-[11px] font-bold text-amber-400 uppercase tracking-wider block mb-1">
                      सरल हिंदी अर्थ
                    </span>
                    <p className="text-amber-100 text-xs leading-relaxed font-sans">
                      {clause.plain_hindi}
                    </p>
                  </div>
                )}
              </div>

              {/* Legal Positions: Obligations, Rights, Prohibitions */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                <div className="p-3 rounded-xl bg-slate-950/50 border border-slate-800 space-y-1.5">
                  <span className="font-bold text-amber-400 block text-xs">Obligations</span>
                  {si.obligations.length > 0 ? (
                    <ul className="list-disc list-inside space-y-1 text-[11px] text-slate-300">
                      {si.obligations.map((item, idx) => (
                        <li key={idx}>{item}</li>
                      ))}
                    </ul>
                  ) : (
                    <span className="text-slate-500 italic text-[11px]">None detected</span>
                  )}
                </div>

                <div className="p-3 rounded-xl bg-slate-950/50 border border-slate-800 space-y-1.5">
                  <span className="font-bold text-emerald-400 block text-xs">Rights</span>
                  {si.rights.length > 0 ? (
                    <ul className="list-disc list-inside space-y-1 text-[11px] text-slate-300">
                      {si.rights.map((item, idx) => (
                        <li key={idx}>{item}</li>
                      ))}
                    </ul>
                  ) : (
                    <span className="text-slate-500 italic text-[11px]">None detected</span>
                  )}
                </div>

                <div className="p-3 rounded-xl bg-slate-950/50 border border-slate-800 space-y-1.5">
                  <span className="font-bold text-red-400 block text-xs">Prohibitions</span>
                  {si.prohibitions.length > 0 ? (
                    <ul className="list-disc list-inside space-y-1 text-[11px] text-slate-300">
                      {si.prohibitions.map((item, idx) => (
                        <li key={idx}>{item}</li>
                      ))}
                    </ul>
                  ) : (
                    <span className="text-slate-500 italic text-[11px]">None detected</span>
                  )}
                </div>
              </div>

              {/* Triggers, Deadlines, Penalties */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                <div className="p-3 rounded-xl bg-slate-950/50 border border-slate-800 space-y-1">
                  <span className="font-bold text-slate-300 block text-xs">Deadlines</span>
                  {si.deadlines.length > 0 ? (
                    <ul className="list-disc list-inside space-y-1 text-[11px] text-slate-300">
                      {si.deadlines.map((d, i) => (
                        <li key={i}>{d}</li>
                      ))}
                    </ul>
                  ) : (
                    <span className="text-slate-500 italic text-[11px]">No specific deadline</span>
                  )}
                </div>

                <div className="p-3 rounded-xl bg-slate-950/50 border border-slate-800 space-y-1">
                  <span className="font-bold text-slate-300 block text-xs">Penalties / Forfeiture</span>
                  {si.penalties.length > 0 ? (
                    <ul className="list-disc list-inside space-y-1 text-[11px] text-red-300">
                      {si.penalties.map((p, i) => (
                        <li key={i}>{p}</li>
                      ))}
                    </ul>
                  ) : (
                    <span className="text-slate-500 italic text-[11px]">No explicit penalty clause</span>
                  )}
                </div>

                <div className="p-3 rounded-xl bg-slate-950/50 border border-slate-800 space-y-1">
                  <span className="font-bold text-slate-300 block text-xs">Termination Conditions</span>
                  {si.termination_conditions.length > 0 ? (
                    <ul className="list-disc list-inside space-y-1 text-[11px] text-slate-300">
                      {si.termination_conditions.map((t, i) => (
                        <li key={i}>{t}</li>
                      ))}
                    </ul>
                  ) : (
                    <span className="text-slate-500 italic text-[11px]">No direct termination terms</span>
                  )}
                </div>
              </div>

              {/* Legal Mechanisms */}
              <div className="p-3.5 rounded-xl bg-slate-950/60 border border-slate-800 space-y-2">
                <span className="font-bold text-amber-400 block text-xs uppercase tracking-wider">
                  Governance & Dispute Mechanisms
                </span>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-[11px]">
                  <div>
                    <span className="text-slate-500 block">Jurisdiction:</span>
                    <span className="font-medium text-slate-200">{si.jurisdiction || 'Not specified'}</span>
                  </div>
                  <div>
                    <span className="text-slate-500 block">Governing Law:</span>
                    <span className="font-medium text-slate-200">{si.governing_law || 'Not specified'}</span>
                  </div>
                  <div>
                    <span className="text-slate-500 block">Arbitration:</span>
                    <span className="font-medium text-slate-200">{si.arbitration || 'Not specified'}</span>
                  </div>
                  <div>
                    <span className="text-slate-500 block">Dispute Resolution:</span>
                    <span className="font-medium text-slate-200">{si.dispute_resolution || 'Standard'}</span>
                  </div>
                </div>
              </div>

              {/* Original Verbatim Evidence */}
              <div className="p-3.5 rounded-xl bg-slate-950/80 border border-slate-800 space-y-1.5">
                <span className="font-bold text-slate-400 block text-[11px] uppercase tracking-wider">
                  Verbatim Evidentiary Source (Page {clause.evidence_location.page_number})
                </span>
                <blockquote className="text-xs text-slate-300 font-mono italic leading-relaxed border-l-2 border-amber-500/50 pl-3">
                  {clause.evidence_location.verbatim_quote}
                </blockquote>
              </div>
            </div>
          )}

          {activeTab === 'deterministic' && (
            <div className="space-y-4">
              <div className="p-3 rounded-xl bg-blue-950/20 border border-blue-500/30 text-blue-200 text-xs">
                Deterministic extraction uses strict regex state machines to parse numerical, temporal, and financial commitments. These facts serve as the immutable anchor that AI cannot fabricate or alter.
              </div>

              {/* Currencies */}
              <div className="p-3.5 rounded-xl bg-slate-950/60 border border-slate-800 space-y-2">
                <span className="font-bold text-amber-400 flex items-center gap-1.5 text-xs">
                  <DollarSign className="w-4 h-4" />
                  <span>Currency & Financial Figures ({df.currencies.length})</span>
                </span>
                {df.currencies.length > 0 ? (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                    {df.currencies.map((c, i) => (
                      <div key={i} className="p-2.5 rounded-lg bg-slate-900 border border-slate-800 text-[11px] flex justify-between items-center">
                        <span className="font-mono text-amber-300 font-bold">{c.raw_match}</span>
                        <span className="text-slate-400">
                          {c.currency_code} {c.amount.toLocaleString()} {c.standardized_inr_equivalent ? `(≈ ₹${c.standardized_inr_equivalent.toLocaleString()})` : ''}
                        </span>
                      </div>
                    ))}
                  </div>
                ) : (
                  <span className="text-slate-500 italic text-[11px]">No financial amounts detected in this clause</span>
                )}
              </div>

              {/* Durations */}
              <div className="p-3.5 rounded-xl bg-slate-950/60 border border-slate-800 space-y-2">
                <span className="font-bold text-emerald-400 flex items-center gap-1.5 text-xs">
                  <Clock className="w-4 h-4" />
                  <span>Durations & Notice Periods ({df.durations.length})</span>
                </span>
                {df.durations.length > 0 ? (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                    {df.durations.map((d, i) => (
                      <div key={i} className="p-2.5 rounded-lg bg-slate-900 border border-slate-800 text-[11px] flex justify-between items-center">
                        <span className="font-mono text-emerald-300 font-bold">{d.raw_match}</span>
                        <span className="text-slate-400">
                          {d.duration_value} {d.unit} (standardized to {d.duration_days} days)
                        </span>
                      </div>
                    ))}
                  </div>
                ) : (
                  <span className="text-slate-500 italic text-[11px]">No durations or notice periods detected</span>
                )}
              </div>

              {/* Percentages */}
              <div className="p-3.5 rounded-xl bg-slate-950/60 border border-slate-800 space-y-2">
                <span className="font-bold text-cyan-400 flex items-center gap-1.5 text-xs">
                  <Percent className="w-4 h-4" />
                  <span>Percentages & Interest Rates ({df.percentages.length})</span>
                </span>
                {df.percentages.length > 0 ? (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                    {df.percentages.map((p, i) => (
                      <div key={i} className="p-2.5 rounded-lg bg-slate-900 border border-slate-800 text-[11px] flex justify-between items-center">
                        <span className="font-mono text-cyan-300 font-bold">{p.raw_match}</span>
                        <span className="text-slate-400">
                          {p.value_percent}% {p.is_per_annum ? 'Per Annum (p.a.)' : 'Flat rate'}
                        </span>
                      </div>
                    ))}
                  </div>
                ) : (
                  <span className="text-slate-500 italic text-[11px]">No percentages or interest rates detected</span>
                )}
              </div>

              {/* Dates */}
              <div className="p-3.5 rounded-xl bg-slate-950/60 border border-slate-800 space-y-2">
                <span className="font-bold text-purple-400 flex items-center gap-1.5 text-xs">
                  <Calendar className="w-4 h-4" />
                  <span>Dates & Milestones ({df.dates.length})</span>
                </span>
                {df.dates.length > 0 ? (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                    {df.dates.map((dt, i) => (
                      <div key={i} className="p-2.5 rounded-lg bg-slate-900 border border-slate-800 text-[11px] flex justify-between items-center">
                        <span className="font-mono text-purple-300 font-bold">{dt.raw_match}</span>
                        <span className="text-slate-400 font-mono">{dt.date_iso}</span>
                      </div>
                    ))}
                  </div>
                ) : (
                  <span className="text-slate-500 italic text-[11px]">No explicit calendar dates detected</span>
                )}
              </div>

              {/* Sections */}
              <div className="p-3.5 rounded-xl bg-slate-950/60 border border-slate-800 space-y-2">
                <span className="font-bold text-indigo-400 flex items-center gap-1.5 text-xs">
                  <Bookmark className="w-4 h-4" />
                  <span>Section / Clause Citations ({df.sections.length})</span>
                </span>
                {df.sections.length > 0 ? (
                  <div className="flex flex-wrap gap-2">
                    {df.sections.map((s, i) => (
                      <span key={i} className="px-2.5 py-1 rounded bg-slate-900 border border-slate-800 text-[11px] font-mono text-indigo-300">
                        {s.raw_match}
                      </span>
                    ))}
                  </div>
                ) : (
                  <span className="text-slate-500 italic text-[11px]">No section citations detected</span>
                )}
              </div>
            </div>
          )}

          {activeTab === 'json' && (
            <div className="space-y-2">
              <div className="flex justify-between items-center">
                <span className="text-[11px] text-slate-400 font-mono">
                  Strict Pydantic Schema Output (extra=&apos;forbid&apos;)
                </span>
                <button
                  type="button"
                  onClick={copyJson}
                  className="px-3 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-white text-xs flex items-center gap-1.5 transition cursor-pointer"
                >
                  {copied ? <CheckCircle className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                  <span>{copied ? 'Copied' : 'Copy JSON'}</span>
                </button>
              </div>

              <pre className="p-4 rounded-xl bg-slate-950 border border-slate-800 text-[11px] font-mono text-amber-300/90 overflow-x-auto max-h-[50vh] leading-relaxed">
                {JSON.stringify(clause, null, 2)}
              </pre>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-slate-800 bg-slate-950/60 flex items-center justify-between text-xs text-slate-400">
          <div className="flex items-center gap-2">
            <ShieldCheck className="w-4 h-4 text-amber-400" />
            <span>Nyaya Rakshak Clause Intelligence Engine</span>
          </div>

          <button
            type="button"
            onClick={onClose}
            className="px-4 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-white font-medium transition cursor-pointer"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
