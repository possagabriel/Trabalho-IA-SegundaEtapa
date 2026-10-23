"""Execute com: streamlit run app.py."""

import json

import pandas as pd
import streamlit as st

from career.engine import build_plan, load_knowledge, rank_careers, report_markdown

st.set_page_config(page_title="Rotas TI · Consultor de carreiras", page_icon="🧭", layout="wide")

try:
    kb = load_knowledge()
except ValueError as error:
    st.error(str(error))
    st.stop()

if "step" not in st.session_state:
    st.session_state.update(step=0, profile={"name": "", "hours": 6, "experience": "Estou começando"},
                            answers={}, knowledge={})

LIKERT = {None: "Não sei / ainda não explorei", 1: "1 · Nenhuma afinidade",
          2: "2 · Pouca afinidade", 3: "3 · Afinidade moderada",
          4: "4 · Muita afinidade", 5: "5 · Afinidade muito alta"}
STEPS = ["Perfil pessoal", "Afinidades técnicas", "Objetivos de carreira", "Seu plano"]


def question_inputs(group):
    values = {}
    columns = st.columns(2)
    for index, question in enumerate(q for q in kb["questions"] if q["group"] == group):
        options = list(LIKERT)
        with columns[index % 2]:
            values[question["id"]] = st.selectbox(
                question["label"], options,
                index=options.index(st.session_state.answers.get(question["id"])),
                format_func=lambda value: LIKERT[value], help=question["prompt"],
                key=f"question_{question['id']}")
    return values


def move(step):
    st.session_state.step = step
    st.rerun()


with st.sidebar:
    st.title("🧭 Rotas TI")
    st.caption("Sistema especialista de carreiras")
    for index, label in enumerate(STEPS):
        prefix = "●" if index == st.session_state.step else "✓" if index < st.session_state.step else "○"
        st.write(f"{prefix} {index + 1}. {label}")
    st.divider()
    st.caption("10 trilhas · regras explicáveis · plano individual")
    st.caption("As respostas ficam na sessão. Você pode baixar o relatório ao concluir.")
    if st.button("Nova avaliação", use_container_width=True):
        for key in list(st.session_state):
            del st.session_state[key]
        st.rerun()

st.title("Encontre sua próxima direção em TI")
st.write("Explore afinidades, reconheça o que já sabe e transforme suas lacunas em um plano de prática.")
st.progress((st.session_state.step + 1) / len(STEPS), text=f"Etapa {st.session_state.step + 1} de 4 · {STEPS[st.session_state.step]}")

if st.session_state.step == 0:
    st.header("1. Perfil pessoal")
    st.write("Vamos ajustar o ritmo do plano à sua disponibilidade. O nome é opcional.")
    with st.form("profile_form"):
        name = st.text_input("Como você quer ser chamado(a)?", value=st.session_state.profile["name"], max_chars=100)
        experiences = ["Estou começando", "Já estudo ou desenvolvo projetos", "Já trabalho com tecnologia"]
        experience = st.selectbox("Seu momento atual", experiences,
                                  index=experiences.index(st.session_state.profile["experience"]))
        hours = st.slider("Horas de estudo por semana", min_value=1, max_value=40,
                          value=st.session_state.profile["hours"])
        st.caption("O momento atual contextualiza o relatório. As competências serão avaliadas individualmente na próxima etapa.")
        if st.form_submit_button("Continuar para afinidades", type="primary"):
            st.session_state.profile = {"name": name.strip(), "experience": experience, "hours": hours}
            move(1)

