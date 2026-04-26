"use client";

import { motion } from "framer-motion";
import { ArrowRight, ShieldCheck, Activity, BrainCircuit } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";

export function Hero195() {
  return (
    <section className="relative overflow-hidden bg-background pt-24 md:pt-32 pb-16">
      <div className="container px-4 md:px-6 mx-auto max-w-7xl">
        <div className="grid gap-12 lg:grid-cols-2 lg:gap-8 items-center">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
            className="flex flex-col justify-center space-y-6"
          >
            <Badge variant="secondary" className="w-fit flex items-center gap-1.5 px-3 py-1 text-sm bg-primary/10 text-primary hover:bg-primary/20 border-primary/20">
              <ShieldCheck className="h-4 w-4" />
              FairLens v1.0 is now live
            </Badge>
            
            <div className="space-y-4">
              <h1 className="text-4xl font-extrabold tracking-tight sm:text-5xl xl:text-6xl text-foreground text-balance">
                Detect and Mitigate AI Bias in Real-Time.
              </h1>
              <p className="max-w-[600px] text-muted-foreground md:text-xl text-balance">
                Enterprise-grade fairness profiling, intersectional audits, and LLM explainability designed for compliance-first AI teams.
              </p>
            </div>
            
            <div className="flex flex-col sm:flex-row gap-4 pt-2">
              <Button size="lg" className="h-12 px-8 text-base">
                Start Assessment <ArrowRight className="ml-2 h-4 w-4" />
              </Button>
              <Button size="lg" variant="outline" className="h-12 px-8 text-base border-muted-foreground/20">
                View Documentation
              </Button>
            </div>
            
            <div className="flex items-center gap-4 text-sm text-muted-foreground pt-4">
              <div className="flex items-center gap-1">
                <Activity className="h-4 w-4 text-green-500" /> Continuous Audit
              </div>
              <div className="flex items-center gap-1">
                <BrainCircuit className="h-4 w-4 text-blue-500" /> LLM Ready
              </div>
            </div>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.7, delay: 0.2 }}
            className="mx-auto w-full lg:max-w-[650px]"
          >
            <div className="relative rounded-xl border border-border/50 bg-card/40 backdrop-blur-sm text-card-foreground shadow-2xl overflow-hidden aspect-[4/3] sm:aspect-video lg:aspect-square xl:aspect-video flex flex-col">
              <div className="absolute inset-0 bg-gradient-to-br from-indigo-500/5 via-transparent to-rose-500/5" />
              
              <div className="p-3 border-b border-border/50 bg-muted/20 flex items-center gap-2">
                <div className="flex gap-1.5 pl-1">
                  <div className="h-2.5 w-2.5 rounded-full bg-red-500/80" />
                  <div className="h-2.5 w-2.5 rounded-full bg-yellow-500/80" />
                  <div className="h-2.5 w-2.5 rounded-full bg-green-500/80" />
                </div>
                <div className="text-[10px] text-muted-foreground font-mono ml-2 font-medium tracking-wider">fairlens-dashboard</div>
              </div>
              
              <div className="p-6 flex-1 flex flex-col gap-6 relative z-10">
                <div className="flex items-center justify-between">
                  <div className="space-y-1.5">
                    <div className="h-4 w-32 bg-primary/20 rounded-md" />
                    <div className="h-8 w-48 bg-foreground/10 rounded-md" />
                  </div>
                  <div className="h-10 w-24 bg-muted/50 rounded-full" />
                </div>
                
                <div className="grid grid-cols-2 gap-4">
                  <div className="h-24 bg-muted/30 rounded-lg border border-border/30 p-4 space-y-3">
                    <div className="h-3 w-1/2 bg-foreground/10 rounded" />
                    <div className="h-6 w-3/4 bg-red-500/20 rounded" />
                  </div>
                  <div className="h-24 bg-muted/30 rounded-lg border border-border/30 p-4 space-y-3">
                    <div className="h-3 w-1/2 bg-foreground/10 rounded" />
                    <div className="h-6 w-1/3 bg-green-500/20 rounded" />
                  </div>
                </div>

                <div className="flex-1 bg-muted/20 rounded-lg border border-border/30 p-4">
                  <div className="flex h-full w-full items-end gap-2">
                    {[40, 25, 60, 45, 80, 55, 70].map((height, i) => (
                      <div 
                        key={i} 
                        className="flex-1 bg-primary/20 rounded-t-sm" 
                        style={{ height: `${height}%` }}
                      />
                    ))}
                  </div>
                </div>
              </div>
            </div>
          </motion.div>
        </div>
      </div>
    </section>
  );
}
