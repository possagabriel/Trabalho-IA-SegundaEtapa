import copy
import json
import math

import pytest

from career.engine import build_plan, load_knowledge, rank_careers, report_markdown, validate_knowledge


@pytest.fixture
def kb():
    return load_knowledge()


def answers(kb, value):
    return {q["id"]: value for q in kb["questions"]}


def test_ten_tracks_and_external_rules(kb):
    assert len(kb["tracks"]) == 10
    original = rank_careers(kb, answers(kb, 5))
    changed = copy.deepcopy(kb)
    changed["tracks"][0]["penalties"].append({
        "id": "external_rule", "conditions": [{"question": "logica", "operator": "gte", "value": 4}],
        "points": 30, "reason": "Regra adicionada externamente para o teste."})
    validate_knowledge(changed)
    modified = rank_careers(changed, answers(kb, 5))
    assert next(r["score"] for r in original["ranking"] if r["id"] == "backend") == pytest.approx(100)
    assert next(r["score"] for r in modified["ranking"] if r["id"] == "backend") == pytest.approx(70)


def test_manual_weighted_calculation_and_penalty(kb):
    values = answers(kb, 3)
    values["programacao"] = 1
    result = next(r for r in rank_careers(kb, values)["ranking"] if r["id"] == "backend")
    # Back-end soma 26 pesos; programação tem peso 5. Demais respostas = 0,5.
    assert result["base_score"] == pytest.approx(100 * (26 - 5) * .5 / 26)
    assert result["penalty_points"] == 12
    assert result["score"] == pytest.approx(100 * 21 * .5 / 26 - 12)
    assert result["penalties"][0]["id"] == "backend_programacao_baixo"


@pytest.mark.parametrize("value,expected", [(1, 0), (5, 100)])
def test_extreme_profiles_are_bounded(kb, value, expected):
    result = rank_careers(kb, answers(kb, value))
    assert len(result["top3"]) == 3
    assert all(r["score"] == pytest.approx(expected) for r in result["ranking"])
    assert result["low_compatibility"] is (value == 1)


def test_unknown_is_neutral_but_not_evidence(kb):
    result = rank_careers(kb, {})
    assert not result["recommendation_available"]
    assert result["coverage"] == 0
    for row in result["ranking"]:
        assert row["score"] == pytest.approx(50)
        assert row["coverage"] == 0
        assert not row["penalties"]


def test_neutral_tie_is_explicit_and_deterministic(kb):
    result = rank_careers(kb, answers(kb, 3))
    assert len(result["close_tracks"]) == 10
    assert result["recommendation_available"]
    assert [r["id"] for r in result["ranking"]] == sorted(t["id"] for t in kb["tracks"])


def test_mixed_data_and_web_profile_has_explanations(kb):
    values = answers(kb, 3)
    values.update(dados=5, matematica=5, programacao=5, logica=5, visual=5,
                  empatia=5, construir=5, investigar=5)
    result = rank_careers(kb, values)
    scores = {r["id"]: r["score"] for r in result["ranking"]}
    assert scores["cientista_dados"] > 75
    assert scores["frontend"] > 75
    assert len(result["close_tracks"]) >= 2
    for row in result["top3"]:
        assert row["factors"]
        assert row["score"] == pytest.approx(max(0, sum(f["points"] for f in row["factors"]) - row["penalty_points"]))


def test_infrastructure_profile_recommends_devops(kb):
    values = answers(kb, 2)
    values.update(infra=5, automacao=5, redes=5, incidentes=5, operar=5, detalhes=5, arquitetar=4)
    assert rank_careers(kb, values)["top3"][0]["id"] == "devops"


@pytest.mark.parametrize("value", [0, 6, -1, True, "5", 3.5, math.nan, math.inf])
def test_invalid_affinity_is_rejected(kb, value):
    with pytest.raises(ValueError):
        rank_careers(kb, {"logica": value})


def test_unknown_question_rejected(kb):
    with pytest.raises(ValueError):
        rank_careers(kb, {"typo": 5})


