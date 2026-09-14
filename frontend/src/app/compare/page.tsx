'use client';

import React, { useCallback, useEffect, useState } from 'react';
import {
  AlertOctagon,
  AlertTriangle,
  ArrowRight,
  ChevronDown,
  FileDiff,
  Filter,
  Info,
  Layers,
  ShieldAlert,
  SlidersHorizontal,
  Target,
  XCircle,
} from 'lucide-react';
import { useLanguage } from '@/components/AppShell';
import { compareDocuments, listDocuments, loadSampleDocument } from '@/lib/api';
import {
  ComparisonCategory,
  ComparisonFindingItem,
  ComparisonResponse,
  DocumentEvidence,
  DocumentMeta,
  MaterialityLevel,
  StructuralDiff,
} from '@/lib/types';

// ─── Constants ───────────────────────────────────────────────────────────────

const CATEGORY_CFG: Record<ComparisonCategory, { label: string; color: string; bg: string; border: string }> = {
  IDENTICAL:   { label: 'Identical',   color: 'text-slate-400',   bg: 'bg-slate-800',   border: 'border-slate-600' },
  SIMILAR:     { label: 'Similar',     color: 'text-emerald-300', bg: 'bg-emerald-950', border: 'border-emerald-600' },
  MODIFIED:    { label: 'Modified',    color: 'text-amber-300',   bg: 'bg-amber-950',   border: 'border-amber-500' },
  CONFLICTING: { label: 'Conflicting', color: 'text-red-300',     bg: 'bg-red-950',     border: 'border-red-500' },
  NEW:         { label: 'New in B',    color: 'text-blue-300',    bg: 'bg-blue-950',    border: 'border-blue-500' },
  REMOVED:     { label: 'Removed',     color: 'text-orange-300',  bg: 'bg-orange-950',  border: 'border-orange-500' },
  MISSING:     { label: 'Missing',     color: 'text-purple-300',  bg: 'bg-purple-950',  border: 'border-purple-500' },
};

const MATERIALITY_CFG: Record<MaterialityLevel, { label: string; color: string; bg: string }> = {
  CRITICAL:   { label: 'CRITICAL',   color: 'text-red-200',    bg: 'bg-red-900 border border-red-500/60' },
  MATERIAL:   { label: 'MATERIAL',   color: 'text-orange-200', bg: 'bg-orange-900 border border-orange-500/50' },
  MEDIUM:     { label: 'MEDIUM',     color: 'text-amber-200',  bg: 'bg-amber-900 border border-amber-500/40' },
  MINOR:      { label: 'MINOR',      color: 'text-slate-300',  bg: 'bg-slate-800 border border-slate-600' },
  NEGLIGIBLE: { label: 'NEGLIGIBLE', color: 'text-slate-500',  bg: 'bg-slate-900 border border-slate-700' },
};

const ALL_CATS: ComparisonCategory[] = ['CONFLICTING', 'MODIFIED', 'NEW', 'REMOVED', 'MISSING', 'SIMILAR', 'IDENTICAL'];
const ALL_MAT: MaterialityLevel[] = ['CRITICAL', 'MATERIAL', 'MEDIUM', 'MINOR', 'NEGLIGIBLE'];

// ─── Structural Diff Bar ─────────────────────────────────────────────────────

function StructuralDiffBar({ diff, lang }: { diff: StructuralDiff; lang: string }) {
  const score = Math.round(diff.structural_alignment_score * 100);
  const barColor = score >= 75 ? 'bg-emerald-500' : score >= 50 ? 'bg-amber-500' : 'bg-red-500';
  const stats = [
    { label: 'Doc A Clauses', value: diff.doc_a_clause_count,  color: 'text-blue-300' },
    { label: 'Doc B Clauses', value: diff.doc_b_clause_count,  color: 'text-purple-300' },
    { label: 'New in B',      value: diff.new_in_b_count,      color: 'text-blue-400' },
    { label: 'Missing from B', value: diff.missing_in_b_count, color: 'text-orange-400' },
  ];
  return (
    <div className="glass-panel p-5 space-y-4">
      <h3 className="text-xs font-semibold text-white uppercase tracking-wider flex items-center gap-2">
        <Layers className="w-4 h-4 text-amber-400" />
        {lang === 'hi' ? 'Sanrachnatmak Vishleshan' : 'Structural Alignment Analysis'}
      </h3>
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        {stats.map((s) => (
          <div key={s.label} className="bg-slate-900/60 rounded-lg p-3 text-center border border-slate-800">
            <span className={`text-2xl font-black ${s.color}`}>{s.value}</span>
            <p className="text-[10px] text-slate-500 mt-1 leading-tight">{s.label}</p>
          </div>
        ))}
      </div>
      <div className="space-y-1">
        <div className="flex justify-between text-xs text-slate-400">
          <span>Alignment Score</span>
          <span className="font-bold text-white">{score}%</span>
        </div>
        <div className="w-full h-2 bg-slate-800 rounded-full overflow-hidden">
          <div className={`h-full rounded-full transition-all duration-700 ${barColor}`} style={{ width: `${score}%` }} />
        </div>
      </div>
    </div>
  );
}

