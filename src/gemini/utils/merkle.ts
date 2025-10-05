export function merkleNext(hashes: string[]) {
  const root = hashes.reduce((acc, h) => acc + h.slice(0, 8), "");
  return { root };
}
