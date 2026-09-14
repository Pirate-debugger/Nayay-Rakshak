'use client';

import React, { createContext, useContext, useEffect, useState } from 'react';
import Link from 'next/link';
import { ExternalLink, Heart, Scale } from 'lucide-react';
import Navbar from './Navbar';
import LegalDisclaimer from './LegalDisclaimer';
import SkipLink from './SkipLink';
import { Language, translations } from '@/lib/i18n';

interface LanguageContextType {
  lang: Language;
  setLang: (lang: Language) => void;
  simpleMode: boolean;
  setSimpleMode: (val: boolean) => void;
  t: (typeof translations)['en'];
}

const LanguageContext = createContext<LanguageContextType>({
  lang: 'en',
  setLang: () => {},
  simpleMode: false,
  setSimpleMode: () => {},
  t: translations['en'],
});

export const useLanguage = () => useContext(LanguageContext);

export default function AppShell({ children }: { children: React.ReactNode }) {
  const [lang, setLangState] = useState<Language>('en');
  const [simpleMode, setSimpleModeState] = useState<boolean>(false);

  useEffect(() => {
    try {
      const saved = localStorage.getItem('nyaya_lang') as Language;
      const savedMode = localStorage.getItem('nyaya_simple_mode');
      if (saved === 'en' || saved === 'hi' || savedMode !== null) {
        queueMicrotask(() => {
          if (saved === 'en' || saved === 'hi') {
            setLangState(saved);
          }
          if (savedMode !== null) {
            setSimpleModeState(savedMode === 'true');
          }
        });
      }
    } catch {
      // ignore storage access errors
    }
  }, []);

  const handleLanguageChange = (newLang: Language) => {
    setLangState(newLang);
    localStorage.setItem('nyaya_lang', newLang);
  };

  const handleSimpleModeChange = (val: boolean) => {
    setSimpleModeState(val);
    localStorage.setItem('nyaya_simple_mode', String(val));
  };

  const t = translations[lang];

  return (
    <LanguageContext.Provider value={{ lang, setLang: handleLanguageChange, simpleMode, setSimpleMode: handleSimpleModeChange, t }}>
      <div className="min-h-screen flex flex-col bg-[#070b12] text-slate-100">
        <SkipLink />
        <LegalDisclaimer lang={lang} />
        <Navbar
          lang={lang}
          onLanguageChange={handleLanguageChange}
          simpleMode={simpleMode}
          onSimpleModeChange={handleSimpleModeChange}
        />

        <main id="main-content" className="flex-1 w-full max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          {children}
        </main>

        <footer className="border-t border-slate-800/80 bg-slate-950/80 mt-16 py-8 text-xs text-slate-400">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="grid grid-cols-1 md:grid-cols-4 gap-8 mb-8">
              {/* Brand & Principles */}
              <div className="space-y-3 md:col-span-2">
                <div className="flex items-center gap-2 text-amber-400">
                  <Scale className="w-5 h-5" aria-hidden="true" />
                  <span className="font-bold text-white text-base tracking-wider">NYAYA RAKSHAK</span>
                </div>
                <p className="text-slate-300 max-w-md leading-relaxed">
                  {t.principle}
                </p>
                <div className="inline-block px-3 py-1 rounded bg-slate-900 border border-slate-800 text-[11px] text-amber-400">
                  {t.jurisdiction} • English & हिन्दी
                </div>
              </div>

              {/* Official Citizen Portals */}
              <div className="space-y-2">
                <h4 className="font-semibold text-white tracking-wide uppercase text-[11px]">
                  {lang === 'hi' ? 'शासकीय कानूनी पोर्टल' : 'Official Legal Portals'}
                </h4>
                <ul className="space-y-1.5">
                  <li>
                    <a
                      href="https://nalsa.gov.in"
                      target="_blank"
                      rel="noopener noreferrer"
                      className="hover:text-amber-400 transition flex items-center gap-1"
                    >
                      <span>NALSA Free Legal Aid (15100)</span>
                      <ExternalLink className="w-3 h-3" />
                    </a>
                  </li>
                  <li>
                    <a
                      href="https://consumerhelpline.gov.in"
                      target="_blank"
                      rel="noopener noreferrer"
                      className="hover:text-amber-400 transition flex items-center gap-1"
                    >
                      <span>National Consumer Helpline (1915)</span>
                      <ExternalLink className="w-3 h-3" />
                    </a>
                  </li>
                  <li>
                    <a
                      href="https://edaakhil.nic.in"
                      target="_blank"
                      rel="noopener noreferrer"
                      className="hover:text-amber-400 transition flex items-center gap-1"
                    >
                      <span>e-Daakhil Consumer E-Filing</span>
                      <ExternalLink className="w-3 h-3" />
                    </a>
                  </li>
                  <li>
                    <a
                      href="https://cybercrime.gov.in"
                      target="_blank"
                      rel="noopener noreferrer"
                      className="hover:text-amber-400 transition flex items-center gap-1"
                    >
                      <span>Cyber Crime Reporting (1930)</span>
                      <ExternalLink className="w-3 h-3" />
                    </a>
                  </li>
                </ul>
              </div>

              {/* Navigation quick links */}
              <div className="space-y-2">
                <h4 className="font-semibold text-white tracking-wide uppercase text-[11px]">
                  {lang === 'hi' ? 'त्वरित लिंक' : 'Quick Navigation'}
                </h4>
                <ul className="space-y-1.5">
                  <li>
                    <Link href="/analyze" className="hover:text-amber-400 transition">
                      {t.nav.analyze}
                    </Link>
                  </li>
                  <li>
                    <Link href="/compare" className="hover:text-amber-400 transition">
                      {t.nav.compare}
                    </Link>
                  </li>
                  <li>
                    <Link href="/verify" className="hover:text-amber-400 transition">
                      {t.nav.verify}
                    </Link>
                  </li>
                  <li>
                    <Link href="/legal-aid" className="hover:text-amber-400 transition">
                      {t.nav.legal_aid}
                    </Link>
                  </li>
                  <li>
                    <Link href="/glossary" className="hover:text-amber-400 transition">
                      {t.nav.glossary}
                    </Link>
                  </li>
                </ul>
              </div>
            </div>

            <div className="pt-6 border-t border-slate-900 flex flex-col sm:flex-row items-center justify-between gap-4">
              <p className="text-slate-500 text-[11px]">
                © 2026 Nyaya Rakshak. Built for India-first citizen legal empowerment. WCAG 2.2 AA Compliant.
              </p>
              <p className="text-slate-500 text-[11px] flex items-center gap-1">
                <span>Made with</span>
                <Heart className="w-3 h-3 text-red-500 fill-current" />
                <span>for Citizen Justice</span>
              </p>
            </div>
          </div>
        </footer>
      </div>
    </LanguageContext.Provider>
  );
}