elif st.session_state.step == 1:
    st.header("2. Afinidades técnicas")
    st.write("Responda de 1 a 5. Gostar de um tema é diferente de já dominá-lo. Use “Não sei” se ainda não explorou a área.")
    with st.form("technical_form"):
        answers = question_inputs("afinidades")
        st.subheader("O que você já sabe fazer?")
        st.write("Avalie suas competências de 0 a 4. O valor inicial 0 significa que você ainda não estudou o tema; revise os que já conhece.")
        st.caption("0: nunca estudei · 1: teoria · 2: prática com orientação · 3: autonomia · 4: aprofundamento e orientação de outras pessoas")
        knowledge = {}
        with st.expander("Autoavaliação de competências — abrir e preencher", expanded=True):
            columns = st.columns(2)
            for index, (skill, spec) in enumerate(kb["skills"].items()):
                with columns[index % 2]:
                    knowledge[skill] = st.select_slider(
                        spec["name"], options=list(range(5)), value=st.session_state.knowledge.get(skill, 0),
                        help=spec["study"], key=f"skill_{skill}")
        left, right = st.columns(2)
        back = left.form_submit_button("Voltar ao perfil")
        forward = right.form_submit_button("Continuar para objetivos", type="primary")
        if back or forward:
            st.session_state.answers.update(answers)
            st.session_state.knowledge = knowledge
            move(0 if back else 2)

elif st.session_state.step == 2:
    st.header("3. Objetivos de carreira")
    st.write("Quanta afinidade você tem com cada tipo de atividade profissional? Essas respostas também entram no cálculo.")
    with st.form("goals_form"):
        answers = question_inputs("objetivos")
        st.info("Você poderá explorar qualquer uma das dez trilhas, mesmo que ela não esteja no Top 3.")
        left, right = st.columns(2)
        back = left.form_submit_button("Voltar às afinidades")
        forward = right.form_submit_button("Gerar meu plano", type="primary")
        if back or forward:
            st.session_state.answers.update(answers)
            move(1 if back else 3)