// ─── Evidence Pane ───────────────────────────────────────────────────────────

function EvidencePane({ evidence, label, side }: {
  evidence?: DocumentEvidence;
  label: string;
  side: 'a' | 'b';
}) {
  const c = side === 'a'
    ? { bg: 'bg-blue-950/30',   border: 'border-blue-500/25',   title: 'text-blue-300' }
    : { bg: 'bg-purple-950/30', border: 'border-purple-500/25', title: 'text-purple-300' };
  return (
    <div className={`rounded-lg p-3 border ${c.bg} ${c.border} text-xs space-y-1.5`}>
      <span className={`font-semibold block ${c.title}`}>{label}</span>
      {evidence ? (
        <>
          <p className="text-slate-200 font-mono leading-relaxed italic">&ldquo;{evidence.verbatim_quote}&rdquo;</p>
          <div className="flex flex-wrap gap-2 text-[10px] text-slate-500 pt-1">
            {evidence.section_heading && <span>{evidence.section_heading}</span>}
            <span>p.{evidence.page_number}</span>
          </div>
        </>
      ) : (
        <p className="text-slate-500 italic">Not present in this document</p>
      )}
    </div>
  );
}

// ─── Finding Card ────────────────────────────────────────────────────────────

function FindingCard({ finding, baseTitle, targetTitle, isActive, onClick }: {
  finding: ComparisonFindingItem;
  baseTitle: string;
  targetTitle: string;
  isActive: boolean;
  onClick: () => void;
}) {
  const cat = CATEGORY_CFG[finding.category] ?? CATEGORY_CFG.MODIFIED;
  const mat = MATERIALITY_CFG[finding.materiality] ?? MATERIALITY_CFG.MEDIUM;
  const [open, setOpen] = useState(false);

  return (
    <div
      id={`finding-${finding.finding_id}`}
      className={`rounded-xl border transition-all overflow-hidden ${isActive ? 'border-amber-500/70 ring-1 ring-amber-500/30 shadow-lg shadow-amber-900/20' : 'border-slate-800 hover:border-slate-600'}`}
    >
      <button
        type="button"
        onClick={() => { onClick(); setOpen((o) => !o); }}
        className="w-full text-left p-4 flex items-start gap-3 bg-slate-900/60 hover:bg-slate-900/80 transition-colors cursor-pointer"
        aria-expanded={open}
      >
        <span className={`shrink-0 text-[11px] font-bold px-2 py-1 rounded-full border ${cat.bg} ${cat.color} ${cat.border}`}>
          {cat.label}
        </span>
        <div className="flex-1 min-w-0 space-y-1">
          <p className="text-sm font-semibold text-white leading-snug">{finding.title}</p>
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-[10px] text-slate-400 bg-slate-800 px-1.5 py-0.5 rounded">
              {finding.dimension.replace('_', ' ')}
            </span>
            <span className={`text-[10px] font-bold px-2 py-0.5 rounded ${mat.bg} ${mat.color}`}>{mat.label}</span>
            <span className="text-[10px] text-slate-500">{Math.round(finding.confidence * 100)}% confidence</span>
          </div>
        </div>
        <ChevronDown className={`shrink-0 w-4 h-4 text-slate-500 transition-transform ${open ? 'rotate-180' : ''}`} />
      </button>

      {open && (
        <div className="p-4 pt-0 space-y-4 bg-slate-900/40 border-t border-slate-800">
          <div className="text-xs text-slate-300 leading-relaxed pt-3">
            <span className="font-semibold text-amber-300 block mb-1">What Changed</span>
            {finding.difference_explanation}
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <EvidencePane evidence={finding.document_a_evidence} label={`Doc A: ${baseTitle}`} side="a" />
            <EvidencePane evidence={finding.document_b_evidence} label={`Doc B: ${targetTitle}`} side="b" />
          </div>
          {finding.risk_implications && (
            <div className="flex items-start gap-2 text-xs bg-red-950/20 border border-red-500/20 rounded-lg p-3">
              <ShieldAlert className="w-4 h-4 text-red-400 shrink-0 mt-0.5" />
              <div>
                <span className="font-semibold text-red-300 block mb-0.5">Risk Implication</span>
                <span className="text-slate-300">{finding.risk_implications}</span>
              </div>
            </div>
          )}
          <div className="flex items-center gap-2 text-[10px] text-slate-500">
            <span>Semantic similarity:</span>
            <div className="w-24 h-1.5 bg-slate-800 rounded-full overflow-hidden">
              <div
                className="h-full rounded-full bg-gradient-to-r from-amber-500 to-emerald-500"
                style={{ width: `${Math.round(finding.semantic_similarity * 100)}%` }}
              />
            </div>
            <span className="font-mono text-slate-400">{Math.round(finding.semantic_similarity * 100)}%</span>
          </div>
        </div>
      )}
    </div>
  );
}

