import cfg from "../config/gemini.config.json";
export async function loadAnchors() {
  const list = cfg.concordium.anchors;
  return { list, merkleRoot: "stub-merkle-root", summary: list.map(a => `${a.type}:${a.id}`) };
}
export async function verifyAnchors(loaded: any, hint: string) {
  return Boolean(loaded?.list?.length && hint);
}
