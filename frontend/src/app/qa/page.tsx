'use client';

import React, { Suspense, useEffect, useState } from 'react';
import { useSearchParams } from 'next/navigation';
import {
  AlertCircle,
  BookOpen,
  HelpCircle,
  Lock,
  Quote,
  Send,
  ShieldCheck,
} from 'lucide-react';
import { useLanguage } from '@/components/AppShell';
import { askQuestion, listDocuments } from '@/lib/api';
import { DocumentMeta, QAResponse } from '@/lib/types';

function QAContent() {
  const { lang, t } = useLanguage();
  const searchParams = useSearchParams();
  const docIdParam = searchParams.get('docId');

  const [documents, setDocuments] = useState<DocumentMeta[]>([]);
  const [selectedDocId, setSelectedDocId] = useState<number | null>(docIdParam ? parseInt(docIdParam, 10) : null);
  const [question, setQuestion] = useState('');
  const [loading, setLoading] = useState(false);
  const [response, setResponse] = useState<QAResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listDocuments()
      .then((docs) => {
        setDocuments(docs);
        if (!selectedDocId && docs.length > 0) {
          setSelectedDocId(docs[0].id);
        }
      })
      .catch(() => {});
  }, [selectedDocId]);

  const handleAsk = async (qText?: string) => {
    const q = qText || question;
    if (!q.trim() || !selectedDocId) return;

    try {
      setLoading(true);
      setError(null);
      const res = await askQuestion(selectedDocId, q.trim());
      setResponse(res);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Failed to get answer';
      setError(message);
    } finally {
      setLoading(false);
    }
  };

  const sampleQuestions = [
    {
      q: 'What is the notice period for terminating the lease agreement?',
      label: lang === 'hi' ? 'अनुबंध समाप्त करने का नोटिस पीरियड क्या है?' : 'Notice Period for Termination',
    },
    {
      q: 'What is the penalty or interest rate if rent payment is delayed?',
      label: lang === 'hi' ? 'किराया देर से देने पर क्या जुर्माना है?' : 'Late Rent Penalty / Interest',
    },
    {
      q: 'When and under what conditions is the security deposit refunded?',
      label: lang === 'hi' ? 'जमानत राशि (डिपॉजिट) कब वापस होगी?' : 'Security Deposit Refund Timeline',
    },
    {
      q: 'Does this contract provide employee equity or stock option grants?',
      label: lang === 'hi' ? 'स्टॉक ऑप्शंस (अनुपस्थित जानकारी का परीक्षण)' : 'Stock Options (Test Absent Data Handling)',
    },
  ];

  return (
    <div className="space-y-8 max-w-4xl mx-auto">
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 border-b border-slate-800 pb-4">
        <div>
          <h1 className="text-2xl sm:text-3xl font-bold text-white flex items-center gap-2.5">
            <HelpCircle className="w-7 h-7 text-amber-400" aria-hidden="true" />
            <span>{t.nav.qa}</span>
          </h1>
          <p className="text-xs sm:text-sm text-slate-400 mt-1">
            {lang === 'hi'
              ? 'अपलोड किए गए दस्तावेज़ से सीधे सवाल पूछें। हर उत्तर पृष्ठ संख्या और मूल उद्धरण के साथ प्रमाणित होगा।'
              : 'Grounded document inquiry. Every answer includes verifiable page and quote citations.'}
          </p>
        </div>

        {/* Contract Selector */}
        {documents.length > 0 && (
          <div className="w-full sm:w-auto">
            <select
              value={selectedDocId || ''}
              onChange={(e) => setSelectedDocId(parseInt(e.target.value, 10))}
              className="w-full sm:w-auto bg-slate-900 border border-slate-700 rounded-lg px-3 py-1.5 text-xs text-white focus-visible:ring-2"
            >
              {documents.map((d) => (
                <option key={d.id} value={d.id}>
                  {d.title}
                </option>
              ))}
            </select>
          </div>
        )}
      </div>

      {/* Suggested Questions */}
      <div className="space-y-2">
        <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider block">
          {lang === 'hi' ? 'सुझाए गए नागरिक प्रश्न:' : 'Suggested Citizen Questions:'}
        </span>
        <div className="flex flex-wrap gap-2">
          {sampleQuestions.map((sq, idx) => (
            <button
              key={idx}
              type="button"
              onClick={() => {
                setQuestion(sq.q);
                handleAsk(sq.q);
              }}
              className="px-3 py-1.5 rounded-lg bg-slate-900 hover:bg-slate-800 border border-slate-700 hover:border-amber-500/40 text-xs text-slate-300 transition cursor-pointer text-left"
            >
              {sq.label}
            </button>
          ))}
        </div>
      </div>

      {/* Question Input Form */}
      <form
        onSubmit={(e) => {
          e.preventDefault();
          handleAsk();
        }}
        className="glass-panel p-4 space-y-3"
      >
        <div className="relative">
          <textarea
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder={
              lang === 'hi'
                ? 'दस्तावेज़ के बारे में अपना प्रश्न लिखें... (जैसे: क्या मकान मालिक कभी भी घर में घुस सकता है?)'
                : 'Ask a grounded question about this contract... (e.g. Can the landlord enter without prior notice?)'
            }
            rows={3}
            className="w-full bg-slate-950/80 border border-slate-700 rounded-xl p-3 text-sm text-white placeholder-slate-500 focus-visible:ring-2 focus-visible:border-transparent resize-none"
          />
        </div>

        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 pt-1 text-xs">
          <div className="flex items-center gap-2 text-emerald-400">
            <Lock className="w-3.5 h-3.5" />
            <span>Prompt Injection Defense Active • Zero System Instruction Override</span>
          </div>

          <button
            type="submit"
            disabled={!question.trim() || !selectedDocId || loading}
            className="px-5 py-2 rounded-xl bg-amber-500 hover:bg-amber-400 disabled:opacity-50 text-slate-950 font-bold text-xs flex items-center gap-2 transition cursor-pointer shadow-md ml-auto sm:ml-0"
          >
            {loading ? (
              <span>{lang === 'hi' ? 'खोज जारी है...' : 'Verifying text...'}</span>
            ) : (
              <>
                <span>{lang === 'hi' ? 'जवाब प्राप्त करें' : 'Get Verified Answer'}</span>
                <Send className="w-3.5 h-3.5" />
              </>
            )}
          </button>
        </div>
      </form>

      {/* Error Alert */}
      {error && (
        <div role="alert" className="p-4 rounded-xl bg-red-950/80 border border-red-500 text-red-200 text-xs flex items-center gap-2">
          <AlertCircle className="w-4 h-4 shrink-0 text-red-400" />
          <span>{error}</span>
        </div>
      )}

      {/* Response Display */}
      {response && (
        <div
          role="region"
          aria-live="polite"
          aria-label="Verified answer response"
          className="glass-panel p-6 space-y-4 border-l-4 border-l-amber-500"
        >
          <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-800 pb-3">
            <h3 className="text-base font-bold text-white flex items-center gap-2">
              <BookOpen className="w-4 h-4 text-amber-400" />
              <span>{lang === 'hi' ? 'प्रमाणित उत्तर' : 'Evidence-Grounded Answer'}</span>
            </h3>

            <span
              className={`px-3 py-1 rounded-full text-xs font-semibold border ${
                response.is_found_in_document
                  ? 'bg-emerald-950 text-emerald-300 border-emerald-500/40'
                  : 'bg-slate-900 text-slate-400 border-slate-700'
              }`}
            >
              {response.is_found_in_document
                ? (lang === 'hi' ? 'दस्तावेज़ में मौजूद' : 'Found in Document')
                : (lang === 'hi' ? 'दस्तावेज़ में अनुपस्थित' : 'Absent from Document')}
            </span>
          </div>

          <div className="text-sm text-slate-100 leading-relaxed bg-slate-900/60 p-4 rounded-xl border border-slate-800">
            {response.answer}
          </div>

          {/* Grounded Citations Drawer */}
          {response.citations.length > 0 ? (
            <div className="space-y-3 pt-2">
              <span className="text-xs font-semibold text-amber-400 uppercase tracking-wider block">
                {t.sections.citations}
              </span>

              <div className="space-y-2">
                {response.citations.map((cit, idx) => (
                  <div key={idx} className="bg-slate-950/80 p-3.5 rounded-xl border border-slate-800 space-y-2">
                    <div className="flex items-center justify-between text-xs text-slate-400">
                      <span className="font-semibold text-slate-300 flex items-center gap-1.5">
                        <Quote className="w-3.5 h-3.5 text-amber-400" />
                        <span>{cit.section_title}</span>
                      </span>
                      <span className="font-mono bg-slate-900 px-2 py-0.5 rounded border border-slate-800">
                        Page {cit.page_number}
                      </span>
                    </div>

                    <p className="text-xs text-slate-300 font-mono italic leading-relaxed bg-slate-900/50 p-2.5 rounded border-l-2 border-l-amber-500">
                      &ldquo;{cit.verbatim_quote}&rdquo;
                    </p>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <div className="p-3.5 rounded-lg bg-amber-950/30 border border-amber-500/20 text-xs text-amber-200 flex items-start gap-2">
              <ShieldCheck className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
              <span>
                <strong>{lang === 'hi' ? 'हैलुसिनेशन सुरक्षा: ' : 'Anti-Hallucination Guard: '}</strong>
                {lang === 'hi'
                  ? 'दस्तावेज़ में इस विषय पर कोई प्रत्यक्ष धारा नहीं मिली। सिस्टम बिना साक्ष्य के गलत उत्तर नहीं बनाता।'
                  : 'No verified clause regarding this was found in the text. The system never invents missing legal facts.'}
              </span>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default function QAPage() {
  return (
    <Suspense fallback={<div className="p-8 text-center text-slate-400">Loading Q&A...</div>}>
      <QAContent />
    </Suspense>
  );
}
