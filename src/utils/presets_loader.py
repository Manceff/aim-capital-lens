"""Load and validate preset deals and configs from YAML."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from src.models.alm_mandate import ALMMandate
from src.models.dl_deal import DLDeal
from src.models.infra_deal import InfraDeal

DATA_DIR = Path(__file__).resolve().parents[2] / "data"


def _load_yaml(path: Path) -> Any:
    with open(path, encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def load_alm_mandate() -> ALMMandate:
    raw = _load_yaml(DATA_DIR / "alm_mandate.yaml")
    return ALMMandate(**raw)


def load_article_176_3() -> dict:
    """Return raw dict {ratings: {rating: {maturity: shock_pct}}, notch_mapping: {...}}."""
    return _load_yaml(DATA_DIR / "article_176_3.yaml")


def load_ratings_pd() -> dict:
    return _load_yaml(DATA_DIR / "ratings_pd.yaml")


def load_preset_deals() -> list[DLDeal | InfraDeal]:
    raw = _load_yaml(DATA_DIR / "preset_deals.yaml")
    deals: list[DLDeal | InfraDeal] = []
    for d in raw["deals"]:
        if d["type"] == "DL":
            deals.append(DLDeal(**d))
        elif d["type"] == "INFRA":
            deals.append(InfraDeal(**d))
        else:
            raise ValueError(f"Unknown deal type: {d['type']}")
    return deals


def get_deal_by_id(deal_id: str) -> DLDeal | InfraDeal:
    for d in load_preset_deals():
        if d.id == deal_id:
            return d
    raise KeyError(f"Deal id not found: {deal_id}")
