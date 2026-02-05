from __future__ import annotations

from fastapi import HTTPException


def require(cond: bool, msg: str, status_code: int = 400) -> None:
    if not cond:
        raise HTTPException(status_code=status_code, detail=msg)


def clamp_float(v: float, lo: float, hi: float) -> float:
    if v < lo:
        return lo
    if v > hi:
        return hi
    return v
