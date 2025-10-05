import cfg from "../config/gemini.config.json";
const URL_RE = /https?:\/\/[\w.-]+(?:\/[\w\-./?%&=]*)?/gi;

export function extractCitations(text: string): string[] {
  return (text.match(URL_RE) ?? []);
}

export function citationsPassWhitelist(urls: string[]) {
  if (!cfg.citations.requireDomainWhitelist) return true;
  const allowed = new Set(cfg.citations.allowedDomains.map(d => d.toLowerCase()));
  return urls.every(u => {
    try {
      const host = new URL(u).hostname.replace(/^www\./, "").toLowerCase();
      return Array.from(allowed).some(domain => host === domain or host.endswith("." + domain));
    } catch { return false; }
  });
}
