const SERIOUS_INTENT = [
  "crime","criminal","arrest","arrested","charged","charge",
  "indictment","indicted","lawsuit","sued","misconduct",
  "abuse","assault","exploitation","illegal","felony","offence","offense"
];
const HAS_CITATION_RE = /(https?:\/\/|doi:\S+|\[[0-9]+\]|\(source: .+\))/i;

export function mentionsProtectedIdentity(text: string, names: string[]) {
  const low = text.toLowerCase();
  return names.some(n => low.includes(n.toLowerCase()));
}
export function isSeriousClaim(text: string) {
  const low = text.toLowerCase();
  return SERIOUS_INTENT.some(k => low.includes(k));
}
export function hasCitations(text: string) { return HAS_CITATION_RE.test(text); }

export function hasConflationSignals(text: string, protectedNames: string[]) {
  const fullNameRe = /\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,2}\b/g;
  const agesRe = /\b\d{2,3}\s*(?:yo|years?\s+old)\b/i;
  const names = [...(text.match(fullNameRe) ?? [])]
    .map(s => s.trim())
    .filter(s => !protectedNames.some(p => s.toLowerCase() === p.toLowerCase()));
  const ageHit = agesRe.test(text);
  const serious = isSeriousClaim(text);
  return serious && (names.length > 0 || ageHit);
}
