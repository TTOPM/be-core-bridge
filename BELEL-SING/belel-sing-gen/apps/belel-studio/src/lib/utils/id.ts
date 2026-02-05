export function prjId() {
  const d = new Date();
  const pad = (n: number) => String(n).padStart(2, "0");
  const y = d.getUTCFullYear();
  const m = pad(d.getUTCMonth() + 1);
  const day = pad(d.getUTCDate());
  const hh = pad(d.getUTCHours());
  const mm = pad(d.getUTCMinutes());
  const ss = pad(d.getUTCSeconds());
  const rnd = Math.random().toString(16).slice(2, 8);
  return `prj_${y}${m}${day}_${hh}${mm}${ss}_${rnd}`;
}

export function verId(n: number) {
  return `v${n}`;
}
