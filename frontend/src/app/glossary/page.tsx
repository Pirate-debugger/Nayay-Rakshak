'use client';

import React, { useEffect, useState } from 'react';
import { BookOpen, Filter, Search, Sparkles } from 'lucide-react';
import { useLanguage } from '@/components/AppShell';
import { getGlossary } from '@/lib/api';
import { GlossaryEntry } from '@/lib/types';

export default function GlossaryPage() {
  const { lang, t } = useLanguage();
  const [terms, setTerms] = useState<GlossaryEntry[]>([]);
  const [search, setSearch] = useState('');
  const [category, setCategory] = useState('ALL');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchGlossary();
  }, [search]);

  const fetchGlossary = async () => {
    try {
      setLoading(true);
      const res = await getGlossary(search || undefined);
      setTerms(res);
    } catch {
      setTerms([]);
    } finally {
      setLoading(false);
    }
  };

  const categories = ['ALL', ...Array.from(new Set(terms.map((t) => t.category)))];

  const filtered = category === 'ALL' ? terms : terms.filter((item) => item.category === category);

  return (
    <div className="space-y-8 max-w-5xl mx-auto">
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 border-b border-slate-800 pb-4">
        <div>
          <h1 className="text-2xl sm:text-3xl font-bold text-white flex items-center gap-2.5">
            <BookOpen className="w-7 h-7 text-amber-400" aria-hidden="true" />
            <span>{t.nav.glossary}</span>
          </h1>
          <p className="text-xs sm:text-sm text-slate-400 mt-1">
            {lang === 'hi'
              ? 'भारतीय एवं आंग्ल-भारतीय कानूनी शब्दों, लैटिन सूत्रों एवं अनुबंध की शर्तों का सरल अंग्रेजी व हिंदी अर्थ।'
              : 'Anglo-Indian legal terms, Latin maxims, and contractual jargon explained in plain English & conversational Hindi.'}
          </p>
        </div>
      </div>

      {/* Search and Category Filter Bar */}
      <div className="glass-panel p-4 space-y-3">
        <div className="flex flex-col sm:flex-row items-center gap-3">
          <div className="relative flex-1 w-full">
            <Search className="w-4 h-4 text-slate-500 absolute left-3.5 top-3" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder={
                lang === 'hi'
                  ? 'शब्द खोजें... (जैसे Indemnity, हर्जाना, Jurisdiction, Arbitration, Non-Compete)'
                  : 'Search legal term in English or Hindi... (e.g. Indemnity, Caveat Emptor, Sub-Judice)'
              }
              className="w-full bg-slate-950/80 border border-slate-700 rounded-xl pl-10 pr-4 py-2.5 text-xs sm:text-sm text-white focus-visible:ring-2"
            />
          </div>

          <div className="flex items-center gap-2 w-full sm:w-auto overflow-x-auto pb-1 sm:pb-0">
            <Filter className="w-3.5 h-3.5 text-slate-400 shrink-0" />
            <select
              value={category}
              onChange={(e) => setCategory(e.target.value)}
              className="bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-xs text-white"
            >
              {categories.map((c) => (
                <option key={c} value={c}>
                  {c}
                </option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {/* Glossary Cards Grid */}
      {loading ? (
        <div className="text-center py-12 text-slate-400 text-sm">Loading legal terms dictionary...</div>
      ) : filtered.length === 0 ? (
        <div className="glass-panel p-12 text-center text-slate-400 text-sm">
          {lang === 'hi' ? 'कोई मेल खाता शब्द नहीं मिला।' : 'No matching legal terms found.'}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {filtered.map((item, idx) => (
            <div
              key={idx}
              className="glass-panel p-5 space-y-3 hover:border-slate-700 transition flex flex-col justify-between"
            >
              <div className="space-y-2">
                <div className="flex items-center justify-between gap-2 border-b border-slate-800 pb-2">
                  <div>
                    <h2 className="text-lg font-bold text-white tracking-wide">{item.term}</h2>
                    <span className="text-xs text-amber-400 font-medium">
                      {item.hindi_term} • <span className="italic font-sans text-slate-400">{item.transliteration}</span>
                    </span>
                  </div>
                  <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-300">
                    {item.category}
                  </span>
                </div>

                {/* Plain English */}
                <div className="text-xs space-y-1">
                  <span className="text-slate-400 font-semibold block">Plain English Meaning:</span>
                  <p className="text-slate-200 leading-relaxed">{item.plain_english}</p>
                </div>

                {/* Plain Hindi */}
                <div className="text-xs space-y-1 bg-amber-950/20 p-2.5 rounded-lg border border-amber-500/20">
                  <span className="text-amber-300 font-semibold block">साधारण हिंदी में अर्थ:</span>
                  <p className="text-amber-100 leading-relaxed font-sans">{item.plain_hindi}</p>
                </div>

                {/* Practical Example */}
                <div className="text-xs text-slate-400 italic bg-slate-900/60 p-2.5 rounded-lg border border-slate-800">
                  <strong className="text-slate-300 not-italic">Example in Practice: </strong>
                  <span>{item.example}</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
