import cfg from "../config/gemini.config.json";
export async function withTrace<T>(name: string, fn: () => Promise<T>) {
  const start = Date.now();
  try { return await fn(); }
  finally {
    if (cfg.telemetry.enabled) {
      const ms = Date.now() - start;
      console.log(`[TRACE] ${name} ${ms}ms`);
    }
  }
}
