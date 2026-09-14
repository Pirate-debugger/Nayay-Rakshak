'use client';

import React, { useCallback, useState } from 'react';
import {
  AlertTriangle,
  BadgeAlert,
  BookOpen,
  Calendar,
  ChevronDown,
  ChevronUp,
  CircleCheck,
  CircleHelp,
  ClipboardList,
  Compass,
  FileQuestion,
  Files,
  Lightbulb,
  Loader2,
  Scale,
  ShieldAlert,
  ShieldCheck,
  UserCheck,
} from 'lucide-react';
import {
  ActionNavigatorResponse,
  IssueSeverity,
  NavActionStep,
  NavDateItem,
  NavDocumentItem,
  NavEscalationTrigger,
  NavFactItem,
  NavIssueItem,
  NavQuestionItem,
  UrgencyLevel,
} from '@/lib/types';
import { generateActionPlan } from '@/lib/api';
import { useLanguage } from '@/components/AppShell';

// ─── Utility helpers ──────────────────────────────────────────────────────────

function urgencyColor(u: UrgencyLevel): string {
  switch (u) {
    case 'IMMEDIATE': return 'text-red-400 bg-red-950/40 border-red-800/60';
    case 'HIGH':      return 'text-orange-400 bg-orange-950/40 border-orange-800/60';
    case 'MEDIUM':    return 'text-amber-400 bg-amber-950/40 border-amber-800/60';
    case 'LOW':       return 'text-emerald-400 bg-emerald-950/40 border-emerald-800/60';
    default:          return 'text-slate-400 bg-slate-900/40 border-slate-700';
  }
}

function urgencyBadge(u: UrgencyLevel): string {
  switch (u) {
    case 'IMMEDIATE': return 'bg-red-900/60 text-red-300 border border-red-700';
    case 'HIGH':      return 'bg-orange-900/60 text-orange-300 border border-orange-700';
    case 'MEDIUM':    return 'bg-amber-900/60 text-amber-300 border border-amber-700';
    case 'LOW':       return 'bg-emerald-900/60 text-emerald-300 border border-emerald-700';
    default:          return 'bg-slate-800 text-slate-400 border border-slate-700';
  }
}

function urgencyLabel(u: UrgencyLevel, lang: 'en' | 'hi'): string {
  const map = {
    en: { IMMEDIATE: 'Act Now', HIGH: 'This Week', MEDIUM: 'This Month', LOW: 'Before Signing', INFORMATIONAL: 'Awareness' },
    hi: { IMMEDIATE: 'तुरंत करें', HIGH: 'इस सप्ताह', MEDIUM: 'इस माह', LOW: 'हस्ताक्षर से पहले', INFORMATIONAL: 'जागरूकता' },
  };
  return map[lang][u] ?? u;
}

function severityColor(s: IssueSeverity): string {
  switch (s) {
    case 'CRITICAL': return 'text-red-400 border-red-800/60 bg-red-950/30';
    case 'HIGH':     return 'text-orange-400 border-orange-800/60 bg-orange-950/30';
    case 'MEDIUM':   return 'text-amber-400 border-amber-800/60 bg-amber-950/30';
    case 'LOW':      return 'text-emerald-400 border-emerald-800/60 bg-emerald-950/30';
  }
}

function severityBadge(s: IssueSeverity): string {
  switch (s) {
    case 'CRITICAL': return 'bg-red-900/70 text-red-300 border border-red-700';
    case 'HIGH':     return 'bg-orange-900/70 text-orange-300 border border-orange-700';
    case 'MEDIUM':   return 'bg-amber-900/70 text-amber-300 border border-amber-700';
    case 'LOW':      return 'bg-emerald-900/70 text-emerald-300 border border-emerald-700';
  }
}

// ─── Section Header ──────────────────────────────────────────────────────────

function SectionHeader({
  icon: Icon,
  title,
  count,
  color = 'text-amber-400',
}: {
  icon: React.ElementType;
  title: string;
  count?: number;
  color?: string;
}) {
  return (
    <div className="flex items-center gap-2 mb-4">
      <Icon className={`w-5 h-5 ${color}`} aria-hidden />
      <h2 className={`text-base font-bold tracking-wide ${color}`}>{title}</h2>
      {count !== undefined && (
        <span className="ml-auto text-xs font-mono text-slate-500 tabular-nums">{count}</span>
      )}
    </div>
  );
}

