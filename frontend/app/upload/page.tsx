"use client";

import { useState } from "react";
import { UploadCloud, Database, FileText, CheckCircle2 } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { uploadDataset } from "@/lib/api";

export default function UploadPage() {
  const [isHovering, setIsHovering] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [columns, setColumns] = useState<string[]>([]);
  const [targetCol, setTargetCol] = useState("");
  const [sensitiveCol, setSensitiveCol] = useState("");
  const [domain, setDomain] = useState("custom");
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [status, setStatus] = useState<"idle" | "processing" | "complete">("idle");

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsHovering(true);
  };

  const handleDragLeave = () => {
    setIsHovering(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsHovering(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFileSelect(e.dataTransfer.files[0]);
    }
  };

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      handleFileSelect(e.target.files[0]);
    }
  };

  const parseCsvHeader = (headerLine: string) => {
    const headers: string[] = [];
    let value = "";
    let inQuotes = false;

    for (let index = 0; index < headerLine.length; index += 1) {
      const char = headerLine[index];
      const nextChar = headerLine[index + 1];

      if (char === '"' && nextChar === '"') {
        value += '"';
        index += 1;
      } else if (char === '"') {
        inQuotes = !inQuotes;
      } else if (char === "," && !inQuotes) {
        headers.push(value.trim());
        value = "";
      } else {
        value += char;
      }
    }

    headers.push(value.trim());
    return headers.filter(Boolean);
  };

  const handleFileSelect = async (selectedFile: File) => {
    setFile(selectedFile);
    setColumns([]);
    setTargetCol("");
    setSensitiveCol("");
    setUploadError(null);
    setStatus("idle");

    if (!selectedFile.name.toLowerCase().endsWith(".csv")) {
      setUploadError("The ML API accepts CSV files only.");
      return;
    }

    try {
      const preview = await selectedFile.slice(0, 64 * 1024).text();
      const firstLine = preview.split(/\r?\n/).find((line) => line.trim().length > 0);
      const headerColumns = firstLine ? parseCsvHeader(firstLine) : [];

      if (headerColumns.length < 2) {
        setUploadError("Could not read at least two CSV columns.");
        return;
      }

      setColumns(headerColumns);
    } catch (error) {
      const message = error instanceof Error ? error.message : "Could not read CSV headers";
      setUploadError(message);
    }
  };

  const runAudit = async () => {
    if (!file || !targetCol || !sensitiveCol) {
      setUploadError("Select both target and sensitive columns.");
      return;
    }
    if (targetCol === sensitiveCol) {
      setUploadError("Target and sensitive columns must be different.");
      return;
    }

    setUploadError(null);
    setStatus("processing");

    try {
      await uploadDataset(file, { targetCol, sensitiveCol, domain });
      setStatus("complete");
    } catch (error) {
      const message = error instanceof Error ? error.message : "Upload failed";
      setUploadError(message);
      setStatus("idle");
    }
  };

  return (
    <div className="min-h-screen bg-[#060606] text-zinc-300 font-sans selection:bg-emerald-500/30 pt-24 pb-12 px-6 flex flex-col items-center justify-center">
      <div className="w-full max-w-4xl space-y-8">
        <header className="space-y-4">
          <div className="inline-flex items-center space-x-2 border border-white/10 rounded-full px-3 py-1 bg-white/5 backdrop-blur-md">
            <Database className="w-4 h-4 text-emerald-500" />
            <span className="text-[10px] uppercase tracking-widest font-mono text-zinc-400 font-semibold">
              Data Ingestion
            </span>
          </div>
          <h1 className="text-4xl md:text-5xl font-light tracking-tight text-zinc-100">
            Upload Dataset
          </h1>
          <p className="text-zinc-500 max-w-xl text-lg font-light leading-relaxed">
            Provide your tabular dataset (CSV) for comprehensive bias analysis and structural profiling.
          </p>
        </header>

        <div className="relative group perspective-1000">
          <motion.div
            className={`
              relative w-full aspect-[2/1] rounded-2xl flex flex-col items-center justify-center
              border border-white/10 bg-[#0a0a0a] overflow-hidden transition-all duration-700
              ${isHovering ? "border-emerald-500/50 bg-emerald-500/5" : ""}
            `}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
            animate={{
              scale: isHovering && status === "idle" ? 1.02 : 1,
            }}
            transition={{ type: "spring", stiffness: 300, damping: 20 }}
          >
            {/* Ambient Background Glow */}
            <div className="absolute inset-0 bg-gradient-to-br from-white/[0.02] to-transparent pointer-events-none" />

            <AnimatePresence mode="wait">
              {status === "idle" && (
                <motion.div
                  key="idle"
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -10 }}
                  className="flex flex-col items-center gap-6 z-10 w-full px-6"
                >
                  <div className="w-20 h-20 rounded-full bg-white/5 border border-white/10 flex items-center justify-center text-zinc-400 group-hover:text-emerald-400 group-hover:scale-110 transition-all duration-500">
                    <UploadCloud strokeWidth={1} size={32} />
                  </div>
                  <div className="text-center space-y-2">
                    <p className="text-xl text-zinc-200 font-light">
                      {file ? file.name : "Drag & drop your file here"}
                    </p>
                    <p className="text-sm text-zinc-500 font-mono">.csv up to 500MB</p>
                  </div>

                  {columns.length > 0 && (
                    <div className="grid w-full max-w-2xl grid-cols-1 gap-3 md:grid-cols-3">
                      <label className="space-y-2 text-left">
                        <span className="block text-[10px] uppercase tracking-widest font-mono text-zinc-500">Target</span>
                        <select
                          value={targetCol}
                          onChange={(event) => setTargetCol(event.target.value)}
                          className="h-10 w-full rounded border border-white/10 bg-black/60 px-3 text-xs text-zinc-200 outline-none focus:border-emerald-500/50"
                        >
                          <option value="">Select column</option>
                          {columns.map((column) => (
                            <option key={column} value={column}>{column}</option>
                          ))}
                        </select>
                      </label>
                      <label className="space-y-2 text-left">
                        <span className="block text-[10px] uppercase tracking-widest font-mono text-zinc-500">Sensitive</span>
                        <select
                          value={sensitiveCol}
                          onChange={(event) => setSensitiveCol(event.target.value)}
                          className="h-10 w-full rounded border border-white/10 bg-black/60 px-3 text-xs text-zinc-200 outline-none focus:border-emerald-500/50"
                        >
                          <option value="">Select column</option>
                          {columns.map((column) => (
                            <option key={column} value={column}>{column}</option>
                          ))}
                        </select>
                      </label>
                      <label className="space-y-2 text-left">
                        <span className="block text-[10px] uppercase tracking-widest font-mono text-zinc-500">Domain</span>
                        <select
                          value={domain}
                          onChange={(event) => setDomain(event.target.value)}
                          className="h-10 w-full rounded border border-white/10 bg-black/60 px-3 text-xs text-zinc-200 outline-none focus:border-emerald-500/50"
                        >
                          <option value="custom">Custom</option>
                          <option value="jobs">Jobs</option>
                          <option value="banking">Banking</option>
                          <option value="healthcare">Healthcare</option>
                          <option value="education">Education</option>
                        </select>
                      </label>
                    </div>
                  )}

                  {uploadError && (
                    <p className="max-w-2xl text-center text-xs text-rose-300">{uploadError}</p>
                  )}

                  <label className="relative overflow-hidden cursor-pointer group/btn mt-4">
                    <input
                      type="file"
                      className="hidden"
                      accept=".csv"
                      onChange={handleFileInput}
                    />
                    <div className="px-8 py-3 bg-white text-black text-sm font-medium rounded-full shadow-[0_0_40px_-10px_rgba(255,255,255,0.3)] hover:scale-[1.02] transition-transform flex items-center gap-2">
                      <span className="relative z-10 uppercase tracking-wider text-[11px] font-bold">
                        {file ? "Change File" : "Browse Files"}
                      </span>
                    </div>
                  </label>

                  {columns.length > 0 && (
                    <button
                      type="button"
                      onClick={runAudit}
                      disabled={!targetCol || !sensitiveCol || targetCol === sensitiveCol}
                      className="px-8 py-3 bg-emerald-500 disabled:bg-white/10 disabled:text-zinc-600 hover:bg-emerald-400 text-black text-sm font-medium rounded-full hover:scale-[1.02] transition-transform flex items-center gap-2 uppercase tracking-wider text-[11px] font-bold"
                    >
                      Run Audit
                    </button>
                  )}
                </motion.div>
              )}

              {status === "processing" && (
                <motion.div
                  key="processing"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  className="flex flex-col items-center justify-center w-full h-full z-10 relative"
                >
                  {/* Scanning Laser Effect */}
                  <motion.div
                    className="absolute top-0 left-0 w-full h-[1px] bg-emerald-500 shadow-[0_0_15px_bg-emerald-500]"
                    animate={{ y: ["0%", "100%", "0%"] }}
                    transition={{ duration: 3, ease: "linear", repeat: Infinity }}
                  />
                  
                  {/* Abstract Pulsing Lines */}
                  <div className="relative w-64 h-32 flex items-center justify-center gap-2 overflow-hidden mask-image:linear-gradient(to_right,transparent,black,transparent)">
                    {[...Array(12)].map((_, i) => (
                      <motion.div
                        key={i}
                        className="w-1 bg-emerald-500/50 rounded-full"
                        animate={{ height: ["20%", "100%", "20%"] }}
                        transition={{
                          duration: 1,
                          repeat: Infinity,
                          delay: i * 0.1,
                          ease: "easeInOut",
                        }}
                      />
                    ))}
                  </div>
                  <motion.p 
                    className="mt-8 text-emerald-400 font-mono text-[11px] uppercase tracking-widest"
                    animate={{ opacity: [0.5, 1, 0.5] }}
                    transition={{ duration: 1.5, repeat: Infinity }}
                  >
                    Processing Dataset... Detecting Bias Vectors
                  </motion.p>
                </motion.div>
              )}

              {status === "complete" && (
                <motion.div
                  key="complete"
                  initial={{ opacity: 0, scale: 0.95 }}
                  animate={{ opacity: 1, scale: 1 }}
                  className="flex flex-col items-center gap-6 z-10"
                >
                  <div className="w-20 h-20 rounded-full border border-emerald-500/30 bg-emerald-500/10 flex items-center justify-center text-emerald-400">
                    <CheckCircle2 strokeWidth={1} size={40} />
                  </div>
                  <div className="text-center space-y-2">
                    <p className="text-2xl text-zinc-100 font-light">Analysis Complete</p>
                    <p className="text-sm text-zinc-500 flex items-center justify-center gap-2">
                      <FileText size={14} />
                      {file?.name}
                    </p>
                  </div>
                  <div className="mt-6 flex gap-4">
                     <a href="/diagnostics" className="px-8 py-3 bg-emerald-500 hover:bg-emerald-400 text-black text-sm font-medium rounded-full  hover:scale-[1.02] transition-transform flex items-center gap-2 uppercase tracking-wider text-[11px] font-bold block">
                        View Diagnostics
                     </a>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </motion.div>
        </div>
      </div>
    </div>
  );
}
