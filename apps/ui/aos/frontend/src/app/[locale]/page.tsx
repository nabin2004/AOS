import type { Metadata } from "next";
import {
  Download,
  Lock,
  Quote,
  RefreshCw,
  Search,
  Smartphone,
  ThumbsUp,
  Users,
  Workflow,
} from "lucide-react";
import { getTranslations } from "next-intl/server";

import type { Locale } from "@/i18n";
import { pageMetadata } from "@/lib/seo";

import { CaseStudy } from "@/components/marketing/case-study";
import { ComparisonTable } from "@/components/marketing/comparison-table";
import { DataFlowDiagram } from "@/components/marketing/data-flow-diagram";
import { EnterpriseSecurity } from "@/components/marketing/enterprise-security";
import { FaqAccordion } from "@/components/marketing/faq-accordion";
import { FeatureBento } from "@/components/marketing/feature-bento";
import { FeatureMockup } from "@/components/marketing/feature-mockup";
import { FinalCta } from "@/components/marketing/final-cta";
import { IntegrationsGrid } from "@/components/marketing/integrations-grid";
import { OutcomesBand } from "@/components/marketing/outcomes-band";
import {
  buildFooterColumns,
  buildFooterLegal,
  buildMarketingNav,
} from "@/components/marketing/footer-config";
import { Hero } from "@/components/marketing/hero";
import { HowItWorks } from "@/components/marketing/how-it-works";
import { LogosStrip } from "@/components/marketing/logos-strip";
import { MarketingFooter } from "@/components/marketing/marketing-footer";
import { Marquee } from "@/components/marketing/marquee";
import { PillNav } from "@/components/marketing/pill-nav";
import { PricingTeaser } from "@/components/marketing/pricing-teaser";
import { Reveal } from "@/components/marketing/reveal";
import { Section } from "@/components/marketing/section";
import { SmoothScroll } from "@/components/marketing/smooth-scroll";
import { TestimonialGrid } from "@/components/marketing/testimonial-grid";
import { JsonLd } from "@/components/seo/json-ld";
import { APP_NAME, ROUTES } from "@/lib/constants";
import { faqSchema, organizationSchema, websiteSchema } from "@/lib/schema-org";

const LOGOS = [
  { brand: "github" as const, name: "GitHub" },
  { brand: "google" as const, name: "Google" },
  { brand: "microsoft" as const, name: "Microsoft" },
  { brand: "vercel" as const, name: "Vercel" },
  { brand: "aws" as const, name: "AWS" },
  { brand: "notion" as const, name: "Notion" },
  { brand: "slack" as const, name: "Slack" },
  { brand: "dropbox" as const, name: "Dropbox" },
];

const MARQUEE_ITEMS = [
  "Classify",
  "Pedagogy",
  "Storyboard",
  "LaTeX Math",
  "Manim CE",
  "Scene Layout",
  "Beat Timing",
  "Kyutai DSM",
  "Word Alignment",
  "Self-Repair",
  "Docker Render",
  "60 FPS MP4",
  "LectureIR",
  "EduClaw RAG",
  "Manim Slides",
  "DBOS Durable",
];

const TESTIMONIALS = [
  {
    quote:
      "Creating 3Blue1Brown-quality linear algebra animations used to take 20 hours of manual Manim coding per lecture. AOS drafts the scenes, LaTeX formulas, and synchronized narration in under five minutes.",
    name: "Dr. Elena Rostova",
    title: "Associate Professor of Mathematics",
    company: "State University",
  },
  {
    quote:
      "The beat-synchronized voiceover with Kyutai DSM word timestamps is unreal. No more wasting weekends manually nudging audio waveforms in Premiere to line up with mathematical transitions.",
    name: "Marcus Chen",
    title: "STEM Creator & Animator",
    company: "VisualMath Studio",
  },
  {
    quote:
      "The self-correcting validation and repair loop makes sure our LaTeX equations and SceneObjects compile cleanly in Docker every time without animation glitches.",
    name: "Sarah Jenkins",
    title: "Curriculum Lead",
    company: "Open STEM Initiative",
  },
];

