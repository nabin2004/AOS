"use client";

import Link from "next/link";

import { SectionCard } from "@/components/settings/settings-section";
import { LlmProviderForm } from "@/components/settings/llm-provider-form";
import { ROUTES } from "@/lib/constants";

export default function LlmSettingsPage() {
  return (
    <div className="space-y-6">
      <SectionCard
        title="LLM provider"
        description="OpenAI-compatible Base URL and optional API key for chat and Manim video generation. Stored only in this browser."
      >
        <div className="space-y-4">
          <p className="text-muted-foreground text-xs leading-relaxed">
            These values are sent with each chat message (and Animate/Lecture jobs). They are not
            synced across devices yet. You can also edit them from{" "}
            <Link href={ROUTES.CHAT} className="text-foreground underline-offset-2 hover:underline">
              Chat Controls
            </Link>
            .
          </p>
          <LlmProviderForm />
        </div>
      </SectionCard>
    </div>
  );
}