else:
    result = rank_careers(kb, st.session_state.answers)
    st.header("Seu mapa de possibilidades")
    if st.session_state.profile["name"]:
        st.write(st.session_state.profile["name"] + ", este é o resultado da sua avaliação.")
    st.caption("Compatibilidade é aderência às regras deste modelo, não probabilidade de sucesso ou contratação. Afinidade e cobertura de competências são medidas distintas.")
    if not result["recommendation_available"]:
        st.warning("Informação insuficiente para recomendar uma trilha. O ranking é provisório: responda a mais perguntas. Você ainda pode explorar os planos.")
    if result["low_compatibility"]:
        st.info("A compatibilidade geral foi baixa. Experimente atividades curtas de diferentes áreas antes de escolher; o primeiro lugar não significa alta afinidade.")
    if len(result["close_tracks"]) > 1:
        close_names = [r["name"] for r in result["ranking"] if r["id"] in result["close_tracks"]]
        st.info(f"Resultados próximos (até {kb['scoring']['tie_tolerance']} pontos do primeiro): {', '.join(close_names)}. Explore as alternativas; empates exatos são ordenados pelo identificador da trilha.")
    for column, row in zip(st.columns(3), result["top3"]):
        with column:
            st.metric(row["name"], f"{row['score']:.1f}%")
            st.caption(f"Perguntas relevantes respondidas: {row['coverage']:.0%} (ponderadas)")
    frame = pd.DataFrame([{"Trilha": r["name"], "Compatibilidade (%)": round(r["score"], 2),
                           "Base (%)": round(r["base_score"], 2), "Penalidade (p.p.)": r["penalty_points"],
                           "Cobertura (%)": round(100 * r["coverage"], 2)} for r in result["ranking"]])
    st.bar_chart(frame.set_index("Trilha")[["Compatibilidade (%)"]], horizontal=True, color="#0F766E")
    with st.expander("Matriz completa de compatibilidade"):
        st.dataframe(frame, hide_index=True, use_container_width=True)
    names = {t["id"]: t["name"] for t in kb["tracks"]}
    chosen = st.selectbox("Escolha a trilha para detalhar o plano", [r["id"] for r in result["ranking"]],
                          format_func=names.get, key="chosen_track")
    plan = build_plan(kb, chosen, st.session_state.knowledge, st.session_state.profile["hours"])
    selected = next(r for r in result["ranking"] if r["id"] == chosen)
    track = next(t for t in kb["tracks"] if t["id"] == chosen)
    st.subheader(track["name"])
    st.write(track["description"])
    with st.expander("Por que esta pontuação? Veja as regras e os pesos"):
        st.write(f"Base ponderada: {selected['base_score']:.2f}% · Penalidades: {selected['penalty_points']:.2f} p.p. · Resultado: {selected['score']:.2f}%")
        factors = pd.DataFrame([{"Fator": f["label"], "Resposta": str(f["answer"]) if f["answer"] is not None else "Não sei",
                                 "Peso": f["weight"], "Contribuição (p.p.)": round(f["points"], 2)} for f in selected["factors"]])
        st.dataframe(factors, hide_index=True, use_container_width=True)
        for penalty in selected["penalties"]:
            st.write(f"−{penalty['points']} p.p.: {penalty['reason']}")
        if not selected["penalties"]:
            st.write("Nenhuma penalidade foi ativada.")
        st.latex(r"C_t = \max(0,\min(100,100\frac{\sum_i w_{ti}n_i}{\sum_i w_{ti}} - \sum_j p_{tj}))")
        st.caption("n = (resposta − 1) / 4. Respostas desconhecidas usam 0,5 e não ativam penalidades. Cada trilha tem sua própria escala de 0 a 100%; os percentuais não somam 100%.")
    gaps_tab, roadmap_tab, project_tab = st.tabs(["Competências e lacunas", "Roteiro de estudos", "Portfólio e certificações"])
    with gaps_tab:
        st.metric("Cobertura das metas iniciais de competência", f"{plan['readiness']:.1f}%")
        st.write(plan["status"])
        st.caption(kb["metadata"]["junior_definition"])
        st.dataframe(pd.DataFrame([{"Competência": r["name"], "Nível atual": r["current"],
                                     "Meta Júnior": r["target"], "Lacuna": r["gap"]} for r in plan["requirements"]]),
                     hide_index=True, use_container_width=True)
    with roadmap_tab:
        st.write(f"**{plan['total_hours']} horas estimadas · {plan['estimated_weeks']} semanas · {plan['hours_per_week']} h por semana**")
        st.caption("Estimativa didática apenas para as lacunas de estudo. Portfólio e exames exigem tempo adicional. A ordem respeita pré-requisitos e prioriza lacunas ponderadas pela importância.")
        if not plan["roadmap"]:
            st.success("Você já declarou as competências das metas iniciais. Avance para o portfólio e valide seu conhecimento na prática.")
        for item in plan["roadmap"]:
            st.markdown(f"**{item['order']}. {item['name']}** · semanas {item['start_week']}–{item['end_week']} · {item['hours']} h")
            st.write(item["study"])
            st.markdown(f"[Estudar na fonte oficial]({item['url']})")
    with project_tab:
        project = plan["portfolio"]
        st.subheader(project["title"])
        st.write(project["summary"])
        for deliverable in project["deliverables"]:
            st.markdown(f"- {deliverable}")
        if project["focus"]:
            st.write("Pratique especialmente: " + ", ".join(project["focus"]) + ".")
        st.write(project["next_step"])
        st.caption("Organize o projeto em um repositório GitHub com README, instruções de execução e evidências das entregas.")
        st.subheader("Certificações opcionais")
        st.caption(kb["metadata"]["certification_note"])
        for cert in plan["certifications"]:
            st.markdown(f"**[{cert['name']}]({cert['url']})**")
            st.write(cert["when"])
    report = report_markdown(kb, st.session_state.profile, result, plan)
    export = {"knowledge_base_version": kb["metadata"]["version"], "profile": st.session_state.profile,
              "answers": st.session_state.answers, "knowledge": st.session_state.knowledge,
              "result": result, "plan": plan}
    st.divider()
    left, middle, right = st.columns(3)
    left.download_button("Baixar relatório (.md)", report, "plano_carreira.md", "text/markdown; charset=utf-8", use_container_width=True)
    middle.download_button("Baixar avaliação (.json)", json.dumps(export, ensure_ascii=False, indent=2),
                           "avaliacao_carreira.json", "application/json", use_container_width=True)
    if right.button("Revisar minhas respostas", use_container_width=True):
        move(0)
    st.caption(kb["metadata"]["method"])
