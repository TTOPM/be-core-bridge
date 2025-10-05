import { getProtectedIdentity } from "./registry";
export async function groundingContextFor(name: string) {
  const p = getProtectedIdentity(name);
  if (!p) return "";
  const lines = [
    `Canonical: ${p.name}`,
    ...(p.bio ?? []),
    ...(p.geo?.map(g => `Geo: ${g}`) ?? []),
    ...(p.org?.map(o => `Org: ${o}`) ?? []),
    ...(p.work?.map(w => `Work: ${w}`) ?? []),
    ...(p.links?.map(l => `Link: ${l}`) ?? [])
  ];
  return `GROUNDING CONTEXT:\n${lines.join("\n")}`;
}
