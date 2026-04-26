"use client";

import {
  ChevronLeft,
  ChevronRight,
  Copy,
  Plus,
  RotateCw,
  Share,
} from "lucide-react";
import React from "react";

import { AvatarGroup } from "@/components/avatar-group";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { useGoogleFont } from "@/hooks/use-google-font";
import { cn } from "@/lib/utils";

interface Hero206Props {
  className?: string;
}

const Hero206 = ({ className }: Hero206Props) => {
  useGoogleFont("Antonio");
  return (
    <section
      className={cn("bg-background", className)}
      style={{ "--font-antonio": "Antonio, sans-serif" } as React.CSSProperties}
    >
      <div className="relative container py-32">
        <header className="mx-auto max-w-3xl text-center">
          <h1 className="text-5xl font-semibold tracking-tight text-foreground md:text-7xl">
            Detect AI Bias. <br /> Build Fairer Models.
          </h1>
          <p className="my-7 font-sans tracking-tight text-muted-foreground md:text-xl">
            Enterprise-grade diagnostic tool to automatically detect, explain, and mitigate bias in your AI models. Protect your users, comply with regulations, and ship responsibly.
          </p>
        </header>

        <Badge
          variant="outline"
          className="mx-auto mt-10 flex h-auto w-fit cursor-pointer gap-3 p-1.5 pr-4 text-base font-normal transition-all ease-in-out hover:gap-4 border-emerald-500/20 bg-emerald-500/10 text-emerald-400"
        >
          <div className="flex h-8 items-center gap-2">
            <span className="relative flex h-2 w-2 ml-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
            </span>
            <p className="tracking-tight md:text-md">
              <span className="font-bold text-emerald-400">FairLens v2.0</span> is now correctly formatted.
            </p>
          </div>
        </Badge>

        <div className="relative mt-12 flex h-full w-full flex-col items-center justify-center">
          <BrowserMockup
            className="w-full"
            url="app.fairlens.dev/diagnostics"
            DahboardUrlDesktop="https://images.unsplash.com/photo-1551288049-bebda4e38f71?auto=format&fit=crop&q=80&w=2070"
            DahboardUrlMobile="https://images.unsplash.com/photo-1551288049-bebda4e38f71?auto=format&fit=crop&q=80&w=800"
          />
          <div className="absolute bottom-0 h-2/3 w-full bg-gradient-to-t from-background to-transparent" />
        </div>
      </div>
    </section>
  );
};

export { Hero206 };

const BrowserMockup = ({
  className = "",
  url = "https://shadcnblocks.com/block/hero206",
  DahboardUrlDesktop = "https://deifkwefumgah.cloudfront.net/shadcnblocks/block/dashboard/dashboard-1.png",
  DahboardUrlMobile = "https://deifkwefumgah.cloudfront.net/shadcnblocks/block/dashboard/dashboard-mobile-1.png",
}) => (
  <div
    className={cn(
      "relative w-full overflow-hidden rounded-4xl border",
      className,
    )}
  >
    <div className="flex items-center justify-between gap-10 bg-muted px-8 py-4 lg:gap-25">
      <div className="flex items-center gap-2">
        <div className="size-3 rounded-full bg-red-500" />
        <div className="size-3 rounded-full bg-yellow-500" />
        <div className="size-3 rounded-full bg-green-500" />
        <div className="ml-6 hidden items-center gap-2 opacity-40 lg:flex">
          <ChevronLeft className="size-5" />
          <ChevronRight className="size-5" />
        </div>
      </div>
      <div className="flex w-full items-center justify-center">
        <p className="relative hidden w-1/3 rounded-full bg-background px-4 py-1 text-center text-sm tracking-tight text-muted-foreground md:block flex items-center justify-center max-w-sm">
          {url}
          <RotateCw className="absolute top-2 right-3 size-3.5 opacity-50" />
        </p>
      </div>

      <div className="flex items-center gap-4 opacity-40">
        <Share className="size-4" />
        <Plus className="size-4" />
        <Copy className="size-4" />
      </div>
    </div>

    <div className="relative w-full">
      <img
        src={DahboardUrlDesktop}
        alt=""
        className="object-cove hidden aspect-video h-full w-full object-top md:block"
      />
      <img
        src={DahboardUrlMobile}
        alt=""
        className="block h-full w-full object-cover md:hidden"
      />
    </div>
    <div className="absolute bottom-0 z-10 flex w-full items-center justify-center bg-muted py-3 md:hidden">
      <p className="relative flex items-center gap-2 rounded-full px-8 py-1 text-center text-sm tracking-tight">
        {url}
      </p>
    </div>
  </div>
);
