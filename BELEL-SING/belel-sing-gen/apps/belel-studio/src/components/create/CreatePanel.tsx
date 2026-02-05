"use client";

import React, { useMemo, useState } from "react";
import { Card } from "@/components/common/Card";
import { StylePromptBox } from "@/components/create/StylePromptBox";
import { LyricsBox } from "@/components/create/LyricsBox";
import { GenerateButton } from "@/components/create/GenerateButton";
import { LanguagePicker } from "@/components/studio/LanguagePicker";
import { useProjectStore } from "@/lib/state/project.store";
import { useRouter } from "next/navigation";

export function CreatePanel() {
  const router = useRouter();
  const ensureProject = useProjectStore((s) => s.ensureProject);
  const [title, setTitle] = useState("Untitled");
  const [prompt, setPrompt] = useState("");
  const [lyrics, setLyrics] = useState("");
  const [lang, setLang] = useState("en");

  const canCreate = useMemo(() => title.trim().length > 0, [title]);

  return (
    <div className="max-w-[1100px]">
      <div className="mb-4">
        <div className="text-xl font-semibold">Create</div>
        <div className="text-sm text-white/60">
          Start a project, then move into Studio for repaint/extend/retake/lyric_edit.
        </div>
      </div>

      <Card className="p-4">
        <div className="grid grid-cols-[1fr_320px] gap-4">
          <div className="space-y-4">
            <div>
              <div className="text-xs text-white/60 mb-1">Project title</div>
              <input
                className="w-full px-3 py-2 rounded border border-white/10 bg-black/30 text-sm"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
              />
            </div>

            <StylePromptBox value={prompt} onChange={setPrompt} />
            <LyricsBox value={lyrics} onChange={setLyrics} />
          </div>

          <div className="space-y-4">
            <LanguagePicker value={lang} onChange={setLang} />

            <Card className="p-3">
              <div className="text-xs text-white/60 mb-2">Create flow</div>
              <ol className="text-sm text-white/80 list-decimal ml-5 space-y-1">
                <li>Define title / style / lyrics</li>
                <li>Create project shell</li>
                <li>Enter Studio</li>
                <li>Run edits with receipts</li>
              </ol>
            </Card>

            <GenerateButton
              disabled={!canCreate}
              onCreate={() => {
                const id = ensureProject(title.trim());
                router.push(`/studio/${id}`);
              }}
            />
          </div>
        </div>
      </Card>
    </div>
  );
}
