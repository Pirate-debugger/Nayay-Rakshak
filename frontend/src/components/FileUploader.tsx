'use client';

import React, { useRef, useState } from 'react';
import { AlertCircle, FileUp, ShieldCheck } from 'lucide-react';
import { uploadDocument } from '@/lib/api';
import { DocumentMeta } from '@/lib/types';
import { Language } from '@/lib/i18n';

interface Props {
  onSuccess: (doc: DocumentMeta) => void;
  lang?: Language;
}

export default function FileUploader({ onSuccess, lang = 'en' }: Props) {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [dragOver, setDragOver] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [redactPii, setRedactPii] = useState(true);

  const handleFile = async (file: File) => {
    setError(null);
    const validExts = ['.pdf', '.docx', '.txt', '.png', '.jpg', '.jpeg'];
    const ext = '.' + file.name.split('.').pop()?.toLowerCase();

    if (!validExts.includes(ext)) {
      setError(
        lang === 'hi'
          ? 'अस्वीकृत फ़ाइल प्रारूप। कृपया केवल PDF, DOCX, TXT, या स्कैन की गई PNG/JPG फ़ाइल अपलोड करें।'
          : 'Invalid file format. Please upload PDF, DOCX, TXT, or scanned PNG/JPG documents only.'
      );
      return;
    }

    if (file.size > 15 * 1024 * 1024) {
      setError(
        lang === 'hi'
          ? 'फ़ाइल का आकार 15 MB से कम होना चाहिए।'
          : 'File size exceeds 15 MB maximum limit.'
      );
      return;
    }

    try {
      setUploading(true);
      const doc = await uploadDocument(file, undefined, redactPii);
      onSuccess(doc);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Upload failed. Please try again.';
      setError(message);
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="space-y-4">
      {/* Drag and drop zone */}
      <div
        onDragOver={(e) => {
          e.preventDefault();
          setDragOver(true);
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragOver(false);
          if (e.dataTransfer.files?.[0]) {
            handleFile(e.dataTransfer.files[0]);
          }
        }}
        onClick={() => fileInputRef.current?.click()}
        className={`border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition flex flex-col items-center justify-center ${
          dragOver
            ? 'border-amber-400 bg-amber-500/10'
            : 'border-slate-700 bg-slate-900/40 hover:border-slate-500 hover:bg-slate-900/70'
        }`}
        role="button"
        tabIndex={0}
        aria-label="Upload legal document"
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            fileInputRef.current?.click();
          }
        }}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf,.docx,.txt,.png,.jpg,.jpeg"
          className="hidden"
          onChange={(e) => {
            if (e.target.files?.[0]) {
              handleFile(e.target.files[0]);
            }
          }}
        />

        <div className="w-14 h-14 rounded-2xl bg-amber-500/10 border border-amber-500/30 flex items-center justify-center text-amber-400 mb-4">
          <FileUp className="w-7 h-7" aria-hidden="true" />
        </div>

        <h3 className="text-base font-semibold text-white mb-1">
          {uploading
            ? (lang === 'hi' ? 'दस्तावेज़ सत्यापित एवं अपलोड हो रहा है...' : 'Verifying and uploading document...')
            : (lang === 'hi' ? 'दस्तावेज़ यहाँ खींचें या ब्राउज़ करें' : 'Drag & drop your document here or browse')}
        </h3>

        <p className="text-xs text-slate-400 max-w-sm mb-2">
          {lang === 'hi'
            ? 'समर्थित प्रारूप: PDF, Word (DOCX), TXT, स्कैन की गई छवियां (अधिकतम 15 MB)'
            : 'Supported formats: PDF, Word (.docx), Text (.txt), Scanned images (.png/.jpg) up to 15 MB'}
        </p>

        <span className="text-[11px] text-amber-400 font-medium bg-amber-950/60 px-2.5 py-0.5 rounded-full border border-amber-500/30">
          {lang === 'hi' ? 'सुरक्षित सैंडबॉक्स सत्यापन' : 'Safe Sandbox & Magic Byte Validation'}
        </span>
      </div>

      {/* PII Privacy Toggle */}
      <div className="flex items-center justify-between p-3 rounded-lg bg-slate-900/70 border border-slate-800 text-xs">
        <div className="flex items-center gap-2">
          <ShieldCheck className="w-4 h-4 text-emerald-400" aria-hidden="true" />
          <div>
            <span className="font-semibold text-white block">
              {lang === 'hi' ? 'गोपनीयता शील्ड (PII रेडैक्शन)' : 'Privacy Shield (Auto PII Redaction)'}
            </span>
            <span className="text-slate-400 text-[11px]">
              {lang === 'hi'
                ? 'आधार, पैन, फोन, ईमेल और बैंक विवरण को सुरक्षित रूप से छुपाता है'
                : 'Masks Aadhaar, PAN, phone numbers, and bank details before processing'}
            </span>
          </div>
        </div>

        <label className="relative inline-flex items-center cursor-pointer">
          <input
            type="checkbox"
            checked={redactPii}
            onChange={(e) => setRedactPii(e.target.checked)}
            className="sr-only peer"
          />
          <div className="w-9 h-5 bg-slate-700 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-slate-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-amber-500"></div>
        </label>
      </div>

      {/* Error display */}
      {error && (
        <div
          role="alert"
          className="flex items-center gap-2 p-3 rounded-lg bg-red-950/70 border border-red-500/50 text-red-200 text-xs"
        >
          <AlertCircle className="w-4 h-4 text-red-400 shrink-0" aria-hidden="true" />
          <span>{error}</span>
        </div>
      )}
    </div>
  );
}
