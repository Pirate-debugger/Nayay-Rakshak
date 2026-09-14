'use client';

import React, { useEffect, useState } from 'react';
import {
  AlertCircle,
  CheckCircle2,
  ExternalLink,
  PhoneCall,
  Scale,
  Search,
  UserCheck,
} from 'lucide-react';
import { useLanguage } from '@/components/AppShell';
import { checkLegalAidEligibility, getLegalAidResources } from '@/lib/api';
import { EligibilityCheckResponse, LegalAidResource } from '@/lib/types';

export default function LegalAidPage() {
  const { lang, t } = useLanguage();
  const [resources, setResources] = useState<LegalAidResource[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [filterType, setFilterType] = useState('ALL');
  const [loading, setLoading] = useState(true);

  // Eligibility Screener Form State
  const [income, setIncome] = useState<number>(250000);
  const [state, setState] = useState('Delhi');
  const [isWomanOrChild, setIsWomanOrChild] = useState(false);
  const [isScOrSt, setIsScOrSt] = useState(false);
  const [isDisabled, setIsDisabled] = useState(false);
  const [isInCustody, setIsInCustody] = useState(false);
  const [isWorkman, setIsWorkman] = useState(false);
  const [eligibilityResult, setEligibilityResult] = useState<EligibilityCheckResponse | null>(null);
  const [checking, setChecking] = useState(false);

  useEffect(() => {
    let active = true;
    getLegalAidResources(
      searchQuery || undefined,
      filterType !== 'ALL' ? filterType : undefined
    )
      .then((res) => {
        if (active) setResources(res);
      })
      .catch(() => {
        if (active) setResources([]);
      })
      .finally(() => {
        if (active) setLoading(false);
      });

    return () => {
      active = false;
    };
  }, [searchQuery, filterType]);

  const handleCheckEligibility = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      setChecking(true);
      const res = await checkLegalAidEligibility({
        annual_income: Number(income),
        state,
        is_woman_or_child: isWomanOrChild,
        is_sc_or_st: isScOrSt,
        is_disabled: isDisabled,
        is_in_custody: isInCustody,
        is_industrial_workman: isWorkman,
      });
      setEligibilityResult(res);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Failed to check eligibility';
      alert(message);
    } finally {
      setChecking(false);
    }
  };

  return (
    <div className="space-y-12">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 border-b border-slate-800 pb-4">
        <div>
          <h1 className="text-2xl sm:text-3xl font-bold text-white flex items-center gap-2.5">
            <Scale className="w-7 h-7 text-amber-400" aria-hidden="true" />
            <span>{t.nav.legal_aid}</span>
          </h1>
          <p className="text-xs sm:text-sm text-slate-400 mt-1">
            {lang === 'hi'
              ? 'राष्ट्रीय विधिक सेवा प्राधिकरण (NALSA), राज्य प्राधिकरण, एवं धारा 12 के तहत मुफ्त कानूनी सहायता।'
              : 'Discover NALSA legal aid clinics, Lok Adalats, and check eligibility for free government advocates.'}
          </p>
        </div>

        <a
          href="tel:15100"
          className="px-4 py-2 rounded-xl bg-gradient-to-r from-emerald-600 to-emerald-700 hover:from-emerald-500 hover:to-emerald-600 text-white font-bold text-xs flex items-center gap-2 shadow-md transition cursor-pointer"
        >
          <PhoneCall className="w-4 h-4" />
          <span>{lang === 'hi' ? 'राष्ट्रीय विधिक सहायता हेल्पलाइन: 15100' : 'National Legal Helpline: 15100'}</span>
        </a>
      </div>

      {/* SECTION 1: Free Legal Aid Eligibility Screener */}
      <section aria-labelledby="eligibility-screener-heading" className="glass-panel p-6 sm:p-8 space-y-6 border-amber-500/30">
        <div className="border-b border-slate-800 pb-3 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <UserCheck className="w-6 h-6 text-amber-400" />
            <div>
              <h2 id="eligibility-screener-heading" className="text-lg font-bold text-white">
                {lang === 'hi'
                  ? 'धारा 12: मुफ्त कानूनी सहायता पात्रता जांचक'
                  : 'Section 12: Free Legal Aid Eligibility Screener'}
              </h2>
              <p className="text-xs text-slate-400">
                Legal Services Authorities Act, 1987 (Act No. 39 of 1987)
              </p>
            </div>
          </div>
        </div>

        <form onSubmit={handleCheckEligibility} className="space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <label htmlFor="state-select" className="text-xs text-slate-300 font-semibold">
                {lang === 'hi' ? 'राज्य / केंद्र शासित प्रदेश:' : 'State / Union Territory:'}
              </label>
              <select
                id="state-select"
                value={state}
                onChange={(e) => setState(e.target.value)}
                className="w-full bg-slate-900 border border-slate-700 rounded-lg p-2.5 text-xs text-white"
              >
                <option value="Delhi">Delhi NCR</option>
                <option value="Karnataka">Karnataka</option>
                <option value="Maharashtra">Maharashtra</option>
                <option value="Tamil Nadu">Tamil Nadu</option>
                <option value="Uttar Pradesh">Uttar Pradesh</option>
                <option value="West Bengal">West Bengal</option>
              </select>
            </div>

            <div className="space-y-1.5">
              <label htmlFor="income-input" className="text-xs text-slate-300 font-semibold">
                {lang === 'hi' ? 'कुल वार्षिक पारिवारिक आय (INR):' : 'Total Annual Family Income (INR):'}
              </label>
              <input
                id="income-input"
                type="number"
                value={income}
                onChange={(e) => setIncome(Number(e.target.value))}
                className="w-full bg-slate-900 border border-slate-700 rounded-lg p-2.5 text-xs text-white"
              />
            </div>
          </div>

          {/* Statutory Category Checkboxes */}
          <div className="space-y-2 pt-2">
            <span className="text-xs font-semibold text-slate-400 block">
              {lang === 'hi'
                ? 'लागू होने वाले विशेष वैधानिक वर्ग चुनें (Section 12 Criteria):'
                : 'Select all qualifying statutory categories under Section 12:'}
            </span>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs">
              <label className="flex items-center gap-2 p-2.5 rounded-lg bg-slate-900/60 border border-slate-800 cursor-pointer hover:border-slate-700">
                <input
                  type="checkbox"
                  checked={isWomanOrChild}
                  onChange={(e) => setIsWomanOrChild(e.target.checked)}
                  className="rounded border-slate-700 text-amber-500"
                />
                <span className="text-slate-200">{lang === 'hi' ? 'महिला अथवा बालक' : 'Woman or Child'}</span>
              </label>

              <label className="flex items-center gap-2 p-2.5 rounded-lg bg-slate-900/60 border border-slate-800 cursor-pointer hover:border-slate-700">
                <input
                  type="checkbox"
                  checked={isScOrSt}
                  onChange={(e) => setIsScOrSt(e.target.checked)}
                  className="rounded border-slate-700 text-amber-500"
                />
                <span className="text-slate-200">{lang === 'hi' ? 'अनुसूचित जाति / जनजाति (SC/ST)' : 'SC / ST Category'}</span>
              </label>

              <label className="flex items-center gap-2 p-2.5 rounded-lg bg-slate-900/60 border border-slate-800 cursor-pointer hover:border-slate-700">
                <input
                  type="checkbox"
                  checked={isDisabled}
                  onChange={(e) => setIsDisabled(e.target.checked)}
                  className="rounded border-slate-700 text-amber-500"
                />
                <span className="text-slate-200">{lang === 'hi' ? 'दिव्यांग व्यक्ति' : 'Person with Disability'}</span>
              </label>

              <label className="flex items-center gap-2 p-2.5 rounded-lg bg-slate-900/60 border border-slate-800 cursor-pointer hover:border-slate-700">
                <input
                  type="checkbox"
                  checked={isWorkman}
                  onChange={(e) => setIsWorkman(e.target.checked)}
                  className="rounded border-slate-700 text-amber-500"
                />
                <span className="text-slate-200">{lang === 'hi' ? 'औद्योगिक कामगार' : 'Industrial Workman'}</span>
              </label>

              <label className="flex items-center gap-2 p-2.5 rounded-lg bg-slate-900/60 border border-slate-800 cursor-pointer hover:border-slate-700">
                <input
                  type="checkbox"
                  checked={isInCustody}
                  onChange={(e) => setIsInCustody(e.target.checked)}
                  className="rounded border-slate-700 text-amber-500"
                />
                <span className="text-slate-200">{lang === 'hi' ? 'हिरासत में निरुद्ध व्यक्ति' : 'Person in Custody'}</span>
              </label>
            </div>
          </div>

          <div className="pt-2 flex justify-end">
            <button
              type="submit"
              disabled={checking}
              className="px-5 py-2.5 rounded-xl bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold text-xs flex items-center gap-2 transition cursor-pointer shadow-md"
            >
              <span>{checking ? 'जांच जारी है...' : t.actions.check_eligibility}</span>
            </button>
          </div>
        </form>

        {/* Screener Result */}
        {eligibilityResult && (
          <div
            className={`p-6 rounded-xl border space-y-4 ${
              eligibilityResult.is_eligible_for_free_legal_aid
                ? 'bg-emerald-950/40 border-emerald-500/40'
                : 'bg-slate-900/80 border-slate-800'
            }`}
          >
            <div className="flex items-center gap-2.5">
              {eligibilityResult.is_eligible_for_free_legal_aid ? (
                <CheckCircle2 className="w-6 h-6 text-emerald-400 shrink-0" />
              ) : (
                <AlertCircle className="w-6 h-6 text-amber-400 shrink-0" />
              )}
              <h3 className="text-base font-bold text-white">
                {eligibilityResult.is_eligible_for_free_legal_aid
                  ? (lang === 'hi' ? 'बधाई: आप मुफ्त कानूनी सहायता और सरकारी वकील के हकदार हैं' : 'Eligible for Free Legal Services under Section 12')
                  : (lang === 'hi' ? 'आय सीमा अधिक है, परंतु आप लोक अदालत व टेली-लॉ का उपयोग कर सकते हैं' : 'Income Exceeds State Threshold, but ADR is Available')}
              </h3>
            </div>

            <ul className="space-y-1 text-xs text-slate-200">
              {eligibilityResult.eligibility_reasons.map((r, i) => (
                <li key={i} className="flex items-start gap-2">
                  <span className="text-emerald-400 font-bold">•</span>
                  <span>{r}</span>
                </li>
              ))}
            </ul>

            {/* Application Checklist */}
            <div className="pt-3 border-t border-slate-800/80 space-y-2 text-xs">
              <span className="font-semibold text-amber-400 block">
                {lang === 'hi' ? 'DLSA/SLSA में आवेदन हेतु आवश्यक दस्तावेज:' : 'Required Application Documents for DLSA/SLSA:'}
              </span>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-slate-300">
                {eligibilityResult.action_checklist.map((doc, idx) => (
                  <div key={idx} className="flex items-center gap-2 bg-slate-900/80 p-2 rounded border border-slate-800">
                    <CheckCircle2 className="w-3.5 h-3.5 text-amber-400 shrink-0" />
                    <span>{doc}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </section>

      {/* SECTION 2: Searchable Indian Legal Aid Directory */}
      <section aria-labelledby="directory-heading" className="space-y-6">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div>
            <span className="text-xs font-semibold text-amber-400 uppercase tracking-wider">
              {lang === 'hi' ? 'आधिकारिक निर्देशिका' : 'Authoritative Directory'}
            </span>
            <h2 id="directory-heading" className="text-xl font-bold text-white">
              {lang === 'hi' ? 'विधिक सेवा प्राधिकरण एवं हेल्पलाइन निर्देशिका' : 'Legal Aid Authorities & Citizen Helplines'}
            </h2>
          </div>

          {/* Search Bar */}
          <div className="flex items-center gap-2 w-full sm:w-auto">
            <div className="relative flex-1 sm:w-64">
              <Search className="w-4 h-4 text-slate-500 absolute left-3 top-2.5" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder={lang === 'hi' ? 'खोजें (जैसे दिल्ली, उपभोक्ता, NALSA)...' : 'Search by name or state...'}
                className="w-full bg-slate-900 border border-slate-700 rounded-lg pl-9 pr-3 py-1.5 text-xs text-white"
              />
            </div>

            <select
              value={filterType}
              onChange={(e) => setFilterType(e.target.value)}
              className="bg-slate-900 border border-slate-700 rounded-lg px-2.5 py-1.5 text-xs text-white"
            >
              <option value="ALL">All Authorities</option>
              <option value="NALSA">NALSA</option>
              <option value="SLSA">State SLSAs</option>
              <option value="TELE_LAW">Tele-Law</option>
              <option value="CONSUMER_FORUM">Consumer Grievance</option>
              <option value="CYBER_HELPLINE">Cyber Crime</option>
            </select>
          </div>
        </div>

        {/* Resources Cards Grid */}
        {loading ? (
          <div className="text-center py-12 text-slate-400 text-sm">Loading legal aid resources...</div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {resources.map((res) => (
              <div key={res.id} className="glass-panel p-5 space-y-3 flex flex-col justify-between">
                <div className="space-y-2">
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-slate-800 text-amber-400">
                      {res.organization_type}
                    </span>
                    <span className="text-xs text-slate-400">{res.jurisdiction}</span>
                  </div>

                  <h3 className="text-base font-bold text-white">{res.name}</h3>
                  <p className="text-xs text-slate-300 leading-relaxed">{res.description}</p>

                  {/* Services List */}
                  <div className="pt-1">
                    <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block mb-1">
                      {lang === 'hi' ? 'उपलब्ध नागरिक सेवाएं:' : 'Services Provided:'}
                    </span>
                    <ul className="space-y-1 text-xs text-slate-300">
                      {res.services_offered.slice(0, 3).map((s, i) => (
                        <li key={i} className="flex items-start gap-1.5">
                          <span className="text-emerald-400 font-bold">•</span>
                          <span>{s}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>

                {/* Helpline & Portal Link */}
                <div className="pt-3 border-t border-slate-800 flex flex-wrap items-center justify-between gap-2 text-xs">
                  <span className="font-mono text-emerald-400 flex items-center gap-1.5">
                    <PhoneCall className="w-3.5 h-3.5" />
                    <span>{res.phone_or_helpline}</span>
                  </span>

                  <a
                    href={res.portal_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-amber-400 hover:text-amber-300 font-semibold flex items-center gap-1"
                  >
                    <span>{lang === 'hi' ? 'पोर्टल देखें' : 'Visit Portal'}</span>
                    <ExternalLink className="w-3 h-3" />
                  </a>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
