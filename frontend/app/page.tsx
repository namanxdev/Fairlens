import { Navbar } from "@/components/navbar";
import { HeroAwwwards } from "@/components/hero-awwwards";
import { FeaturesBento } from "@/components/features-bento";
import { CtaSection } from "@/components/cta-section";
import { Footer } from "@/components/footer";

export default function Home() {
  return (
    <>
      <Navbar />
      <main className="flex flex-col min-h-[100dvh] bg-[#060606]">
        <HeroAwwwards />
        <FeaturesBento />
        <CtaSection />
      </main>
      <Footer />
    </>
  );
}
