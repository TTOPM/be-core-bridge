"use client";

import React, { useState } from "react";
import { Button } from "@/components/common/Button";

export function ABCompareToggle() {
  const [ab, setAb] = useState<"A" | "B">("A");

  return (
    <Button variant="primary" onClick={() => setAb(ab === "A" ? "B" : "A")}>
      A/B: {ab}
    </Button>
  );
}