// ─── Main Page ───────────────────────────────────────────────────────────────

export default function ComparePage() {
  const { lang, t } = useLanguage();
  const [documents, setDocuments] = useState<DocumentMeta[]>([]);
  const [baseDocId, setBaseDocId] = useState<number | null>(null);
  const [targetDocId, setTargetDocId] = useState<number | null>(null);
  const [comparison, setComparison] = useState<ComparisonResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [quickLoading, setQuickLoading] = useState(false);
  const [activeFinding, setActiveFinding] = useState<string | null>(null);
  const [catFilter, setCatFilter] = useState<ComparisonCategory | 'ALL'>('ALL');
  const [dimFilter, setDimFilter] = useState('ALL');
  const [matFilter, setMatFilter] = useState('ALL');

  useEffect(() => {
    listDocuments()
      .then((docs) => {
        setDocuments(docs);
        if (docs.length >= 2) { setBaseDocId(docs[0].id); setTargetDocId(docs[1].id); }
      })
      .catch(() => {});
  }, []);

  const handleCompare = async (base: number, target: number) => {
    setLoading(true);
    setCatFilter('ALL'); setDimFilter('ALL'); setMatFilter('ALL'); setActiveFinding(null);
    try {
      setComparison(await compareDocuments(base, target));
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Comparison failed';
      alert(message);
    } finally {
      setLoading(false);
    }
  };

  const handleQuickCompareSample = async () => {
    setQuickLoading(true);
    try {
      const base = await loadSampleDocument('standard_residential_lease_delhi');
      const target = await loadSampleDocument('harsh_landlord_lease_delhi');
      setDocuments([base, target, ...documents]);
      setBaseDocId(base.id); setTargetDocId(target.id);
      await handleCompare(base.id, target.id);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Quick compare failed';
      alert(message);
    } finally {
      setQuickLoading(false);
    }
  };

  const handleFindingClick = useCallback((id: string) => {
    setActiveFinding(id);
    document.getElementById(`finding-${id}`)?.scrollIntoView({ behavior: 'smooth', block: 'center' });
  }, []);

  const findings = comparison?.findings ?? [];

  const filteredFindings = findings.filter((f) => {
    if (catFilter !== 'ALL' && f.category !== catFilter) return false;
    if (dimFilter !== 'ALL' && f.dimension !== dimFilter) return false;
    if (matFilter !== 'ALL' && f.materiality !== matFilter) return false;
    return true;
  });

  const criticalCount = findings.filter((f) => f.materiality === 'CRITICAL').length;
  const materialCount = findings.filter((f) => f.materiality === 'MATERIAL').length;
  const uniqueDims = Array.from(new Set(findings.map((f) => f.dimension)));

  return (
    <div className="space-y-8">

      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 border-b border-slate-800 pb-4">
        <div>
          <h1 className="text-2xl sm:text-3xl font-bold text-white flex items-center gap-2.5">
            <FileDiff className="w-7 h-7 text-amber-400" aria-hidden="true" />
            <span>{t.nav.compare}</span>
          </h1>
          <p className="text-xs sm:text-sm text-slate-400 mt-1">
            {lang === 'hi'
              ? 'Do kanuni anubhandhon ki gehri tulna: joodi gayi denadarian, hataye gaye adhikar, aur bhaautic parivartan.'
              : 'Deep semantic comparison: added liabilities, removed rights, and material modifications detected clause-by-clause.'}
          </p>
        </div>
        <button
          type="button"
          onClick={handleQuickCompareSample}
          disabled={quickLoading}
          className="px-4 py-2 rounded-xl bg-gradient-to-r from-amber-500 to-amber-600 hover:from-amber-400 hover:to-amber-500 disabled:opacity-50 text-slate-950 font-bold text-xs flex items-center gap-2 transition cursor-pointer shadow-md"
        >
          <span>
            {quickLoading
              ? 'Running Comparison...'
              : (lang === 'hi' ? 'Demo: Standard vs Harsh Lease' : 'Quick Demo: Standard vs Harsh Lease')}
          </span>
          <ArrowRight className="w-3.5 h-3.5" />
        </button>
      </div>

      {/* Document Selectors */}
      <div className="glass-panel p-6 space-y-4">
        <h2 className="text-sm font-semibold text-white uppercase tracking-wider">
          {lang === 'hi' ? 'Tulna hetu Dastavez chunen' : 'Select Documents to Compare'}
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="space-y-1.5">
            <label htmlFor="base-doc" className="text-xs text-slate-400 font-medium">
              {lang === 'hi' ? 'Mul Dastavez (Base Draft):' : 'Base Document (Original / Standard Draft):'}
            </label>
            <select
              id="base-doc"
              value={baseDocId || ''}
              onChange={(e) => setBaseDocId(parseInt(e.target.value, 10))}
              className="w-full bg-slate-900 border border-slate-700 rounded-lg p-2.5 text-xs text-white focus-visible:ring-2"
            >
              <option value="">-- Choose Base Document --</option>
              {documents.map((d) => (
                <option key={`base-${d.id}`} value={d.id}>{d.title} ({d.file_type.toUpperCase()})</option>
              ))}
            </select>
          </div>
          <div className="space-y-1.5">
            <label htmlFor="target-doc" className="text-xs text-slate-400 font-medium">
              {lang === 'hi' ? 'Sanshodhit Dastavez (Target Draft):' : 'Target Document (Proposed / Counterparty Draft):'}
            </label>
            <select
              id="target-doc"
              value={targetDocId || ''}
              onChange={(e) => setTargetDocId(parseInt(e.target.value, 10))}
              className="w-full bg-slate-900 border border-slate-700 rounded-lg p-2.5 text-xs text-white focus-visible:ring-2"
            >
              <option value="">-- Choose Target Document --</option>
              {documents.map((d) => (
                <option key={`target-${d.id}`} value={d.id}>{d.title} ({d.file_type.toUpperCase()})</option>
              ))}
            </select>
          </div>
        </div>
        <div className="pt-2 flex justify-end">
          <button
            type="button"
            disabled={!baseDocId || !targetDocId || baseDocId === targetDocId || loading}
            onClick={() => baseDocId && targetDocId && handleCompare(baseDocId, targetDocId)}
            className="px-5 py-2.5 rounded-lg bg-amber-500 hover:bg-amber-400 disabled:opacity-50 text-slate-950 font-bold text-xs flex items-center gap-2 cursor-pointer transition shadow-md"
          >
            {loading ? (
              <span>{lang === 'hi' ? 'Tulna ki ja rahi hai...' : 'Comparing Documents...'}</span>
            ) : (
              <>
                <span>{lang === 'hi' ? 'Semantic Tulna Chalayen' : 'Run Semantic Comparison'}</span>
                <FileDiff className="w-4 h-4" />
              </>
            )}
          </button>
        </div>
      </div>

      {/* Results */}
      {comparison && (
        <div className="space-y-6">

          {/* Verdict Card */}
          <div className="glass-panel p-6 border-l-4 border-l-amber-500 space-y-4">
            <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-800 pb-3">
              <div>
                <span className="text-xs font-semibold text-amber-400 uppercase tracking-wider block">
                  {lang === 'hi' ? 'Samagra Jokhim Nirnay' : 'Risk Delta Verdict'}
                </span>
                <h3 className="text-xl font-bold text-white mt-1">
                  {comparison.summary.net_risk_verdict === 'TARGET_MORE_HARSH'
                    ? (lang === 'hi' ? 'Savdhan: Target Draft adhik kathor hai' : 'Warning: Target Draft Is Significantly Harsher')
                    : (lang === 'hi' ? 'Anubandh santulit hain' : 'Contracts Are Broadly Balanced')}
                </h3>
              </div>
              <div className="flex flex-wrap gap-2">
                <span className={`px-3 py-1 rounded-full text-xs font-bold border ${
                  comparison.summary.net_risk_verdict === 'TARGET_MORE_HARSH'
                    ? 'bg-red-950 text-red-300 border-red-500/50'
                    : 'bg-emerald-950 text-emerald-300 border-emerald-500/40'
                }`}>
                  {comparison.summary.net_risk_verdict}
                </span>
                {criticalCount > 0 && (
                  <span className="px-3 py-1 rounded-full text-xs font-bold border bg-red-950 text-red-200 border-red-500/60">
                    {criticalCount} CRITICAL
                  </span>
                )}
                {materialCount > 0 && (
                  <span className="px-3 py-1 rounded-full text-xs font-bold border bg-orange-950 text-orange-200 border-orange-500/50">
                    {materialCount} MATERIAL
                  </span>
                )}
              </div>
            </div>

            <p className="text-sm text-slate-200 leading-relaxed">{comparison.overall_verdict}</p>

            {comparison.summary.critical_warnings.length > 0 && (
              <div className="space-y-2 pt-2">
                <span className="text-xs font-semibold text-red-400 flex items-center gap-1.5">
                  <AlertOctagon className="w-4 h-4" />
                  {lang === 'hi' ? 'Mahatvapurn Chetavaniyan:' : 'Critical Risk Warnings:'}
                </span>
                <ul className="space-y-1.5 text-xs text-slate-300">
                  {comparison.summary.critical_warnings.map((w, i) => (
                    <li key={i} className="flex items-start gap-2 bg-red-950/30 p-2.5 rounded-lg border border-red-500/20">
                      <span className="text-red-400 font-bold shrink-0">&#8226;</span>
                      <span>{w}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>

          {/* Structural diff */}
          {comparison.structural_diff && (
            <StructuralDiffBar diff={comparison.structural_diff} lang={lang} />
          )}

          {/* Semantic Findings */}
          {findings.length > 0 && (
            <div className="space-y-4">
              <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
                <h3 className="text-lg font-bold text-white flex items-center gap-2">
                  <Target className="w-5 h-5 text-amber-400" />
                  {lang === 'hi' ? `Semantic Khoj (${findings.length} nishkarsh)` : `Semantic Findings (${findings.length} total)`}
                </h3>
                <span className="text-xs text-slate-500">
                  {lang === 'hi' ? `${filteredFindings.length} dikhaaye ja rahe hain` : `${filteredFindings.length} showing`}
                </span>
              </div>

              {/* Category filter pills */}
              <div className="flex flex-wrap gap-2">
                <button
                  type="button"
                  onClick={() => setCatFilter('ALL')}
                  className={`text-xs px-3 py-1.5 rounded-full border font-semibold transition ${
                    catFilter === 'ALL'
                      ? 'bg-amber-500 text-slate-950 border-amber-400'
                      : 'bg-slate-900 text-slate-400 border-slate-700 hover:border-slate-500'
                  }`}
                >
                  ALL ({findings.length})
                </button>
                {ALL_CATS.map((cat) => {
                  const count = findings.filter((f) => f.category === cat).length;
                  if (!count) return null;
                  const c = CATEGORY_CFG[cat];
                  return (
                    <button
                      key={cat}
                      type="button"
                      onClick={() => setCatFilter(catFilter === cat ? 'ALL' : cat)}
                      className={`text-xs px-3 py-1.5 rounded-full border font-semibold transition ${
                        catFilter === cat
                          ? `${c.bg} ${c.color} ${c.border}`
                          : 'bg-slate-900 text-slate-400 border-slate-700 hover:border-slate-500'
                      }`}
                    >
                      {c.label} ({count})
                    </button>
                  );
                })}
              </div>

              {/* Secondary filters */}
              {uniqueDims.length > 1 && (
                <div className="flex flex-wrap gap-2 items-center">
                  <span className="text-[10px] text-slate-500 flex items-center gap-1">
                    <SlidersHorizontal className="w-3 h-3" /> Filter:
                  </span>
                  <select
                    value={dimFilter}
                    onChange={(e) => setDimFilter(e.target.value)}
                    className="bg-slate-900 border border-slate-700 rounded-lg px-2 py-1 text-xs text-white"
                    aria-label="Filter by dimension"
                  >
                    <option value="ALL">All Dimensions</option>
                    {uniqueDims.map((d) => <option key={d} value={d}>{d.replace('_', ' ')}</option>)}
                  </select>
                  <select
                    value={matFilter}
                    onChange={(e) => setMatFilter(e.target.value)}
                    className="bg-slate-900 border border-slate-700 rounded-lg px-2 py-1 text-xs text-white"
                    aria-label="Filter by materiality"
                  >
                    <option value="ALL">All Materiality</option>
                    {ALL_MAT.map((m) => <option key={m} value={m}>{m}</option>)}
                  </select>
                </div>
              )}

              {/* Findings list */}
              <div className="space-y-3">
                {filteredFindings.length === 0 ? (
                  <div className="text-center py-12 text-slate-500 text-sm">
                    <Filter className="w-8 h-8 mx-auto mb-2 opacity-30" />
                    {lang === 'hi' ? 'Chune gaye filter ke liye koi nishkarsh nahi.' : 'No findings match the current filters.'}
                  </div>
                ) : (
                  filteredFindings.map((f) => (
                    <FindingCard
                      key={f.finding_id}
                      finding={f}
                      baseTitle={comparison.base_title}
                      targetTitle={comparison.target_title}
                      isActive={activeFinding === f.finding_id}
                      onClick={() => handleFindingClick(f.finding_id)}
                    />
                  ))
                )}
              </div>
            </div>
          )}

          {/* Legacy clause diffs fallback */}
          {findings.length === 0 && comparison.clause_diffs.length > 0 && (
            <div className="space-y-4">
              <h3 className="text-lg font-bold text-white">
                {lang === 'hi' ? 'Dhara-dar-Dhara Tulnatmak Vivaran' : 'Clause-by-Clause Impact Analysis'}
              </h3>
              <div className="grid grid-cols-1 gap-4">
                {comparison.clause_diffs.map((diff, idx) => (
                  <div key={idx} className="glass-panel p-5 space-y-3">
                    <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-800 pb-2">
                      <div className="flex items-center gap-2">
                        <span className="text-base font-bold text-white">{diff.category}</span>
                        <span className={`text-[11px] px-2 py-0.5 rounded font-mono ${
                          diff.change_type === 'MODIFIED'
                            ? 'bg-amber-950 text-amber-300 border border-amber-500/30'
                            : diff.change_type === 'ADDED'
                            ? 'bg-red-950 text-red-300 border border-red-500/30'
                            : 'bg-slate-800 text-slate-400'
                        }`}>{diff.change_type}</span>
                      </div>
                      <span className={`text-xs font-semibold px-2.5 py-0.5 rounded-full border ${
                        diff.risk_delta === 'INCREASED_RISK'
                          ? 'bg-red-950/80 text-red-300 border-red-500/50'
                          : 'bg-slate-900 text-slate-400 border-slate-800'
                      }`}>{diff.risk_delta}</span>
                    </div>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
                      <div className="bg-slate-900/60 p-3 rounded-lg border border-slate-800">
                        <span className="text-slate-400 font-semibold block mb-1">{comparison.base_title}</span>
                        <p className="text-slate-300 font-mono leading-relaxed">{diff.base_text || 'None'}</p>
                      </div>
                      <div className="bg-red-950/20 p-3 rounded-lg border border-red-500/30">
                        <span className="text-amber-400 font-semibold block mb-1">{comparison.target_title}</span>
                        <p className="text-red-200 font-mono leading-relaxed">{diff.target_text || 'None'}</p>
                      </div>
                    </div>
                    <div className="text-xs bg-slate-900 p-2.5 rounded-lg text-slate-300 flex items-start gap-1.5">
                      <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
                      <span>
                        <strong className="text-white">{lang === 'hi' ? 'Prabhav: ' : 'Impact: '}</strong>
                        {diff.impact_analysis}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Dimensions analyzed footer */}
          {(comparison.dimensions_analyzed ?? []).length > 0 && (
            <div className="flex flex-wrap items-center gap-2 text-[10px] text-slate-600 pt-2 border-t border-slate-800">
              <Info className="w-3 h-3" />
              <span>{lang === 'hi' ? 'Vishlesit aayam:' : 'Dimensions analyzed:'}</span>
              {comparison.dimensions_analyzed.map((d) => (
                <span key={d} className="text-slate-500">{d.replace('_', ' ')}</span>
              ))}
            </div>
          )}

        </div>
      )}
    </div>
  );
}
