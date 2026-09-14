'use client';

import React from 'react';
import { AlertOctagon, AlertTriangle, Info, ShieldCheck } from 'lucide-react';
import { RiskLevel } from '@/lib/types';
import { Language, translations } from '@/lib/i18n';

interface Props {
  severity: RiskLevel;
  lang?: Language;
}

export default function RiskPill({ severity, lang = 'en' }: Props) {
  const t = translations[lang].risk_levels;

  const config = {
    LOW: {
      label: t.LOW,
      icon: ShieldCheck,
      bg: 'bg-emerald-950/60 text-emerald-300 border-emerald-500/30',
      iconColor: 'text-emerald-400',
    },
    MEDIUM: {
      label: t.MEDIUM,
      icon: Info,
      bg: 'bg-amber-950/60 text-amber-300 border-amber-500/30',
      iconColor: 'text-amber-400',
    },
    HIGH: {
      label: t.HIGH,
      icon: AlertTriangle,
      bg: 'bg-orange-950/70 text-orange-300 border-orange-500/40',
      iconColor: 'text-orange-400',
    },
    SEVERE: {
      label: t.SEVERE,
      icon: AlertOctagon,
      bg: 'bg-red-950/90 text-red-200 border-red-500/60 font-bold animate-pulse',
      iconColor: 'text-red-400',
    },
  }[severity] || {
    label: severity,
    icon: Info,
    bg: 'bg-slate-800 text-slate-300 border-slate-700',
    iconColor: 'text-slate-400',
  };

  const IconComponent = config.icon;

  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium border ${config.bg}`}
      role="status"
      aria-label={`Risk level: ${config.label}`}
    >
      <IconComponent className={`w-3.5 h-3.5 ${config.iconColor} shrink-0`} aria-hidden="true" />
      <span>{config.label}</span>
    </span>
  );
}
