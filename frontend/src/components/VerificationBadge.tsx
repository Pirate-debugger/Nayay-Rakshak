'use client';

import React from 'react';
import { AlertCircle, AlertTriangle, CheckCircle, HelpCircle, XCircle } from 'lucide-react';
import { VerificationStatus } from '@/lib/types';
import { Language, translations } from '@/lib/i18n';

interface Props {
  status: VerificationStatus;
  confidence?: number;
  lang?: Language;
  showConfidence?: boolean;
}

export default function VerificationBadge({
  status,
  confidence,
  lang = 'en',
  showConfidence = true,
}: Props) {
  const t = translations[lang].verification_states;

  const config = {
    SUPPORTED: {
      label: t.SUPPORTED,
      icon: CheckCircle,
      bg: 'bg-emerald-950/70 text-emerald-300 border-emerald-500/40',
      iconColor: 'text-emerald-400',
    },
    PARTIALLY_SUPPORTED: {
      label: t.PARTIALLY_SUPPORTED,
      icon: AlertCircle,
      bg: 'bg-amber-950/70 text-amber-300 border-amber-500/40',
      iconColor: 'text-amber-400',
    },
    UNSUPPORTED: {
      label: t.UNSUPPORTED,
      icon: XCircle,
      bg: 'bg-rose-950/70 text-rose-300 border-rose-500/40',
      iconColor: 'text-rose-400',
    },
    CONFLICTING: {
      label: t.CONFLICTING,
      icon: AlertTriangle,
      bg: 'bg-red-950/80 text-red-200 border-red-500/60 font-semibold',
      iconColor: 'text-red-400',
    },
    UNVERIFIED: {
      label: t.UNVERIFIED,
      icon: HelpCircle,
      bg: 'bg-slate-900/80 text-slate-300 border-slate-700',
      iconColor: 'text-slate-400',
    },
  }[status] || {
    label: status,
    icon: HelpCircle,
    bg: 'bg-slate-900 text-slate-300 border-slate-700',
    iconColor: 'text-slate-400',
  };

  const IconComponent = config.icon;

  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border ${config.bg}`}
      role="status"
      aria-label={`Verification status: ${config.label}`}
    >
      <IconComponent className={`w-3.5 h-3.5 ${config.iconColor} shrink-0`} aria-hidden="true" />
      <span>{config.label}</span>
      {showConfidence && confidence !== undefined && (
        <span className="text-[11px] opacity-75 font-mono ml-0.5">
          ({Math.round(confidence * 100)}%)
        </span>
      )}
    </span>
  );
}
