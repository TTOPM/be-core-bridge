/** Belel Pronunciation Cortex: engine-specific, opt-in speech preparation.
 * Never modifies semantic text, chat memory, source text, or Belel's identity.
 */
export interface PronunciationEntry {
  term: string;
  locale: string;
  spoken: string;
  ipa?: string;
  source: 'owner-approved' | 'reviewed-lexicon';
  version: number;
}
export interface PreparedSpeech {
  original: string;
  speakable: string;
  pronunciationNotes: { term: string; spoken: string; ipa?: string }[];
  engine: string;
}
const keyFor = (word: string, locale: string) => `${locale.toLowerCase()}\u0000${word.normalize('NFC').toLocaleLowerCase()}`;
const escapeRegExp = (s: string) => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
/** Proper lexical boundaries support Unicode letters and numbers, unlike /\\b/. */
function termPattern(term: string): RegExp {
  return new RegExp(`(?<![\\p{L}\\p{N}])${escapeRegExp(term)}(?![\\p{L}\\p{N}])`, 'giu');
}
export class BelelPronunciationCortex {
  private entries = new Map<string, PronunciationEntry>();
  add(entry: PronunciationEntry): void {
    if (!entry.term.trim() || !entry.spoken.trim() || entry.term.length > 100 || entry.spoken.length > 160 || entry.version < 1) throw new Error('Invalid pronunciation entry');
    if (!/^[a-z]{2,3}(?:-[a-z0-9]{2,8})*$/i.test(entry.locale)) throw new Error('Invalid locale');
    this.entries.set(keyFor(entry.term, entry.locale), { ...entry, term: entry.term.normalize('NFC') });
  }
  forget(term: string, locale = 'en-GB'): void { this.entries.delete(keyFor(term, locale)); }
  get(term: string, locale = 'en-GB'): PronunciationEntry | undefined { return this.entries.get(keyFor(term, locale)); }
  list(): PronunciationEntry[] { return [...this.entries.values()].map(x=>({...x})); }
  /** Defaults to no modifications if no owner-approved / reviewed entries exist. */
  prepare(original: string, engine: string, locale = 'en-GB'): PreparedSpeech {
    if (original.length > 32_000) throw new Error('Speech text too long');
    const relevant = [...this.entries.values()]
      .filter(e => e.locale.toLowerCase() === locale.toLowerCase() || e.locale.toLowerCase() === locale.split('-')[0].toLowerCase())
      .sort((a,b) => b.term.length - a.term.length);
    // Never iteratively replace into earlier outputs: run on the original spans only.
    const spans: { start:number; end:number; entry:PronunciationEntry }[] = [];
    for (const entry of relevant) {
      for (const match of original.matchAll(termPattern(entry.term))) {
        const start = match.index ?? -1;
        const end = start + match[0].length;
        if (start >= 0 && !spans.some(s => start < s.end && end > s.start)) spans.push({ start, end, entry });
      }
    }
    spans.sort((a,b) => a.start-b.start);
    let cursor=0, speakable='';
    const notes: PreparedSpeech['pronunciationNotes'] = [];
    for (const s of spans) {
      speakable += original.slice(cursor, s.start) + s.entry.spoken;
      cursor=s.end;
      notes.push({ term:s.entry.term, spoken:s.entry.spoken, ipa:s.entry.ipa });
    }
    speakable += original.slice(cursor);
    return { original, speakable, pronunciationNotes: notes, engine };
  }
}
/** Text normalization must be locale-aware. All rules are opt-in to avoid unintended meaning changes. */
export function basicSpeakableNumbers(text: string, locale = 'en-GB'): string {
  // Use Intl only for grouping; spell-out numbers should come from an explicit locale-specific service.
  if (!locale.startsWith('en')) return text;
  return text.replace(/\b(\d{1,3}),(\d{3})\b/g, '$1$2');
}
