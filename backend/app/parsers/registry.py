"""Registry of supported vendor parsers. Adding a vendor = add a parser class and register it here."""
from __future__ import annotations

from app.parsers.base import BaseConfigParser
from app.parsers.cisco_ios import CiscoIosParser
from app.parsers.juniper_junos import JuniperJunosParser
from app.schemas.normalized import Vendor

_PARSERS: dict[Vendor, BaseConfigParser] = {
    Vendor.CISCO_IOS: CiscoIosParser(),
    Vendor.JUNIPER_JUNOS: JuniperJunosParser(),
}

VENDOR_DISPLAY_NAMES: dict[Vendor, str] = {
    Vendor.CISCO_IOS: "Cisco IOS",
    Vendor.JUNIPER_JUNOS: "Juniper Junos",
    Vendor.PALO_ALTO_PANOS: "Palo Alto PAN-OS",
    Vendor.FORTINET_FORTIOS: "Fortinet FortiOS",
    Vendor.ARISTA_EOS: "Arista EOS",
}


def get_parser(vendor: Vendor) -> BaseConfigParser | None:
    return _PARSERS.get(vendor)


def supported_vendors() -> list[Vendor]:
    return list(_PARSERS)


def all_parsers() -> list[BaseConfigParser]:
    return list(_PARSERS.values())
