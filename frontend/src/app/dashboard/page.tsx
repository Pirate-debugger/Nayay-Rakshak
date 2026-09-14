'use client';

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import {
  ArrowRight,
  FileCheck2,
  FileDiff,
  FileText,
  HelpCircle,
  Plus,
  Scale,
  Shield,
  ShieldCheck,
  Trash2,
} from 'lucide-react';
import FileUploader from '@/components/FileUploader';
import { useLanguage } from '@/components/AppShell';
import { deleteDocument, listDocuments, loadSampleDocument } from '@/lib/api';
import { DocumentMeta } from '@/lib/types';

export default function DashboardPage() {
  const { lang, t } = useLanguage();
  const router = useRouter();
  const [documents, setDocuments] = useState<DocumentMeta[]>([]);
  const [loading, setLoading] = useState(true);
  const [showUploader, setShowUploader] = useState(false);
  const [sampleLoading, setSampleLoading] = useState(false);

  const fetchDocs = async () => {
    try {
      setLoading(true);
      const docs = await listDocuments();
      setDocuments(docs);
    } catch {
      // If unauthorized or error, empty list is fine for demo
      setDocuments([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDocs();
  }, []);

  const handleDelete = async (id: number) => {
    if (confirm(lang === 'hi' ? 'क्या आप इस दस्तावेज़ को हटाना चाहते हैं?' : 'Are you sure you want to delete this document?')) {
      try {
        await deleteDocument(id);
        setDocuments(documents.filter((d) => d.id !== id));
      } catch (err: any) {
        alert(err.message || 'Failed to delete');
      }
    }
  };

  const handleSampleLoad = async (sampleKey: string) => {
    try {
      setSampleLoading(true);
      const doc = await loadSampleDocument(sampleKey);
      setDocuments([doc, ...documents]);
      setShowUploader(false);
      router.push(`/analyze?docId=${doc.id}`);
    } catch (err: any) {
      alert(err.message || 'Failed to load sample');
    } finally {
      setSampleLoading(false);
    }
  };

  return (
    <div className="space-y-8">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 border-b border-slate-800 pb-4">
        <div>
          <h1 className="text-2xl sm:text-3xl font-bold text-white flex items-center gap-2.5">
            <FileText className="w-7 h-7 text-amber-400" aria-hidden="true" />
            <span>{t.nav.dashboard}</span>
          </h1>
          <p className="text-xs sm:text-sm text-slate-400 mt-1">
            {lang === 'hi'
              ? 'अपलोड किए गए कानूनी अनुबंध और उनकी सुरक्षा समीक्षा स्थिति।'
              : 'Your uploaded legal contracts and their security analysis status.'}
          </p>
        </div>

        <button
          type="button"
          onClick={() => setShowUploader(!showUploader)}
          className="px-4 py-2.5 rounded-xl bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold text-xs sm:text-sm flex items-center gap-2 shadow-md transition cursor-pointer"
        >
          <Plus className="w-4 h-4" />
          <span>{t.actions.upload_doc}</span>
        </button>
      </div>

      {/* Upload Drawer / Modal */}
      {showUploader && (
        <div className="glass-panel p-6 border-amber-500/30 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-base font-bold text-white">
              {lang === 'hi' ? 'नया कानूनी दस्तावेज़ अपलोड करें' : 'Upload Legal Document for Analysis'}
            </h2>
            <button
              type="button"
              onClick={() => setShowUploader(false)}
              className="text-xs text-slate-400 hover:text-white"
            >
              {t.actions.close}
            </button>
          </div>

          <FileUploader
            onSuccess={(doc) => {
              setDocuments([doc, ...documents]);
              setShowUploader(false);
              router.push(`/analyze?docId=${doc.id}`);
            }}
            lang={lang}
          />

          <div className="pt-2 border-t border-slate-800">
            <p className="text-xs text-slate-400 mb-2">
              {lang === 'hi' ? 'या तुरंत परीक्षण के लिए एक उदाहरण दस्तावेज़ लोड करें:' : 'Or test immediately with an Indian sample document:'}
            </p>
            <div className="flex flex-wrap gap-2">
              <button
                type="button"
                disabled={sampleLoading}
                onClick={() => handleSampleLoad('standard_residential_lease_delhi')}
                className="px-3 py-1.5 rounded-lg bg-slate-900 hover:bg-slate-800 border border-slate-700 text-xs text-slate-200"
              >
                Standard Lease (Delhi)
              </button>
              <button
                type="button"
                disabled={sampleLoading}
                onClick={() => handleSampleLoad('harsh_landlord_lease_delhi')}
                className="px-3 py-1.5 rounded-lg bg-red-950/40 hover:bg-red-900/50 border border-red-500/30 text-xs text-red-200"
              >
                Harsh Landlord Lease (Red Flags)
              </button>
              <button
                type="button"
                disabled={sampleLoading}
                onClick={() => handleSampleLoad('employment_agreement_tech_bangalore')}
                className="px-3 py-1.5 rounded-lg bg-slate-900 hover:bg-slate-800 border border-slate-700 text-xs text-slate-200"
              >
                Tech Employment Agreement
              </button>
              <button
                type="button"
                disabled={sampleLoading}
                onClick={() => handleSampleLoad('consumer_services_contract')}
                className="px-3 py-1.5 rounded-lg bg-slate-900 hover:bg-slate-800 border border-slate-700 text-xs text-slate-200"
              >
                Consumer Services Terms
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Documents List */}
      {loading ? (
        <div className="text-center py-12 text-slate-400 text-sm">
          {lang === 'hi' ? 'दस्तावेज़ लोड हो रहे हैं...' : 'Loading your documents...'}
        </div>
      ) : documents.length === 0 ? (
        <div className="glass-panel p-12 text-center max-w-lg mx-auto space-y-4">
          <div className="w-14 h-14 rounded-2xl bg-amber-500/10 border border-amber-500/30 flex items-center justify-center text-amber-400 mx-auto">
            <FileText className="w-7 h-7" />
          </div>
          <h2 className="text-lg font-bold text-white">
            {lang === 'hi' ? 'कोई दस्तावेज़ उपलब्ध नहीं है' : 'No Documents Uploaded Yet'}
          </h2>
          <p className="text-xs text-slate-400 leading-relaxed">
            {lang === 'hi'
              ? 'अपना किराया अनुबंध या नौकरी का समझौता अपलोड करें, या त्वरित परीक्षण के लिए नीचे दिए गए बटन से एक उदाहरण लोड करें।'
              : 'Upload your residential lease, employment agreement, or consumer contract, or load a realistic sample to test the platform.'}
          </p>
          <div className="pt-2 flex flex-col sm:flex-row items-center justify-center gap-3">
            <button
              type="button"
              onClick={() => handleSampleLoad('harsh_landlord_lease_delhi')}
              className="px-4 py-2 rounded-xl bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold text-xs shadow-md cursor-pointer"
            >
              {lang === 'hi' ? 'कठोर लीज़ उदाहरण लोड करें' : 'Load Harsh Lease Sample'}
            </button>
            <button
              type="button"
              onClick={() => setShowUploader(true)}
              className="px-4 py-2 rounded-xl bg-slate-900 hover:bg-slate-800 border border-slate-700 text-white font-medium text-xs cursor-pointer"
            >
              {t.actions.upload_doc}
            </button>
          </div>
        </div>
      ) : (
        <div className="space-y-4">
          <div className="grid grid-cols-1 gap-4">
            {documents.map((doc) => (
              <div
                key={doc.id}
                className="glass-panel p-5 hover:border-slate-700 transition flex flex-col lg:flex-row items-start lg:items-center justify-between gap-4"
              >
                <div className="space-y-1.5">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-mono uppercase bg-slate-800 text-amber-400 px-2 py-0.5 rounded">
                      {doc.file_type}
                    </span>
                    <span className="text-xs text-slate-400">
                      {doc.page_count} {doc.page_count === 1 ? 'Page' : 'Pages'} • {(doc.file_size / 1024).toFixed(1)} KB
                    </span>
                    {doc.status && doc.status !== 'READY' ? (
                      <span className={`inline-flex items-center gap-1 text-[11px] px-2 py-0.5 rounded-full font-mono font-medium ${
                        doc.status === 'FAILED' ? 'text-red-400 bg-red-950/60 border border-red-500/30' : 'text-amber-400 bg-amber-950/60 border border-amber-500/30 animate-pulse'
                      }`}>
                        {doc.status}
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1 text-[11px] text-emerald-400 bg-emerald-950/60 border border-emerald-500/30 px-2 py-0.5 rounded-full font-mono font-medium">
                        READY
                      </span>
                    )}
                    {doc.pii_redacted && (
                      <span className="inline-flex items-center gap-1 text-[11px] text-emerald-400 bg-emerald-950/60 border border-emerald-500/30 px-2 py-0.5 rounded-full">
                        <ShieldCheck className="w-3 h-3" />
                        <span>PII Masked</span>
                      </span>
                    )}
                  </div>
                  <h3 className="text-base font-bold text-white">{doc.title}</h3>
                  <p className="text-xs text-slate-400 font-mono">{doc.filename}</p>
                </div>

                {/* Action Buttons */}
                <div className="flex flex-wrap items-center gap-2 pt-2 lg:pt-0 w-full lg:w-auto">
                  <Link
                    href={`/analyze?docId=${doc.id}`}
                    className="px-3 py-1.5 rounded-lg bg-amber-500 hover:bg-amber-400 text-slate-950 font-semibold text-xs flex items-center gap-1.5 transition"
                  >
                    <Scale className="w-3.5 h-3.5" />
                    <span>{lang === 'hi' ? 'विश्लेषण' : 'Analyze Clauses'}</span>
                  </Link>

                  <Link
                    href={`/qa?docId=${doc.id}`}
                    className="px-3 py-1.5 rounded-lg bg-slate-900 hover:bg-slate-800 border border-slate-700 text-slate-200 hover:text-white text-xs flex items-center gap-1.5 transition"
                  >
                    <HelpCircle className="w-3.5 h-3.5 text-blue-400" />
                    <span>{lang === 'hi' ? 'सवाल पूछें' : 'Grounded Q&A'}</span>
                  </Link>

                  <Link
                    href={`/verify?docId=${doc.id}`}
                    className="px-3 py-1.5 rounded-lg bg-slate-900 hover:bg-slate-800 border border-slate-700 text-slate-200 hover:text-white text-xs flex items-center gap-1.5 transition"
                  >
                    <FileCheck2 className="w-3.5 h-3.5 text-emerald-400" />
                    <span>{lang === 'hi' ? 'दावा जांच' : 'Verify Claims'}</span>
                  </Link>

                  <Link
                    href={`/brief?docId=${doc.id}`}
                    className="px-3 py-1.5 rounded-lg bg-slate-900 hover:bg-slate-800 border border-slate-700 text-slate-200 hover:text-white text-xs flex items-center gap-1.5 transition"
                  >
                    <Shield className="w-3.5 h-3.5 text-amber-400" />
                    <span>{lang === 'hi' ? 'वकील ब्रीफ' : 'Brief'}</span>
                  </Link>

                  <button
                    type="button"
                    onClick={() => handleDelete(doc.id)}
                    className="p-1.5 rounded-lg text-slate-500 hover:text-red-400 hover:bg-red-950/40 transition cursor-pointer ml-auto lg:ml-0"
                    title="Delete document"
                    aria-label="Delete document"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
