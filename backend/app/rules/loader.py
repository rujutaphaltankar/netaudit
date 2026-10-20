"""Loads and validates the rule catalog (catalog.json)."""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from app.rules.models import RuleCatalog
from app.rules.operators import OPERATORS, resolve_arg
from app.schemas.normalized import NormalizedConfig, Vendor, _Setting

CATALOG_PATH = Path(__file__).with_name("catalog.json")


def _resolves_to_setting(path: str) -> bool:
    model: object = NormalizedConfig
    for i, part in enumerate(path.split(".")):
        fields = getattr(model, "model_fields", {})
        if part not in fields:
            return False
        model = fields[part].annotation
        if isinstance(model, type) and issubclass(model, _Setting):
            return i == len(path.split(".")) - 1
    return False


def validate_catalog(catalog: RuleCatalog) -> list[str]:
    """Return a list of problems (empty when the catalog is consistent)."""
    problems: list[str] = []
    ids = [r.id for r in catalog.rules]
    problems += [f"duplicate rule id {i}" for i in set(ids) if ids.count(i) > 1]
    valid_vendors = {v.value for v in Vendor}
    for r in catalog.rules:
        for c in [*r.applies_when, *r.fail_when, r.check]:
            if c.op not in OPERATORS:
                problems.append(f"{r.id}: unknown operator {c.op}")
            if not _resolves_to_setting(c.path):
                problems.append(f"{r.id}: path {c.path} is not a normalized setting")
            try:
                resolve_arg(c.arg)
            except KeyError as exc:
                problems.append(f"{r.id}: {exc}")
        for v in r.vendors or []:
            if v not in valid_vendors:
                problems.append(f"{r.id}: unknown vendor {v}")
        if "generic" not in r.remediation:
            problems.append(f"{r.id}: remediation needs a 'generic' entry")
        if not r.references:
            problems.append(f"{r.id}: no framework references")
    return problems


@lru_cache
def load_catalog() -> RuleCatalog:
    catalog = RuleCatalog.model_validate(json.loads(CATALOG_PATH.read_text(encoding="utf-8")))
    problems = validate_catalog(catalog)
    if problems:
        raise ValueError("Invalid rule catalog: " + "; ".join(problems))
    return catalog
