'use client';

import React, { Suspense, useEffect, useState } from 'react';
import { useSearchParams } from 'next/navigation';
import {
  AlertTriangle,
  ArrowRight,
  CheckCircle2,
  FileCheck2,
  FileText,
  HelpCircle,
  Plus,
  Scale,
  ShieldAlert,
  Trash2,
} from 'lucide-react';
import VerificationBadge from '@/components/VerificationBadge';
import { useLanguage } from '@/components/AppShell';
import { listDocuments, verifyClaims } from '@/lib/api';
import { DocumentMeta, VerificationBatchResponse } from '@/lib/types';

function VerifyContent() {
  const { lang, t } = useLanguage();
  const searchParams = useSearchParams();
  const docIdParam = searchParams.get('docId');

  const [documents, setDocuments] = useState<DocumentMeta[]>([]);
  const [selectedDocId, setSelectedDocId] = useState<number | null>(docIdParam ? parseInt(docIdParam, 10) : null);
  const [claimsList, setClaimsList] = useState<string[]>([
    'The monthly rent payable is Thirty-Five Thousand Indian Rupees.',
    'The tenant is strictly forbidden from terminating the agreement at any point.',
    'The employer grants employee 500 stock options vesting after 1 year.',
    'Cheating is punishable under Section 318 of Bharatiya Nyaya Sanhita (BNS).',
    'Post-employment non-compete agreements are void under Section 27 of the Indian Contract Act.',
  ]);
  const [newClaim, setNewClaim] = useState('');
  const [batchResult, setBatchResult] = useState<VerificationBatchResponse | null>(null);
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

  const handleRunVerification = async () => {
    if (claimsList.length === 0) return;

    try {
      setLoading(true);
      const res = await verifyClaims(claimsList, selectedDocId || undefined);
      setBatchResult(res);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Verification failed';
      alert(message);
    } finally {
      setLoading(false);
    }
  };

  const handleAddClaim = () => {
    if (!newClaim.trim()) return;
    setClaimsList([...claimsList, newClaim.trim()]);
    setNewClaim('');
  };

  const handleRemoveClaim = (index: number) => {
    setClaimsList(claimsList.filter((_, i) => i !== index));
  };

  return (
    <div className="space-y-8 max-w-5xl mx-auto">
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 border-b border-slate-800 pb-4">
        <div>
          <h1 className="text-2xl sm:text-3xl font-bold text-white flex items-center gap-2.5">
            <FileCheck2 className="w-7 h-7 text-amber-400" aria-hidden="true" />
            <span>{t.nav.verify}</span>
          </h1>
          <p className="text-xs sm:text-sm text-slate-400 mt-1">
            {lang === 'hi'
              ? 'दस्तावेज़ और भारतीय कानूनों से कानूनी और तथ्यात्मक दावों का 5-स्तरीय साक्ष्य सत्यापन।'
              : 'Multi-evidence grounding engine classifying claims across 5 strict verification states.'}
          </p>
        </div>

        {/* Contract Selector */}
        {documents.length > 0 && (
          <div className="w-full sm:w-auto flex items-center gap-2">
            <label htmlFor="verify-doc-select" className="text-xs text-slate-400 whitespace-nowrap">
              {lang === 'hi' ? 'दस्तावेज़:' : 'Context Document:'}
            </label>
            <select
              id="verify-doc-select"
              value={selectedDocId || ''}
              onChange={(e) => setSelectedDocId(e.target.value ? parseInt(e.target.value, 10) : null)}
              className="bg-slate-900 border border-slate-700 rounded-lg px-3 py-1.5 text-xs text-white focus-visible:ring-2"
            >
              <option value="">-- General Statutory Law Only --</option>
              {documents.map((d) => (
                <option key={d.id} value={d.id}>
                  {d.title}
                </option>
              ))}
            </select>
          </div>
        )}
      </div>

      {/* Claims Input Workbench */}
      <div className="glass-panel p-6 space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-semibold text-white uppercase tracking-wider">
            {lang === 'hi' ? 'जांच के लिए दावे (Claims to Verify)' : 'Claims Workbench'}
          </h2>
          <span className="text-xs text-slate-400">{claimsList.length} claims ready</span>
        </div>

        {/* Add Claim Bar */}
        <div className="flex gap-2">
          <input
            type="text"
            value={newClaim}
            onChange={(e) => setNewClaim(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') {
                e.preventDefault();
                handleAddClaim();
              }
            }}
            placeholder={
              lang === 'hi'
                ? 'नया दावा दर्ज करें... (उदा. किराया 1 तारीख को देय है)'
                : 'Enter a claim to verify... (e.g. Deposit must be refunded within 14 days)'
            }
            className="flex-1 bg-slate-950/80 border border-slate-700 rounded-xl px-3.5 py-2 text-xs sm:text-sm text-white focus-visible:ring-2"
          />
          <button
            type="button"
            onClick={handleAddClaim}
            className="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-white font-medium text-xs flex items-center gap-1.5 transition cursor-pointer"
          >
            <Plus className="w-4 h-4" />
            <span>{lang === 'hi' ? 'जोड़ें' : 'Add'}</span>
          </button>
        </div>

        {/* Claims List Table */}
        <div className="space-y-2 max-h-60 overflow-y-auto pr-1">
          {claimsList.map((claim, idx) => (
            <div
              key={idx}
              className="flex items-center justify-between p-2.5 rounded-lg bg-slate-900/60 border border-slate-800 text-xs text-slate-200"
            >
              <div className="flex items-center gap-2.5">
                <span className="font-mono text-slate-500 w-6">#{idx + 1}</span>
                <span>{claim}</span>
              </div>
              <button
                type="button"
                onClick={() => handleRemoveClaim(idx)}
                className="text-slate-500 hover:text-red-400 p-1"
                aria-label="Remove claim"
              >
                <Trash2 className="w-3.5 h-3.5" />
              </button>
            </div>
          ))}
        </div>

        {/* Verify Trigger Button */}
        <div className="pt-2 flex justify-end">
          <button
            type="button"
            onClick={handleRunVerification}
            disabled={loading || claimsList.length === 0}
            className="px-6 py-2.5 rounded-xl bg-gradient-to-r from-amber-500 to-amber-600 hover:from-amber-400 hover:to-amber-500 disabled:opacity-50 text-slate-950 font-bold text-xs sm:text-sm flex items-center gap-2 shadow-md transition cursor-pointer"
          >
            {loading ? (
              <span>{lang === 'hi' ? 'सत्यापन जारी है...' : 'Verifying Claims...'}</span>
            ) : (
              <>
                <span>{lang === 'hi' ? 'सभी दावों का सत्यापन करें' : 'Verify All Claims'}</span>
                <ArrowRight className="w-4 h-4" />
              </>
            )}
          </button>
        </div>
      </div>

      {/* Batch Results View */}
      {batchResult && (
        <div className="space-y-6">
          {/* Summary Verdict Bar */}
          <div className="glass-panel p-4 border-l-4 border-l-amber-500 flex flex-wrap items-center justify-between gap-3 text-xs sm:text-sm">
            <span className="font-semibold text-white">{batchResult.summary_verdict}</span>
            <span className="text-xs text-slate-400 font-mono">
              Evaluated: {batchResult.total_claims} Claims
            </span>
          </div>

          {/* Individual Verified Claim Cards */}
          <div className="grid grid-cols-1 gap-4">
            {batchResult.results.map((item) => (
              <div
                key={item.claim_id}
                className="glass-panel p-5 space-y-3 hover:border-slate-700 transition"
              >
                <div className="flex flex-wrap items-start justify-between gap-2 border-b border-slate-800 pb-3">
                  <div className="space-y-1">
                    <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-400">
                      {item.claim_id}
                    </span>
                    <h3 className="text-base font-bold text-white mt-1">"{item.claim_text}"</h3>
                  </div>

                  <VerificationBadge
                    status={item.verification_status}
                    confidence={item.confidence_strength}
                    lang={lang}
                  />
                </div>

                {/* Evidence Metadata */}
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs">
                  <div className="bg-slate-900/60 p-2.5 rounded-lg border border-slate-800">
                    <span className="text-slate-400 font-semibold block mb-0.5">Evidence Source:</span>
                    <span className="text-slate-200">{item.evidence_source}</span>
                  </div>

                  <div className="bg-slate-900/60 p-2.5 rounded-lg border border-slate-800">
                    <span className="text-slate-400 font-semibold block mb-0.5">Source Authority:</span>
                    <span className="text-slate-200">{item.source_authority}</span>
                  </div>

                  <div className="bg-slate-900/60 p-2.5 rounded-lg border border-slate-800">
                    <span className="text-slate-400 font-semibold block mb-0.5">Version / Date:</span>
                    <span className="text-slate-200">{item.source_date_or_version || 'Current'}</span>
                  </div>
                </div>

                {/* Evidence Snippet */}
                {item.evidence_snippet && (
                  <div className="bg-slate-950/80 p-3 rounded-lg border border-slate-800 text-xs space-y-1">
                    <span className="text-amber-400 font-semibold block">Grounded Evidence Excerpt:</span>
                    <p className="text-slate-300 font-mono italic">"{item.evidence_snippet}"</p>
                  </div>
                )}

                {/* Reasoning */}
                <div className="text-xs text-slate-300 flex items-start gap-1.5 pt-1">
                  <span className="font-semibold text-white shrink-0">Verification Finding:</span>
                  <span>{item.reasoning}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

export default function VerifyPage() {
  return (
    <Suspense fallback={<div className="p-8 text-center text-slate-400">Loading claim verification...</div>}>
      <VerifyContent />
    </Suspense>
  );
}
