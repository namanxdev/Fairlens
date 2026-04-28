"use client";

import { useEffect, useMemo, useState, useRef } from "react";
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
  ZAxis,
  Cell,
  LabelList,
} from "recharts";
import { AlertCircle, ShieldAlert, Cpu } from "lucide-react";
import {
  DashboardStats,
  FairnessAudit,
  getCurrentAudit,
  getDashboardStats,
  getSavedAudit,
  readLastAudit,
  saveLastAudit,
  uploadDataset,
  remediateAndDownload,
} from "@/lib/api";

const FAIRNESS_THRESHOLD = 0.8;

type ParityPoint = {
  group: string;
  value: number;
};

type ScatterPoint = {
  x: number;
  y: number;
  z: number;
  name: string;
  impactLabel: string;
};

type Vulnerability = {
  tone: "rose" | "amber";
  title: string;
  detail: string;
};

function titleize(value?: string) {
  return (value || "audit").replace(/[_-]/g, " ").replace(/\b\w/g, (char) => char.toUpperCase());
}

function formatRatio(value?: number | null) {
  return typeof value === "number" && Number.isFinite(value) ? value.toFixed(2) : "--";
}

function formatPercent(value?: number | null) {
  return typeof value === "number" && Number.isFinite(value) ? `${Math.round(value * 100)}%` : "--";
}

function getWorstResult(audit: FairnessAudit | null) {
  return (audit?.results || []).reduce<FairnessAudit["results"][number] | null>((worst, result) => {
    if (typeof result.disparate_impact_ratio !== "number") {
      return worst;
    }
    if (!worst || typeof worst.disparate_impact_ratio !== "number") {
      return result;
    }
    return result.disparate_impact_ratio < worst.disparate_impact_ratio ? result : worst;
  }, null);
}

function riskLabel(ratio?: number | null) {
  if (typeof ratio !== "number") {
    return "Pending";
  }
  if (ratio < 0.6) {
    return "Critical";
  }
  if (ratio < FAIRNESS_THRESHOLD) {
    return "High";
  }
  if (ratio < 0.9) {
    return "Medium";
  }
  return "Low";
}

function metricStatus(value?: number | null) {
  if (typeof value !== "number") {
    return "Pending";
  }
  const absValue = Math.abs(value);
  if (absValue <= 0.1) {
    return "Pass";
  }
  if (absValue <= 0.2) {
    return "Marginal";
  }
  return "Fail";
}

function primaryAttributeRows(dashboard: DashboardStats | null, audit: FairnessAudit | null) {
  if (!dashboard?.by_attribute) {
    return null;
  }
  if (audit?.sensitive_col && dashboard.by_attribute[audit.sensitive_col]) {
    return dashboard.by_attribute[audit.sensitive_col];
  }
  return Object.values(dashboard.by_attribute)[0] || null;
}

function buildParityData(audit: FairnessAudit | null, dashboard: DashboardStats | null): ParityPoint[] {
  const rows = primaryAttributeRows(dashboard, audit);
  return Object.entries(rows || {})
    .filter(([, row]) => typeof row.approval_rate === "number")
    .map(([group, row]) => ({
      group: `${titleize(audit?.sensitive_col)}: ${group}`,
      value: row.approval_rate || 0,
    }));
}

function buildScatterData(dashboard: DashboardStats | null, audit: FairnessAudit | null): ScatterPoint[] {
  const rows = primaryAttributeRows(dashboard, audit);
  if (!rows) {
    return [];
  }

  const featureBuckets = new Map<string, number[]>();
  Object.values(rows).forEach((row) => {
    Object.entries(row.numeric_averages || {}).forEach(([feature, value]) => {
      if (typeof value !== "number" || !Number.isFinite(value)) {
        return;
      }
      if (!featureBuckets.has(feature)) {
        featureBuckets.set(feature, []);
      }
      featureBuckets.get(feature)?.push(value);
    });
  });

  const visibleFeatureLimit = Math.min(Math.max(5, audit?.feature_cols?.length || 5), 12);
  const featureRows = Array.from(featureBuckets.entries())
    .filter(([, values]) => values.length > 0)
    .slice(0, visibleFeatureLimit)
    .map(([feature, values], index) => {
      const average = values.reduce((sum, value) => sum + value, 0) / values.length;
      const spread = Math.max(...values) - Math.min(...values);
      return { feature, average, spread, index };
    });

  if (featureRows.length === 0) {
    return [];
  }

  const minAverage = Math.min(...featureRows.map((row) => row.average));
  const maxAverage = Math.max(...featureRows.map((row) => row.average));
  const maxSpread = Math.max(...featureRows.map((row) => row.spread), 1);

  return featureRows.map((row) => {
    const averageRange = maxAverage - minAverage || 1;
    return {
      x: ((row.index + 1) / (featureRows.length + 1)) * 100,
      y: ((row.average - minAverage) / averageRange) * 100,
      z: 40 + (row.spread / maxSpread) * 360,
      name: row.feature,
      impactLabel: row.spread.toFixed(3),
    };
  });
}

