/** Metrics are in-memory only; privacy-preserving counters instead of transcripts or samples. */
export class AcousticMetrics {
  private counts = new Map<string, number>();
  private samples = new Map<string, number[]>();
  constructor(private readonly maxSamplesPerMetric = 250) {}
  increment(name: string, amount = 1): void {
    if (!/^[a-z0-9_.-]{1,60}$/i.test(name) || !Number.isFinite(amount)) throw new Error('Bad metric');
    this.counts.set(name, (this.counts.get(name) ?? 0) + amount);
  }
  sample(name: string, value: number): void {
    if (!/^[a-z0-9_.-]{1,60}$/i.test(name) || !Number.isFinite(value)) throw new Error('Bad sample');
    const items = this.samples.get(name) ?? [];
    items.push(value);
    if (items.length > this.maxSamplesPerMetric) items.shift();
    this.samples.set(name, items);
  }
  snapshot(): { counts: Record<string, number>; latency: Record<string, { n: number; p50: number; p95: number }> } {
    const latency: Record<string, { n: number; p50: number; p95: number }> = {};
    for (const [name, arr] of this.samples) {
      const sorted = [...arr].sort((a,b) => a-b);
      latency[name] = { n: arr.length, p50: sorted[Math.max(0, Math.ceil(arr.length * .5)-1)] ?? 0, p95: sorted[Math.max(0, Math.ceil(arr.length * .95)-1)] ?? 0 };
    }
    return { counts: Object.fromEntries(this.counts), latency };
  }
  reset(): void { this.counts.clear(); this.samples.clear(); }
}
