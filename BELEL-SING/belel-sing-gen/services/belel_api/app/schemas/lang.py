from __future__ import annotations

from typing import List, Literal

from pydantic import BaseModel


Tier = Literal["stable", "experimental"]


class LanguageItem(BaseModel):
    code: str
    name: str
    tier: Tier = "stable"


class LangGates(BaseModel):
    block_unsupported: bool = True
    warn_experimental: bool = True


class LangReportResponse(BaseModel):
    documented_count: int
    languages: List[LanguageItem]
    gates: LangGates
