import copy
import json
import math

import pytest

from career.engine import (
    build_plan,
    load_knowledge,
    rank_careers,
    report_markdown,
    validate_knowledge,
)


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


def test_score_intervals_contain_all_completions(kb):
    from itertools import product
    values = answers(kb, 3)
    values.update(logica=None, programacao=None)
    bounds = {r["id"]: r for r in rank_careers(kb, values)["ranking"]}
    for logic, programming in product(range(1, 6), repeat=2):
        completed = {**values, "logica": logic, "programacao": programming}
        for row in rank_careers(kb, completed)["ranking"]:
            bound = bounds[row["id"]]
            assert bound["score_min"] - 1e-9 <= row["score"] <= bound["score_max"] + 1e-9
            assert row["score_min"] == pytest.approx(row["score_max"])


def test_gte_penalty_interval_is_conservative(kb):
    kb["tracks"][0]["penalties"].append({"id": "gte", "points": 35, "reason": "Teste de regra inversa",
        "conditions": [{"question": "programacao", "operator": "gte", "value": 4}]})
    values = answers(kb, 3)
    values["programacao"] = None
    bounds = next(r for r in rank_careers(kb, values)["ranking"] if r["id"] == "backend")
    for value in range(1, 6):
        result = next(r for r in rank_careers(kb, {**values, "programacao": value})["ranking"] if r["id"] == "backend")
        assert bounds["score_min"] <= result["score"] <= bounds["score_max"]


def test_unknown_intervals_cover_full_scale(kb):
    for row in rank_careers(kb, {})["ranking"]:
        assert row["score_min"] == 0
        assert row["score_max"] == 100


def test_advanced_skill_without_prerequisite_is_flagged(kb):
    plan = build_plan(kb, "backend", {"api": 3})
    assert {item["prerequisite"] for item in plan["inconsistencies"]} == {"Fundamentos de programação", "HTTP e APIs"}
    assert "api" not in [item["skill"] for item in plan["roadmap"]]
    assert all(item["evidence"] for item in plan["roadmap"])


@pytest.mark.parametrize("track_id", ["backend", "frontend", "cientista_dados", "engenheiro_dados",
                                     "ciberseguranca", "devops", "cloud", "mobile", "qa", "produto"])
def test_seniority_targets_change_gaps_without_changing_affinity(kb, track_id):
    knowledge = {skill: 2 for skill in kb["skills"]}
    junior = build_plan(kb, track_id, knowledge)
    pleno = build_plan(kb, track_id, knowledge, target_level="pleno")
    senior = build_plan(kb, track_id, knowledge, target_level="senior")
    assert junior["readiness"] == 100
    assert junior["total_hours"] == 0
    assert pleno["readiness"] == pytest.approx(200 / 3)
    assert senior["readiness"] == pytest.approx(50)
    assert 0 < pleno["total_hours"] < senior["total_hours"]
    assert all(row["target"] == 4 for row in senior["requirements"])
    assert pleno["portfolio"]["level_guidance"] != junior["portfolio"]["level_guidance"]
    assert senior["target_level_name"] == "Sênior"


def test_seniority_rules_are_external_and_reported(kb):
    kb["seniority_levels"]["pleno"]["target_floor"] = 4
    validate_knowledge(kb)
    plan = build_plan(kb, "backend", {"git": 3}, target_level="pleno")
    assert next(row for row in plan["requirements"] if row["skill"] == "git")["gap"] == 1
    report = report_markdown(kb, {}, rank_careers(kb, {}), plan)
    assert "Meta de estudo: Pleno" in report
    assert plan["portfolio"]["level_guidance"] in report


@pytest.mark.parametrize("target", [None, [], "unknown", 3, True])
def test_invalid_seniority_target(kb, target):
    with pytest.raises(ValueError, match="senioridade"):
        build_plan(kb, "backend", {}, target_level=target)


@pytest.mark.parametrize("floor", [0, 5, 2.5, True, None])
def test_invalid_seniority_knowledge_base(kb, floor):
    kb["seniority_levels"]["pleno"]["target_floor"] = floor
    with pytest.raises(ValueError):
        validate_knowledge(kb)


def test_roadmap_respects_transitive_prerequisite_even_if_middle_skill_is_known(kb):
    # React depends on JavaScript, which depends on HTML/CSS. Declaring
    # JavaScript mastered must not let React precede missing HTML/CSS.
    track = next(track for track in kb["tracks"] if track["id"] == "frontend")
    next(req for req in track["requirements"] if req["skill"] == "react")["importance"] = 10
    next(req for req in track["requirements"] if req["skill"] == "html_css")["importance"] = 1
    validate_knowledge(kb)
    plan = build_plan(kb, "frontend", {"javascript": 2})
    order = [step["skill"] for step in plan["roadmap"]]
    assert "javascript" not in order
    assert order.index("html_css") < order.index("react")
