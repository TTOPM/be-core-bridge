import { GEMINI_MANDATE } from "./mandate";
export const buildSystemPrompt = (extra?: string) =>
  [GEMINI_MANDATE, extra ?? ""].filter(Boolean).join("\n\n");
