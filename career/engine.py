"""Inferência ponderada e planejamento, sem dependência da interface."""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

DEFAULT_KB = Path(__file__).resolve().parent.parent / "regras_carreiras.json"


def _number(value: Any, low: float, high: float, label: str) -> None:
    if (isinstance(value, bool) or not isinstance(value, (int, float))
            or not low <= value <= high or not math.isfinite(value)):
        raise ValueError(f"{label}: esperado número entre {low} e {high}.")


def validate_knowledge(kb: dict) -> None:
    """Falha cedo em referências inválidas, pesos nulos e ciclos de estudo."""
    try:
        if type(kb["schema_version"]) is not int or kb["schema_version"] != 2:
            raise ValueError("Versão da base de conhecimento não suportada.")
        cfg = kb["scoring"]
        _number(cfg["min"], 1, 1, "Escala mínima")
        _number(cfg["max"], 5, 5, "Escala máxima")
        for key in ("unknown_normalized", "min_coverage"):
            _number(cfg[key], 0, 1, key)
        for key in ("tie_tolerance", "low_compatibility"):
            _number(cfg[key], 0, 100, key)
        levels = kb["seniority_levels"]
        if not isinstance(levels, dict) or "junior" not in levels:
            raise ValueError("Defina ao menos a referência Júnior de senioridade.")
        for level in levels.values():
            _number(level["target_floor"], 1, 4, "Meta mínima de senioridade")
            if type(level["target_floor"]) is not int:
                raise ValueError("Meta de senioridade deve ser inteira.")
            for field in ("name", "description", "portfolio_guidance"):
                if not isinstance(level[field], str) or not level[field].strip():
                    raise ValueError("Referência de senioridade incompleta.")
        questions = {q["id"]: q for q in kb["questions"]}
        if not questions or len(questions) != len(kb["questions"]):
            raise ValueError("Perguntas vazias ou com identificadores repetidos.")
        for q in questions.values():
            if not q["label"] or not q["prompt"] or q["group"] not in ("afinidades", "objetivos"):
                raise ValueError("Pergunta sem descrição ou com grupo inválido.")
        skills = kb["skills"]
        if not skills:
            raise ValueError("Catálogo de competências vazio.")
        visited, active = set(), set()

        def visit(skill: str) -> None:
            if skill not in skills:
                raise ValueError(f"Competência inexistente: {skill}.")
            if skill in active:
                raise ValueError(f"Ciclo de pré-requisitos em {skill}.")
            if skill in visited:
                return
            active.add(skill)
            spec = skills[skill]
            _number(spec["hours_per_level"], 1, 1000, "Horas por nível")
            for field in ("name", "study", "url"):
                if not spec[field]:
                    raise ValueError(f"Competência {skill} sem {field}.")
            for field in ("category", "evidence"):
                if field in spec and (not isinstance(spec[field], str) or not spec[field].strip()):
                    raise ValueError(f"Competência {skill} com {field} inválido.")
            for prerequisite in spec["prerequisites"]:
                visit(prerequisite)
            active.remove(skill)
            visited.add(skill)

        for skill in skills:
            visit(skill)
        if not kb["tracks"]:
            raise ValueError("Base sem trilhas.")
        ids = set()
        for track in kb["tracks"]:
            if track["id"] in ids:
                raise ValueError("Identificadores de trilhas repetidos.")
            ids.add(track["id"])
            if not track["name"] or not track["description"]:
                raise ValueError("Trilha sem descrição.")
            weights = track["weights"]
            if not weights or set(weights) - questions.keys():
                raise ValueError("Pesos com perguntas inexistentes ou vazios.")
            for weight in weights.values():
                _number(weight, 0, 100, "Peso")
            if sum(weights.values()) <= 0:
                raise ValueError("A soma dos pesos deve ser positiva.")
            penalty_ids = set()
            for rule in track["penalties"]:
                if rule["id"] in penalty_ids or not rule["reason"]:
                    raise ValueError("Penalidade repetida ou sem justificativa.")
                penalty_ids.add(rule["id"])
                _number(rule["points"], 0, 100, "Penalidade")
                if not rule["conditions"]:
                    raise ValueError("Penalidade sem condições.")
                for condition in rule["conditions"]:
                    if condition["question"] not in questions or condition["operator"] not in ("lte", "gte"):
                        raise ValueError("Condição de penalidade inválida.")
                    _number(condition["value"], 1, 5, "Limiar")
            requirements = {r["skill"]: r for r in track["requirements"]}
            if not requirements or len(requirements) != len(track["requirements"]):
                raise ValueError("Requisitos vazios ou repetidos.")
            for skill, req in requirements.items():
                if skill not in skills:
                    raise ValueError(f"Requisito inexistente: {skill}.")
                _number(req["target"], 1, 4, "Meta de competência")
                if not isinstance(req["target"], int):
                    raise ValueError("Meta deve ser inteira.")
                _number(req["importance"], 1, 10, "Importância")
                for prerequisite in skills[skill]["prerequisites"]:
                    if prerequisite not in requirements:
                        raise ValueError(f"Pré-requisito {prerequisite} ausente em {track['id']}.")
            for cert in track["certifications"]:
                for field in ("name", "url", "when"):
                    if not cert[field]:
                        raise ValueError("Certificação incompleta.")
            for field in ("title", "summary", "deliverables"):
                if not track["portfolio"][field]:
                    raise ValueError("Projeto de portfólio incompleto.")
        if set(kb["knowledge_levels"]) != {str(n) for n in range(5)}:
            raise ValueError("Escala de conhecimento inválida.")
        for field in ("title", "version", "method", "junior_definition", "certification_note"):
            if not kb["metadata"][field]:
                raise ValueError("Metadados incompletos.")
    except (KeyError, TypeError, AttributeError) as exc:
        raise ValueError(f"Estrutura inválida na base de conhecimento: {exc}") from exc


