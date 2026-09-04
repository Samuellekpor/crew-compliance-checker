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
            retrieved="2026-09-04",
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
            retrieved="2026-09-04",
        ),
    ),
    default_ruleset_id="faa-117-v1",
)

UK_CAA = RegulatoryFramework(
    id="uk_caa",
    display_name="UK CAA (assimilated Air Ops FTL)",
    jurisdiction="United Kingdom",
    applicability=(
        "UK commercial air transport crew subject to assimilated Regulation (EU) No 965/2012 "
        "Subpart FTL as applied by the UK CAA, plus the Civil Aviation (Working Time) Regulations 2004 "
        "reg. 9 annual caps. This is not EASA EU oversight and is not a CAP 371 FTLS scheme."
    ),
    sources=(
        Source(
            title="UK CAA Regulatory Library — ORO.FTL.210 / ORO.FTL.235",
            locator="ORO.FTL.210, ORO.FTL.235",
            url="https://regulatorylibrary.caa.co.uk/965-2012/Content/Document%20Structure/03%20ORO/2%20Regs/05140_ORO.FTL.210_Flight_times_and_duty_periods.htm",
            retrieved="2026-09-04",
        ),
        Source(
            title="The Civil Aviation (Working Time) Regulations 2004, regulation 9",
            locator="SI 2004/756 reg. 9",
            url="https://www.legislation.gov.uk/uksi/2004/756/regulation/9",
            retrieved="2026-09-04",
        ),
    ),
    default_ruleset_id="uk-ftl-v1",
)

TRANSPORT_CANADA = RegulatoryFramework(
    id="transport_canada",
    display_name="Transport Canada / CARs Subpart 700",
    jurisdiction="Canada",
    applicability=(
        "Canadian air operators subject to the flight-time, hours-of-work, and rest rules in "
        "Canadian Aviation Regulations SOR/96-433 Subpart 700 (as amended, including SOR/2018-269). "
        "Medical-evacuation 700.103, FRMS exemptions, and maximum FDP tables in 700.28 are not this screen."
    ),
    sources=(
        Source(
            title="Canadian Aviation Regulations — maximum flight time, hours of work, rest",
            locator="CARs 700.27, 700.29, 700.40",
            url="https://laws-lois.justice.gc.ca/eng/regulations/SOR-96-433/section-700.27.html",
            retrieved="2026-09-04",
        ),
    ),
    default_ruleset_id="tc-cars-700-v1",
)

CASA = RegulatoryFramework(
    id="casa",
    display_name="CASA Australia / CAO 48.1 Appendix 2",
    jurisdiction="Australia",
    applicability=(
        "Australian AOC holders using Civil Aviation Order 48.1 Instrument 2019 Appendix 2 "
        "(multi-pilot operations except flight training). Other appendices (1, 3–7, FRMS) are not this screen."
    ),
    sources=(
        Source(
            title="Civil Aviation Order 48.1 Instrument 2019",
            locator="Appendix 2 clauses 1, 11 and 12",
            url="https://www.legislation.gov.au/F2019L01070/latest/text",
            retrieved="2026-09-04",
        ),
    ),
    default_ruleset_id="casa-48-1-a2-v1",
)

FRAMEWORKS = {
    EASA.id: EASA,
    FAA_PART_117.id: FAA_PART_117,
    UK_CAA.id: UK_CAA,
    TRANSPORT_CANADA.id: TRANSPORT_CANADA,
    CASA.id: CASA,
}

STUB_FRAMEWORKS: tuple[tuple[str, str], ...] = ()


def get_framework(framework_id: str) -> RegulatoryFramework:
    return FRAMEWORKS[framework_id]
