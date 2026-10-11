"""Common parser interface. Every vendor parser implements this contract."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import ClassVar

from app.schemas.normalized import Vendor
from app.schemas.parsing import ParseResult


class BaseConfigParser(ABC):
    vendor: ClassVar[Vendor]
    name: ClassVar[str]
    version: ClassVar[str]
    # Distinct detection signals required when the vendor is auto-detected.
    min_auto_signals: ClassVar[int] = 2

    @abstractmethod
    def detection_signals(self, content: str) -> list[str]:
        """Names of vendor-specific signals found in the content (used for detection)."""

    def can_parse(self, content: str, vendor_hint: Vendor | None = None) -> bool:
        """True if the content plausibly is this vendor's configuration.

        An explicit hint for a *different* vendor always yields False. An explicit hint for
        this vendor needs one signal; auto-detection needs `min_auto_signals`.
        """
        if vendor_hint is not None and vendor_hint != self.vendor:
            return False
        required = 1 if vendor_hint == self.vendor else self.min_auto_signals
        return len(self.detection_signals(content)) >= required

    @abstractmethod
    def parse(self, content: str, vendor_hint: Vendor | None = None) -> ParseResult:
        """Parse content into the normalized schema. Must not raise on malformed input."""
