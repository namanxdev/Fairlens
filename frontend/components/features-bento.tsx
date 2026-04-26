"use client";

import { motion } from "framer-motion";
import { ShieldCheck, Scale, Network, Database } from "lucide-react";
import React from "react";
import { AreaChart, Area, Tooltip, ResponsiveContainer, RadarChart, PolarGrid, PolarAngleAxis, Radar, BarChart, Bar, Cell } from "recharts";

// --- Mock Data for Charts ---
const biasTrendData = [
  { time: "00:00", bias: 85, threshold: 20 },
  { time: "04:00", bias: 70, threshold: 20 },
  { time: "08:00", bias: 90, threshold: 20 },
  { time: "12:00", bias: 15, threshold: 20 }, // Deployment fix happens here
  { time: "16:00", bias: 12, threshold: 20 },
  { time: "20:00", bias: 14, threshold: 20 },
  { time: "24:00", bias: 10, threshold: 20 },
];

const intersectionalData = [
  { subject: "Age", Scanned: 95, Baseline: 100, fullMark: 100 },
  { subject: "Gender", Scanned: 80, Baseline: 90, fullMark: 100 },
  { subject: "Race", Scanned: 85, Baseline: 95, fullMark: 100 },
  { subject: "Income", Scanned: 90, Baseline: 85, fullMark: 100 },
  { subject: "Geo", Scanned: 85, Baseline: 90, fullMark: 100 },
  { subject: "Disability", Scanned: 90, Baseline: 95, fullMark: 100 },
];

const complianceData = [
  { name: "EU AI Act", score: 98 },
  { name: "NIST RMF", score: 100 },
  { name: "ECOA", score: 95 },
  { name: "NYC 144", score: 92 },
];

// Custom Tooltip for premium look
const CustomTooltip = ({ active, payload, label }: any) => {
  if (active && payload && payload.length) {
    return (
      <div className="rounded-lg border border-white/10 bg-[#060606]/90 p-3 shadow-xl backdrop-blur-md">
        <p className="mb-2 font-mono text-[10px] uppercase text-zinc-500">{label}</p>
        {payload.map((entry: any, index: number) => (
          <div key={`item-${index}`} className="flex items-center gap-2">
            <div className="h-1.5 w-1.5 rounded-full" style={{ backgroundColor: entry.color || "#10b981" }} />
            <p className="font-mono text-sm font-medium text-white">
              {entry.name}: <span className="text-emerald-400">{entry.value}%</span>
            </p>
          </div>
        ))}
      </div>
    );
  }
  return null;
};

// Custom Tooltip for Bar Chart
const BarTooltip = ({ active, payload }: any) => {
  if (active && payload && payload.length) {
    return (
      <div className="flex items-center gap-2 rounded-lg border border-white/10 bg-[#060606]/90 px-3 py-2 shadow-xl backdrop-blur-md">
        <span className="font-mono text-[10px] uppercase text-zinc-500">{payload[0].payload.name}</span>
        <span className="font-mono text-sm text-emerald-400">{payload[0].value}%</span>
      </div>
    );
  }
  return null;
};

const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: { staggerChildren: 0.15, delayChildren: 0.2 },
  },
};

const itemVariants = {
  hidden: { opacity: 0, y: 20 },
  visible: { 
    opacity: 1, 
    y: 0, 
    transition: { type: "spring", stiffness: 350, damping: 30, mass: 0.8 } 
  },
};

