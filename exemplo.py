"""Demonstração do motor sem dependências externas: python exemplo.py."""

from career.engine import build_plan, load_knowledge, rank_careers, report_markdown


def main():
    kb = load_knowledge()
    answers = {question["id"]: 2 for question in kb["questions"]}
    answers.update(infra=5, automacao=5, redes=5, incidentes=5, operar=5, detalhes=5, arquitetar=4)
    result = rank_careers(kb, answers)
    profile = {"name": "Perfil demonstrativo de infraestrutura", "hours": 6}
    plan = build_plan(kb, result["top3"][0]["id"], {"git": 2, "linux": 1}, profile["hours"])
    print(report_markdown(kb, profile, result, plan))


if __name__ == "__main__":
    main()
