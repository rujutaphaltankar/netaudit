from app.schemas.detection import Confidence
from app.schemas.normalized import Vendor
from app.services.vendor_detection import detect_vendor
from tests.conftest import read_sample


def test_detects_cisco():
    d = detect_vendor(read_sample("cisco_ios_weak.cfg"))
    assert d.detected_vendor == Vendor.CISCO_IOS and d.supported and d.confidence == Confidence.HIGH


def test_detects_junos_set_and_hierarchical():
    for name in ("juniper_junos_weak.set", "juniper_junos_hardened.conf"):
        d = detect_vendor(read_sample(name))
        assert d.detected_vendor == Vendor.JUNIPER_JUNOS and d.supported, name


def test_recognises_unsupported_vendor_without_claiming_support():
    d = detect_vendor(read_sample("arista_eos_unsupported.cfg"))
    assert d.detected_vendor == Vendor.ARISTA_EOS and d.supported is False


def test_fortinet_and_palo_alto_recognised_as_unsupported():
    forti = "#config-version=FG100E\nconfig system global\n set hostname FW\nend\nconfig firewall policy\n edit 1\n next\nend\n"
    palo = "set deviceconfig system hostname PA1\nset rulebase security rules r1 action allow\nset mgt-config users admin\n"
    assert detect_vendor(forti).detected_vendor == Vendor.FORTINET_FORTIOS
    assert detect_vendor(palo).detected_vendor == Vendor.PALO_ALTO_PANOS
    assert not detect_vendor(forti).supported and not detect_vendor(palo).supported


def test_does_not_guess_on_unrelated_text():
    d = detect_vendor("hello world\nthis is just a note\n")
    assert d.detected_vendor is None and d.confidence == Confidence.NONE
