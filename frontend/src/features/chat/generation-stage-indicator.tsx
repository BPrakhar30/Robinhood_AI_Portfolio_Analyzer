"use client";

import { useEffect, useMemo, useState } from "react";
import { getGenerationStages } from "./chat-suggestions";

export function GenerationStageIndicator({ question }: { question: string }) {
  const stages = useMemo(() => getGenerationStages(question), [question]);
  const [stageIndex, setStageIndex] = useState(0);
  const label = stages[Math.min(stageIndex, stages.length - 1)] ?? "Thinking";

  useEffect(() => {
    const id = window.setInterval(() => {
      setStageIndex((prev) => (prev + 1) % stages.length);
    }, 1800);
    return () => window.clearInterval(id);
  }, [stages.length]);

  return (
    <div className="inline-flex items-center gap-2 text-muted-foreground">
      <span className="relative flex h-4 w-4 items-center justify-center">
        <span className="absolute h-4 w-4 rounded-full border-2 border-amber-500/20" />
        <span className="absolute h-4 w-4 animate-spin rounded-full border-2 border-transparent border-t-amber-500 border-r-amber-500" />
      </span>
      <span className="text-xs font-medium">{label}</span>
    </div>
  );
}
