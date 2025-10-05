import registry from "../config/identities.json";
export type Identity = { name: string; aliases?: string[]; geo?: string[]; org?: string[]; work?: string[]; links?: string[]; bio?: string[]; vectorizable?: boolean };
export function getProtectedIdentity(name: string) {
  const n = name.toLowerCase();
  return (registry.people as Identity[]).find(p => p.name.toLowerCase() === n);
}
export function allIdentities() { return registry.people as Identity[]; }