def test_every_track_has_consistent_roadmap(kb):
    for track in kb["tracks"]:
        plan = build_plan(kb, track["id"], {}, 6)
        assert plan["readiness"] == 0
        positions = {item["skill"]: i for i, item in enumerate(plan["roadmap"])}
        for item in plan["roadmap"]:
            assert item["start_week"] <= item["end_week"]
            for prerequisite in kb["skills"][item["skill"]]["prerequisites"]:
                assert positions[prerequisite] < positions[item["skill"]]
        assert plan["total_hours"] == sum(item["hours"] for item in plan["roadmap"])
        assert plan["estimated_weeks"] == math.ceil(plan["total_hours"] / 6)


def test_partial_knowledge_changes_gaps_hours_and_focus(kb):
    beginner = build_plan(kb, "backend", {}, 6)
    partial = build_plan(kb, "backend", {"programacao": 2, "git": 4, "http": 1}, 6)
    assert 0 < partial["readiness"] < 100
    assert partial["total_hours"] == beginner["total_hours"] - 32 - 16 - 8
    assert "programacao" not in [item["skill"] for item in partial["roadmap"]]
    assert "Fundamentos de programação" not in partial["portfolio"]["focus"]


def test_no_gaps_does_not_invent_seniority(kb):
    plan = build_plan(kb, "backend", {skill: 4 for skill in kb["skills"]})
    assert plan["readiness"] == 100
    assert not plan["gaps"] and not plan["roadmap"]
    assert plan["total_hours"] == plan["estimated_weeks"] == 0
    assert plan["status"] == "Metas iniciais atendidas"


def test_weekly_time_changes_schedule_not_ranking_or_content(kb):
    slow = build_plan(kb, "qa", {}, 3)
    fast = build_plan(kb, "qa", {}, 12)
    assert slow["total_hours"] == fast["total_hours"]
    assert slow["estimated_weeks"] > fast["estimated_weeks"]
    assert [s["skill"] for s in slow["roadmap"]] == [s["skill"] for s in fast["roadmap"]]


@pytest.mark.parametrize("knowledge,hours", [({"git": -1}, 6), ({"git": 5}, 6), ({"git": True}, 6),
                                              ({"git": 1.5}, 6), ({"typo": 1}, 6), ({}, 0), ({}, 41), ({}, math.inf)])
def test_invalid_plan_inputs(kb, knowledge, hours):
    with pytest.raises(ValueError):
        build_plan(kb, "backend", knowledge, hours)


def test_invalid_track(kb):
    with pytest.raises(ValueError):
        build_plan(kb, "missing", {})


@pytest.mark.parametrize("mutation", ["cycle", "missing_question", "zero_weights", "missing_dependency", "missing_skill", "duplicate"])
def test_invalid_knowledge_base(kb, mutation):
    bad = copy.deepcopy(kb)
    if mutation == "cycle":
        bad["skills"]["programacao"]["prerequisites"] = ["api"]
    elif mutation == "missing_question":
        bad["tracks"][0]["weights"]["typo"] = 5
    elif mutation == "zero_weights":
        bad["tracks"][0]["weights"] = {"logica": 0}
    elif mutation == "missing_dependency":
        bad["tracks"][0]["requirements"] = [r for r in bad["tracks"][0]["requirements"] if r["skill"] != "http"]
    elif mutation == "missing_skill":
        bad["tracks"][0]["requirements"][0]["skill"] = "typo"
    else:
        bad["tracks"].append(copy.deepcopy(bad["tracks"][0]))
    with pytest.raises(ValueError):
        validate_knowledge(bad)


def test_loading_errors_are_readable(tmp_path):
    with pytest.raises(ValueError, match="carregar"):
        load_knowledge(tmp_path / "missing.json")
    path = tmp_path / "bad.json"
    path.write_text("{ broken", encoding="utf-8")
    with pytest.raises(ValueError, match="carregar"):
        load_knowledge(path)
    path.write_text(json.dumps({}), encoding="utf-8")
    with pytest.raises(ValueError, match="Estrutura"):
        load_knowledge(path)


def test_report_includes_caveats_explanations_and_chosen_track(kb):
    result = rank_careers(kb, {})
    plan = build_plan(kb, "mobile", {}, 5)
    report = report_markdown(kb, {"name": "Teste"}, result, plan)
    for expected in ("Teste", "Mobile", "Informação insuficiente", "Resultados próximos", "Não sei (neutro)",
                     "Lacuna", "Roteiro", "Flutter", "Certificações opcionais", "GitHub Foundations"):
        assert expected in report
