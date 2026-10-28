/** Reproducible performance metrics; no model assertions, no hidden gold standards. */
export interface WakeLabel { expectedWake: boolean; detectedWake: boolean; noise: 'quiet' | 'moderate' | 'high'; }
export function evaluateWakeLabels(labels: readonly WakeLabel[]) {
  const positives = labels.filter(x=>x.expectedWake);
  const negatives = labels.filter(x=>!x.expectedWake);
  const truePositives = positives.filter(x=>x.detectedWake).length;
  const falsePositives = negatives.filter(x=>x.detectedWake).length;
  return {
    trials: labels.length,
    truePositives, falsePositives,
    truePositiveRate: positives.length ? truePositives / positives.length : null,
    falseNegativeRate: positives.length ? 1-truePositives/positives.length : null,
    falsePositiveRate: negatives.length ? falsePositives/negatives.length : null,
    // False activations per hour must use actual recorded idle hours, not merely this ratio.
  };
}
const words=(s:string)=>s.normalize('NFC').toLocaleLowerCase().match(/[\p{L}\p{N}']+/gu) ?? [];
export function wordErrorRate(reference: string, hypothesis: string): number {
  const a=words(reference), b=words(hypothesis);
  if (!a.length) return b.length ? 1 : 0;
  let prev=Array.from({length:b.length+1},(_,i)=>i);
  for (let i=1;i<=a.length;i++) {
    const next=[i];
    for (let j=1;j<=b.length;j++) next[j]=Math.min(next[j-1]+1,prev[j]+1,prev[j-1]+(a[i-1]===b[j-1]?0:1));
    prev=next;
  }
  return prev[b.length]/a.length;
}
/** Pronunciation correctness requires owner-rated audio samples; orthographic WER alone is insufficient. */
export function pronunciationPassRate(items: readonly { approved: boolean }[]): number | null {
  return items.length ? items.filter(x=>x.approved).length / items.length : null;
}
