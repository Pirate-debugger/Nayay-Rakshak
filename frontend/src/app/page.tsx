'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import {
  AlertTriangle,
  ArrowRight,
  BookOpen,
  CheckCircle2,
  FileCheck2,
  FileDiff,
  FileText,
  HelpCircle,
  Lock,
  Scale,
  Shield,
  ShieldAlert,
  Sparkles,
  Users,
} from 'lucide-react';
import { useLanguage } from '@/components/AppShell';
import { loadSampleDocument } from '@/lib/api';

export default function HomePage() {
  const { lang, t } = useLanguage();
  const router = useRouter();
  const [loadingSample, setLoadingSample] = useState<string | null>(null);

  const handleQuickLoad = async (sampleKey: string) => {
    try {
      setLoadingSample(sampleKey);
      const doc = await loadSampleDocument(sampleKey);
      router.push(`/analyze?docId=${doc.id}`);
    } catch (err: any) {
      alert(err.message || 'Failed to load sample. You can still test from the dashboard.');
      router.push('/dashboard');
    } finally {
      setLoadingSample(null);
    }
  };

  const sampleContracts = [
    {
      key: 'standard_residential_lease_delhi',
      title: lang === 'hi' ? 'मानक आवासीय लीज़ (दिल्ली)' : 'Standard Residential Lease (Delhi NCR)',
      category: lang === 'hi' ? 'आवासीय किराया' : 'Residential Tenancy',
      desc:
        lang === 'hi'
          ? 'संतुलित 11 महीने का अनुबंध: 30 दिन का नोटिस, 2 महीने की जमानत राशि, मकान मालिक द्वारा संरचनात्मक रखरखाव।'
          : 'Balanced 11-month lease with mutual 30-day notice, 2-month deposit, and landlord structural repairs.',
      badge: lang === 'hi' ? 'संतुलित अनुबंध' : 'Balanced Terms',
      badgeColor: 'bg-emerald-950/70 text-emerald-300 border-emerald-500/30',
    },
    {
      key: 'harsh_landlord_lease_delhi',
      title: lang === 'hi' ? 'कठोर मकान मालिक अनुबंध (रेड फ्लैग)' : 'Harsh Landlord Lease (Severe Red Flags)',
      category: lang === 'hi' ? 'उच्च जोखिम किराया' : 'High Risk Tenancy',
      desc:
        lang === 'hi'
          ? 'एकतरफा शर्तें: 18% विलंब ब्याज, ₹1,000/दिन जुर्माना, 90 दिन में डिपॉजिट वापसी, मकान मालिक को 7 दिन में निकालने का अधिकार।'
          : 'Asymmetric terms: 18% compounding interest, ₹1,000/day fine, 90-day deposit lock-in, unilateral 7-day landlord termination.',
      badge: lang === 'hi' ? 'उच्च जोखिम' : 'High Risk Alert',
      badgeColor: 'bg-red-950/70 text-red-300 border-red-500/40',
    },
    {
      key: 'employment_agreement_tech_bangalore',
      title: lang === 'hi' ? 'आईटी रोजगार समझौता (बेंगलुरु)' : 'IT Employment Agreement (Bangalore)',
      category: lang === 'hi' ? 'रोजगार अनुबंध' : 'Employment & IP',
      desc:
        lang === 'hi'
          ? 'नौकरी के बाद 12 महीने का नॉन-कंपीट (जो धारा 27 के तहत अमान्य है), 90 दिन की नोटिस अवधि, और ₹3 लाख हर्जाना।'
          : '12-month post-employment non-compete (void under Section 27), 90-day notice period, and ₹3,00,000 damages clause.',
      badge: lang === 'hi' ? 'श्रम कानून टकराव' : 'Section 27 Conflict',
      badgeColor: 'bg-amber-950/70 text-amber-300 border-amber-500/30',
    },
    {
      key: 'consumer_services_contract',
      title: lang === 'hi' ? 'उपभोक्ता सदस्यता शर्तें (अनुचित अनुबंध)' : 'Consumer Subscription Terms (Unfair Terms)',
      category: lang === 'hi' ? 'उपभोक्ता अधिकार' : 'Consumer Rights',
      desc:
        lang === 'hi'
          ? 'गैर-वापसी योग्य फीस और उपभोक्ता फोरम में जाने के अधिकार को त्यागने की अवैध शर्त (उपभोक्ता संरक्षण अधिनियम 2019)।'
          : 'Non-refundable upfront fee and illegal waiver of consumer dispute commission jurisdiction under CPA 2019.',
      badge: lang === 'hi' ? 'अनुचित अनुबंध' : 'Unfair Contract',
      badgeColor: 'bg-purple-950/70 text-purple-300 border-purple-500/30',
    },
  ];

  const corePillars = [
    {
      title: lang === 'hi' ? 'दस्तावेज़ सरलीकरण' : 'Plain Language Clarity',
      desc:
        lang === 'hi'
          ? 'जटिल कानूनी भाषा को आम नागरिक और छात्र के स्तर पर सरल हिंदी और अंग्रेजी में बदलें।'
          : 'Convert dense legalese into actionable, tiered summaries in plain English and conversational Hindi.',
      icon: BookOpen,
      color: 'text-blue-400',
    },
    {
      title: lang === 'hi' ? 'शर्तों का वर्गीकरण एवं जोखिम जांच' : 'Clause Extraction & Risk Scrutiny',
      desc:
        lang === 'hi'
          ? 'समाप्ति, हर्जाना, किराया वृद्धि, और विवाद समाधान जैसी मुख्य शर्तों का स्वतः वर्गीकरण और जोखिम स्कोरिंग।'
          : 'Automatically detect termination, indemnity, rent escalation, penalty, and unilateral variation clauses.',
      icon: ShieldAlert,
      color: 'text-amber-400',
    },
    {
      title: lang === 'hi' ? 'दस्तावेज़ तुलना व जोखिम अंतर' : 'Semantic Comparison & Risk Delta',
      desc:
        lang === 'hi'
          ? 'दो अनुबंधों (जैसे मानक ड्राफ्ट बनाम संशोधित ड्राफ्ट) की तुलना कर बढ़े हुए जोखिमों को तुरंत पहचानें।'
          : 'Compare original drafts against revised counter-offers to instantly spot added liabilities and deleted rights.',
      icon: FileDiff,
      color: 'text-purple-400',
    },
    {
      title: lang === 'hi' ? 'साक्ष्य आधारित प्रश्नोत्तरी' : 'Grounded Q&A with Citations',
      desc:
        lang === 'hi'
          ? 'सवालों के जवाब पृष्ठ संख्या और मूल उद्धरण के साथ। जो दस्तावेज़ में नहीं है, उसे स्पष्ट रूप से असत्यापित बताएं।'
          : 'Extract verified answers with exact page and quote citations. If absent, the AI explicitly states it cannot be verified.',
      icon: HelpCircle,
      color: 'text-emerald-400',
    },
    {
      title: lang === 'hi' ? '5-स्तरीय दावा सत्यापन' : '5-State Claim Verification',
      desc:
        lang === 'hi'
          ? 'दावों को 5 अवस्थाओं (समर्थित, आंशिक, असमर्थित, विरोधाभासी, असत्यापित) में आधिकारिक साक्ष्य से जांचें।'
          : 'Evaluate claims across SUPPORTED, PARTIALLY_SUPPORTED, UNSUPPORTED, CONFLICTING, and UNVERIFIED states.',
      icon: FileCheck2,
      color: 'text-emerald-400',
    },
    {
      title: lang === 'hi' ? 'अधिवक्ता परामर्श ब्रीफ' : 'Advocate Consultation Brief',
      desc:
        lang === 'hi'
          ? 'वकील से मिलने से पहले महत्वपूर्ण मुद्दों, रेड फ्लैग और पूछे जाने वाले सवालों का संरचित मेमो तैयार करें।'
          : 'Generate a structured brief for a qualified lawyer summarizing key issues, liabilities, and targeted questions.',
      icon: Shield,
      color: 'text-amber-400',
    },
    {
      title: lang === 'hi' ? 'भारतीय कानूनी ज्ञानकोष' : 'India-First Statutory Knowledge',
      desc:
        lang === 'hi'
          ? 'भारतीय न्याय संहिता (BNS), BNSS, उपभोक्ता संरक्षण अधिनियम 2019, और मॉडल टेनेंसी एक्ट का अंतर्निहित ज्ञानकोष।'
          : 'Grounded in Bharatiya Nyaya Sanhita (BNS 2023), Consumer Protection Act 2019, RERA, and Contract Act.',
      icon: Scale,
      color: 'text-blue-400',
    },
    {
      title: lang === 'hi' ? 'मुफ्त कानूनी सहायता मार्गदर्शक' : 'Legal Aid & Section 12 Screener',
      desc:
        lang === 'hi'
          ? 'NALSA, राज्य विधिक सेवा प्राधिकरण (SLSA), लोक अदालत, और धारा 12 के तहत मुफ्त वकील पाने की पात्रता जांचें।'
          : 'Find NALSA, state/district legal aid clinics, and check eligibility for free government advocates under Section 12.',
      icon: Users,
      color: 'text-cyan-400',
    },
  ];

  return (
    <div className="space-y-16 pb-12">
      {/* Hero Section */}
      <section className="relative overflow-hidden pt-8 pb-12 text-center max-w-4xl mx-auto space-y-6">
        <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-amber-500/10 border border-amber-500/30 text-amber-300 text-xs font-semibold">
          <Sparkles className="w-3.5 h-3.5" aria-hidden="true" />
          <span>{lang === 'hi' ? 'नागरिक-केंद्रित एआई कानूनी मार्गदर्शक' : 'India-First Citizen GenAI Platform'}</span>
        </div>

        <h1 className="text-3xl sm:text-5xl md:text-6xl font-black text-white tracking-tight leading-tight">
          {lang === 'hi' ? (
            <>
              कानूनी स्पष्टता, साक्ष्य सत्यापन <br />
              <span className="text-transparent bg-clip-text bg-gradient-to-r from-amber-400 via-amber-200 to-amber-500">
                एवं नागरिक मार्गदर्शक
              </span>
            </>
          ) : (
            <>
              AI Legal Clarity, Verification <br />
              <span className="text-transparent bg-clip-text bg-gradient-to-r from-amber-400 via-amber-200 to-amber-500">
                & Action Navigator
              </span>
            </>
          )}
        </h1>

        <p className="text-sm sm:text-base md:text-lg text-slate-300 max-w-2xl mx-auto leading-relaxed">
          {lang === 'hi'
            ? 'अनुबंधों, किराए के समझौतों और कानूनी दस्तावेजों को समझें, तुलना करें और अपने अधिकारों को सुरक्षित रखें।'
            : 'Demystify Indian contracts, detect harsh terms, compare revisions, verify legal claims with evidence, and prepare structured briefs for your advocate.'}
        </p>

        {/* Product Principle Badge */}
        <div className="p-3.5 rounded-xl bg-slate-900/80 border border-slate-800 text-xs sm:text-sm text-amber-300 font-mono tracking-wide max-w-xl mx-auto shadow-inner">
          {t.principle}
        </div>

        {/* Primary CTA Buttons */}
        <div className="flex flex-wrap items-center justify-center gap-4 pt-2">
          <Link
            href="/dashboard"
            className="px-6 py-3 rounded-xl bg-gradient-to-r from-amber-500 to-amber-600 hover:from-amber-400 hover:to-amber-500 text-slate-950 font-bold text-sm shadow-lg shadow-amber-500/20 flex items-center gap-2 transition hover:scale-105"
          >
            <span>{lang === 'hi' ? 'दस्तावेज़ अपलोड करें' : 'Analyze a Document'}</span>
            <ArrowRight className="w-4 h-4" />
          </Link>

          <Link
            href="/legal-aid"
            className="px-6 py-3 rounded-xl bg-slate-900 hover:bg-slate-800 border border-slate-700 text-white font-semibold text-sm flex items-center gap-2 transition"
          >
            <Scale className="w-4 h-4 text-amber-400" />
            <span>{lang === 'hi' ? 'मुफ्त कानूनी सहायता खोजें' : 'Free Legal Aid Directory'}</span>
          </Link>
        </div>
      </section>

      {/* Quick Start: One-Click Realistic Sample Documents */}
      <section aria-labelledby="sample-docs-heading" className="space-y-6">
        <div className="flex flex-col sm:flex-row items-start sm:items-end justify-between gap-2 border-b border-slate-800 pb-4">
          <div>
            <span className="text-xs font-semibold text-amber-400 uppercase tracking-wider">
              {lang === 'hi' ? 'तुरंत परीक्षण करें' : 'Instant One-Click Test'}
            </span>
            <h2 id="sample-docs-heading" className="text-xl sm:text-2xl font-bold text-white mt-0.5">
              {lang === 'hi' ? 'वास्तविक भारतीय कानूनी दस्तावेज़ों से जांचें' : 'Explore Realistic Indian Sample Contracts'}
            </h2>
          </div>
          <p className="text-xs text-slate-400">
            {lang === 'hi' ? 'बिना अपलोड किए सीधे विश्लेषण देखें' : 'Click any contract to run full legal clarity engine'}
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {sampleContracts.map((sc) => (
            <div
              key={sc.key}
              className="glass-panel p-5 flex flex-col justify-between hover:border-slate-700 transition space-y-4"
            >
              <div className="space-y-2">
                <div className="flex items-center justify-between gap-2">
                  <span className="text-xs text-slate-400 font-medium">{sc.category}</span>
                  <span className={`text-[11px] px-2.5 py-0.5 rounded-full font-medium border ${sc.badgeColor}`}>
                    {sc.badge}
                  </span>
                </div>
                <h3 className="text-base font-bold text-white">{sc.title}</h3>
                <p className="text-xs text-slate-300 leading-relaxed">{sc.desc}</p>
              </div>

              <button
                type="button"
                onClick={() => handleQuickLoad(sc.key)}
                disabled={loadingSample === sc.key}
                className="w-full py-2 px-4 rounded-lg bg-slate-900 hover:bg-slate-800 border border-slate-700 hover:border-amber-500/40 text-amber-400 font-medium text-xs flex items-center justify-center gap-2 transition cursor-pointer"
              >
                {loadingSample === sc.key ? (
                  <span>{lang === 'hi' ? 'दस्तावेज़ लोड हो रहा है...' : 'Loading & Analyzing...'}</span>
                ) : (
                  <>
                    <span>{lang === 'hi' ? 'इस दस्तावेज़ का विश्लेषण करें' : 'Inspect & Analyze This Sample'}</span>
                    <ArrowRight className="w-3.5 h-3.5" />
                  </>
                )}
              </button>
            </div>
          ))}
        </div>
      </section>

      {/* 12 Core Capabilities Grid */}
      <section aria-labelledby="capabilities-heading" className="space-y-6">
        <div className="text-center max-w-2xl mx-auto space-y-2">
          <span className="text-xs font-semibold text-amber-400 uppercase tracking-wider">
            {lang === 'hi' ? 'उत्पाद क्षमताएं' : 'Platform Capabilities'}
          </span>
          <h2 id="capabilities-heading" className="text-2xl sm:text-3xl font-bold text-white">
            {lang === 'hi' ? 'नागरिक सुरक्षा हेतु 12 सशक्त उपकरण' : 'Engineered for Citizen Legal Safety'}
          </h2>
          <p className="text-xs sm:text-sm text-slate-400">
            {lang === 'hi'
              ? 'दस्तावेज़ की भाषा समझने से लेकर वकील के पास जाने तक, हर कदम पर साक्ष्य आधारित सहायता।'
              : 'From understanding terms to preparing briefs for your advocate, every feature is grounded in evidence.'}
          </p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {corePillars.map((p, idx) => {
            const Icon = p.icon;
            return (
              <div
                key={idx}
                className="glass-panel p-5 hover:border-slate-700 transition flex flex-col justify-between space-y-3"
              >
                <div className="space-y-2.5">
                  <div className="w-10 h-10 rounded-xl bg-slate-900 border border-slate-800 flex items-center justify-center">
                    <Icon className={`w-5 h-5 ${p.color}`} aria-hidden="true" />
                  </div>
                  <h3 className="text-sm font-bold text-white">{p.title}</h3>
                  <p className="text-xs text-slate-300 leading-relaxed">{p.desc}</p>
                </div>
              </div>
            );
          })}
        </div>
      </section>

      {/* Security, Privacy & Safety Architecture Banner */}
      <section className="glass-panel p-6 sm:p-8 border-amber-500/20 bg-gradient-to-br from-slate-950 via-slate-900 to-amber-950/20 rounded-2xl space-y-6">
        <div className="flex items-center gap-2.5 text-amber-400">
          <Lock className="w-5 h-5" />
          <h2 className="text-lg sm:text-xl font-bold text-white">
            {lang === 'hi' ? 'सुरक्षा, गोपनीयता एवं नैतिक सुरक्षा सिद्धांत' : 'Security, Privacy & Non-Autonomous Guardrails'}
          </h2>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 text-xs text-slate-300">
          <div className="p-4 rounded-xl bg-slate-950/70 border border-slate-800 space-y-1.5">
            <div className="flex items-center gap-2 text-emerald-400 font-semibold">
              <CheckCircle2 className="w-4 h-4" />
              <span>{lang === 'hi' ? 'सैंडबॉक्स्ड फाइल सत्यापन' : 'Untrusted Document Sandbox'}</span>
            </div>
            <p className="text-slate-400 leading-relaxed">
              {lang === 'hi'
                ? 'मैजिक बाइट्स जांच द्वारा जाली एक्सटेंशन खारिज होते हैं। कोई भी फाइल निष्पादित (execute) नहीं होती।'
                : 'Every upload is validated against true file magic bytes (PDF, DOCX, TXT) to prevent executable injection.'}
            </p>
          </div>

          <div className="p-4 rounded-xl bg-slate-950/70 border border-slate-800 space-y-1.5">
            <div className="flex items-center gap-2 text-emerald-400 font-semibold">
              <CheckCircle2 className="w-4 h-4" />
              <span>{lang === 'hi' ? 'भारतीय PII स्वचालित रेडैक्शन' : 'Indian PII Redaction'}</span>
            </div>
            <p className="text-slate-400 leading-relaxed">
              {lang === 'hi'
                ? 'आधार संख्या, पैन कार्ड, मोबाइल, ईमेल और बैंक विवरण को AI के पास भेजने से पहले स्वतः छुपाया जाता है।'
                : 'Aadhaar, PAN, phone numbers, and bank details are scrubbed locally before any processing.'}
            </p>
          </div>

          <div className="p-4 rounded-xl bg-slate-950/70 border border-slate-800 space-y-1.5">
            <div className="flex items-center gap-2 text-amber-400 font-semibold">
              <AlertTriangle className="w-4 h-4" />
              <span>{lang === 'hi' ? 'मानव निर्णय (गैर-स्वायत्त)' : 'Humans Decide (No Auto-Filing)'}</span>
            </div>
            <p className="text-slate-400 leading-relaxed">
              {lang === 'hi'
                ? 'सिस्टम कभी भी अपने आप केस दायर नहीं करता और न ही नोटिस भेजता है। अंतिम निर्णय सदैव आपका है।'
                : 'Zero autonomous court filing, notice sending, or signing. AI provides evidence and clarity; humans make decisions.'}
            </p>
          </div>
        </div>
      </section>
    </div>
  );
}