// ─── Facts Card ───────────────────────────────────────────────────────────────

function FactCard({ fact, accent }: { fact: NavFactItem; accent: string }) {
  const pct = Math.round(fact.confidence * 100);
  return (
    <div className={`rounded-xl border p-3.5 space-y-1.5 ${accent}`}>
      <p className="text-sm text-slate-100 leading-relaxed">{fact.fact}</p>
      <div className="flex items-center gap-3 text-xs text-slate-400">
        <span className="font-mono bg-slate-900/60 px-1.5 py-0.5 rounded text-[10px]">
          {fact.category}
        </span>
        <span className="ml-auto">{pct}% confidence</span>
      </div>
      <p className="text-[10px] text-slate-500">Source: {fact.source}</p>
    </div>
  );
}

// ─── Document Card ───────────────────────────────────────────────────────────

function DocumentCard({ doc, lang }: { doc: NavDocumentItem; lang: 'en' | 'hi' }) {
  return (
    <div className={`rounded-xl border p-4 space-y-2 ${urgencyColor(doc.urgency)}`}>
      <div className="flex items-start justify-between gap-2">
        <p className="text-sm font-semibold text-slate-100">{doc.document_name}</p>
        <span className={`text-[10px] px-1.5 py-0.5 rounded font-mono whitespace-nowrap ${urgencyBadge(doc.urgency)}`}>
          {urgencyLabel(doc.urgency, lang)}
        </span>
      </div>
      <p className="text-xs text-slate-300 leading-relaxed">{doc.why_needed}</p>
      <p className="text-[11px] text-slate-500 border-t border-slate-800/60 pt-1.5">
        ⚠ {doc.consequence_if_missing}
      </p>
    </div>
  );
}

// ─── Date Card ───────────────────────────────────────────────────────────────

function DateCard({ item, lang }: { item: NavDateItem; lang: 'en' | 'hi' }) {
  return (
    <div className={`rounded-xl border p-4 space-y-2 ${urgencyColor(item.urgency)}`}>
      <div className="flex items-center gap-2">
        <Calendar className="w-4 h-4 flex-shrink-0" aria-hidden />
        <p className="text-sm font-semibold text-slate-100">{item.date_description}</p>
        <span className={`ml-auto text-[10px] px-1.5 py-0.5 rounded font-mono ${urgencyBadge(item.urgency)}`}>
          {urgencyLabel(item.urgency, lang)}
        </span>
      </div>
      {item.estimated_date && (
        <p className="text-sm font-mono text-amber-300">{item.estimated_date}</p>
      )}
      <p className="text-xs text-slate-300 leading-relaxed">{item.consequence}</p>
      <p className="text-[10px] text-slate-500">Source: {item.source}</p>
    </div>
  );
}

// ─── Issue Card ──────────────────────────────────────────────────────────────

