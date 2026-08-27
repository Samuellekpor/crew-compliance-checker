from __future__ import annotations

from datetime import date

from crew_compliance.domain.models import RegulatoryFramework, Source

EASA = RegulatoryFramework(
    id="easa",
    display_name="EASA (EU Air Ops Subpart FTL)",
    jurisdiction="European Union / EASA",
    applicability=(
        "Commercial air transport crew members subject to Regulation (EU) No 965/2012 "
        "Annex III Subpart FTL (ORO.FTL). This is not a UK CAA scheme and is not ICAO SARPs."
    ),
    sources=(
        Source(
            title="Regulation (EU) No 965/2012 Annex III Subpart FTL",
            locator="ORO.FTL.105, ORO.FTL.210, ORO.FTL.215, ORO.FTL.235",
            url="https://www.legislation.gov.uk/eur/2012/965/annex/III/division/subpart%2Bftl",
            retrieved="2026-08-27",
        ),
    ),
    default_ruleset_id="easa-ftl-v1",
)

FAA_PART_117 = RegulatoryFramework(
    id="faa_part_117",
    display_name="FAA 14 CFR Part 117",
    jurisdiction="United States",
    applicability=(
        "Passenger-carrying operations of U.S. air carriers under 14 CFR Part 121, and flying "
        "for Part 91 on behalf of that Part 121 passenger certificate holder, as described in "
        "14 CFR § 117.1. This framework does not apply to Part 135, Part 91 generally, or "
        "Part 121 all-cargo operations under Subparts Q/R/S."
    ),
    sources=(
        Source(
            title="14 CFR Part 117 — Flight and Duty Limitations and Rest Requirements: Flightcrew Members",
            locator="14 CFR §§ 117.1, 117.3, 117.23, 117.25",
            url="https://www.ecfr.gov/current/title-14/chapter-I/subchapter-G/part-117",
            retrieved="2026-08-27",
        ),
    ),
    default_ruleset_id="faa-117-v1",
)

FRAMEWORKS = {EASA.id: EASA, FAA_PART_117.id: FAA_PART_117}

STUB_FRAMEWORKS = (
    ("uk_caa", "UK CAA"),
    ("transport_canada", "Transport Canada / CARs"),
    ("casa", "CASA Australia / CAO 48.1"),
)


def get_framework(framework_id: str) -> RegulatoryFramework:
    return FRAMEWORKS[framework_id]