import Link from 'next/link';
import { Shield } from 'lucide-react';

export function Footer() {
  const currentYear = new Date().getFullYear();

  return (
    <footer className="bg-zinc-950 border-t border-zinc-900 pt-16 pb-8">
      <div className="mx-auto max-w-7xl px-6 lg:px-8">
        <div className="xl:grid xl:grid-cols-3 xl:gap-8">
          <div className="space-y-8">
            <Link href="/" className="flex items-center gap-2">
              <div className="flex items-center justify-center w-8 h-8 rounded-lg bg-zinc-900 border border-zinc-800 shadow-sm">
                <Shield className="w-4 h-4 text-emerald-500" />
              </div>
              <span className="font-semibold text-white tracking-tight">FairLens</span>
            </Link>
            <p className="text-sm leading-6 text-zinc-400 max-w-xs">
              Automated bias detection, explainability, and regulatory compliance infrastructure for enterprise AI.
            </p>
          </div>
          <div className="mt-16 grid grid-cols-2 gap-8 xl:col-span-2 xl:mt-0">
            <div className="md:grid md:grid-cols-2 md:gap-8">
              <div>
                <h3 className="text-sm font-semibold leading-6 text-white">Product</h3>
                <ul role="list" className="mt-6 space-y-4">
                  <li>
                    <Link href="/features" className="text-sm leading-6 text-zinc-400 hover:text-white hover:underline transition-colors">Features</Link>
                  </li>
                  <li>
                    <Link href="/pricing" className="text-sm leading-6 text-zinc-400 hover:text-white hover:underline transition-colors">Pricing</Link>
                  </li>
                  <li>
                    <Link href="/changelog" className="text-sm leading-6 text-zinc-400 hover:text-white hover:underline transition-colors">Changelog</Link>
                  </li>
                </ul>
              </div>
              <div className="mt-10 md:mt-0">
                <h3 className="text-sm font-semibold leading-6 text-white">Compliance</h3>
                <ul role="list" className="mt-6 space-y-4">
                  <li>
                    <Link href="/compliance/eu-ai-act" className="text-sm leading-6 text-zinc-400 hover:text-white hover:underline transition-colors">EU AI Act</Link>
                  </li>
                  <li>
                    <Link href="/compliance/iso-24027" className="text-sm leading-6 text-zinc-400 hover:text-white hover:underline transition-colors">ISO 24027</Link>
                  </li>
                  <li>
                    <Link href="/compliance/nist-rmf" className="text-sm leading-6 text-zinc-400 hover:text-white hover:underline transition-colors">NIST AI RMF</Link>
                  </li>
                </ul>
              </div>
            </div>
            <div className="md:grid md:grid-cols-2 md:gap-8">
              <div>
                <h3 className="text-sm font-semibold leading-6 text-white">Resources</h3>
                <ul role="list" className="mt-6 space-y-4">
                  <li>
                    <Link href="/docs" className="text-sm leading-6 text-zinc-400 hover:text-white hover:underline transition-colors">Documentation</Link>
                  </li>
                  <li>
                    <Link href="/blog" className="text-sm leading-6 text-zinc-400 hover:text-white hover:underline transition-colors">Blog</Link>
                  </li>
                  <li>
                    <Link href="/research" className="text-sm leading-6 text-zinc-400 hover:text-white hover:underline transition-colors">Research</Link>
                  </li>
                </ul>
              </div>
              <div className="mt-10 md:mt-0">
                <h3 className="text-sm font-semibold leading-6 text-white">Company</h3>
                <ul role="list" className="mt-6 space-y-4">
                  <li>
                    <Link href="/about" className="text-sm leading-6 text-zinc-400 hover:text-white hover:underline transition-colors">About</Link>
                  </li>
                  <li>
                    <Link href="/security" className="text-sm leading-6 text-zinc-400 hover:text-white hover:underline transition-colors">Security</Link>
                  </li>
                  <li>
                    <Link href="/contact" className="text-sm leading-6 text-zinc-400 hover:text-white hover:underline transition-colors">Contact</Link>
                  </li>
                </ul>
              </div>
            </div>
          </div>
        </div>
        <div className="mt-16 sm:mt-20 flex flex-col md:flex-row items-center justify-between border-t border-zinc-900/80 pt-8">
          <p className="text-xs leading-5 text-zinc-500">
            &copy; {currentYear} FairLens Inc. All rights reserved.
          </p>
          <div className="mt-4 md:mt-0 flex items-center gap-2 group cursor-default">
            <div className="relative flex h-3 w-3 items-center justify-center">
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-500 opacity-20"></span>
              <span className="relative inline-flex h-2 w-2 rounded-full bg-emerald-500"></span>
            </div>
            <span className="text-xs text-zinc-500 group-hover:text-zinc-400 transition-colors">
              System Status: All systems normal
            </span>
          </div>
        </div>
      </div>
    </footer>
  );
}
