from __future__ import annotations

from typing import Any, Dict

from pydantic import BaseModel


class ReceiptResponse(BaseModel):
    receipt: Dict[str, Any]