function buildVulnerabilities(
  audit: FairnessAudit | null,
  dashboard: DashboardStats | null,
  loadError: string | null,
  viewMode: "raw" | "debiased" = "raw"
): Vulnerability[] {
  if (loadError) {
    return [{ tone: "rose", title: "Audit connection failed", detail: loadError }];
  }

  if (!audit) {
    return [{
      tone: "amber",
      title: "No audit loaded",
      detail: "Upload a dataset to populate live diagnostics.",
    }];
  }

  const vulnerabilities: Vulnerability[] = [];
  const byAttribute = dashboard?.by_attribute || {};
  Object.entries(dashboard?.legal_flags || {}).forEach(([attribute, flag]) => {
    if (flag !== "FAIL") {
      return;
    }
    const rows = byAttribute[attribute] || {};
    const ranked = Object.entries(rows)
      .filter(([, row]) => typeof row.approval_rate === "number")
      .sort(([, a], [, b]) => (a.approval_rate || 0) - (b.approval_rate || 0));
    const lowest = ranked[0];
    const highest = ranked[ranked.length - 1];
    vulnerabilities.push({
      tone: "rose",
      title: `${titleize(attribute)} 80% rule failure`,
      detail: lowest && highest
        ? `${lowest[0]} approval is ${formatPercent(lowest[1].approval_rate)} vs ${highest[0]} at ${formatPercent(highest[1].approval_rate)}.`
        : `Disparate impact ratio is ${formatRatio(dashboard?.di_ratios?.[attribute])}.`,
    });
  });

  const relevantResults = viewMode === "debiased"
    ? audit.results.filter(r => r.model.toLowerCase().includes("fair in-processing") || r.model.toLowerCase().includes("stage 1"))
    : audit.results.filter(r => r.model.toLowerCase().includes("baseline"));

  relevantResults.forEach((result) => {
    if (result.legal_pass) {
      return;
    }
    vulnerabilities.push({
      tone: vulnerabilities.length === 0 ? "rose" : "amber",
      title: `${result.model} disparate impact`,
      detail: `DI ratio ${formatRatio(result.disparate_impact_ratio)} is below the 80% rule threshold.`,
    });
  });

  if (vulnerabilities.length === 0) {
    return [{
      tone: "amber",
      title: "No active 80% rule failure",
      detail: "The latest audit metrics did not flag a protected-class failure.",
    }];
  }

  return vulnerabilities.slice(0, 2);
}

function vulnerabilityClassNames(tone: Vulnerability["tone"]) {
  if (tone === "rose") {
    return {
      item: "flex items-start gap-3 bg-rose-500/5 p-3 rounded border border-rose-500/10",
      icon: "text-rose-400 shrink-0 mt-0.5",
      title: "text-xs text-rose-200",
    };
  }

  return {
    item: "flex items-start gap-3 bg-amber-500/5 p-3 rounded border border-amber-500/10",
    icon: "text-amber-400 shrink-0 mt-0.5",
    title: "text-xs text-amber-200",
  };
}

