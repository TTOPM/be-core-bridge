import { z } from "zod";

type ApiJsonInit = RequestInit & { body?: BodyInit };

export async function apiJson<T>(
  url: string,
  schema: z.ZodSchema<T>,
  init?: ApiJsonInit
): Promise<T> {
  const res = await fetch(url, {
    ...init,
    headers: {
      "content-type": "application/json",
      ...(init?.headers ?? {}),
    },
    cache: "no-store",
  });

  const text = await res.text();
  let data: unknown = null;

  try {
    data = text ? JSON.parse(text) : null;
  } catch {
    // non-json error body
    if (!res.ok) throw new Error(`HTTP ${res.status}: ${text || "request failed"}`);
    throw new Error(`Expected JSON but got: ${text}`);
  }

  if (!res.ok) {
    const detail =
      (data as any)?.detail ||
      (data as any)?.message ||
      JSON.stringify(data);
    throw new Error(`HTTP ${res.status}: ${detail}`);
  }

  return schema.parse(data);
}