def load_knowledge(path: str | Path = DEFAULT_KB) -> dict:
    try:
        with Path(path).open(encoding="utf-8") as source:
            kb = json.load(source)
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Não foi possível carregar a base de conhecimento: {exc}") from exc
    validate_knowledge(kb)
    return kb


def rank_careers(kb: dict, answers: dict[str, int | None]) -> dict:
    """Normaliza Likert em [0,1]; soma pesos; desconta regras SE–ENTÃO."""
    questions = {q["id"]: q for q in kb["questions"]}
    if set(answers) - questions.keys():
        raise ValueError("Resposta para uma pergunta inexistente.")
    cfg = kb["scoring"]
    for key, value in answers.items():
        if value is not None:
            _number(value, cfg["min"], cfg["max"], key)
            if not isinstance(value, int):
                raise ValueError("As respostas Likert devem ser inteiras.")
    ranking = []
    for track in kb["tracks"]:
        total_weight = sum(track["weights"].values())
        factors = []
        for key, weight in track["weights"].items():
            value = answers.get(key)
            normalized = (cfg["unknown_normalized"] if value is None else
                          (value - cfg["min"]) / (cfg["max"] - cfg["min"]))
            factors.append({"question": key, "label": questions[key]["label"],
                            "answer": value, "weight": weight,
                            "points": 100 * normalized * weight / total_weight})
        base = sum(f["points"] for f in factors)
        penalties = []
        possible_penalty = 0
        for rule in track["penalties"]:
            def matches(condition: dict) -> bool:
                value = answers.get(condition["question"])
                if value is None:
                    return False
                return (value <= condition["value"] if condition["operator"] == "lte"
                        else value >= condition["value"])
            if all(matches(c) for c in rule["conditions"]):
                penalties.append({"id": rule["id"], "points": rule["points"], "reason": rule["reason"]})
            # Limite conservador: uma regra ainda pode ativar se nenhuma
            # resposta conhecida contradiz suas condições.
            if all(answers.get(c["question"]) is None or matches(c) for c in rule["conditions"]):
                possible_penalty += rule["points"]
        deduction = sum(p["points"] for p in penalties)
        coverage = sum(f["weight"] for f in factors if f["answer"] is not None) / total_weight
        known_points = sum(f["points"] for f in factors if f["answer"] is not None)
        unknown_points = 100 * sum(f["weight"] for f in factors if f["answer"] is None) / total_weight
        ranking.append({"id": track["id"], "name": track["name"],
                        "score": max(0.0, min(100.0, base - deduction)),
                        "base_score": base, "penalty_points": deduction,
                        "coverage": coverage, "factors": factors, "penalties": penalties,
                        "score_min": min(100.0, max(0.0, known_points - possible_penalty)),
                        "score_max": min(100.0, max(0.0, known_points + unknown_points - deduction))})
    # Desempate estável; a interface avisa quando a diferença é pequena.
    ranking.sort(key=lambda result: (-round(result["score"], 10), result["id"]))
    best = ranking[0]
    close = [r["id"] for r in ranking if best["score"] - r["score"] <= cfg["tie_tolerance"]]
    coverage = sum(answers.get(key) is not None for key in questions) / len(questions)
    return {"ranking": ranking, "top3": ranking[:3], "close_tracks": close,
            "coverage": coverage,
            "recommendation_available": coverage >= cfg["min_coverage"] and best["coverage"] >= cfg["min_coverage"],
            "low_compatibility": best["score"] < cfg["low_compatibility"]}


