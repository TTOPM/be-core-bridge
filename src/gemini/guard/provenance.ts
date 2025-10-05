import { sha256Hex } from "../utils/hash";
import { merkleNext } from "../utils/merkle";
export function buildProvenance(payload: {
  request: string; response: string; model: string;
  anchors: string[]; policyCategories: string[]; action: string;
}) {
  const reqHash = sha256Hex(payload.request);
  const resHash = sha256Hex(payload.response);
  const step = merkleNext([reqHash, resHash]);
  return {
    manifest_version: 1, model: payload.model, anchors: payload.anchors,
    policy_categories: payload.policyCategories, action: payload.action,
    hashes: { request: reqHash, response: resHash, step_root: step.root },
    timestamp: new Date().toISOString()
  };
}
