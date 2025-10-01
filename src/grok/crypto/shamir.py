# DEMO ONLY: educational k-of-n split. Use a proven lib/HSM in prod.
from __future__ import annotations
import secrets
from typing import List, Tuple

def _eval_poly(coeffs: List[int], x: int, p: int) -> int:
    y = 0
    for c in reversed(coeffs):
        y = (y*x + c) % p
    return y

def shamir_split(secret: int, k: int, n: int, p: int = 2**127-1) -> List[Tuple[int,int]]:
    coeffs = [secret] + [secrets.randbelow(p) for _ in range(k-1)]
    shares = []
    for x in range(1, n+1):
        shares.append((x, _eval_poly(coeffs, x, p)))
    return shares

def shamir_combine(shares: List[Tuple[int,int]], p: int = 2**127-1) -> int:
    # Lagrange interpolation at x=0
    s = 0
    for j,(xj,yj) in enumerate(shares):
        num, den = 1, 1
        for m,(xm,_) in enumerate(shares):
            if m==j: continue
            num = (num * (-xm)) % p
            den = (den * (xj - xm)) % p
        s = (s + yj * num * pow(den, -1, p)) % p
    return s
