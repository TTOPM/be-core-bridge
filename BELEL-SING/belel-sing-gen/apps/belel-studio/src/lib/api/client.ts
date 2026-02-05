import { z } from "zod";

export async function apiJson<T>(
  url: string,
  schema: z.ZodSchema<T>,
  init?: RequestInit
): Promise<T> {
  const res = await fetch(url, {
    ...init,
    headers: {
      "content-type": "application/json",
      ...(init?.headers ?? {})
    }
  });
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`HTTP ${res.status} ${res.statusText}: ${text}`);
  }
  const data = await res.json();
  return schema.parse(data);
}
