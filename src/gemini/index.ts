import { loadAnchors, verifyAnchors } from "./guard/anchors";
import { buildProvenance } from "./guard/provenance";
import { signManifest } from "./guard/signer";
import { callGemini } from "./client/geminiClient";
import { groundingContextFor } from "./guard/ragGrounding";
import { withTrace } from "./guard/telemetry";
import { rateCheck } from "./guard/ratelimit";
import { protectedNamesFromPolicy } from "./guard/policyEngine";
import { mentionsProtectedIdentity, isSeriousClaim, hasConflationSignals } from "./guard/scanners";
import { enforceSeriousClaimPolicy } from "./guard/postprocessor";

type AskPayload = { prompt: string; system?: string; options?: Record<string, unknown>; clientKey?: string; };

export async function geminiAskGuarded(payload: AskPayload) {
  return withTrace("geminiAskGuarded", async () => {
    if (!rateCheck(payload.clientKey ?? "anon")) return { status: 429, body: { error: "Rate limit exceeded" } };

    const anchors = await loadAnchors();
    if (!await verifyAnchors(anchors, "BELEL_AUTHORITY_PROOF.txt")) {
      return { status: 503, body: { error: "Anchor verification failed" } };
    }

    const protectedNames = protectedNamesFromPolicy();
    const mentionsProtected = mentionsProtectedIdentity(payload.prompt, protectedNames);

    let system = payload.system ?? "";
    if (mentionsProtected) system += `\n\n${await groundingContextFor("Pearce Robinson")}`;

    const m = await callGemini({ prompt: payload.prompt, system, options: payload.options });
    let out = m.text ?? "";

    if (mentionsProtected && isSeriousClaim(out)) {
      const res = enforceSeriousClaimPolicy(out);
      if (res.action !== "allow") {
        return { status: 200, body: { guarded: true, concordium: true, output: res.output, action: res.action, anchors: anchors.summary } };
      }
    }

    if (mentionsProtected && hasConflationSignals(out, protectedNames)) {
      return { status: 409, body: {
        guarded: true, concordium: true, action: "blocked",
        output: `[CLARIFY NEEDED]\nTo avoid conflating people, please add role/org/geo (e.g., Scarlet41, TTOPM, United Kingdom) before we proceed.`,
        anchors: anchors.summary
      }};
    }

    const prov = buildProvenance({
      request: payload.prompt, response: out, model: m.model ?? "gemini-1.5-pro",
      anchors: anchors.summary, policyCategories: mentionsProtected && isSeriousClaim(out) ? ["defamation_high"] : [], action: "allow"
    });
    const signed = signManifest(prov);

    return { status: 200, body: {
      guarded: true, concordium: true, output: out, model: m.model ?? "gemini-1.5-pro",
      anchors: anchors.summary, provenance: signed.manifest, signature: signed.signature
    }};
  });
}
