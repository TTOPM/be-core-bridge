import clsx, { type ClassValue } from "clsx";

export function cn(...inputs: ClassValue[]) {
  return clsx(inputs);
}

export function clamp(n: number, a: number, b: number) {
  return Math.max(a, Math.min(b, n));
}

export function fmt2(n: number) {
  return Number.isFinite(n) ? n.toFixed(2) : "0.00";
}
