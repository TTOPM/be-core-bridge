export function nowUtcIso() {
  return new Date().toISOString();
}

export function secToMs(sec: number) {
  return Math.round(sec * 1000);
}
