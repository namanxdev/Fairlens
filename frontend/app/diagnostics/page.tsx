"use client";

import { motion } from "framer-motion";
import { 
  BarChart, 
  Bar, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  ResponsiveContainer,
  ScatterChart,
  Scatter,
  ZAxis
} from "recharts";
import { AlertCircle, ShieldAlert, Cpu } from "lucide-react";

const parityData = [
  { group: "Gender: Female", value: 0.82, threshold: 0.8 },
  { group: "Gender: Male", value: 0.95, threshold: 0.8 },
  { group: "Age: < 25", value: 0.65, threshold: 0.8 },
  { group: "Age: 25-60", value: 0.91, threshold: 0.8 },
  { group: "Age: > 60", value: 0.72, threshold: 0.8 },
];

const scatterData = [
  { x: 10, y: 30, z: 200, name: 'Income' },
  { x: 40, y: 50, z: 260, name: 'Credit Score' },
  { x: 70, y: 20, z: 400, name: 'Age' },
  { x: 90, y: 80, z: 100, name: 'Education' },
  { x: 20, y: 70, z: 300, name: 'Employment Length' },
];

export default function DiagnosticsPage() {
  return (
    <div className="min-h-screen bg-[#060606] text-zinc-300 font-sans selection:bg-emerald-500/30 px-6 py-24 flex justify-center">
      <div className="w-full max-w-7xl space-y-12">
        <header className="flex flex-col md:flex-row md:items-end justify-between border-b border-white/5 pb-8 gap-6">
          <div className="space-y-4">
            <h1 className="text-3xl md:text-4xl font-light tracking-tight text-white flex items-center gap-3">
               Diagnostic Cockpit
            </h1>
            <p className="text-zinc-500 max-w-xl text-sm font-light leading-relaxed">
              Real-time audit of automated decisioning models. Detecting disparate impact and representation flaws.
            </p>
          </div>
          <motion.button 
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.98 }}
            className="px-6 py-3 bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-[10px] uppercase tracking-widest font-mono font-bold rounded flex items-center gap-2 whitespace-nowrap self-start md:self-auto"
          >
            <Cpu size={14} />
            Remediate Model
          </motion.button>
        </header>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Summary Stats */}
          <div className="lg:col-span-1 space-y-6">
             <div className="border border-white/5 bg-[#0a0a0a] p-6 rounded-lg relative overflow-hidden group">
                <div className="absolute top-0 right-0 p-4 opacity-10 group-hover:opacity-20 transition-opacity">
                    <ShieldAlert size={120} />
                </div>
                <div className="space-y-6 relative z-10">
                    <div className="space-y-1">
                        <span className="text-[10px] uppercase tracking-widest font-mono text-zinc-500">Overall Bias Score</span>
                        <div className="text-5xl font-light text-rose-400">Critical</div>
                    </div>
                    <div className="space-y-3">
                        <div className="flex justify-between border-b border-white/5 pb-2">
                            <span className="text-xs text-zinc-400">Disparate Impact ratio</span>
                            <span className="text-xs font-mono text-rose-400">0.72 &lt; 0.8 (Fail)</span>
                        </div>
                        <div className="flex justify-between border-b border-white/5 pb-2">
                            <span className="text-xs text-zinc-400">Demographic Parity</span>
                            <span className="text-xs font-mono text-amber-400">Marginal</span>
                        </div>
                        <div className="flex justify-between pb-2">
                            <span className="text-xs text-zinc-400">Equal Opportunity</span>
                            <span className="text-xs font-mono text-emerald-400">Pass</span>
                        </div>
                    </div>
                </div>
             </div>

             <div className="border border-white/5 bg-[#0a0a0a] p-6 rounded-lg">
                <span className="text-[10px] uppercase tracking-widest font-mono text-zinc-500 block mb-4">Detected Vulnerabilities</span>
                <ul className="space-y-3">
                    <li className="flex items-start gap-3 bg-rose-500/5 p-3 rounded border border-rose-500/10">
                        <AlertCircle size={16} className="text-rose-400 shrink-0 mt-0.5" />
                        <div className="space-y-1">
                            <p className="text-xs text-rose-200">Age &lt; 25 discrimination</p>
                            <p className="text-[10px] text-zinc-500">Loan approval rate is 35% lower than baseline.</p>
                        </div>
                    </li>
                    <li className="flex items-start gap-3 bg-amber-500/5 p-3 rounded border border-amber-500/10">
                        <AlertCircle size={16} className="text-amber-400 shrink-0 mt-0.5" />
                        <div className="space-y-1">
                            <p className="text-xs text-amber-200">Proxy Feature Risk</p>
                            <p className="text-[10px] text-zinc-500">'Zip Code' highly correlates with protected class.</p>
                        </div>
                    </li>
                </ul>
             </div>
          </div>

          {/* Charts Area */}
          <div className="lg:col-span-2 space-y-6">
            <div className="border border-white/5 bg-[#0a0a0a] p-6 rounded-lg h-[350px] flex flex-col">
              <span className="text-[10px] uppercase tracking-widest font-mono text-zinc-500 mb-6 block">Protected Class Parity</span>
              <div className="flex-1 w-full relative">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={parityData} margin={{ top: 0, right: 0, left: -20, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#ffffff05" />
                    <XAxis 
                      dataKey="group" 
                      axisLine={false} 
                      tickLine={false} 
                      tick={{ fill: '#71717a', fontSize: 10, fontFamily: 'monospace' }} 
                      dy={10} 
                    />
                    <YAxis 
                      axisLine={false} 
                      tickLine={false} 
                      tick={{ fill: '#71717a', fontSize: 10, fontFamily: 'monospace' }} 
                    />
                    <Tooltip 
                      cursor={{fill: '#ffffff02'}}
                      contentStyle={{ backgroundColor: '#000', border: '1px solid #ffffff10', borderRadius: '4px', fontSize: '12px' }}
                      itemStyle={{ color: '#fff' }}
                    />
                    <Bar dataKey="value" radius={[2, 2, 0, 0]}>
                      {parityData.map((entry, index) => (
                        <cell key={`cell-${index}`} fill={entry.value < 0.8 ? '#fb7185' : '#34d399'} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
                   {/* Threshold line */}
                   <div className="absolute top-[20%] left-10 right-0 border-t border-rose-500/50 border-dashed pointer-events-none">
                       <span className="absolute -top-4 right-0 text-[8px] font-mono text-rose-500 uppercase">80% Rule</span>
                   </div>
              </div>
            </div>

            <div className="border border-white/5 bg-[#0a0a0a] p-6 rounded-lg h-[300px] flex flex-col">
              <span className="text-[10px] uppercase tracking-widest font-mono text-zinc-500 mb-6 block">Feature Weight Distribution</span>
              <div className="flex-1 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <ScatterChart margin={{ top: 0, right: 0, left: -20, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#ffffff05" />
                    <XAxis type="number" dataKey="x" axisLine={false} tickLine={false} tick={{ fill: '#71717a', fontSize: 10 }} />
                    <YAxis type="number" dataKey="y" axisLine={false} tickLine={false} tick={{ fill: '#71717a', fontSize: 10 }} />
                    <ZAxis type="number" dataKey="z" range={[20, 400]} />
                    <Tooltip 
                       cursor={{strokeDasharray: '3 3', stroke: '#ffffff20'}}
                       content={({ active, payload }) => {
                        if (active && payload && payload.length) {
                          return (
                            <div className="bg-black border border-white/10 p-2 text-xs rounded shadow-xl">
                              <p className="text-emerald-400 font-mono">{`${payload[0].payload.name}`}</p>
                              <p className="text-zinc-400 mt-1">Impact: {payload[0].value}</p>
                            </div>
                          );
                        }
                        return null;
                      }}
                    />
                    <Scatter name="Features" data={scatterData} fill="#10b981" opacity={0.6} />
                  </ScatterChart>
                </ResponsiveContainer>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
