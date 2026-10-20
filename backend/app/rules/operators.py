"""Condition operators. Every operator is tri-state: True / False / None (cannot be determined).

An UNKNOWN setting always yields None, so a rule can never PASS on missing evidence.
"""
from __future__ import annotations

from typing import Any, Callable

from app.schemas.normalized import WEAK_CREDENTIAL_STORAGE, _Setting

CONSTANTS: dict[str, Any] = {
    "$WEAK_CREDENTIAL_STORAGE": sorted(WEAK_CREDENTIAL_STORAGE),
}


def resolve_arg(arg: Any) -> Any:
    if isinstance(arg, str) and arg.startswith("$"):
        if arg not in CONSTANTS:
            raise KeyError(f"Unknown rule constant {arg}")
        return CONSTANTS[arg]
    return arg


def _matches(item: str, pattern: str) -> bool:
    """Exact match, or prefix match when the pattern ends with '*'."""
    return item.startswith(pattern[:-1]) if pattern.endswith("*") else item == pattern


def _as_list(value: Any) -> list[str]:
    return list(value) if isinstance(value, (list, tuple, set)) else [value]


def _is_true(v: Any, _a: Any) -> bool: return v is True
def _is_false(v: Any, _a: Any) -> bool: return v is False
def _equals(v: Any, a: Any) -> bool: return v == a
def _not_equals(v: Any, a: Any) -> bool: return v != a
def _in(v: Any, a: Any) -> bool: return v in a
def _not_in(v: Any, a: Any) -> bool: return v not in a
def _non_empty(v: Any, _a: Any) -> bool: return len(v) > 0
def _empty(v: Any, _a: Any) -> bool: return len(v) == 0
def _min_length(v: Any, a: Any) -> bool: return len(v) >= int(a)
def _includes_any(v: Any, a: Any) -> bool: return any(_matches(i, p) for i in _as_list(v) for p in a)
def _excludes_all(v: Any, a: Any) -> bool: return not _includes_any(v, a)


def _in_range(v: Any, a: Any) -> bool:
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        return False
    checks = {"gt": lambda x, b: x > b, "gte": lambda x, b: x >= b,
              "lt": lambda x, b: x < b, "lte": lambda x, b: x <= b}
    return all(checks[k](v, b) for k, b in a.items())


OPERATORS: dict[str, Callable[[Any, Any], bool]] = {
    "is_true": _is_true, "is_false": _is_false, "equals": _equals, "not_equals": _not_equals,
    "in": _in, "not_in": _not_in, "non_empty": _non_empty, "empty": _empty,
    "min_length": _min_length, "includes_any": _includes_any, "excludes_all": _excludes_all,
    "in_range": _in_range,
}


def apply_operator(op: str, setting: _Setting, arg: Any) -> bool | None:
    """Evaluate `op` on a setting. Returns None if the setting is UNKNOWN."""
    if op not in OPERATORS:
        raise KeyError(f"Unknown operator '{op}'")
    if setting.value is None:  # unknown state (a known setting always carries a value)
        return None
    return OPERATORS[op](setting.value, resolve_arg(arg))