const PLANS = [
  {
    name: "Open Source / Local",
    price: "$0",
    cadence: "/ month",
    description: "For researchers and self-hosters running locally.",
    features: [
      "Full local CLI & Ollama support",
      "Resident Pocket TTS CPU narration",
      "Local Docker ManimCE render",
      "Community GitHub support",
    ],
    cta: { label: "Get Started Free", href: ROUTES.REGISTER },
  },
  {
    name: "Creator Pro",
    price: "$19",
    cadence: "/ creator / month",
    description: "For educators and creators generating high-res videos.",
    features: [
      "Cloud GPU accelerated rendering",
      "Kyutai DSM studio-quality voices",
      "1080p & 4K 60fps video exports",
      "Interactive Manim Slides generation",
      "Live IR inspector & scene editor",
    ],
    cta: { label: "Start Free Trial", href: ROUTES.REGISTER },
    featured: true,
    badge: "Most Popular",
  },
  {
    name: "Academic & Campus",
    price: "Custom",
    cadence: "",
    description: "For universities, departments, and course creators.",
    features: [
      "Everything in Creator Pro",
      "Dedicated Docker render cluster",
      "Custom fine-tuned Qwen coder models",
      "LMS export (Canvas & Blackboard)",
      "SSO, RBAC & Priority SLA",
    ],
    cta: { label: "Contact Us", href: ROUTES.CONTACT },
  },
];

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: Locale }>;
}): Promise<Metadata> {
  const { locale } = await params;
  const t = await getTranslations({ locale, namespace: "marketing.landing" });
  return pageMetadata({
    title: APP_NAME,
    description: t("metaDescription"),
    path: "/",
    locale,
  });
}

