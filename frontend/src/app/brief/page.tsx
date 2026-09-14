'use client';

import React, { Suspense, useEffect, useState } from 'react';
import { useSearchParams } from 'next/navigation';
import {
  ArrowRight,
  Download,
  FileText,
  Printer,
  Scale,
  Shield,
  ShieldCheck,
  UserCheck,
} from 'lucide-react';
import { useLanguage } from '@/components/AppShell';
import { createBrief, getExportBriefUrl, listDocuments } from '@/lib/api';
import { BriefResponse, DocumentMeta } from '@/lib/types';

function BriefContent() {
  const { lang, t } = useLanguage();
  const searchParams = useSearchParams();
  const docIdParam = searchParams.get('docId');

  const [documents, setDocuments] = useState<DocumentMeta[]>([]);
  const [selectedDocId, setSelectedDocId] = useState<number | null>(docIdParam ? parseInt(docIdParam, 10) : null);
  const [clientName, setClientName] = useState('Ananya Iyer');
  const [customQuestion, setCustomQuestion] = useState('');
  const [questions, setQuestions] = useState<string[]>([
    'Are the late rent interest terms of 18% p.a. legally enforceable?',
    'Can the landlord retain my security deposit for 90 days after vacating?',
  ]);
  const [brief, setBrief] = useState<BriefResponse | null>(null);
  const [loading, setLoading] = useState(false);

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

  const handleGenerate = async () => {
    if (!selectedDocId || !clientName.trim()) return;

    try {
      setLoading(true);
      const res = await createBrief(selectedDocId, clientName.trim(), questions);
      setBrief(res);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Failed to generate brief';
      alert(message);
    } finally {
      setLoading(false);
    }
  };

  const handleAddQuestion = () => {
    if (!customQuestion.trim()) return;
    setQuestions([...questions, customQuestion.trim()]);
    setCustomQuestion('');
  };

  return (
    <div className="space-y-8 max-w-4xl mx-auto">
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 border-b border-slate-800 pb-4">
        <div>
          <h1 className="text-2xl sm:text-3xl font-bold text-white flex items-center gap-2.5">
            <Shield className="w-7 h-7 text-amber-400" aria-hidden="true" />
            <span>{t.nav.brief}</span>
          </h1>
          <p className="text-xs sm:text-sm text-slate-400 mt-1">
            {lang === 'hi'
              ? 'अधिवक्ता से परामर्श से पूर्व अपने दस्तावेज़ का संरचित सारांश और महत्वपूर्ण प्रश्नों की सूची तैयार करें।'
              : 'Prepare a structured briefing memo with red flags and targeted questions before consulting a lawyer.'}
          </p>
        </div>

        {brief && (
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => window.print()}
              className="px-3 py-1.5 rounded-lg bg-slate-900 hover:bg-slate-800 border border-slate-700 text-xs text-slate-200 flex items-center gap-1.5 transition cursor-pointer"
            >
              <Printer className="w-3.5 h-3.5" />
              <span>{lang === 'hi' ? 'प्रिंट करें' : 'Print / PDF'}</span>
            </button>
            <a
              href={getExportBriefUrl(brief.id)}
              download
              className="px-3.5 py-1.5 rounded-lg bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold text-xs flex items-center gap-1.5 transition"
            >
              <Download className="w-3.5 h-3.5" />
              <span>{lang === 'hi' ? 'डाउनलोड (.md)' : 'Download Brief'}</span>
            </a>
          </div>
        )}
      </div>

      {/* Brief Configuration Card */}
      <div className="glass-panel p-6 space-y-4">
        <h2 className="text-sm font-semibold text-white uppercase tracking-wider">
          {lang === 'hi' ? 'परामर्श ब्रीफ विवरण' : 'Brief Configuration'}
        </h2>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="space-y-1.5">
            <label htmlFor="brief-doc-select" className="text-xs text-slate-400 font-medium">
              {lang === 'hi' ? 'दस्तावेज़ चुनें:' : 'Select Document:'}
            </label>
            <select
              id="brief-doc-select"
              value={selectedDocId || ''}
              onChange={(e) => setSelectedDocId(parseInt(e.target.value, 10))}
              className="w-full bg-slate-900 border border-slate-700 rounded-lg p-2.5 text-xs text-white focus-visible:ring-2"
            >
              {documents.map((d) => (
                <option key={d.id} value={d.id}>
                  {d.title}
                </option>
              ))}
            </select>
          </div>

          <div className="space-y-1.5">
            <label htmlFor="client-name" className="text-xs text-slate-400 font-medium">
              {lang === 'hi' ? 'नागरिक / मुवक्किल का नाम:' : 'Citizen / Client Full Name:'}
            </label>
            <input
              id="client-name"
              type="text"
              value={clientName}
              onChange={(e) => setClientName(e.target.value)}
              className="w-full bg-slate-900 border border-slate-700 rounded-lg p-2.5 text-xs text-white focus-visible:ring-2"
            />
          </div>
        </div>

        {/* Custom Questions for Lawyer */}
        <div className="space-y-2 pt-2">
          <label className="text-xs text-slate-400 font-medium block">
            {lang === 'hi' ? 'वकील से पूछे जाने वाले विशिष्ट प्रश्न:' : 'Specific Questions to Ask Your Advocate:'}
          </label>
          <div className="flex gap-2">
            <input
              type="text"
              value={customQuestion}
              onChange={(e) => setCustomQuestion(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') {
                  e.preventDefault();
                  handleAddQuestion();
                }
              }}
              placeholder="Add question for advocate..."
              className="flex-1 bg-slate-950/80 border border-slate-700 rounded-lg px-3 py-1.5 text-xs text-white"
            />
            <button
              type="button"
              onClick={handleAddQuestion}
              className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-xs text-white"
            >
              {lang === 'hi' ? 'प्रश्न जोड़ें' : 'Add'}
            </button>
          </div>

          <ul className="space-y-1 text-xs text-slate-300">
            {questions.map((q, idx) => (
              <li key={idx} className="flex items-center justify-between p-2 rounded bg-slate-900/40 border border-slate-800">
                <span>{q}</span>
                <button
                  type="button"
                  onClick={() => setQuestions(questions.filter((_, i) => i !== idx))}
                  className="text-slate-500 hover:text-red-400 text-xs ml-2"
                >
                  ✕
                </button>
              </li>
            ))}
          </ul>
        </div>

        <div className="pt-2 flex justify-end">
          <button
            type="button"
            onClick={handleGenerate}
            disabled={!selectedDocId || !clientName.trim() || loading}
            className="px-5 py-2.5 rounded-xl bg-amber-500 hover:bg-amber-400 disabled:opacity-50 text-slate-950 font-bold text-xs flex items-center gap-2 shadow-md transition cursor-pointer"
          >
            {loading ? (
              <span>{lang === 'hi' ? 'ब्रीफ तैयार हो रहा है...' : 'Generating Brief...'}</span>
            ) : (
              <>
                <span>{t.actions.generate_brief}</span>
                <ArrowRight className="w-4 h-4" />
              </>
            )}
          </button>
        </div>
      </div>

      {/* Generated Brief Viewer */}
      {brief && (
        <article className="glass-panel p-8 space-y-6 border border-slate-700 bg-slate-950/95 font-sans leading-relaxed">
          <div className="border-b border-slate-800 pb-4 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Scale className="w-8 h-8 text-amber-400" />
              <div>
                <h2 className="text-xl font-bold text-white tracking-wide">
                  CITIZEN LEGAL CONSULTATION BRIEF
                </h2>
                <p className="text-xs text-slate-400">
                  Prepared for: <strong className="text-amber-300">{brief.client_name}</strong> • Document ID: #{brief.document_id}
                </p>
              </div>
            </div>
            <span className="text-[11px] px-2.5 py-1 rounded bg-amber-950/80 text-amber-300 border border-amber-500/40 font-mono">
              PRE-CONSULTATION READY
            </span>
          </div>

          <div className="prose prose-invert max-w-none text-xs sm:text-sm text-slate-200 whitespace-pre-wrap font-mono leading-relaxed bg-slate-900/40 p-6 rounded-xl border border-slate-800/80">
            {brief.brief_markdown}
          </div>
        </article>
      )}
    </div>
  );
}

export default function BriefPage() {
  return (
    <Suspense fallback={<div className="p-8 text-center text-slate-400">Loading brief generator...</div>}>
      <BriefContent />
    </Suspense>
  );
}
