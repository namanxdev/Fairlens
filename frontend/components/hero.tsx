"use client";

import { motion } from "framer-motion";
import { ArrowRight, Activity, ShieldCheck, Database } from "lucide-react";

export function Hero() {
  const container = {
    hidden: { opacity: 0 },
    show: {
      opacity: 1,
      transition: {
        staggerChildren: 0.15,
        delayChildren: 0.2,
      },
    },
  };

  const item = {
    hidden: { opacity: 0, y: 20 },
    show: { 
      opacity: 1, 
      y: 0, 
      transition: { 
        duration: 0.8, 
        ease: [0.16, 1, 0.3, 1] 
      } 
    },
  };

  return (
    <section className="relative min-h-[100dvh] w-full bg-zinc-950 flex items-center overflow-hidden pt-20">
      {/* Subtle Noise / Grid Pattern */}
      <div className="absolute inset-0 bg-[linear-gradient(to_right,#ffffff05_1px,transparent_1px),linear-gradient(to_bottom,#ffffff05_1px,transparent_1px)] bg-[size:4rem_4rem] [mask-image:radial-gradient(ellipse_60%_60%_at_50%_50%,#000_70%,transparent_100%)] pointer-events-none" />

      <div className="container mx-auto px-6 relative z-10 grid lg:grid-cols-2 gap-16 items-center">
        {/* Left: Typography */}
        <motion.div 
          variants={container}
          initial="hidden"
          animate="show"
          className="flex flex-col items-start max-w-2xl"
        >
          <motion.div variants={item} className="inline-flex items-center gap-2 px-3 py-1 mb-8 rounded-full bg-white/5 border border-white/10 text-xs font-medium text-zinc-300">
            <span className="w-2 h-2 rounded-full bg-emerald-500" />
            ISO 24027 & EU AI Act Compliant
          </motion.div>
          
          <motion.h1 variants={item} className="text-6xl md:text-7xl font-semibold tracking-tighter text-zinc-100 leading-[1.1]">
            Detect AI Bias.<br />
            <span className="text-zinc-500">Before Deployment.</span>
          </motion.h1>
          
          <motion.p variants={item} className="mt-6 text-lg md:text-xl text-zinc-400 leading-relaxed max-w-xl font-normal">
            Enterprise-grade proactive bias detection and compliance auditing for your machine learning models. Built for serious AI governance.
          </motion.p>
          
          <motion.div variants={item} className="mt-10 flex flex-wrap items-center gap-4">
            <button className="group relative inline-flex items-center justify-center gap-2 px-6 py-3 text-sm font-medium text-zinc-950 bg-emerald-500 rounded-md hover:bg-emerald-400 transition-all duration-300 ease-out active:scale-95">
              Run First Audit
              <ArrowRight className="w-4 h-4 transition-transform duration-300 ease-out group-hover:translate-x-1" />
            </button>
            <button className="inline-flex items-center justify-center px-6 py-3 text-sm font-medium text-zinc-100 bg-transparent border border-zinc-800 rounded-md hover:bg-zinc-900 hover:border-zinc-700 transition-all duration-300 ease-out active:scale-95">
              View Documentation
            </button>
          </motion.div>
        </motion.div>

        {/* Right: Abstract UI / Data Viz */}
        <motion.div
          initial={{ opacity: 0, scale: 0.95, x: 20 }}
          animate={{ opacity: 1, scale: 1, x: 0 }}
          transition={{ duration: 1, delay: 0.4, ease: [0.16, 1, 0.3, 1] }}
          className="relative lg:ml-auto w-full max-w-lg aspect-square lg:aspect-auto lg:h-[500px]"
        >
          {/* Main Glass Panel */}
          <div className="absolute inset-0 bg-zinc-900/60 backdrop-blur-2xl border border-white/10 shadow-[inset_0_1px_0_rgba(255,255,255,0.1),0_20px_40px_-15px_rgba(0,0,0,0.5)] rounded-2xl p-6 flex flex-col overflow-hidden">
            <div className="flex items-center justify-between pb-6 border-b border-white/5 mb-6 shrink-0">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-zinc-800/80 rounded-lg">
                  <Database className="w-4 h-4 text-zinc-300" />
                </div>
                <div>
                  <h3 className="text-sm font-medium text-zinc-100">Credit_Approval_Model_v3</h3>
                  <p className="text-xs text-zinc-500 mt-0.5">Scanned 2 mins ago</p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <span className="relative flex h-2 w-2">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                  <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
                </span>
                <span className="text-xs font-medium text-emerald-500 bg-emerald-500/10 px-2 py-1 rounded">
                  Live
                </span>
              </div>
            </div>

            {/* Simulated Data */}
            <div className="flex-1 flex flex-col space-y-6">
              <div className="space-y-3">
                <div className="flex items-center justify-between text-sm">
                  <span className="text-zinc-400">Overall Bias Risk</span>
                  <span className="text-zinc-100 font-medium">Low</span>
                </div>
                <div className="h-2 w-full bg-zinc-800 rounded-full overflow-hidden">
                  <motion.div 
                    initial={{ width: 0 }}
                    animate={{ width: "18%" }}
                    transition={{ duration: 1.5, delay: 0.8, ease: [0.16, 1, 0.3, 1] }}
                    className="h-full bg-emerald-500 rounded-full pointer-events-none"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4 pt-2 shrink-0">
                <div className="p-4 rounded-xl bg-zinc-950/50 border border-white/5">
                  <div className="flex items-center gap-2 text-zinc-500 mb-2">
                    <Activity className="w-3.5 h-3.5" />
                    <span className="text-xs font-medium">Demographic Parity</span>
                  </div>
                  <span className="text-2xl font-semibold text-zinc-100">0.94</span>
                </div>
                <div className="p-4 rounded-xl bg-zinc-950/50 border border-white/5">
                  <div className="flex items-center gap-2 text-zinc-500 mb-2">
                    <ShieldCheck className="w-3.5 h-3.5" />
                    <span className="text-xs font-medium">Equal Opportunity</span>
                  </div>
                  <span className="text-2xl font-semibold text-zinc-100">0.96</span>
                </div>
              </div>

              {/* Faux graph rows */}
              <div className="space-y-4 pt-4 flex-1">
                {[
                  { label: "Age", value: 85, color: "bg-zinc-200" },
                  { label: "Gender", value: 72, color: "bg-zinc-500" },
                  { label: "Ethnicity", value: 91, color: "bg-emerald-500" },
                ].map((stat, i) => (
                  <div key={i} className="flex items-center gap-4">
                    <span className="text-xs text-zinc-500 w-16">{stat.label}</span>
                    <div className="flex-1 h-1.5 bg-zinc-800 rounded-full overflow-hidden">
                      <motion.div
                        initial={{ width: 0 }}
                        animate={{ width: `${stat.value}%` }}
                        transition={{ duration: 1.5, delay: 1 + (i * 0.2), ease: [0.16, 1, 0.3, 1] }}
                        className={`h-full rounded-full ${stat.color} pointer-events-none`}
                      />
                    </div>
                  </div>
                ))}
              </div>
            </div>
            
            {/* Decoration Glow */}
            <div className="absolute -z-10 -bottom-32 -right-32 w-64 h-64 bg-emerald-500/20 blur-[100px] rounded-full pointer-events-none" />
          </div>
        </motion.div>
      </div>
    </section>
  );
}
