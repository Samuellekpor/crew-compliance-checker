from __future__ import annotations

from enum import Enum


class Position(str, Enum):
    CAPTAIN = "captain"
    FO = "first_officer"
    UNKNOWN = "unknown"


class DutyKind(str, Enum):
    OPERATING_FLIGHT = "operating_flight"
    POSITIONING = "positioning"
    OTHER = "other"
    UNKNOWN = "unknown"


class FindingKind(str, Enum):
    POTENTIAL_ISSUE = "potential_issue"
    INSUFFICIENT_DATA = "insufficient_data"
    INFORMATIONAL = "informational"


class Severity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFORMATIONAL = "informational"