'use client';

import Link from 'next/link';
import { motion } from 'framer-motion';
import { ArrowRight, ShieldCheck } from 'lucide-react';

export function CtaSection() {
  return (
    <section className="relative overflow-hidden py-32 bg-[#060606] border-y border-white/5 font-sans antialiased">
      {/* Structural background lines */}
      <div className="absolute inset-0 pointer-events-none flex justify-center">
        <div className="w-full max-w-7xl h-full border-x border-white/[0.02]" />
      </div>
      <div className="absolute top-1/2 left-0 w-full h-[1px] bg-white/[0.02] -translate-y-1/2 pointer-events-none" />

      {/* Very faint spotlight */}
      <div className="absolute inset-0 z-0 bg-[radial-gradient(circle_at_center,rgba(16,185,129,0.03)_0%,transparent_60%)] pointer-events-none" />

      <div className="relative z-10 mx-auto max-w-7xl px-6 lg:px-8 flex flex-col items-center">
        <motion.div
          initial={{ opacity: 0, y: 15 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-100px" }}
          transition={{ duration: 0.8, ease: [0.16, 1, 0.3, 1] }}
          className="flex flex-col items-center"
        >
          <div className="inline-flex items-center justify-center p-px mb-8 overflow-hidden rounded-full backdrop-blur-sm bg-white/5 border border-white/10">
            <div className="flex items-center gap-2 px-3 py-1.5 bg-[#060606] rounded-full text-xs text-zinc-400 font-mono tracking-widest uppercase">
              <ShieldCheck className="w-3.5 h-3.5 text-emerald-500" strokeWidth={2} />
              <span>Enterprise-grade detection</span>
            </div>
          </div>
          
          <h2 className="text-4xl md:text-6xl font-light tracking-tight text-white mb-6 text-center leading-[1.1]">
            Ready to ensure your models are <br className="hidden md:block" />
            <span className="text-zinc-500 font-serif italic">fair and compliant?</span>
          </h2>
          
          <p className="text-base text-zinc-400 max-w-lg text-center font-light leading-relaxed mb-10">
            Start auditing your datasets and models today. Generate immutable compliance reports aligned with the EU AI Act and NIST RMF in minutes.
          </p>

          <div className="flex flex-col sm:flex-row items-center gap-6">
            <Link
              href="/dashboard"
              className="group relative inline-flex items-center justify-center rounded-none bg-white text-black px-6 py-3 text-sm font-medium transition-all hover:bg-zinc-200"
            >
              <span className="relative z-10 flex items-center gap-2">
                Start your audit
                <ArrowRight className="w-4 h-4 transition-transform duration-300 group-hover:translate-x-1" strokeWidth={1.5} />
              </span>
            </Link>
            <Link 
              href="/docs" 
              className="group flex items-center gap-2 text-sm font-light text-zinc-400 hover:text-white transition-colors"
            >
              Read documentation
              <span className="inline-flex overflow-hidden">
                <span className="inline-block transition-transform duration-300 group-hover:translate-x-1 -translate-x-full opacity-0 group-hover:opacity-100">→</span>
              </span>
            </Link>
          </div>
        </motion.div>
      </div>
    </section>
  );
}
