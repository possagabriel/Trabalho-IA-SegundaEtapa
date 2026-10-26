"""Importação e exportação de entradas; resultados são sempre recalculados."""

import json

from career.engine import build_plan, rank_careers

EXPERIENCES = ["Estou começando", "Já estudo ou desenvolvo projetos", "Já trabalho com tecnologia"]
MAX_IMPORT_BYTES = 1_000_000


def empty_assessment():
    return {"profile": {"name": "", "hours": 6, "experience": EXPERIENCES[0], "target_level": "junior"},
            "answers": {}, "knowledge": {}}


def export_assessment(kb, profile, answers, knowledge, *, result=None, plan=None):
    payload = {"format_version": 1, "knowledge_base_version": kb["metadata"]["version"],
               "profile": profile, "answers": answers, "knowledge": knowledge}
    if result is not None:
        payload["result"] = result
    if plan is not None:
        payload["plan"] = plan
    return json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False)


def import_assessment(raw: bytes, kb: dict) -> dict:
    """Aceita também exportações antigas; não confia em pontuações importadas."""
    if len(raw) > MAX_IMPORT_BYTES:
        raise ValueError("O arquivo deve ter no máximo 1 MB.")
    try:
        data = json.loads(raw.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError) as exc:
        raise ValueError("Arquivo inválido. Use a avaliação JSON exportada pelo Rotas TI.") from exc
    if not isinstance(data, dict):
        raise ValueError("A avaliação deve ser um objeto JSON.")
    if type(data.get("format_version", 1)) is not int or data.get("format_version", 1) != 1:
        raise ValueError("Versão de arquivo não suportada.")
    for key in ("profile", "answers", "knowledge"):
        if not isinstance(data.get(key), dict):
            raise ValueError(f"Campo obrigatório inválido: {key}.")
    profile = data["profile"]
    name = profile.get("name", "")
    experience = profile.get("experience", EXPERIENCES[0])
    if not isinstance(name, str) or len(name) > 100:
        raise ValueError("O nome deve ter até 100 caracteres.")
    if experience not in EXPERIENCES:
        raise ValueError("Momento profissional inválido.")
    hours = profile.get("hours", 6)
    target_level = profile.get("target_level", "junior")
    # Reutiliza as regras do motor, incluindo faixas e rejeição de booleanos.
    rank_careers(kb, data["answers"])
    build_plan(kb, kb["tracks"][0]["id"], data["knowledge"], hours, target_level)
    return {"profile": {"name": name.strip(), "experience": experience, "hours": hours,
                        "target_level": target_level},
            "answers": data["answers"], "knowledge": data["knowledge"],
            "version_changed": data.get("knowledge_base_version") != kb["metadata"]["version"]}
