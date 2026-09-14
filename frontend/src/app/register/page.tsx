'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { AlertCircle, ArrowRight, Lock, Mail, Scale, User } from 'lucide-react';
import { useLanguage } from '@/components/AppShell';
import { registerUser } from '@/lib/api';

export default function RegisterPage() {
  const { lang, t } = useLanguage();
  const router = useRouter();
  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (password.length < 8) {
      setError('Password must be at least 8 characters');
      return;
    }

    try {
      setLoading(true);
      setError(null);
      await registerUser(email.trim(), password, fullName.trim());
      router.push('/dashboard');
    } catch (err: any) {
      setError(err.message || 'Registration failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-md mx-auto py-12 space-y-6">
      <div className="text-center space-y-2">
        <div className="w-12 h-12 rounded-xl bg-amber-500/10 border border-amber-500/30 flex items-center justify-center text-amber-400 mx-auto">
          <Scale className="w-6 h-6" />
        </div>
        <h1 className="text-2xl font-bold text-white tracking-wide">
          {lang === 'hi' ? 'न्याय रक्षक में नया खाता बनाएं' : 'Create an Account'}
        </h1>
        <p className="text-xs text-slate-400">
          {lang === 'hi' ? 'नागरिक-केंद्रित कानूनी स्पष्टता एवं सत्यापन' : 'Empowering Indian citizens with legal clarity'}
        </p>
      </div>

      <form onSubmit={handleSubmit} className="glass-panel p-6 space-y-4">
        {error && (
          <div role="alert" className="p-3 rounded-lg bg-red-950/80 border border-red-500 text-red-200 text-xs flex items-center gap-2">
            <AlertCircle className="w-4 h-4 shrink-0 text-red-400" />
            <span>{error}</span>
          </div>
        )}

        <div className="space-y-1">
          <label htmlFor="reg-name" className="text-xs text-slate-300 font-semibold block">
            Full Name
          </label>
          <div className="relative">
            <User className="w-4 h-4 text-slate-500 absolute left-3 top-3" />
            <input
              id="reg-name"
              type="text"
              required
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              placeholder="Ramesh Gupta"
              className="w-full bg-slate-950/80 border border-slate-700 rounded-xl pl-9 pr-3 py-2 text-xs text-white focus-visible:ring-2"
            />
          </div>
        </div>

        <div className="space-y-1">
          <label htmlFor="reg-email" className="text-xs text-slate-300 font-semibold block">
            Email Address
          </label>
          <div className="relative">
            <Mail className="w-4 h-4 text-slate-500 absolute left-3 top-3" />
            <input
              id="reg-email"
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="citizen@example.com"
              className="w-full bg-slate-950/80 border border-slate-700 rounded-xl pl-9 pr-3 py-2 text-xs text-white focus-visible:ring-2"
            />
          </div>
        </div>

        <div className="space-y-1">
          <label htmlFor="reg-password" className="text-xs text-slate-300 font-semibold block">
            Password (min 8 chars)
          </label>
          <div className="relative">
            <Lock className="w-4 h-4 text-slate-500 absolute left-3 top-3" />
            <input
              id="reg-password"
              type="password"
              required
              minLength={8}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              className="w-full bg-slate-950/80 border border-slate-700 rounded-xl pl-9 pr-3 py-2 text-xs text-white focus-visible:ring-2"
            />
          </div>
        </div>

        <button
          type="submit"
          disabled={loading}
          className="w-full py-2.5 rounded-xl bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold text-xs flex items-center justify-center gap-2 transition cursor-pointer shadow-md"
        >
          <span>{loading ? 'Creating Account...' : t.nav.register}</span>
          <ArrowRight className="w-4 h-4" />
        </button>

        <div className="text-center pt-2 border-t border-slate-800 text-xs text-slate-400">
          <span>{lang === 'hi' ? 'पहले से खाता है? ' : 'Already have an account? '}</span>
          <Link href="/login" className="text-amber-400 hover:underline font-semibold">
            {t.nav.login}
          </Link>
        </div>
      </form>
    </div>
  );
}