function IssueCard({ issue }: { issue: NavIssueItem }) {
  const [open, setOpen] = useState(false);
  return (
    <div className={`rounded-xl border p-4 space-y-2 transition ${severityColor(issue.severity)}`}>
      <div className="flex items-start gap-2">
        <BadgeAlert className="w-4 h-4 flex-shrink-0 mt-0.5" aria-hidden />
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <p className="text-sm font-semibold text-slate-100">{issue.issue}</p>
            <span className={`text-[10px] px-1.5 py-0.5 rounded font-mono ${severityBadge(issue.severity)}`}>
              {issue.severity}
            </span>
            <span className="text-[10px] text-slate-500 font-mono">{issue.category}</span>
          </div>
          <p className="text-xs text-slate-300 mt-1 leading-relaxed">{issue.explanation}</p>
        </div>
        <button
          onClick={() => setOpen(!open)}
          className="flex-shrink-0 p-1 text-slate-500 hover:text-slate-300 transition"
          aria-label={open ? 'Collapse' : 'Expand'}
        >
          {open ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
        </button>
      </div>
      {open && (
        <div className="mt-2 pl-6 space-y-1.5 border-t border-slate-800/60 pt-2">
          <p className="text-xs text-slate-400"><span className="text-slate-500">Potential impact:</span> {issue.potential_impact}</p>
          {issue.source_risk_id && (
            <p className="text-[10px] text-slate-600 font-mono">Risk ID: {issue.source_risk_id}</p>
          )}
        </div>
      )}
    </div>
  );
}

// ─── Step Card ───────────────────────────────────────────────────────────────

function StepCard({ step, lang }: { step: NavActionStep; lang: 'en' | 'hi' }) {
  const [open, setOpen] = useState(false);
  return (
    <div
      className={`rounded-xl border p-4 transition ${
        step.is_professional_review_step
          ? 'border-purple-700/60 bg-purple-950/20'
          : urgencyColor(step.urgency)
      }`}
    >
      <div className="flex gap-3 items-start">
        <div
          className={`flex-shrink-0 w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold ${
            step.is_professional_review_step
              ? 'bg-purple-800/60 text-purple-300'
              : 'bg-slate-800 text-slate-300'
          }`}
        >
          {step.step_number}
        </div>
        <div className="flex-1 min-w-0">
          <p className={`text-sm font-medium leading-relaxed ${
            step.is_professional_review_step ? 'text-purple-200' : 'text-slate-100'
          }`}>
            {step.action}
          </p>
          <div className="flex flex-wrap gap-2 mt-1.5 items-center">
            <span className={`text-[10px] px-1.5 py-0.5 rounded font-mono ${urgencyBadge(step.urgency)}`}>
              {urgencyLabel(step.urgency, lang)}
            </span>
            {step.is_professional_review_step && (
              <span className="text-[10px] px-1.5 py-0.5 rounded font-mono bg-purple-900/60 text-purple-300 border border-purple-700">
                Professional Review
              </span>
            )}
          </div>
        </div>
        <button
          onClick={() => setOpen(!open)}
          className="flex-shrink-0 p-1 text-slate-500 hover:text-slate-300 transition"
          aria-label="Toggle details"
        >
          {open ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
        </button>
      </div>
      {open && (
        <div className="mt-3 pl-10 space-y-2 border-t border-slate-800/60 pt-3">
          <p className="text-xs text-slate-300 leading-relaxed">
            <span className="text-slate-500">Why:</span> {step.reason}
          </p>
          <p className="text-[11px] text-slate-500 font-mono">
            Evidence: {step.evidence_source}
          </p>
          {step.dependency && (
            <p className="text-[11px] text-slate-500">
              Depends on: {step.dependency}
            </p>
          )}
        </div>
      )}
    </div>
  );
}

// ─── Question Card ────────────────────────────────────────────────────────────

function QuestionCard({ q, lang }: { q: NavQuestionItem; lang: 'en' | 'hi' }) {
  const [open, setOpen] = useState(false);
  return (
    <div className={`rounded-xl border p-4 space-y-2 ${urgencyColor(q.priority)}`}>
      <div className="flex items-start gap-2">
        <CircleHelp className="w-4 h-4 flex-shrink-0 mt-0.5" aria-hidden />
        <div className="flex-1">
          <p className="text-sm text-slate-100 leading-relaxed">{q.question}</p>
          <p className="text-xs text-slate-500 mt-0.5">Ask: <span className="text-slate-400">{q.ask_whom}</span></p>
        </div>
        <button
          onClick={() => setOpen(!open)}
          className="flex-shrink-0 p-1 text-slate-500 hover:text-slate-300 transition"
          aria-label="Toggle purpose"
        >
          {open ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
        </button>
      </div>
      {open && (
        <p className="text-xs text-slate-300 pl-6 leading-relaxed border-t border-slate-800/60 pt-2">
          <span className="text-slate-500">Purpose:</span> {q.purpose}
        </p>
      )}
    </div>
  );
}

// ─── Escalation Card ─────────────────────────────────────────────────────────

function EscalationCard({ trigger }: { trigger: NavEscalationTrigger }) {
  return (
    <div className={`rounded-xl border p-4 space-y-2 ${severityColor(trigger.severity)}`}>
      <div className="flex items-start gap-2">
        <ShieldAlert className="w-4 h-4 flex-shrink-0 mt-0.5" aria-hidden />
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <p className="text-sm font-semibold text-slate-100">
              {trigger.trigger_type.replace(/_/g, ' ')}
            </p>
            <span className={`text-[10px] px-1.5 py-0.5 rounded font-mono ${severityBadge(trigger.severity)}`}>
              {trigger.severity}
            </span>
          </div>
          <p className="text-xs text-slate-300 mt-1 leading-relaxed">{trigger.reason}</p>
          <p className="text-xs mt-2 text-amber-400 font-medium">
            → {trigger.recommended_resource}
          </p>
        </div>
      </div>
    </div>
  );
}

// ─── Disclaimer Banner ────────────────────────────────────────────────────────

function DisclaimerFooter({ text }: { text: string }) {
  return (
    <div className="mt-8 rounded-xl border border-slate-700/60 bg-slate-900/60 p-4" role="note" aria-label="Legal Disclaimer">
      <div className="flex gap-2 items-start">
        <Scale className="w-4 h-4 text-amber-500 flex-shrink-0 mt-0.5" aria-hidden />
        <p className="text-xs text-slate-400 leading-relaxed">{text}</p>
      </div>
    </div>
  );
}

// ─── Professional Review Banner ───────────────────────────────────────────────

function ProfessionalReviewBanner({
  recommended,
  urgency,
  triggerCount,
  lang,
}: {
  recommended: boolean;
  urgency: UrgencyLevel;
  triggerCount: number;
  lang: 'en' | 'hi';
}) {
  if (!recommended) return null;
  const isCritical = urgency === 'IMMEDIATE' || urgency === 'HIGH';
  return (
    <div
      className={`rounded-xl border p-4 flex gap-3 items-start mb-6 ${
        isCritical
          ? 'border-red-700/60 bg-red-950/30'
          : 'border-amber-700/60 bg-amber-950/20'
      }`}
      role="alert"
      aria-live="polite"
    >
      <ShieldAlert
        className={`w-5 h-5 flex-shrink-0 mt-0.5 ${isCritical ? 'text-red-400' : 'text-amber-400'}`}
        aria-hidden
      />
      <div className="flex-1">
        <p className={`font-bold text-sm ${isCritical ? 'text-red-300' : 'text-amber-300'}`}>
          {lang === 'hi'
            ? `पेशेवर कानूनी सलाह की आवश्यकता — ${triggerCount} कारण पाए गए`
            : `Professional Legal Review Recommended — ${triggerCount} trigger${triggerCount !== 1 ? 's' : ''} identified`}
        </p>
        <p className="text-xs text-slate-300 mt-1">
          {lang === 'hi'
            ? 'इस दस्तावेज़ में गंभीर जोखिम पाए गए हैं। हस्ताक्षर करने से पहले किसी योग्य अधिवक्ता से परामर्श लें। NALSA निःशुल्क सहायता: 15100'
            : 'This document contains conditions that warrant professional assessment before you sign or act. Free legal aid: NALSA 15100 · nalsa.gov.in'}
        </p>
      </div>
      <span className={`flex-shrink-0 text-[10px] px-1.5 py-0.5 rounded font-mono ${urgencyBadge(urgency)}`}>
        {urgencyLabel(urgency, lang)}
      </span>
    </div>
  );
}

// ─── Document Selector ───────────────────────────────────────────────────────

function DocumentSelector({
  onSelect,
  lang,
}: {
  onSelect: (id: number) => void;
  lang: 'en' | 'hi';
}) {
  const [docId, setDocId] = useState('');
  const valid = /^\d+$/.test(docId.trim()) && parseInt(docId, 10) > 0;

  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-5 flex flex-col sm:flex-row gap-4 items-start sm:items-end">
      <div className="flex-1">
        <label htmlFor="doc-id-input" className="block text-xs text-slate-400 mb-1.5 font-medium">
          {lang === 'hi' ? 'दस्तावेज़ ID दर्ज करें' : 'Enter Document ID'}
        </label>
        <input
          id="doc-id-input"
          type="number"
          min={1}
          value={docId}
          onChange={(e) => setDocId(e.target.value)}
          placeholder="e.g. 1"
          className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-100
                     placeholder-slate-600 focus:outline-none focus:ring-2 focus:ring-amber-500/50"
        />
        <p className="mt-1 text-[11px] text-slate-600">
          {lang === 'hi'
            ? 'My Documents से दस्तावेज़ ID प्राप्त करें।'
            : 'Find your Document ID in My Documents.'}
        </p>
      </div>
      <button
        disabled={!valid}
        onClick={() => valid && onSelect(parseInt(docId, 10))}
        className="px-5 py-2 rounded-lg text-sm font-semibold transition
                   bg-amber-500 text-slate-950 hover:bg-amber-400
                   disabled:opacity-40 disabled:cursor-not-allowed"
      >
        {lang === 'hi' ? 'योजना बनाएं' : 'Generate Plan'}
      </button>
    </div>
  );
}

// ─── Empty State ─────────────────────────────────────────────────────────────

function EmptyState({ lang }: { lang: 'en' | 'hi' }) {
  return (
    <div className="text-center py-16 space-y-3">
      <Compass className="w-12 h-12 text-slate-700 mx-auto" />
      <p className="text-slate-400 text-sm">
        {lang === 'hi'
          ? 'ऊपर अपना दस्तावेज़ ID दर्ज करें और Action Navigator शुरू करें।'
          : 'Enter your Document ID above to generate your Action Plan.'}
      </p>
    </div>
  );
}

// ─── Main Page ────────────────────────────────────────────────────────────────

export default function ActionNavigatorPage() {
  const { lang } = useLanguage();
  const [plan, setPlan] = useState<ActionNavigatorResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleGenerate = useCallback(async (documentId: number) => {
    setLoading(true);
    setError(null);
    setPlan(null);
    try {
      const result = await generateActionPlan(documentId);
      setPlan(result);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to generate action plan.');
    } finally {
      setLoading(false);
    }
  }, []);

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      {/* Page Header */}
      <div className="space-y-1">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-amber-500 to-amber-700 flex items-center justify-center">
            <Compass className="w-4.5 h-4.5 text-slate-950" aria-hidden />
          </div>
          <h1 className="text-2xl font-black tracking-tight text-white">
            {lang === 'hi' ? 'कार्य मार्गदर्शक' : 'Action Navigator'}
          </h1>
        </div>
        <p className="text-sm text-slate-400 pl-10">
          {lang === 'hi'
            ? 'आपके दस्तावेज़ विश्लेषण को व्यावहारिक, गैर-बाध्यकारी अगले कदमों में बदलता है।'
            : 'Converts document analysis into practical, non-binding next steps. Never a guaranteed legal outcome.'}
        </p>
      </div>

      {/* Document Selector */}
      <DocumentSelector onSelect={handleGenerate} lang={lang} />

      {/* Loading State */}
      {loading && (
        <div className="flex items-center justify-center py-14 gap-3 text-slate-400">
          <Loader2 className="w-5 h-5 animate-spin text-amber-400" />
          <span className="text-sm">
            {lang === 'hi' ? 'योजना तैयार हो रही है…' : 'Generating your action plan…'}
          </span>
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="rounded-xl border border-red-800/60 bg-red-950/30 p-4 flex gap-3 items-start">
          <AlertTriangle className="w-4 h-4 text-red-400 flex-shrink-0 mt-0.5" />
          <p className="text-sm text-red-300">{error}</p>
        </div>
      )}

      {/* Empty state */}
      {!loading && !error && !plan && <EmptyState lang={lang} />}

      {/* Plan output */}
      {plan && !loading && (
        <div className="space-y-6">
          {/* Meta */}
          <div className="rounded-xl border border-slate-800 bg-slate-900/40 px-4 py-3 flex flex-wrap gap-x-6 gap-y-1 items-center text-xs text-slate-400">
            <span>
              <span className="text-slate-500">Document:</span>{' '}
              <span className="text-slate-200 font-medium">{plan.document_title}</span>
            </span>
            <span>
              <span className="text-slate-500">Engine:</span>{' '}
              <span className="font-mono">{plan.engine_version}</span>
            </span>
            <span>
              <span className="text-slate-500">Generated:</span>{' '}
              {new Date(plan.generated_at).toLocaleString()}
            </span>
          </div>

          {/* Professional Review Banner */}
          <ProfessionalReviewBanner
            recommended={plan.professional_review_recommended}
            urgency={plan.professional_review_urgency}
            triggerCount={plan.when_to_seek_professional_help.length}
            lang={lang}
          />

          {/* ── Row 1: Known + Unknown Facts ── */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
            {/* Known Facts */}
            <section aria-labelledby="known-facts-heading" className="rounded-xl border border-slate-800 bg-slate-900/30 p-5">
              <SectionHeader
                icon={CircleCheck}
                title={lang === 'hi' ? 'ज्ञात तथ्य' : 'Known Facts'}
                count={plan.known_facts.length}
                color="text-emerald-400"
              />
              {plan.known_facts.length === 0 ? (
                <p className="text-xs text-slate-500">{lang === 'hi' ? 'कोई स्पष्ट तथ्य नहीं पाए गए।' : 'No concrete facts extracted.'}</p>
              ) : (
                <div className="space-y-2">
                  {plan.known_facts.map((f, i) => (
                    <FactCard
                      key={i}
                      fact={f}
                      accent="border-emerald-800/40 bg-emerald-950/20"
                    />
                  ))}
                </div>
              )}
            </section>

            {/* Unknown / Ambiguous Facts */}
            <section aria-labelledby="unknown-facts-heading" className="rounded-xl border border-slate-800 bg-slate-900/30 p-5">
              <SectionHeader
                icon={FileQuestion}
                title={lang === 'hi' ? 'अस्पष्ट / अनुपस्थित जानकारी' : 'Unknown / Gaps'}
                count={plan.unknown_facts.length}
                color="text-amber-400"
              />
              {plan.unknown_facts.length === 0 ? (
                <p className="text-xs text-slate-500">{lang === 'hi' ? 'कोई स्पष्ट अंतर नहीं पाया गया।' : 'No significant gaps detected.'}</p>
              ) : (
                <div className="space-y-2">
                  {plan.unknown_facts.map((f, i) => (
                    <FactCard
                      key={i}
                      fact={f}
                      accent="border-amber-800/40 bg-amber-950/20"
                    />
                  ))}
                </div>
              )}
            </section>
          </div>

          {/* ── Row 2: Documents + Dates ── */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
            {/* Important Documents */}
            <section aria-labelledby="docs-heading" className="rounded-xl border border-slate-800 bg-slate-900/30 p-5">
              <SectionHeader
                icon={Files}
                title={lang === 'hi' ? 'महत्वपूर्ण दस्तावेज़' : 'Important Documents'}
                count={plan.important_documents.length}
                color="text-sky-400"
              />
              <div className="space-y-3">
                {plan.important_documents.map((doc, i) => (
                  <DocumentCard key={i} doc={doc} lang={lang} />
                ))}
              </div>
            </section>

            {/* Important Dates */}
            <section aria-labelledby="dates-heading" className="rounded-xl border border-slate-800 bg-slate-900/30 p-5">
              <SectionHeader
                icon={Calendar}
                title={lang === 'hi' ? 'महत्वपूर्ण तिथियां / समय-सीमा' : 'Important Dates & Deadlines'}
                count={plan.important_dates.length}
                color="text-rose-400"
              />
              {plan.important_dates.length === 0 ? (
                <p className="text-xs text-slate-500">{lang === 'hi' ? 'कोई विशिष्ट तिथि नहीं मिली।' : 'No specific dates extracted.'}</p>
              ) : (
                <div className="space-y-3">
                  {plan.important_dates.map((d, i) => (
                    <DateCard key={i} item={d} lang={lang} />
                  ))}
                </div>
              )}
            </section>
          </div>

          {/* ── Section: Potential Issues ── */}
          {plan.potential_issues.length > 0 && (
            <section aria-labelledby="issues-heading" className="rounded-xl border border-slate-800 bg-slate-900/30 p-5">
              <SectionHeader
                icon={AlertTriangle}
                title={lang === 'hi' ? 'संभावित समस्याएं' : 'Potential Issues'}
                count={plan.potential_issues.length}
                color="text-orange-400"
              />
              <div className="space-y-2">
                {plan.potential_issues.map((issue, i) => (
                  <IssueCard key={i} issue={issue} />
                ))}
              </div>
            </section>
          )}

          {/* ── Section: Next Steps ── */}
          <section aria-labelledby="steps-heading" className="rounded-xl border border-slate-800 bg-slate-900/30 p-5">
            <SectionHeader
              icon={ClipboardList}
              title={lang === 'hi' ? 'संभावित अगले कदम' : 'Possible Next Steps'}
              count={plan.possible_next_steps.length}
              color="text-amber-400"
            />
            <p className="text-[11px] text-slate-500 mb-3">
              {lang === 'hi'
                ? 'ये कदम सुझावात्मक हैं, बाध्यकारी नहीं। कोई कानूनी परिणाम की गारंटी नहीं है।'
                : 'These steps are suggestions only — non-binding. No legal outcome is guaranteed.'}
            </p>
            <div className="space-y-2">
              {plan.possible_next_steps.map((step, i) => (
                <StepCard key={i} step={step} lang={lang} />
              ))}
            </div>
          </section>

          {/* ── Section: Questions to Ask ── */}
          {plan.questions_to_ask.length > 0 && (
            <section aria-labelledby="questions-heading" className="rounded-xl border border-slate-800 bg-slate-900/30 p-5">
              <SectionHeader
                icon={BookOpen}
                title={lang === 'hi' ? 'पूछे जाने वाले प्रश्न' : 'Questions to Ask'}
                count={plan.questions_to_ask.length}
                color="text-violet-400"
              />
              <div className="space-y-2">
                {plan.questions_to_ask.map((q, i) => (
                  <QuestionCard key={i} q={q} lang={lang} />
                ))}
              </div>
            </section>
          )}

          {/* ── Section: When to Seek Professional Help ── */}
          {plan.when_to_seek_professional_help.length > 0 && (
            <section aria-labelledby="escalation-heading" className="rounded-xl border border-slate-800 bg-slate-900/30 p-5">
              <SectionHeader
                icon={UserCheck}
                title={lang === 'hi' ? 'वकील से कब मिलें?' : 'When to Seek Professional Help'}
                count={plan.when_to_seek_professional_help.length}
                color="text-red-400"
              />
              <p className="text-[11px] text-slate-500 mb-3">
                {lang === 'hi'
                  ? 'ये स्थितियां पहचानी गई हैं जहां विशेषज्ञ कानूनी सहायता लेना उचित होगा।'
                  : 'These conditions have been identified where professional legal consultation is advisable.'}
              </p>
              <div className="space-y-2">
                {plan.when_to_seek_professional_help.map((t, i) => (
                  <EscalationCard key={i} trigger={t} />
                ))}
              </div>
              {/* NALSA quick link */}
              <div className="mt-4 flex flex-wrap gap-3 text-xs">
                <a
                  href="https://nalsa.gov.in"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg
                             bg-emerald-950/40 border border-emerald-800/60 text-emerald-400 hover:text-emerald-300 transition"
                >
                  <ShieldCheck className="w-3.5 h-3.5" />
                  NALSA Free Legal Aid — 15100
                </a>
                <a
                  href="https://edaakhil.nic.in"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg
                             bg-sky-950/40 border border-sky-800/60 text-sky-400 hover:text-sky-300 transition"
                >
                  <Lightbulb className="w-3.5 h-3.5" />
                  e-Daakhil Consumer E-Filing
                </a>
              </div>
            </section>
          )}

          {/* Mandatory Disclaimer — non-dismissible */}
          <DisclaimerFooter text={plan.disclaimer} />
        </div>
      )}
    </div>
  );
}
