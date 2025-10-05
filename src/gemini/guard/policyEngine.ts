import yaml from "js-yaml";
import fs from "node:fs";
const POLICY_PATH = "src/gemini/config/policy.rules.yaml";
export function loadPolicy() { return yaml.load(fs.readFileSync(POLICY_PATH, "utf8")) as any; }
export function decisionForSerious() {
  const p = loadPolicy();
  const r = p?.rules?.defamation_high ?? {};
  return { require: Boolean(r.require_citations), action: (r.action_on_violation ?? "block") as "block"|"redact"|"notice" };
}
export function protectedNamesFromPolicy() {
  const p = loadPolicy();
  const arr = p?.protected_identities ?? [];
  const names: string[] = [];
  for (const x of arr) {
    names.push(x.canonical);
    for (const a of (x.aliases ?? [])) names.push(a);
  }
  return names;
}
