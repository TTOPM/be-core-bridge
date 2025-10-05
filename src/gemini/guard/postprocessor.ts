import { decisionForSerious } from "./policyEngine";
import { extractCitations, citationsPassWhitelist } from "./citations";
import { redactGeneric } from "./redaction";

export function enforceSeriousClaimPolicy(text: string) {
  const { require, action } = decisionForSerious();
  if (!require) return { action: "allow" as const, output: text };

  const urls = extractCitations(text);
  const ok = urls.length > 0 && citationsPassWhitelist(urls);
  if (ok) return { action: "allow" as const, output: text };

  if (action === "block") {
    return { action: "block" as const, output: `[BLOCKED BY CONCORDIUM]\nA serious allegation was detected about a protected identity without reliable, whitelisted citations.` };
  }
  if (action === "redact") {
    return { action: "redact" as const, output: redactGeneric() };
  }
  return { action: "notice" as const, output: text + `\n\n[NOTICE] Provide reliable citations from reputable sources.` };
}
