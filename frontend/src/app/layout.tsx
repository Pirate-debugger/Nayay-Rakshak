import type { Metadata } from 'next';
import './globals.css';
import AppShell from '@/components/AppShell';

export const metadata: Metadata = {
  title: 'NYAYA RAKSHAK - AI Legal Clarity, Verification & Action Navigator',
  description:
    'An India-first, citizen-centric GenAI platform that helps users understand, compare, analyze, and navigate legal documents and Indian legal aid resources.',
  keywords: [
    'Indian Law',
    'Legal AI',
    'BNS 2023',
    'IPC transition',
    'Document Simplification',
    'Lease Agreement Analysis',
    'NALSA Free Legal Aid',
    'Consumer Protection Act',
  ],
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="h-full">
      <body className="min-h-full flex flex-col bg-[#070b12] text-slate-100">
        <AppShell>{children}</AppShell>
      </body>
    </html>
  );
}