def build_plan(kb: dict, track_id: str, knowledge: dict[str, int], hours_per_week: int = 6,
               target_level: str = "junior") -> dict:
    """Ordena lacunas por pré-requisitos e prioridade; estima esforço restante."""
    _number(hours_per_week, 1, 40, "Horas semanais")
    if not isinstance(hours_per_week, int):
        raise ValueError("Horas semanais devem ser inteiras.")
    if set(knowledge) - kb["skills"].keys():
        raise ValueError("Competência desconhecida na autoavaliação.")
    for skill, level in knowledge.items():
        _number(level, 0, 4, skill)
        if not isinstance(level, int):
            raise ValueError("Níveis de conhecimento devem ser inteiros.")
    track = next((t for t in kb["tracks"] if t["id"] == track_id), None)
    if track is None:
        raise ValueError("Trilha inexistente.")
    if not isinstance(target_level, str) or target_level not in kb["seniority_levels"]:
        raise ValueError("Meta de senioridade inexistente.")
    level = kb["seniority_levels"][target_level]
    rows, gaps = [], {}
    inconsistencies = []
    targets = {req["skill"]: max(req["target"], level["target_floor"])
               for req in track["requirements"]}
    reached = total = 0
    for req in track["requirements"]:
        skill = req["skill"]
        spec = kb["skills"][skill]
        target = targets[skill]
        current = knowledge.get(skill, 0)
        gap = max(0, target - current)
        row = {"skill": skill, "name": spec["name"], "current": current,
               "target": target, "gap": gap, "importance": req["importance"]}
        rows.append(row)
        if current >= target:
            for prerequisite in spec["prerequisites"]:
                if knowledge.get(prerequisite, 0) < targets[prerequisite]:
                    inconsistencies.append({"skill": spec["name"],
                                            "prerequisite": kb["skills"][prerequisite]["name"]})
        total += target * req["importance"]
        reached += min(current, target) * req["importance"]
        if gap:
            gaps[skill] = {**row, "hours": gap * spec["hours_per_level"],
                           "study": spec["study"], "url": spec["url"],
                           "evidence": spec.get("evidence", spec["study"]),
                           "prerequisites": [kb["skills"][p]["name"] for p in spec["prerequisites"]],
                           "priority": gap * req["importance"]}
    remaining = dict(gaps)
    roadmap = []
    elapsed = 0

    def ancestors(skill: str) -> set[str]:
        dependencies = set(kb["skills"][skill]["prerequisites"])
        return dependencies.union(*(ancestors(p) for p in dependencies))

    while remaining:
        available = [g for skill, g in remaining.items()
                     if not (ancestors(skill) & remaining.keys())]
        if not available:
            raise ValueError("Não foi possível ordenar os pré-requisitos.")
        item = min(available, key=lambda g: (-g["priority"], g["skill"]))
        item = {**item, "order": len(roadmap) + 1,
                "start_week": elapsed // hours_per_week + 1,
                "end_week": math.ceil((elapsed + item["hours"]) / hours_per_week)}
        elapsed += item["hours"]
        roadmap.append(item)
        del remaining[item["skill"]]
    portfolio = {**track["portfolio"],
                 "level_guidance": level["portfolio_guidance"],
                 "focus": [g["name"] for g in roadmap],
                 "next_step": ("Aplicar no projeto as competências estudadas e registrar evidências de evolução."
                               if roadmap else "Ampliar o projeto, justificar decisões e pedir revisão de código ou produto.")}
    return {"track_id": track_id, "track_name": track["name"], "requirements": rows,
            "target_level": target_level, "target_level_name": level["name"],
            "target_description": level["description"],
            "gaps": list(gaps.values()), "readiness": 100 * reached / total,
            "status": (("Metas iniciais atendidas" if target_level == "junior" else "Metas de estudo atendidas")
                       if not gaps else "Competências em desenvolvimento"),
            "roadmap": roadmap, "total_hours": elapsed,
            "estimated_weeks": math.ceil(elapsed / hours_per_week),
            "hours_per_week": hours_per_week, "portfolio": portfolio,
            "inconsistencies": inconsistencies,
            "certifications": track["certifications"]}