export function FeaturesBento() {
  return (
    <section className="relative flex w-full justify-center overflow-hidden border-t border-white/5 bg-[#060606] px-6 py-32 font-sans antialiased md:px-12">
      <div className="pointer-events-none absolute left-1/2 top-1/2 h-[800px] w-[800px] -translate-x-1/2 -translate-y-1/2 rounded-full bg-emerald-500/5 blur-[120px]" />
      
      <div className="relative z-10 mx-auto w-full max-w-6xl">
        <motion.div 
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-100px" }}
          transition={{ duration: 0.8, ease: [0.16, 1, 0.3, 1] }}
          className="mb-20"
        >
          <div className="mb-6 flex items-center gap-2">
            <div className="h-px w-8 bg-emerald-500" />
            <span className="font-mono text-[10px] uppercase tracking-widest text-emerald-500">Platform Capabilities</span>
          </div>
          <h2 className="mb-6 text-4xl font-light tracking-tight text-white md:text-5xl">
            Auditing engineered for <span className="font-serif italic text-zinc-500">scale</span>.
          </h2>
          <p className="max-w-2xl font-sans text-sm font-light leading-relaxed text-zinc-400 md:text-base">
            Detect, explain, and mitigate algorithmic bias with a full-stack platform designed for uncompromising regulatory compliance. No black boxes.
          </p>
        </motion.div>

        <motion.div 
          variants={containerVariants}
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true, margin: "-100px" }}
          className="grid grid-cols-1 gap-0 border-l border-t border-white/5 md:grid-cols-3"
        >
          {/* Top Left: Automated Bias Detection (Area Chart) */}
          <motion.div
            variants={itemVariants}
            className="group relative col-span-1 flex min-h-[400px] flex-col justify-between overflow-hidden border-b border-r border-white/5 bg-[#060606] p-8 transition-colors duration-500 hover:bg-white/[0.02] md:col-span-2 md:p-12"
          >
            <div className="relative z-20 mb-8 max-w-md">
              <div className="mb-6 flex h-8 w-8 items-center justify-center rounded-full border border-white/10 bg-[#060606] text-zinc-400 transition-all duration-500 group-hover:border-emerald-500/30 group-hover:text-emerald-400">
                <Scale strokeWidth={1.5} className="h-4 w-4" />
              </div>
              <h3 className="mb-3 text-lg font-medium tracking-tight text-zinc-100">Automated Bias Detection</h3>
              <p className="font-sans text-sm font-light leading-relaxed text-zinc-400">
                Scan datasets and model outputs for implicit demographic biases continuously. Our engine captures deviations in real-time.
              </p>
            </div>
            
            {/* Area Chart Background */}
            <div className="absolute bottom-0 right-0 h-[250px] w-full md:w-[80%] opacity-40 transition-opacity duration-700 group-hover:opacity-80">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={biasTrendData} margin={{ top: 20, right: 0, left: 0, bottom: 0 }}>
                  <defs>
                    <linearGradient id="colorBias" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#10b981" stopOpacity={0.3} />
                      <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
                    </linearGradient>
                    <linearGradient id="colorThreshold" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#71717a" stopOpacity={0.1} />
                      <stop offset="95%" stopColor="#71717a" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <Tooltip content={<CustomTooltip />} cursor={{ stroke: 'rgba(255,255,255,0.1)', strokeWidth: 1 }} />
                  <Area type="monotone" name="Static Threshold" dataKey="threshold" stroke="#3f3f46" strokeWidth={1} strokeDasharray="4 4" fill="url(#colorThreshold)" />
                  <Area type="monotone" name="Bias Disparity" dataKey="bias" stroke="#10b981" strokeWidth={2} fill="url(#colorBias)" />
                </AreaChart>
              </ResponsiveContainer>
            </div>
            
            <div className="relative z-20 flex w-full justify-end opacity-0 transition-opacity duration-500 group-hover:opacity-100 mt-auto">
              <div className="h-1.5 w-1.5 rounded-full bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.5)]" />
            </div>
          </motion.div>

          {/* Top Right: Regulatory Compliance (Bar Chart) */}
          <motion.div
            variants={itemVariants}
            className="group relative col-span-1 flex min-h-[400px] flex-col justify-between overflow-hidden border-b border-r border-white/5 bg-[#060606] p-8 transition-colors duration-500 hover:bg-white/[0.02] md:p-12"
          >
            <div className="relative z-20 mb-8">
              <div className="mb-6 flex h-8 w-8 items-center justify-center rounded-full border border-white/10 bg-[#060606] text-zinc-400 transition-all duration-500 group-hover:border-emerald-500/30 group-hover:text-emerald-400">
                <ShieldCheck strokeWidth={1.5} className="h-4 w-4" />
              </div>
              <h3 className="mb-3 text-lg font-medium tracking-tight text-zinc-100">Regulatory Compliance</h3>
              <p className="font-sans text-sm font-light leading-relaxed text-zinc-400">
                Built-in checks for EU AI Act, ECOA, and NIST guidelines.
              </p>
            </div>

            {/* Bar Chart Background */}
            <div className="absolute bottom-0 left-0 right-0 h-[180px] w-full px-8 opacity-40 transition-opacity duration-700 group-hover:opacity-80">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={complianceData} margin={{ top: 10, right: 0, left: 0, bottom: 0 }}>
                  <Tooltip content={<BarTooltip />} cursor={{ fill: 'rgba(255,255,255,0.02)' }} />
                  <Bar dataKey="score" radius={[4, 4, 0, 0]}>
                    {complianceData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={index === 0 ? "#10b981" : "#27272a"} className="transition-all duration-300 hover:fill-emerald-400" />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </motion.div>

          {/* Bottom Left: Explainable AI */}
          <motion.div
            variants={itemVariants}
            className="group flex col-span-1 flex-col justify-between border-b border-r border-white/5 p-8 transition-colors duration-500 hover:bg-white/[0.02] md:p-12"
          >
            <div className="mb-12">
              <div className="mb-6 flex h-8 w-8 items-center justify-center rounded-full border border-white/10 bg-[#060606] text-zinc-400 transition-all duration-500 group-hover:border-emerald-500/30 group-hover:text-emerald-400">
                <Network strokeWidth={1.5} className="h-4 w-4" />
              </div>
              <h3 className="mb-3 text-lg font-medium tracking-tight text-zinc-100">Explainable AI</h3>
              <p className="font-sans text-sm font-light leading-relaxed text-zinc-400">
                Trace model decisions down to the exact feature weight and training data point in the pipeline.
              </p>
            </div>
            <div className="flex w-full justify-end opacity-0 transition-opacity duration-500 group-hover:opacity-100">
              <div className="h-1.5 w-1.5 rounded-full bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.5)]" />
            </div>
          </motion.div>

          {/* Bottom Right: Intersectional Profiling (Radar Chart) */}
          <motion.div
            variants={itemVariants}
            className="group relative col-span-1 flex min-h-[450px] flex-col justify-between overflow-hidden border-b border-r border-white/5 bg-[#060606] p-8 transition-colors duration-500 hover:bg-white/[0.02] md:col-span-2 md:p-12"
          >
            <div className="relative z-20 max-w-sm">
              <div className="mb-6 flex h-8 w-8 items-center justify-center rounded-full border border-white/10 bg-[#060606] text-zinc-400 transition-all duration-500 group-hover:border-emerald-500/30 group-hover:text-emerald-400">
                <Database strokeWidth={1.5} className="h-4 w-4" />
              </div>
              <h3 className="mb-3 text-lg font-medium tracking-tight text-zinc-100">Intersectional Profiling</h3>
              <p className="mb-8 font-sans text-sm font-light leading-relaxed text-zinc-400">
                Uncover compounding disparities across multidimensional demographic and behavioral segments.
              </p>
            </div>

            {/* Radar Chart Visual */}
            <div className="absolute -right-[15%] -top-[10%] bottom-0 h-[500px] w-[500px] opacity-40 transition-opacity duration-700 group-hover:opacity-80">
              <ResponsiveContainer width="100%" height="100%">
                <RadarChart cx="50%" cy="50%" outerRadius="60%" data={intersectionalData}>
                  <PolarGrid stroke="rgba(255,255,255,0.05)" />
                  <PolarAngleAxis dataKey="subject" tick={{ fill: '#71717a', fontSize: 10, fontFamily: 'monospace', textAnchor: 'middle', textTransform: 'uppercase' }} />
                  <Radar name="Baseline" dataKey="Baseline" stroke="#3f3f46" strokeWidth={1} fill="#3f3f46" fillOpacity={0.1} />
                  <Radar name="Scanned Model" dataKey="Scanned" stroke="#10b981" strokeWidth={2} fill="#10b981" fillOpacity={0.3} />
                  <Tooltip content={<CustomTooltip />} />
                </RadarChart>
              </ResponsiveContainer>
            </div>
            
            <div className="relative z-20 mt-auto flex w-full justify-end opacity-0 transition-opacity duration-500 group-hover:opacity-100">
              <div className="flex items-center gap-3 rounded-full border border-white/10 bg-white/5 px-4 py-1.5 backdrop-blur-md">
                <span className="h-1.5 w-1.5 rounded-full bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.5)]" />
                <span className="font-mono text-[9px] uppercase tracking-wider text-white">Full Spectrum Analysis</span>
              </div>
            </div>
          </motion.div>
        </motion.div>
      </div>
    </section>
  );
}