export default function DiagnosticsPage() {
  const [audit, setAudit] = useState<FairnessAudit | null>(null);
  const [dashboard, setDashboard] = useState<DashboardStats | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [isDownloading, setIsDownloading] = useState(false);
  const [downloadSummary, setDownloadSummary] = useState<any>(null);
  const [bannerVisible, setBannerVisible] = useState(false);
  const [uploadedFile, setUploadedFile] = useState<File | null>(null);
  const [filePickerMode, setFilePickerMode] = useState<"upload" | "download" | null>(null);
  
  const [viewMode, setViewMode] = useState<"raw" | "debiased">("raw");
  
  const fileInputRef = useRef<HTMLInputElement>(null);

  const runDebiasedDownload = async (sourceFile?: File | null) => {
    if (!audit?.audit_id) {
      throw new Error("Please upload a dataset first so we can remediate it.");
    }

    setIsDownloading(true);
    try {
      const { blob, filename, summary } = await remediateAndDownload(audit.audit_id, sourceFile);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      
      if (sourceFile) {
        setUploadedFile(sourceFile);
      }
      setDownloadSummary(summary);
      setBannerVisible(true);
    } finally {
      setIsDownloading(false);
    }
  };

  const handleDownloadDebiasedClick = async () => {
    if (!audit?.audit_id) {
      alert("Please upload a dataset first so we can remediate it.");
      return;
    }

    setLoadError(null);
    try {
      await runDebiasedDownload(uploadedFile);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Download failed";
      const needsOriginalCsv =
        !uploadedFile &&
        /original dataset not available|raw uploaded data is not available|re-upload the csv/i.test(message);

      if (needsOriginalCsv) {
        setLoadError("Choose the original CSV once so we can generate the debiased dataset.");
        setFilePickerMode("download");
        fileInputRef.current?.click();
        return;
      }

      setLoadError(message);
    }
  };

  const handleRemediateClick = () => {
    setFilePickerMode("upload");
    fileInputRef.current?.click();
  };

  const handleToggleView = async () => {
    if (!audit?.audit_id || !audit?.sensitive_col) return;
    setIsUploading(true);
    try {
      const stats = await getDashboardStats([audit.sensitive_col], viewMode === "raw");
      setDashboard(stats);
      setViewMode(viewMode === "raw" ? "debiased" : "raw");
    } catch (err) {
      setLoadError(err instanceof Error ? err.message : "Failed to switch views");
    } finally {
      setIsUploading(false);
    }
  };

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file || !audit) return;

    const mode = filePickerMode || "upload";

    setLoadError(null);
    try {
      if (mode === "download") {
        await runDebiasedDownload(file);
        return;
      }

      setIsUploading(true);
      const newAudit = await uploadDataset(file, {
        targetCol: audit.target_col,
        sensitiveCol: audit.sensitive_col,
        domain: audit.domain || "custom",
      });
      setAudit(newAudit);
      setUploadedFile(file);
      saveLastAudit(newAudit);
      if (newAudit.sensitive_col) {
        const stats = await getDashboardStats([newAudit.sensitive_col], false);
        setDashboard(stats);
        setViewMode("raw");
      }
    } catch (err) {
      setLoadError(err instanceof Error ? err.message : mode === "download" ? "Download failed" : "Upload failed");
    } finally {
      setIsUploading(false);
      setFilePickerMode(null);
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };

  useEffect(() => {
    let cancelled = false;

    async function loadAudit() {
      const cachedAudit = readLastAudit();
      if (cachedAudit) {
        setAudit(cachedAudit);
      }

      try {
        let latestAudit: FairnessAudit;
        try {
          latestAudit = await getCurrentAudit();
        } catch (currentAuditError) {
          if (!cachedAudit?.audit_id) {
            throw currentAuditError;
          }
          latestAudit = await getSavedAudit(cachedAudit.audit_id);
        }

        if (cancelled) {
          return;
        }

        setAudit(latestAudit);
        saveLastAudit(latestAudit);
        setLoadError(null);

        if (latestAudit.sensitive_col) {
          try {
            const stats = await getDashboardStats([latestAudit.sensitive_col], viewMode === "debiased");
            if (!cancelled) {
              setDashboard(stats);
            }
          } catch {
            if (!cancelled) {
              setDashboard(null);
            }
          }
        }
      } catch (error) {
        if (!cancelled) {
          setAudit(null);
          setDashboard(null);
          setLoadError(error instanceof Error ? error.message : "Could not load audit data.");
        }
      }
    }

    loadAudit();
    return () => {
      cancelled = true;
    };
  }, [viewMode]);

  const targetResult = useMemo(() => {
    if (!audit) return null;
    if (viewMode === "raw") {
      // Show unmodified baseline so users see the starting point.
      return audit.results.find(r => r.model.toLowerCase().includes("baseline")) || getWorstResult(audit);
    }
    // Show EG (Fair in-processing) — it improves demographic parity DI directly.
    // ThresholdOptimizer targets TPR parity, which can worsen DI on some datasets.
    return (
      audit.results.find(r => r.model.toLowerCase().includes("fair in-processing") || r.model.toLowerCase().includes("stage 1")) ||
      audit.results.find(r => r.model.toLowerCase().includes("threshold optimizer")) ||
      getWorstResult(audit)
    );
  }, [audit, viewMode]);

  const parityData = useMemo(() => buildParityData(audit, dashboard), [audit, dashboard]);
  const scatterData = useMemo(() => buildScatterData(dashboard, audit), [dashboard, audit]);
  const vulnerabilities = useMemo(
    () => buildVulnerabilities(audit, dashboard, loadError, viewMode),
    [audit, dashboard, loadError, viewMode],
  );

  // Use model-prediction DI (changes with raw/debiased viewMode).
  // dashboard.di_ratios is raw-data approval rate DI — shown in the bar chart already.
  const mainDiRatio = targetResult?.disparate_impact_ratio
    ?? (audit?.sensitive_col ? dashboard?.di_ratios?.[audit.sensitive_col] : undefined);

  const overallRisk = riskLabel(mainDiRatio);
  const diPass = typeof mainDiRatio === "number"
    ? mainDiRatio >= FAIRNESS_THRESHOLD
    : false;
  const demographicParity = metricStatus(targetResult?.demographic_parity_difference);
  const equalizedOdds = metricStatus(targetResult?.equalized_odds_difference);

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
          <div className="flex items-center gap-3">
            <motion.button
              onClick={handleDownloadDebiasedClick}
              disabled={isDownloading || !audit}
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.98 }}
              className={`px-6 py-3 bg-indigo-500/10 border border-indigo-500/30 text-indigo-400 text-[10px] uppercase tracking-widest font-mono font-bold rounded flex items-center gap-2 whitespace-nowrap self-start md:self-auto ${isDownloading || !audit ? "opacity-50 cursor-not-allowed" : ""}`}
            >
              <Cpu size={14} className={isDownloading ? "animate-spin" : ""} />
              {isDownloading ? "Downloading..." : "Download Debiased Dataset"}
            </motion.button>

            <motion.button
              onClick={handleRemediateClick}
              disabled={isUploading || !audit}
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.98 }}
              className={`px-6 py-3 bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-[10px] uppercase tracking-widest font-mono font-bold rounded flex items-center gap-2 whitespace-nowrap self-start md:self-auto ${isUploading || !audit ? "opacity-50 cursor-not-allowed" : ""}`}
            >
              <Cpu size={14} className={isUploading ? "animate-pulse text-emerald-300" : ""} />
              {isUploading ? "Uploading..." : "Remediate Model"}
            </motion.button>
            
            <motion.button
              onClick={handleToggleView}
              disabled={isUploading || !audit}
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.98 }}
              className={`px-6 py-3 bg-blue-500/10 border border-blue-500/30 text-blue-400 text-[10px] uppercase tracking-widest font-mono font-bold rounded flex items-center gap-2 whitespace-nowrap self-start md:self-auto ${isUploading || !audit ? "opacity-50 cursor-not-allowed" : ""}`}
            >
              <Cpu size={14} className={isUploading ? "animate-pulse text-blue-300" : ""} />
              {isUploading ? "Loading..." : viewMode === "raw" ? "View Debiased Model" : "View Raw Model"}
            </motion.button>
            <input
              type="file"
              accept=".csv"
              ref={fileInputRef}
              onChange={handleFileChange}
              className="hidden"
            />
          </div>
        </header>

        {bannerVisible && downloadSummary && (
          <motion.div 
            initial={{ opacity: 0, y: -10 }} 
            animate={{ opacity: 1, y: 0 }} 
            className="w-full bg-emerald-500/10 border border-emerald-500/30 rounded p-4 flex flex-col md:flex-row items-start md:items-center justify-between gap-4"
          >
            <div>
              <h3 className="text-emerald-400 font-bold text-sm uppercase tracking-widest font-mono mb-1">Debiased Dataset Ready</h3>
              <p className="text-emerald-200/80 text-sm">
                Re-upload this exported file with &quot;Remediate Model&quot; if you want to audit the debiased version side by side.
              </p>
            </div>
            <div className="bg-black/40 p-3 rounded border border-emerald-500/20 text-xs font-mono text-zinc-300 space-y-1">
              <p><span className="text-zinc-500">Rows changed:</span> <span className="text-emerald-400">{downloadSummary.rows_changed}</span> ({downloadSummary.pct_changed}%)</p>
              <p><span className="text-zinc-500">DI ratio improved:</span> <span className="text-rose-400">{downloadSummary.original_di_ratio}</span> → <span className="text-emerald-400">{downloadSummary.debiased_di_ratio}</span></p>
            </div>
            <button onClick={() => setBannerVisible(false)} className="text-emerald-500/50 hover:text-emerald-500 absolute top-4 right-4 md:static">
              ✕
            </button>
          </motion.div>
        )}

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
                        <div className={`text-5xl font-light ${diPass ? "text-emerald-400" : "text-rose-400"}`}>{overallRisk}</div>
                    </div>
                    <div className="space-y-3">
                        <div className="flex justify-between border-b border-white/5 pb-2">
                            <span className="text-xs text-zinc-400">Disparate Impact ratio</span>
                            <span className={`text-xs font-mono ${diPass ? "text-emerald-400" : "text-rose-400"}`}>
                              {formatRatio(mainDiRatio)} {diPass ? ">=" : "<"} 0.8 ({diPass ? "Pass" : "Fail"})
                            </span>
                        </div>
                        {typeof audit?.verified_di_ratio_after_retraining === "number" && (
                          <div className="flex justify-between border-b border-white/5 pb-2">
                            <span className="text-xs text-zinc-400">DI after remediation</span>
                            <span className={`text-xs font-mono ${audit.verified_di_ratio_after_retraining >= FAIRNESS_THRESHOLD ? "text-emerald-400" : "text-rose-400"}`}>
                              {formatRatio(audit.verified_di_ratio_after_retraining)} ({audit.verified_di_ratio_after_retraining >= FAIRNESS_THRESHOLD ? "Pass" : "Fail"})
                            </span>
                          </div>
                        )}
                        <div className="flex justify-between border-b border-white/5 pb-2">
                            <span className="text-xs text-zinc-400">Demographic Parity</span>
                            <span className="text-xs font-mono text-amber-400">{demographicParity}</span>
                        </div>
                        <div className="flex justify-between pb-2">
                            <span className="text-xs text-zinc-400">Equal Opportunity</span>
                            <span className="text-xs font-mono text-emerald-400">{equalizedOdds}</span>
                        </div>
                    </div>
                </div>
             </div>

             <div className="border border-white/5 bg-[#0a0a0a] p-6 rounded-lg">
                <span className="text-[10px] uppercase tracking-widest font-mono text-zinc-500 block mb-4">Detected Vulnerabilities</span>
                <ul className="space-y-3">
                    {vulnerabilities.map((item) => {
                      const classes = vulnerabilityClassNames(item.tone);
                      return (
                        <li key={`${item.title}-${item.detail}`} className={classes.item}>
                          <AlertCircle size={16} className={classes.icon} />
                          <div className="space-y-1">
                              <p className={classes.title}>{item.title}</p>
                              <p className="text-[10px] text-zinc-500">{item.detail}</p>
                          </div>
                        </li>
                      );
                    })}
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
                      tick={{ fill: "#71717a", fontSize: 10, fontFamily: "monospace" }}
                      dy={10}
                    />
                    <YAxis
                      domain={[0, Math.max(0.1, ...parityData.map(d => d.value)) * 1.2]}
                      axisLine={false}
                      tickLine={false}
                      tick={{ fill: "#71717a", fontSize: 10, fontFamily: "monospace" }}
                    />
                    <Tooltip
                      cursor={{fill: "#ffffff02"}}
                      contentStyle={{ backgroundColor: "#000", border: "1px solid #ffffff10", borderRadius: "4px", fontSize: "12px" }}
                      itemStyle={{ color: "#fff" }}
                      formatter={(value) => formatPercent(Number(value))}
                    />
                    <Bar dataKey="value" radius={[2, 2, 0, 0]}>
                      {parityData.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={entry.value < FAIRNESS_THRESHOLD ? "#fb7185" : "#34d399"} />
                      ))}
                      <LabelList
                        dataKey="value"
                        position="top"
                        formatter={(v: any) => (v !== undefined && v !== null) ? `${Math.round(Number(v) * 100)}%` : ""}
                        style={{ fill: "#a1a1aa", fontSize: 10, fontFamily: "monospace" }}
                      />
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
                    <XAxis type="number" dataKey="x" domain={[0, 100]} axisLine={false} tickLine={false} tick={{ fill: "#71717a", fontSize: 10 }} />
                    <YAxis type="number" dataKey="y" domain={[0, 100]} axisLine={false} tickLine={false} tick={{ fill: "#71717a", fontSize: 10 }} />
                    <ZAxis type="number" dataKey="z" range={[20, 400]} />
                    <Tooltip
                       cursor={{strokeDasharray: "3 3", stroke: "#ffffff20"}}
                       content={({ active, payload }) => {
                        if (active && payload && payload.length) {
                          return (
                            <div className="bg-black border border-white/10 p-2 text-xs rounded shadow-xl">
                              <p className="text-emerald-400 font-mono">{`${payload[0].payload.name}`}</p>
                              <p className="text-zinc-400 mt-1">Impact: {payload[0].payload.impactLabel}</p>
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
