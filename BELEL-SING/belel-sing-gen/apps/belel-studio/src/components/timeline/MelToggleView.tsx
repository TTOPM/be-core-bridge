"use client";

import React, { useState } from "react";
import { Card } from "@/components/common/Card";
import { Tabs } from "@/components/common/Tabs";

export function MelToggleView() {
  const [tab, setTab] = useState("Waveform");

  return (
    <div className="space-y-2">
      <div className="flex items-center">
        <div className="text-xs text-white/60">View</div>
        <div className="ml-auto">
          <Tabs tabs={["Waveform", "Mel"]} active={tab} onChange={setTab} />
        </div>
      </div>

      <Card className="p-3">
        {tab === "Waveform" ? (
          <div className="text-xs text-white/60">
            Waveform view active. Step 2 loads real audio + enables A/B loudness match.
          </div>
        ) : (
          <div className="text-xs text-white/60">
            Mel view active. Step 2 will request `/api/mel/preview` for downsampled mel rendering (80 bins).
          </div>
        )}
      </Card>
    </div>
  );
}
