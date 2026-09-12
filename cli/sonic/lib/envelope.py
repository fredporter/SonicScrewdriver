"""SonicScrewdriver structured response envelopes.

Aligns with uCore snackbar conventions for success/warn/error states
and the spool event adapter shape (timestamp, module, level, message, tags).
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class EnvelopeStatus(str, Enum):
    """Snackbar-compatible status levels."""
    SUCCESS = "success"
    WARN = "warn"
    ERROR = "error"


class EventLevel(str, Enum):
    """uCore spool-compatible log levels."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


@dataclass
class SnackbarResponse:
    """Structured response envelope for CLI/API actions.

    Aligned to uCore snackbar conventions:
    - status: success | warn | error
    - code: machine-readable exit/status code
    - message: human-readable description
    - module: originating component (e.g. 'sonic.usb')
    - timestamp: ISO 8601
    - tags: lowercase kebab-case labels
    - data: optional structured payload
    - details: optional list of sub-messages for diagnostics
    """

    status: EnvelopeStatus
    code: int
    message: str
    module: str
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    tags: list[str] = field(default_factory=list)
    data: dict[str, Any] | None = None
    details: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a plain dict for JSON output."""
        result = asdict(self)
        result["status"] = self.status.value
        return result

    @classmethod
    def ok(cls, module: str, message: str, **kwargs: Any) -> SnackbarResponse:
        """Shorthand for a success envelope."""
        return cls(
            status=EnvelopeStatus.SUCCESS,
            code=0,
            message=message,
            module=module,
            **kwargs,
        )

    @classmethod
    def warn(cls, module: str, message: str, code: int = 1, **kwargs: Any) -> SnackbarResponse:
        """Shorthand for a warning envelope."""
        return cls(
            status=EnvelopeStatus.WARN,
            code=code,
            message=message,
            module=module,
            **kwargs,
        )

    @classmethod
    def error(cls, module: str, message: str, code: int = 1, **kwargs: Any) -> SnackbarResponse:
        """Shorthand for an error envelope."""
        return cls(
            status=EnvelopeStatus.ERROR,
            code=code,
            message=message,
            module=module,
            **kwargs,
        )


@dataclass
class SpoolEvent:
    """Event adapter for spool/feed writes.

    Aligned to uCore SpoolEntry dataclass:
    - timestamp: ISO 8601
    - level: INFO, WARNING, ERROR, DEBUG, CRITICAL
    - module: originating component (e.g. 'sonic.usb')
    - message: human-readable event description
    - tags: lowercase kebab-case labels for filtering
    - metadata: optional structured data
    """

    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    level: EventLevel = EventLevel.INFO
    module: str = "sonic"
    message: str = ""
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["level"] = self.level.value
        return result