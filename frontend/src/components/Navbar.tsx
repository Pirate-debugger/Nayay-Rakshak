'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  BookOpen,
  Compass,
  FileCheck2,
  FileDiff,
  FileText,
  HelpCircle,
  Menu,
  Scale,
  Shield,
  X,
} from 'lucide-react';
import LanguageToggle from './LanguageToggle';
import SimpleModeToggle from './SimpleModeToggle';
import { Language, translations } from '@/lib/i18n';

interface Props {
  lang: Language;
  onLanguageChange: (lang: Language) => void;
  simpleMode?: boolean;
  onSimpleModeChange?: (val: boolean) => void;
}

export default function Navbar({
  lang,
  onLanguageChange,
  simpleMode = false,
  onSimpleModeChange = () => {},
}: Props) {
  const pathname = usePathname();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const t = translations[lang];

  const navLinks = [
    { href: '/dashboard', label: t.nav.dashboard, icon: FileText },
    { href: '/analyze', label: t.nav.analyze, icon: Scale },
    { href: '/compare', label: t.nav.compare, icon: FileDiff },
    { href: '/qa', label: t.nav.qa, icon: HelpCircle },
    { href: '/verify', label: t.nav.verify, icon: FileCheck2 },
    { href: '/action-navigator', label: t.nav.action_navigator, icon: Compass },
    { href: '/brief', label: t.nav.brief, icon: Shield },
    { href: '/legal-aid', label: t.nav.legal_aid, icon: Scale },
    { href: '/glossary', label: t.nav.glossary, icon: BookOpen },
  ];

  return (
    <header className="sticky top-0 z-40 bg-slate-950/90 backdrop-blur-md border-b border-slate-800">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Brand Logo */}
          <Link
            href="/"
            className="flex items-center gap-3 text-amber-400 hover:text-amber-300 transition group focus-visible:ring-2"
          >
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-amber-500 to-amber-700 flex items-center justify-center text-slate-950 shadow-md shadow-amber-500/20 group-hover:scale-105 transition">
              <Scale className="w-6 h-6 stroke-[2.2]" aria-hidden="true" />
            </div>
            <div>
              <span className="text-lg font-black tracking-wider text-white block leading-none">
                NYAYA <span className="text-amber-400">RAKSHAK</span>
              </span>
              <span className="text-[10px] text-slate-400 font-medium tracking-tight block mt-0.5">
                {lang === 'hi' ? 'कानूनी स्पष्टता व साक्ष्य सत्यापन' : 'Legal Clarity & Verification'}
              </span>
            </div>
          </Link>

          {/* Desktop Navigation Links */}
          <nav aria-label="Main Navigation" className="hidden lg:flex items-center gap-1">
            {navLinks.map((item) => {
              const Icon = item.icon;
              const isActive = pathname === item.href || pathname?.startsWith(`${item.href}/`);
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition ${
                    isActive
                      ? 'bg-amber-500/10 text-amber-400 border border-amber-500/30'
                      : 'text-slate-300 hover:text-white hover:bg-slate-900'
                  }`}
                  aria-current={isActive ? 'page' : undefined}
                >
                  <Icon className="w-3.5 h-3.5" aria-hidden="true" />
                  <span>{item.label}</span>
                </Link>
              );
            })}
          </nav>

          {/* Right Action: Simple Mode, Language Toggle & Mobile Hamburger */}
          <div className="flex items-center gap-2 sm:gap-3">
            <SimpleModeToggle
              simpleMode={simpleMode}
              onSimpleModeChange={onSimpleModeChange}
              lang={lang}
            />
            <LanguageToggle currentLang={lang} onLanguageChange={onLanguageChange} />

            <button
              type="button"
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="lg:hidden p-2 rounded-lg text-slate-400 hover:text-white hover:bg-slate-900 focus-visible:ring-2"
              aria-expanded={mobileMenuOpen}
              aria-label="Toggle navigation menu"
            >
              {mobileMenuOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
            </button>
          </div>
        </div>
      </div>

      {/* Mobile Drawer Menu */}
      {mobileMenuOpen && (
        <nav aria-label="Mobile Navigation" className="lg:hidden bg-slate-950 border-b border-slate-800 px-4 pt-2 pb-4 space-y-1">
          {navLinks.map((item) => {
            const Icon = item.icon;
            const isActive = pathname === item.href;
            return (
              <Link
                key={item.href}
                href={item.href}
                onClick={() => setMobileMenuOpen(false)}
                className={`flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium ${
                  isActive
                    ? 'bg-amber-500/15 text-amber-400 border border-amber-500/30 font-semibold'
                    : 'text-slate-300 hover:text-white hover:bg-slate-900'
                }`}
                aria-current={isActive ? 'page' : undefined}
              >
                <Icon className="w-4 h-4" aria-hidden="true" />
                <span>{item.label}</span>
              </Link>
            );
          })}
        </nav>
      )}
    </header>
  );
}
