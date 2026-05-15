"""Verdict 3-piliers schema."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

Status = Literal["PASS", "CONDITIONS", "REJECT"]
FinalVerdict = Literal["PROCEED", "CONDITIONS", "REJECT"]


class Pillar(BaseModel):
    status: Status
    reason: str | None = None


class Verdict(BaseModel):
    credit: Pillar
    s2: Pillar
    alm: Pillar
    final: FinalVerdict
