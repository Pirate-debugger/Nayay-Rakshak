'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { AlertCircle, ArrowRight, Lock, Mail, Scale } from 'lucide-react';
import { useLanguage } from '@/components/AppShell';
import { loginUser } from '@/lib/api';

export default function LoginPage() {
  const { lang, t } = useLanguage();
  const router = useRouter();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      setLoading(true);
      setError(null);
      await loginUser(email.trim(), password);
      router.push('/dashboard');
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Login failed';
      setError(message);
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
          {lang === 'hi' ? 'न्याय रक्षक में प्रवेश करें' : 'Sign in to Nyaya Rakshak'}
        </h1>
        <p className="text-xs text-slate-400">
          {lang === 'hi' ? 'अपने कानूनी दस्तावेज़ों की सुरक्षित समीक्षा करें' : 'Secure legal clarity and verification navigator'}
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
          <label htmlFor="login-email" className="text-xs text-slate-300 font-semibold block">
            Email Address
          </label>
          <div className="relative">
            <Mail className="w-4 h-4 text-slate-500 absolute left-3 top-3" />
            <input
              id="login-email"
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
          <label htmlFor="login-password" className="text-xs text-slate-300 font-semibold block">
            Password
          </label>
          <div className="relative">
            <Lock className="w-4 h-4 text-slate-500 absolute left-3 top-3" />
            <input
              id="login-password"
              type="password"
              required
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
          <span>{loading ? 'Authenticating...' : t.nav.login}</span>
          <ArrowRight className="w-4 h-4" />
        </button>

        <div className="text-center pt-2 border-t border-slate-800 text-xs text-slate-400">
          <span>{lang === 'hi' ? 'खाता नहीं है? ' : "Don't have an account? "}</span>
          <Link href="/register" className="text-amber-400 hover:underline font-semibold">
            {t.nav.register}
          </Link>
        </div>
      </form>
    </div>
  );
}
