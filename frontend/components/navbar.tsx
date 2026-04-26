"use client";

import Link from "next/link";
import { Shield } from "lucide-react";
import { motion } from "framer-motion";

export function Navbar() {
  return (
    <motion.nav 
      initial={{ opacity: 0, y: -20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.8, ease: [0.16, 1, 0.3, 1] }}
      className="fixed top-0 left-0 right-0 z-50 flex items-center justify-between px-6 py-4 border-b border-white/5 bg-zinc-950/80 backdrop-blur-md"
    >
      <Link href="/" className="flex items-center gap-2 group">
        <div className="flex items-center justify-center w-8 h-8 rounded-lg bg-zinc-900 border border-white/10 group-hover:border-emerald-500/50 transition-colors duration-300">
          <Shield className="w-4 h-4 text-zinc-100 group-hover:text-emerald-400 transition-colors duration-300" />
        </div>
        <span className="text-sm font-medium tracking-wide text-zinc-100 group-hover:text-emerald-400 transition-colors duration-300">
          FairLens
        </span>
      </Link>

      <div className="hidden md:flex items-center gap-8 text-sm font-medium text-zinc-400">
        <Link href="#features" className="hover:text-zinc-100 transition-colors">Platform</Link>
        <Link href="#audits" className="hover:text-zinc-100 transition-colors">Audits</Link>
        <Link href="#compliance" className="hover:text-zinc-100 transition-colors">Compliance</Link>
        <Link href="#company" className="hover:text-zinc-100 transition-colors">Company</Link>
      </div>

      <div className="flex items-center gap-4">
        <Link href="/login" className="text-sm font-medium text-zinc-400 hover:text-zinc-100 transition-colors duration-200">
          Sign in
        </Link>
        <button className="px-4 py-2 text-sm font-medium text-zinc-950 bg-emerald-500 rounded-md hover:bg-emerald-400 transition-all duration-300 ease-out active:scale-95">
          Start Audit
        </button>
      </div>
    </motion.nav>
  );
}
