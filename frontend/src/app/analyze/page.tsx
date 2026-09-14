'use client';

import React, { Suspense, useEffect, useState } from 'react';
import Link from 'next/link';
import { useSearchParams } from 'next/navigation';
import {
  AlertOctagon,
  AlertTriangle,
  ArrowRight,
  BookOpen,
  CheckCircle2,
  Clock,
  FileCheck2,
  FileText,
  Filter,
  HelpCircle,
  Lightbulb,
  ListChecks,
  Scale,
  ShieldAlert,
} from 'lucide-react';
import ClauseCard from '@/components/ClauseCard';
import RiskPill from '@/components/RiskPill';
import { useLanguage } from '@/components/AppShell';
import { analyzeDocument, getDocumentAnalysis, getDocumentChecklist, listDocuments } from '@/lib/api';
import { AnalysisResponse, DocumentMeta } from '@/lib/types';

function AnalyzeContent() {
  const { lang, t } = useLanguage();
  const searchParams = useSearchParams();
  const docIdParam = searchParams.get('docId');

  const [documents, setDocuments] = useState<DocumentMeta[]>([]);
  const [selectedDocId, setSelectedDocId] = useState<number | null>(docIdParam ? parseInt(docIdParam, 10) : null);
  const [analysis, setAnalysis] = useState<AnalysisResponse | null>(null);
  const [checklist, setChecklist] = useState<any | null>(null);
  const [loading, setLoading] = useState(false);
  const [selectedCategory, setSelectedCategory] = useState<string>('ALL');
  const [activeTab, setActiveTab] = useState<'clauses' | 'risks' | 'obligations' | 'missing' | 'checklist'>('clauses');

  useEffect(() => {
    listDocuments()
      .then((docs) => {
        setDocuments(docs);
        if (!selectedDocId && docs.length > 0) {
          setSelectedDocId(docs[0].id);
        }
      })
      .catch(() => {});
  }, []);

  useEffect(() => {
    if (selectedDocId) {
      loadAnalysis(selectedDocId);
    }
  }, [selectedDocId]);

  const loadAnalysis = async (id: number) => {
    try {
      setLoading(true);
      try {
        const cached = await getDocumentAnalysis(id);
        setAnalysis(cached);
      } catch {
        const fresh = await analyzeDocument(id);
        setAnalysis(fresh);
      }

      try {
        const chk = await getDocumentChecklist(id);
        setChecklist(chk);
      } catch {
        // ignore checklist failure
      }
    } catch (err: any) {
      alert(err.message || 'Failed to load analysis');
    } finally {
      setLoading(false);
    }
  };

  const categories = analysis
    ? ['ALL', ...Array.from(new Set(analysis.clauses.map((c) => c.category)))]
    : ['ALL'];

  const filteredClauses = analysis
    ? selectedCategory === 'ALL'
      ? analysis.clauses
      : analysis.clauses.filter((c) => c.category === selectedCategory)
    : [];

  return (
    <div className="space-y-8">
      {/* Top Bar: Title and Document Selector */}
      <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4 border-b border-slate-800 pb-4">
        <div>
          <h1 className="text-2xl sm:text-3xl font-bold text-white flex items-center gap-2.5">
            <Scale className="w-7 h-7 text-amber-400" aria-hidden="true" />
            <span>{t.nav.analyze}</span>
          </h1>
          <p className="text-xs sm:text-sm text-slate-400 mt-1">
            {lang === 'hi'
              ? 'अनुबंध की शर्तों की सरल भाषा में समीक्षा, जोखिमों की पहचान और नागरिक सुझाव।'
              : 'Plain language legal clause extraction, red flag detection, and citizen action tips.'}
          </p>
        </div>

        {/* Document Selector */}
        {documents.length > 0 && (
          <div className="flex items-center gap-2 w-full md:w-auto">
            <label htmlFor="doc-select" className="text-xs text-slate-400 whitespace-nowrap">
              {lang === 'hi' ? 'दस्तावेज़ चुनें:' : 'Select Contract:'}
            </label>
            <select
              id="doc-select"
              value={selectedDocId || ''}
              onChange={(e) => setSelectedDocId(parseInt(e.target.value, 10))}
              className="bg-slate-900 border border-slate-700 rounded-lg px-3 py-1.5 text-xs text-white focus-visible:ring-2"
            >
              {documents.map((d) => (
                <option key={d.id} value={d.id}>
                  {d.title} ({d.file_type.toUpperCase()})
                </option>
              ))}
            </select>
          </div>
        )}
      </div>

      {loading ? (
        <div className="text-center py-20 space-y-3">
          <div className="w-12 h-12 border-4 border-amber-500/20 border-t-amber-500 rounded-full animate-spin mx-auto"></div>
          <p className="text-sm text-slate-300 font-medium">
            {lang === 'hi'
              ? 'दस्तावेज़ का विश्लेषण हो रहा है (शर्तें, जोखिम और कानूनी सारांश)...'
              : 'Analyzing contract structure, extracting clauses, and detecting risks...'}
          </p>
        </div>
      ) : !analysis ? (
        <div className="glass-panel p-12 text-center max-w-md mx-auto space-y-3">
          <FileText className="w-12 h-12 text-slate-500 mx-auto" />
          <h2 className="text-base font-bold text-white">
            {lang === 'hi' ? 'विश्लेषण के लिए कोई दस्तावेज़ नहीं चुना गया' : 'No Document Selected'}
          </h2>
          <p className="text-xs text-slate-400">
            {lang === 'hi'
              ? 'कृपया डैशबोर्ड से दस्तावेज़ चुनें या नया दस्तावेज़ अपलोड करें।'
              : 'Please choose a document from the dropdown above or upload one from the dashboard.'}
          </p>
          <Link
            href="/dashboard"
            className="inline-block px-4 py-2 rounded-lg bg-amber-500 text-slate-950 text-xs font-semibold"
          >
            {t.actions.upload_doc}
          </Link>
        </div>
      ) : (
        <div className="space-y-8">
          {/* Executive Summaries */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
            {/* Citizen Summary */}
            <div className="glass-panel p-5 space-y-2 lg:col-span-2">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-amber-400 uppercase tracking-wider flex items-center gap-1.5">
                  <BookOpen className="w-4 h-4" />
                  <span>{t.sections.summary_citizen}</span>
                </span>
                <span className="text-[11px] font-mono bg-slate-900 text-slate-400 px-2 py-0.5 rounded border border-slate-800">
                  Readability: {analysis.flesch_kincaid_score.toFixed(1)} / 100
                </span>
              </div>
              <p className="text-sm text-slate-200 leading-relaxed pt-1">{analysis.summary_citizen}</p>

              {/* Hindi Summary */}
              <div className="mt-4 pt-3 border-t border-slate-800 space-y-1 bg-amber-950/20 p-3 rounded-lg border border-amber-500/20">
                <span className="text-xs font-semibold text-amber-300 block">
                  {t.sections.summary_hindi}
                </span>
                <p className="text-sm text-amber-100/90 leading-relaxed font-sans">{analysis.summary_hindi}</p>
              </div>
            </div>

            {/* Quick Metrics & Links */}
            <div className="glass-panel p-5 space-y-4 flex flex-col justify-between">
              <div className="space-y-3">
                <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider block">
                  {lang === 'hi' ? 'दस्तावेज़ सांख्यिकी' : 'Analysis Metrics'}
                </span>
                <div className="grid grid-cols-2 gap-3 text-center">
                  <div className="bg-slate-900/80 p-2.5 rounded-lg border border-slate-800">
                    <span className="text-2xl font-bold text-white block">{analysis.clauses.length}</span>
                    <span className="text-[11px] text-slate-400">{lang === 'hi' ? 'पहचानी गई शर्तें' : 'Clauses'}</span>
                  </div>
                  <div className="bg-red-950/40 p-2.5 rounded-lg border border-red-500/30">
                    <span className="text-2xl font-bold text-red-300 block">{analysis.risks.length}</span>
                    <span className="text-[11px] text-red-200">{lang === 'hi' ? 'रेड फ्लैग' : 'Red Flags'}</span>
                  </div>
                  <div className="bg-slate-900/80 p-2.5 rounded-lg border border-slate-800">
                    <span className="text-2xl font-bold text-blue-300 block">{analysis.obligations.length}</span>
                    <span className="text-[11px] text-slate-400">{lang === 'hi' ? 'जिम्मेदारियां' : 'Obligations'}</span>
                  </div>
                  <div className="bg-amber-950/40 p-2.5 rounded-lg border border-amber-500/30">
                    <span className="text-2xl font-bold text-amber-300 block">{analysis.missing_clauses.length}</span>
                    <span className="text-[11px] text-amber-200">{lang === 'hi' ? 'अनुपस्थित सुरक्षा' : 'Missing Safe'}</span>
                  </div>
                </div>
              </div>

              {/* Action Jump to Grounded QA / Brief */}
              <div className="pt-2 border-t border-slate-800 flex flex-col gap-2">
                <Link
                  href={`/qa?docId=${analysis.document_id}`}
                  className="w-full py-2 px-3 rounded-lg bg-slate-900 hover:bg-slate-800 border border-slate-700 text-xs font-semibold text-white flex items-center justify-between transition"
                >
                  <span>{lang === 'hi' ? 'इस दस्तावेज़ पर सवाल पूछें' : 'Ask Grounded Questions'}</span>
                  <HelpCircle className="w-3.5 h-3.5 text-amber-400" />
                </Link>
                <Link
                  href={`/brief?docId=${analysis.document_id}`}
                  className="w-full py-2 px-3 rounded-lg bg-amber-500 hover:bg-amber-400 text-slate-950 text-xs font-bold flex items-center justify-between transition"
                >
                  <span>{lang === 'hi' ? 'अधिवक्ता परामर्श ब्रीफ बनाएं' : 'Generate Lawyer Brief'}</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </Link>
              </div>
            </div>
          </div>

          {/* Navigation Tabs */}
          <div className="flex border-b border-slate-800 gap-2 overflow-x-auto text-xs font-semibold">
            <button
              type="button"
              onClick={() => setActiveTab('clauses')}
              className={`pb-3 px-3 transition cursor-pointer border-b-2 ${
                activeTab === 'clauses'
                  ? 'border-amber-400 text-amber-400 font-bold'
                  : 'border-transparent text-slate-400 hover:text-white'
              }`}
            >
              {t.sections.extracted_clauses} ({analysis.clauses.length})
            </button>
            <button
              type="button"
              onClick={() => setActiveTab('risks')}
              className={`pb-3 px-3 transition cursor-pointer border-b-2 flex items-center gap-1.5 ${
                activeTab === 'risks'
                  ? 'border-red-400 text-red-300 font-bold'
                  : 'border-transparent text-slate-400 hover:text-white'
              }`}
            >
              <AlertTriangle className="w-3.5 h-3.5 text-red-400" />
              <span>{t.sections.red_flags} ({analysis.risks.length})</span>
            </button>
            <button
              type="button"
              onClick={() => setActiveTab('obligations')}
              className={`pb-3 px-3 transition cursor-pointer border-b-2 ${
                activeTab === 'obligations'
                  ? 'border-blue-400 text-blue-300 font-bold'
                  : 'border-transparent text-slate-400 hover:text-white'
              }`}
            >
              {t.sections.obligations} ({analysis.obligations.length})
            </button>
            <button
              type="button"
              onClick={() => setActiveTab('missing')}
              className={`pb-3 px-3 transition cursor-pointer border-b-2 ${
                activeTab === 'missing'
                  ? 'border-purple-400 text-purple-300 font-bold'
                  : 'border-transparent text-slate-400 hover:text-white'
              }`}
            >
              {t.sections.missing_clauses} ({analysis.missing_clauses.length})
            </button>
            <button
              type="button"
              onClick={() => setActiveTab('checklist')}
              className={`pb-3 px-3 transition cursor-pointer border-b-2 flex items-center gap-1.5 ${
                activeTab === 'checklist'
                  ? 'border-emerald-400 text-emerald-300 font-bold'
                  : 'border-transparent text-slate-400 hover:text-white'
              }`}
            >
              <ListChecks className="w-3.5 h-3.5 text-emerald-400" />
              <span>{lang === 'hi' ? 'नागरिक चेकलिस्ट' : 'Action Checklist'}</span>
            </button>
          </div>

          {/* TAB 1: Clauses Breakdown */}
          {activeTab === 'clauses' && (
            <div className="space-y-4">
              {/* Category Filter */}
              <div className="flex items-center gap-2 overflow-x-auto pb-2 text-xs">
                <Filter className="w-3.5 h-3.5 text-slate-400 shrink-0" />
                {categories.map((cat) => (
                  <button
                    key={cat}
                    type="button"
                    onClick={() => setSelectedCategory(cat)}
                    className={`px-3 py-1 rounded-full whitespace-nowrap transition cursor-pointer border ${
                      selectedCategory === cat
                        ? 'bg-amber-500 text-slate-950 font-bold border-amber-500'
                        : 'bg-slate-900 text-slate-300 hover:bg-slate-800 border-slate-700'
                    }`}
                  >
                    {cat}
                  </button>
                ))}
              </div>

              <div className="grid grid-cols-1 gap-4">
                {filteredClauses.map((c) => (
                  <ClauseCard key={c.clause_id} clause={c} lang={lang} />
                ))}
              </div>
            </div>
          )}

          {/* TAB 2: Red Flags & Risks */}
          {activeTab === 'risks' && (
            <div className="space-y-4">
              {analysis.risks.length === 0 ? (
                <div className="glass-panel p-8 text-center text-slate-400 text-sm">
                  {lang === 'hi' ? 'कोई गंभीर जोखिम नहीं पाया गया।' : 'No severe red flags detected.'}
                </div>
              ) : (
                analysis.risks.map((r) => (
                  <div
                    key={r.risk_id}
                    className="glass-panel p-5 border-l-4 border-l-red-500 space-y-3"
                  >
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <div className="flex items-center gap-2">
                        <AlertOctagon className="w-4 h-4 text-red-400 shrink-0" />
                        <span className="font-bold text-white text-base">{r.title}</span>
                      </div>
                      <RiskPill severity={r.severity} lang={lang} />
                    </div>

                    <p className="text-xs sm:text-sm text-slate-200 leading-relaxed">{r.description}</p>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs pt-1">
                      <div className="bg-slate-900/60 p-2.5 rounded-lg border border-slate-800">
                        <span className="text-slate-400 font-semibold block mb-0.5">
                          {lang === 'hi' ? 'अनुबंध संदर्भ:' : 'Contract Reference:'}
                        </span>
                        <span className="text-slate-300 font-mono">{r.clause_reference}</span>
                      </div>

                      <div className="bg-amber-950/40 p-2.5 rounded-lg border border-amber-500/30 text-amber-200">
                        <span className="text-amber-300 font-semibold block mb-0.5">
                          {lang === 'hi' ? 'नागरिक सुरक्षा उपाय (Countermeasure):' : 'Suggested Countermeasure:'}
                        </span>
                        <span>{r.countermeasure}</span>
                      </div>
                    </div>
                  </div>
                ))
              )}
            </div>
          )}

          {/* TAB 3: Obligations Matrix */}
          {activeTab === 'obligations' && (
            <div className="space-y-4">
              <div className="overflow-x-auto rounded-xl border border-slate-800">
                <table className="w-full text-left text-xs">
                  <thead className="bg-slate-900 text-slate-400 uppercase tracking-wider">
                    <tr>
                      <th className="p-3.5">{lang === 'hi' ? 'पक्ष' : 'Responsible Party'}</th>
                      <th className="p-3.5">{lang === 'hi' ? 'आवश्यक कार्य' : 'Mandated Action'}</th>
                      <th className="p-3.5">{lang === 'hi' ? 'समय-सीमा / आवृत्ति' : 'Deadline / Frequency'}</th>
                      <th className="p-3.5">{lang === 'hi' ? 'उल्लंघन पर दंड' : 'Penalty for Breach'}</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800 bg-slate-950/60">
                    {analysis.obligations.map((o) => (
                      <tr key={o.obligation_id} className="hover:bg-slate-900/50 transition">
                        <td className="p-3.5 font-bold text-amber-400 whitespace-nowrap">{o.responsible_party}</td>
                        <td className="p-3.5 text-slate-200">{o.action}</td>
                        <td className="p-3.5 text-slate-300 font-mono whitespace-nowrap flex items-center gap-1.5">
                          <Clock className="w-3.5 h-3.5 text-slate-400" />
                          <span>{o.deadline_or_frequency}</span>
                        </td>
                        <td className="p-3.5 text-red-300 font-mono">{o.penalty_for_breach}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* TAB 4: Missing Clauses */}
          {activeTab === 'missing' && (
            <div className="space-y-4">
              {analysis.missing_clauses.length === 0 ? (
                <div className="glass-panel p-8 text-center text-slate-400 text-sm">
                  {lang === 'hi' ? 'सभी मानक सुरक्षा शर्तें मौजूद हैं।' : 'All standard statutory protections present.'}
                </div>
              ) : (
                analysis.missing_clauses.map((m, idx) => (
                  <div key={idx} className="glass-panel p-5 space-y-3 border-l-4 border-l-amber-500">
                    <div className="flex items-center justify-between gap-2">
                      <h3 className="font-bold text-white text-base">{m.clause_name}</h3>
                      <span className="text-[11px] font-bold px-2 py-0.5 rounded bg-amber-950/80 text-amber-300 border border-amber-500/30">
                        {m.importance}
                      </span>
                    </div>

                    <p className="text-xs sm:text-sm text-slate-300 leading-relaxed">{m.why_needed}</p>

                    <div className="bg-slate-900 p-3 rounded-lg border border-slate-800 text-xs">
                      <span className="text-amber-400 font-semibold block mb-1">
                        {lang === 'hi' ? 'अनुशंसित भाषा (शामिल करने के लिए):' : 'Suggested Language to Include:'}
                      </span>
                      <p className="font-mono text-slate-300 italic">"{m.suggested_language}"</p>
                    </div>

                    <div className="text-xs text-red-300 flex items-start gap-1.5">
                      <AlertTriangle className="w-3.5 h-3.5 text-red-400 shrink-0 mt-0.5" />
                      <span>
                        <strong>{lang === 'hi' ? 'अनुपस्थित रहने पर जोखिम: ' : 'Risk if Missing: '}</strong>
                        {m.risk_if_missing}
                      </span>
                    </div>
                  </div>
                ))
              )}
            </div>
          )}

          {/* TAB 5: Actionable Checklist */}
          {activeTab === 'checklist' && (
            <div className="space-y-4">
              {checklist && (
                <div className="glass-panel p-6 space-y-4">
                  <div className="border-b border-slate-800 pb-3">
                    <h3 className="text-lg font-bold text-white flex items-center gap-2">
                      <ListChecks className="w-5 h-5 text-emerald-400" />
                      <span>{checklist.title}</span>
                    </h3>
                    <p className="text-xs text-slate-400 mt-0.5">{checklist.jurisdiction}</p>
                  </div>

                  <div className="space-y-3">
                    {checklist.items?.map((item: any) => (
                      <label
                        key={item.id}
                        className="flex items-start gap-3 p-3 rounded-lg bg-slate-900/60 border border-slate-800 hover:border-slate-700 transition cursor-pointer"
                      >
                        <input
                          type="checkbox"
                          className="w-4 h-4 mt-1 rounded border-slate-700 text-amber-500 focus:ring-amber-400"
                        />
                        <div className="space-y-0.5">
                          <div className="flex items-center gap-2">
                            <span className="text-sm font-semibold text-white">{item.title}</span>
                            <span className="text-[10px] px-1.5 py-0.5 rounded font-mono bg-slate-800 text-slate-400">
                              {item.importance}
                            </span>
                          </div>
                          <p className="text-xs text-slate-300 leading-relaxed">{item.description}</p>
                        </div>
                      </label>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default function AnalyzePage() {
  return (
    <Suspense fallback={<div className="p-8 text-center text-slate-400">Loading analysis...</div>}>
      <AnalyzeContent />
    </Suspense>
  );
}