export default async function HomePage() {
  const t = await getTranslations("marketing.landing");
  const tNav = await getTranslations("marketing");

  const navLinks = buildMarketingNav((k) => tNav(k));
  const footerColumns = buildFooterColumns((k) => tNav(k));
  const footerLegal = buildFooterLegal((k) => tNav(k));

  const heroStats = [
    { value: "10k", label: t("hero.stat_teams") },
    { value: "98%", label: t("hero.stat_speed") },
    { value: "24/7", label: t("hero.stat_uptime") },
  ];
  const faqItems = t.raw("faq.items") as { q: string; a: string }[];

  return (
    <>
      <SmoothScroll />
      <JsonLd data={[organizationSchema(), websiteSchema(), faqSchema(faqItems)]} />

      <PillNav
        brand={APP_NAME}
        links={navLinks}
        ctaLabel={tNav("nav.getStarted")}
        ctaHref={ROUTES.REGISTER}
        secondaryCta={{ label: tNav("nav.signIn"), href: ROUTES.LOGIN }}
      />

      <main id="main">
        <Hero
          eyebrow={t("hero.eyebrow")}
          title={
            <>
              {t("hero.titlePre")} <em>{t("hero.titleHighlight")}</em> <em>{t("hero.titleEm")}</em>
            </>
          }
          description={t("hero.description")}
          primaryCta={{ label: t("hero.ctaPrimary"), href: ROUTES.REGISTER }}
          secondaryCta={{ label: t("hero.ctaSecondary"), href: ROUTES.CONTACT }}
          ratingLabel={t("hero.ratingLabel")}
          trustNote={t("hero.trustNote")}
          stats={heroStats}
          theme="dark"
        />

        <Marquee items={MARQUEE_ITEMS} />

        <Section theme="light" padding="py-16 md:py-20">
          <Reveal>
            <LogosStrip label="Engineered for open-source AI, mathematical computing & visual education" logos={LOGOS} />
          </Reveal>
        </Section>

        <Section theme="dark" id="how">
          <div className="mb-14 max-w-2xl">
            <div className="mb-5">
              <span className="eyebrow-badge">How it works</span>
            </div>
            <h2 className="text-display-lg text-foreground [&_em]:font-accent [&_em]:font-normal [&_em]:italic">
              Get started in <em>three steps.</em>
            </h2>
          </div>
          <Reveal>
            <HowItWorks />
          </Reveal>
        </Section>

        <Section theme="light">
          <Reveal>
            <OutcomesBand />
          </Reveal>
        </Section>

        <Section theme="dark" id="features">
          <Reveal>
            <FeatureBento
              eyebrow="Agentic Orchestration"
              title={
                <>
                  Pydantic AI <em>Lecture Graph.</em>
                </>
              }
              description="A multi-agent cognitive architecture decomposes complex STEM subjects into pedagogical outlines, visual scenes, and granular animation beats."
              cta={{ label: "Explore the pipeline", href: ROUTES.CHAT }}
              mockup={<FeatureMockup kind="agents" className="max-w-none" />}
              mockupSide="left"
              stat={{ value: "9 Agents", label: "collaborating in real time" }}
              bullets={[
                {
                  icon: Workflow,
                  title: "Pedagogical Storyboarding",
                  body: "Classifies audience prerequisites and scaffolds concepts visually from intuition to formal proof.",
                },
                {
                  icon: RefreshCw,
                  title: "Autonomous Repair Loop",
                  body: "Validates AST schemas and recompiles syntax errors automatically before rendering.",
                },
                {
                  icon: Lock,
                  title: "Durable DBOS Workflows",
                  body: "Step-level checkpointing guarantees pipeline resumption if a process or render gets interrupted.",
                },
              ]}
            />
          </Reveal>
        </Section>

        <Section theme="light">
          <Reveal>
            <FeatureBento
              eyebrow="Pedagogical RAG"
              title={
                <>
                  EduClaw <em>Knowledge Ingestion.</em>
                </>
              }
              description="Ingest textbooks, research papers, and course syllabi. EduClaw extracts mathematical theorems and maps core concepts directly to visual animation cues."
              cta={{ label: "View knowledge base", href: ROUTES.RAG }}
              mockup={<FeatureMockup kind="rag" className="max-w-none" />}
              mockupSide="right"
              stat={{ value: "100%", label: "LaTeX formula fidelity" }}
              bullets={[
                {
                  icon: Quote,
                  title: "LaTeX MathTex Native",
                  body: "Flawless rendering of complex equations, matrices, integrals, and coordinate systems.",
                },
                {
                  icon: Search,
                  title: "Concept-to-Scene Mapping",
                  body: "Automatically queries syllabus definitions to ground every visual beat in textbook clarity.",
                },
                {
                  icon: Smartphone,
                  title: "Multimodal Video & Slides",
                  body: "Outputs standard MP4 videos or interactive Manim Slides for web and live presentations.",
                },
              ]}
            />
          </Reveal>
        </Section>

        <Section theme="dark">
          <Reveal>
            <FeatureBento
              eyebrow="Studio Engine"
              title={
                <>
                  60 FPS <em>Docker Rendering.</em>
                </>
              }
              description="High-speed containerized Manim rendering paired with Kyutai DSM speech synthesis. Millisecond-accurate word timestamps keep audio locked to visual animations."
              cta={{ label: "Inspect render studio", href: ROUTES.DASHBOARD }}
              mockup={<FeatureMockup kind="billing" className="max-w-none" />}
              mockupSide="left"
              stat={{ value: "60 FPS", label: "smooth vector animations" }}
              bullets={[
                {
                  icon: Users,
                  title: "Kyutai DSM Audio Alignment",
                  body: "Delayed Streams Modeling produces studio-grade narration with native word-level timestamps.",
                },
                {
                  icon: ThumbsUp,
                  title: "Persistent Docker Containers",
                  body: "Pre-warmed render environments eliminate cold start latency for rapid scene compilation.",
                },
                {
                  icon: Download,
                  title: "Direct Code & Video Export",
                  body: "Download raw compilable Manim Python scripts, LectureIR JSON, or 1080p/4K video assets.",
                },
              ]}
            />
          </Reveal>
        </Section>

        <Section theme="light" className="relative overflow-hidden">
          <div aria-hidden className="bg-dots pointer-events-none absolute inset-0 -z-10" />
          <div className="mb-14 max-w-2xl">
            <div className="mb-5">
              <span className="eyebrow-badge">The AOS Pipeline</span>
            </div>
            <h2 className="text-display-lg text-foreground [&_em]:font-accent [&_em]:font-normal [&_em]:italic">
              From raw concept. <em>To cinematic animation.</em>
            </h2>
            <p className="text-foreground/70 mt-5 max-w-xl text-lg leading-relaxed">
              Every lecture travels through our structured Pydantic AI graph. Agents architect visual scenes, write verified Manim code, align Kyutai speech timestamps, and Docker renders the final video.
            </p>
          </div>
          <Reveal>
            <DataFlowDiagram />
          </Reveal>
        </Section>

        <Section theme="dark" id="security">
          <Reveal>
            <EnterpriseSecurity cta={{ label: "Read our architecture overview", href: ROUTES.SECURITY }} />
          </Reveal>
        </Section>

        <Section theme="light">
          <Reveal>
            <IntegrationsGrid cta={{ label: "Browse all integrations", href: ROUTES.HELP }} />
          </Reveal>
        </Section>

        <Section theme="dark">
          <Reveal>
            <CaseStudy
              quote="AOS transformed how we create university-level physics and calculus animations. Visualizing complex differential equations used to take our animator weeks — now we produce verified, synchronized videos before each class."
              name="Dr. Julian Vance"
              role="Director of Digital Pedagogy"
              company="Cambridge STEM Lab"
              metrics={[
                { value: "−92%", label: "production turnaround time" },
                { value: "60 FPS", label: "native render quality" },
                { value: "100%", label: "LaTeX formula accuracy" },
              ]}
            />
          </Reveal>
        </Section>

        <Section theme="light">
          <div className="mb-14 text-center">
            <p className="eyebrow text-foreground/55 mb-4">{t("testimonials.eyebrow")}</p>
            <h2 className="text-display-lg text-foreground [&_em]:font-accent mx-auto max-w-2xl [&_em]:font-normal [&_em]:italic">
              {t("testimonials.titlePre")} <em>{t("testimonials.titleEm")}</em>
            </h2>
          </div>
          <Reveal>
            <TestimonialGrid items={TESTIMONIALS} />
          </Reveal>
        </Section>

        <Section theme="light">
          <Reveal>
            <ComparisonTable
              brand={APP_NAME}
              alternatives={["Manual Manim Scripting", "Slide Decks / Screencasts"]}
              rows={[
                { feature: "AI Pedagogical Planning & Outlines", cells: ["yes", "no", "no"] },
                { feature: "Automated Manim Scene Synthesis", cells: ["yes", "no", "no"] },
                { feature: "Word-Aligned Voiceover (Kyutai DSM)", cells: ["yes", "no", "no"] },
                { feature: "3Blue1Brown-Grade Vector Visuals", cells: ["yes", "yes", "no"] },
                { feature: "Autonomous Schema Repair & Linting", cells: ["yes", "no", "no"] },
                { feature: "Fast Dockerized Container Rendering", cells: ["yes", "partial", "yes"] },
                { feature: "Interactive Manim Slides Export", cells: ["yes", "partial", "partial"] },
                { feature: "Self-Hosted & Local Model Support", cells: ["yes", "yes", "partial"] },
              ]}
            />
          </Reveal>
        </Section>

        <Section theme="dark" id="pricing">
          <div className="mb-14 max-w-2xl">
            <div className="mb-5">
              <span className="eyebrow-badge">{t("pricing.eyebrow")}</span>
            </div>
            <h2 className="text-display-lg text-foreground [&_em]:font-accent [&_em]:font-normal [&_em]:italic">
              {t("pricing.titlePre")} <em>{t("pricing.titleEm")}</em>
            </h2>
            <p className="text-foreground/70 mt-5 max-w-xl text-lg leading-relaxed">
              {t("pricing.subtitle")}
            </p>
          </div>
          <Reveal>
            <PricingTeaser plans={PLANS} fullPricingHref={ROUTES.PRICING} />
          </Reveal>
        </Section>

        <Section theme="light" id="faq">
          <div className="mb-14 text-center">
            <p className="eyebrow text-foreground/55 mb-4">{t("faq.eyebrow")}</p>
            <h2 className="text-display-lg text-foreground">{t("faq.title")}</h2>
          </div>
          <Reveal>
            <FaqAccordion
              items={faqItems.map((it) => ({ ...it, q: it.q.replace("{appName}", APP_NAME) }))}
            />
          </Reveal>
        </Section>

        <Section theme="light" padding="pb-24 md:pb-32">
          <Reveal>
            <FinalCta
              stat={{ value: t("finalCta.statValue"), label: t("finalCta.statLabel") }}
              title={
                <>
                  {t("finalCta.titlePre")} <em>{t("finalCta.titleEm")}</em>
                </>
              }
              description={t("finalCta.description")}
              primary={{ label: t("finalCta.primary"), href: ROUTES.REGISTER }}
              secondary={{ label: t("finalCta.secondary"), href: ROUTES.PRICING }}
            />
          </Reveal>
        </Section>
      </main>

      <MarketingFooter
        brand={APP_NAME}
        tagline={tNav("footer.tagline")}
        operationalLabel={tNav("footer.operational")}
        columns={footerColumns}
        legal={footerLegal}
      />
    </>
  );
}

