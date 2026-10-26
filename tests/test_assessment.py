import json

import pytest

from career.assessment import empty_assessment, export_assessment, import_assessment
from career.engine import build_plan, load_knowledge, rank_careers


@pytest.fixture
def kb():
    return load_knowledge()


def test_round_trip_and_ignore_forged_results(kb):
    data = empty_assessment()
    data["profile"].update(name="  Maria  ", hours=12)
    data["answers"] = {q["id"]: 3 for q in kb["questions"]}
    data["knowledge"] = {"git": 2, "linux": 1}
    raw = export_assessment(kb, **data, result={"top3": [{"score": 999}]}, plan={"total_hours": -1})
    restored = import_assessment(raw.encode(), kb)
    assert restored["profile"]["name"] == "Maria"
    assert restored["profile"]["hours"] == 12
    assert restored["knowledge"] == data["knowledge"]
    assert "result" not in restored and "plan" not in restored
    assert not restored["version_changed"]
    assert rank_careers(kb, restored["answers"])["top3"][0]["score"] == pytest.approx(50)


def test_legacy_export_and_version_change(kb):
    data = {**empty_assessment(), "knowledge_base_version": "1.0.0"}
    data["profile"] = {"name": "Antigo", "hours": 4}
    restored = import_assessment(json.dumps(data).encode(), kb)
    assert restored["version_changed"]
    assert restored["profile"]["experience"] == "Estou começando"
    assert restored["profile"]["target_level"] == "junior"


def test_seniority_survives_round_trip(kb):
    data = empty_assessment()
    data["profile"]["target_level"] = "senior"
    restored = import_assessment(export_assessment(kb, **data).encode(), kb)
    assert restored["profile"]["target_level"] == "senior"


@pytest.mark.parametrize("target", ["unknown", None, [], True])
def test_import_rejects_invalid_seniority(kb, target):
    data = empty_assessment()
    data["profile"]["target_level"] = target
    with pytest.raises(ValueError, match="senioridade"):
        import_assessment(json.dumps(data).encode(), kb)


@pytest.mark.parametrize("raw", [b"broken", b"[]", b"null", b"\xff", b"{}", b"x" * 1_000_001,
                                 b"[" * 2000 + b"]" * 2000])
def test_invalid_files_fail_with_readable_error(kb, raw):
    with pytest.raises(ValueError):
        import_assessment(raw, kb)


@pytest.mark.parametrize("field,value", [
    ("profile", None), ("answers", []), ("knowledge", []),
    ("format_version", 2), ("format_version", True),
    ("answers", {"logica": 10}), ("answers", {"logica": {"bad": 1}}),
    ("answers", {"logica": 10**400}), ("knowledge", {"git": True}),
    ("knowledge", {"typo": 2}), ("profile", {"name": "x" * 101}),
    ("profile", {"hours": 0}), ("profile", {"experience": "typo"})])
def test_invalid_assessment_values(kb, field, value):
    data = empty_assessment()
    data[field] = value
    with pytest.raises(ValueError):
        import_assessment(json.dumps(data).encode(), kb)


def test_demo_profiles_are_valid(kb):
    from pathlib import Path
    demos = json.loads((Path(__file__).resolve().parents[1] / "data/perfis_exemplo.json").read_text())
    for demo in demos:
        restored = import_assessment(json.dumps(demo).encode(), kb)
        result = rank_careers(kb, restored["answers"])
        assert result["recommendation_available"]
        assert build_plan(kb, result["top3"][0]["id"], restored["knowledge"])["roadmap"]
