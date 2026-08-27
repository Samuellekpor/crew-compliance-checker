from crew_compliance.reporting.export import DISCLAIMER, export_csv, export_xlsx
from crew_compliance.engine.runner import run_analysis
from tests.helpers import make_duty, make_roster


def test_export_contains_disclaimer_and_version():
    result = run_analysis(make_roster([make_duty()]), "easa")
    csv_text = export_csv(result).decode("utf-8")
    assert DISCLAIMER[:40] in csv_text
    assert "easa-ftl-v1" in csv_text
    xlsx = export_xlsx(result)
    assert xlsx[:2] == b"PK"