def report_markdown(kb: dict, profile: dict, result: dict, plan: dict) -> str:
    """Relatório portátil, gerado a partir dos mesmos resultados da interface."""
    lines = ["# Plano de carreira em TI", "", f"Participante: {profile.get('name') or 'Não informado'}",
             f"Momento atual: {profile.get('experience') or 'Não informado'}",
             f"Base de conhecimento: {kb['metadata']['version']}", "",
             "## Compatibilidade com as trilhas", "",
             "Os percentuais expressam aderência ao modelo; não são probabilidades de contratação.", ""]
    for index, row in enumerate(result["ranking"], 1):
        lines.append(f"{index}. {row['name']}: {row['score']:.1f}% (cobertura: {row['coverage']:.0%})")
    if not result["recommendation_available"]:
        lines += ["", "Informação insuficiente para recomendar uma trilha; ranking provisório."]
    if result["low_compatibility"]:
        lines += ["", "Baixa compatibilidade geral: explore atividades práticas antes de decidir."]
    if len(result["close_tracks"]) > 1:
        names = [r["name"] for r in result["ranking"] if r["id"] in result["close_tracks"]]
        lines += ["", "Resultados próximos: " + ", ".join(names) + "."]
    selected = next(r for r in result["ranking"] if r["id"] == plan["track_id"])
    lines += ["", f"## Trilha escolhida: {plan['track_name']}", "",
              f"Pontuação base: {selected['base_score']:.1f}%; penalidades: {selected['penalty_points']:.1f} pontos.",
              f"Meta de estudo: {plan['target_level_name']}. {plan['target_description']}",
              f"Cobertura das metas: {plan['readiness']:.1f}%. {plan['status']}.",
              "As referências são didáticas; a autoavaliação não comprova senioridade profissional.",
              "", "### Explicação do cálculo", ""]
    for f in selected["factors"]:
        answer = f["answer"] if f["answer"] is not None else "Não sei (neutro)"
        lines.append(f"- {f['label']}: resposta {answer}, peso {f['weight']}, contribuição {f['points']:.2f} pontos.")
    for penalty in selected["penalties"]:
        lines.append(f"- Penalidade: −{penalty['points']} pontos. {penalty['reason']}")
    if selected["coverage"] < 1:
        lines += ["", f"Faixa conservadora com respostas pendentes: {selected['score_min']:.1f}% a {selected['score_max']:.1f}%.",
                  "Essa faixa representa possíveis variações das respostas desconhecidas, não um intervalo de confiança estatístico."]
    if plan["inconsistencies"]:
        lines += ["", "### Pontos da autoavaliação para revisar", ""]
        for item in plan["inconsistencies"]:
            lines.append(f"- Você declarou domínio inicial de {item['skill']}, mas ainda falta a base em {item['prerequisite']}.")
    lines += ["", "### Competências", "", "| Competência | Atual | Meta | Lacuna |",
              "|---|---:|---:|---:|"]
    for req in plan["requirements"]:
        lines.append(f"| {req['name']} | {req['current']} | {req['target']} | {req['gap']} |")
    lines += ["", "### Roteiro de estudos", "",
              f"Estimativa didática: {plan['total_hours']} horas, cerca de {plan['estimated_weeks']} semanas a {plan['hours_per_week']} h/semana.",
              "O prazo considera apenas as lacunas de estudo; projeto e preparação para exames têm duração adicional.", ""]
    for step in plan["roadmap"]:
        lines += [f"{step['order']}. **{step['name']}** — semanas {step['start_week']}–{step['end_week']}, {step['hours']} h.",
                  f"   {step['study']} [Material oficial]({step['url']}).",
                  f"   **Evidência de aprendizagem:** {step['evidence']}"]
    if not plan["roadmap"]:
        lines.append("Sem lacunas para a meta selecionada nesta base. Avance para o projeto de portfólio.")
    project = plan["portfolio"]
    lines += ["", f"### Portfólio: {project['title']}", "", project["summary"], ""]
    lines.extend(f"- {item}" for item in project["deliverables"])
    if project["focus"]:
        lines += ["", "Pratique especialmente: " + ", ".join(project["focus"]) + "."]
    lines += ["", project["next_step"], "", project["level_guidance"],
              "", "### Certificações opcionais", "", kb["metadata"]["certification_note"], ""]
    for cert in plan["certifications"]:
        lines.append(f"- [{cert['name']}]({cert['url']}): {cert['when']}")
    lines += ["", "### Limitações", "", kb["metadata"]["method"],
              "Respostas desconhecidas usam valor neutro e não ativam penalidades. A autoavaliação não substitui avaliação prática."]
    return "\n".join(lines) + "\n"
