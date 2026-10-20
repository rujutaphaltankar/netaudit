from pathlib import Path

from app.parsers.registry import get_parser
from app.schemas.normalized import Vendor

SAMPLES = Path(__file__).resolve().parents[2] / "samples"


def parse_sample(name: str, vendor: Vendor):
    return get_parser(vendor).parse((SAMPLES / name).read_text(encoding="utf-8"), vendor)


def results_by_id(evaluation) -> dict:
    return {r.rule_id: r for r in evaluation.results}
