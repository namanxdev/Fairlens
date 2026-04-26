"use client";

import React, { useRef } from "react";
import { motion, useScroll, useTransform, useSpring } from "framer-motion";
import { ArrowRight, Activity, ShieldAlert, Code2 } from "lucide-react";
import { cn } from "@/lib/utils";

export function HeroAwwwards() {
  const containerRef = useRef<HTMLDivElement>(null);
  const { scrollYProgress } = useScroll({
    target: containerRef,
    offset: ["start start", "end start"],
  });

  const y = useTransform(scrollYProgress, [0, 1], ["0%", "50%"]);
  const opacity = useTransform(scrollYProgress, [0, 0.8], [1, 0]);

  // Spring physics for a more high-end feel
  const springY = useSpring(y, { stiffness: 100, damping: 30 });

  return (
    <section
      ref={containerRef}
      className="relative min-h-[100dvh] w-full overflow-hidden bg-[#060606] text-white selection:bg-emerald-500/30 font-sans"
    >
      {/* Noise Overlay */}
      <div 
        className="pointer-events-none absolute inset-0 z-50 h-full w-full opacity-[0.035] mix-blend-color-dodge"
        style={{
          backgroundImage: `url("data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noiseFilter'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.85' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noiseFilter)'/%3E%3C/svg%3E")`,
        }}
      />

      {/* Abstract Glowing Orbs (Liquid Gradient Feel) */}
      <div className="pointer-events-none absolute left-[15%] top-[15%] h-[35vw] w-[45vw] rounded-full bg-emerald-500/10 mix-blend-screen blur-[120px] animate-pulse" />
      <div className="pointer-events-none absolute right-[0%] top-[40%] h-[30vw] w-[30vw] rounded-full bg-blue-500/10 mix-blend-screen blur-[100px]" style={{ animation: "pulse 10s infinite alternate-reverse" }} />

      <motion.div
        style={{ y: springY, opacity }}
        className="relative z-10 flex h-full min-h-[100dvh] w-full flex-col items-center justify-center px-6 pt-24"
      >
        <div className="mx-auto flex h-full w-full max-w-[1500px] flex-col items-start justify-center gap-12 lg:flex-row lg:items-end lg:justify-between pb-12">
          
          {/* Main Massive Typography */}
          <div className="z-20 flex flex-col justify-end">
            <motion.div
              initial={{ opacity: 0, y: 30 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 1, ease: [0.16, 1, 0.3, 1], delay: 0.1 }}
              className="mb-8 flex items-center gap-3"
            >
              <div className="flex h-7 items-center gap-2 rounded-full border border-white/10 bg-white/5 px-3 py-1 backdrop-blur-md shadow-[inset_0_1px_0_rgba(255,255,255,0.1)]">
                <span className="relative flex h-2 w-2">
                  <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75"></span>
                  <span className="relative inline-flex h-2 w-2 rounded-full bg-emerald-500"></span>
                </span>
                <span className="font-mono text-[10px] uppercase tracking-[0.2em] text-emerald-400/90">V2.0 Engine Live</span>
              </div>
            </motion.div>

            <h1 className="flex flex-col font-sans uppercase leading-[0.8] tracking-[-0.04em] text-transparent bg-clip-text bg-gradient-to-b from-white to-white/40">
              <motion.span
                initial={{ opacity: 0, y: 120, rotate: 2 }}
                animate={{ opacity: 1, y: 0, rotate: 0 }}
                transition={{ duration: 1.4, ease: [0.16, 1, 0.3, 1], delay: 0.2 }}
                className="text-[clamp(4rem,10vw,12rem)] font-bold pb-2"
              >
                DETECT.
              </motion.span>
              <div className="overflow-hidden">
                <motion.span
                  initial={{ opacity: 0, y: 120, rotate: 2 }}
                  animate={{ opacity: 1, y: 0, rotate: 0 }}
                  transition={{ duration: 1.4, ease: [0.16, 1, 0.3, 1], delay: 0.25 }}
                  className="text-[clamp(4rem,10vw,12rem)] font-bold text-white/30 italic block pb-2"
                >
                  DIAGNOSE.
                </motion.span>
              </div>
              <div className="overflow-hidden">
                <motion.span
                  initial={{ opacity: 0, y: 120, rotate: 2 }}
                  animate={{ opacity: 1, y: 0, rotate: 0 }}
                  transition={{ duration: 1.4, ease: [0.16, 1, 0.3, 1], delay: 0.3 }}
                  className="text-[clamp(4rem,10vw,12rem)] font-bold block pb-2"
                >
                  DEPLOY.
                </motion.span>
              </div>
            </h1>
          </div>

          {/* Context & Actions Block (Asymmetric Right) */}
          <motion.div
            initial={{ opacity: 0, x: 40 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 1, ease: [0.16, 1, 0.3, 1], delay: 0.6 }}
            className="z-20 flex w-full max-w-[420px] flex-col gap-10 lg:pb-6"
          >
            <p className="text-lg leading-relaxed text-zinc-400 font-sans mix-blend-plus-lighter">
              The enterprise diagnostic engine exposing hidden biases in production AI. Fix algorithmic harm <strong className="font-medium italic text-white">before</strong> your users ever see it.
            </p>
            
            <div className="flex flex-col gap-4 sm:flex-row sm:items-center">
              <a href="/upload" className="group relative flex h-12 w-full sm:w-auto items-center justify-center gap-2 overflow-hidden rounded-full bg-white px-8 text-sm font-semibold text-black transition-all hover:scale-[0.98] active:scale-95 shadow-[0_0_40px_rgba(255,255,255,0.2)]">
                <span>Start Audit</span>
                <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-1" />
              </a>
              <a href="/diagnostics" className="group relative flex h-12 w-full sm:w-auto items-center justify-center gap-2 rounded-full border border-white/10 bg-white/5 px-8 text-sm font-medium text-white transition-all hover:bg-white/10 active:scale-95 backdrop-blur-md shadow-[inset_0_1px_0_rgba(255,255,255,0.1)]">
                <span className="font-mono text-[11px] uppercase tracking-wider text-zinc-400 group-hover:text-white transition-colors">View Data</span>
              </a>
            </div>
            
            {/* High-end Minimal Data Metrics */}
            <div className="mt-4 flex items-center justify-between border-t border-white/10 pt-8">
              <div className="flex flex-col">
                <span className="mb-2 font-mono text-[10px] uppercase tracking-widest text-zinc-500">Models Scanned</span>
                <span className="font-mono text-3xl font-light tracking-tighter text-emerald-400">4,291</span>
              </div>
              <div className="flex flex-col">
                <span className="mb-2 font-mono text-[10px] uppercase tracking-widest text-zinc-500">Bias Prevented</span>
                <span className="font-mono text-3xl font-light tracking-tighter text-white">99.8%</span>
              </div>
            </div>
          </motion.div>
        </div>

        {/* Abstract Floating Cards (Awwwards 3D/Glass element simulation) */}
        <div className="pointer-events-none absolute inset-0 z-0 hidden h-full w-full overflow-hidden lg:block">
          <BentoFloatCard 
            delay={0.8} 
            className="right-[20%] top-[25%] rotate-[8deg]"
            icon={<Activity className="h-5 w-5 text-emerald-400" />}
            title="LATENCY"
            value="12ms"
          />
          <BentoFloatCard 
            delay={1.2} 
            className="bottom-[20%] left-[8%] -rotate-[6deg]"
            icon={<ShieldAlert className="h-5 w-5 text-rose-400" />}
            title="ANOMALY DETECTED"
            value="High"
          />
          <BentoFloatCard 
            delay={1.6} 
            className="bottom-[30%] right-[35%] rotate-[3deg]"
            icon={<Code2 className="h-5 w-5 text-blue-400" />}
            title="AST INTEGRATION"
            value="Parsed"
          />
        </div>
      </motion.div>
    </section>
  );
}

function BentoFloatCard({ className, delay, icon, title, value }: { className?: string, delay: number, icon: React.ReactNode, title: string, value: string }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 80, scale: 0.9 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      transition={{ duration: 1.6, delay, ease: [0.16, 1, 0.3, 1] }}
      className={cn(
        "absolute flex items-center gap-4 rounded-2xl border border-white/10 bg-black/40 p-5 backdrop-blur-2xl shadow-2xl",
        "before:absolute before:inset-0 before:-z-10 before:rounded-2xl before:bg-gradient-to-b before:from-white/10 before:to-transparent before:p-[1px]",
        className
      )}
      style={{
        boxShadow: "0 30px 60px -15px rgba(0, 0, 0, 0.8), inset 0 1px 1px rgba(255, 255, 255, 0.15)"
      }}
    >
      <div className="flex h-12 w-12 items-center justify-center rounded-full bg-white/5 border border-white/5 shadow-inner">
        {icon}
      </div>
      <div className="flex flex-col gap-0.5">
        <span className="font-mono text-[9px] uppercase tracking-[0.2em] text-zinc-500">{title}</span>
        <span className="font-serif text-sm tracking-wide text-white/90">{value}</span>
      </div>
    </motion.div>
  );
}
