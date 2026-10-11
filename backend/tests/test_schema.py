import pytest
from pydantic import ValidationError

from app.schemas.normalized import (BoolSetting, NormalizedConfig, StrListSetting, UnknownReason,
                                    ValueState, Vendor)


def test_known_setting_requires_value():
    with pytest.raises(ValidationError):
        BoolSetting(state=ValueState.KNOWN, unknown_reason=None)


def test_unknown_setting_cannot_carry_value():
    with pytest.raises(ValidationError):
        BoolSetting(state=ValueState.UNKNOWN, value=True)


def test_unknown_requires_reason():
    with pytest.raises(ValidationError):
        BoolSetting(state=ValueState.UNKNOWN, unknown_reason=None)


def test_known_empty_list_is_valid_and_distinct_from_unknown():
    s = StrListSetting.known([])
    assert s.state == ValueState.KNOWN and s.value == []


def test_defaults_are_unknown_not_found():
    cfg = NormalizedConfig(vendor=Vendor.CISCO_IOS)
    assert cfg.management.telnet_enabled.state == ValueState.UNKNOWN
    assert cfg.snmp.versions.unknown_reason == UnknownReason.NOT_FOUND
