"""Apresentação Streamlit; as regras de domínio ficam no motor e no JSON."""

import json
from html import escape
from pathlib import Path

import pandas as pd
import streamlit as st

from career.assessment import EXPERIENCES, empty_assessment, export_assessment, import_assessment
from career.charts import compatibility_chart, comparison_chart
from career.engine import build_plan, rank_careers, report_markdown

ROOT = Path(__file__).resolve().parent.parent
STEPS = ["Seu momento", "Suas afinidades", "Seus objetivos", "Seu próximo passo"]
LIKERT = {None: "Não sei / ainda não explorei", 1: "1 · Nenhuma afinidade",
          2: "2 · Pouca afinidade", 3: "3 · Afinidade moderada",
          4: "4 · Muita afinidade", 5: "5 · Afinidade muito alta"}


def move(step):
    st.session_state.step = step
    st.rerun()


def replace_assessment(data, step=0, notice=None):
    for key in list(st.session_state):
        del st.session_state[key]
    st.session_state.update({key: data[key] for key in ("profile", "answers", "knowledge")})
    st.session_state.step = step
    if notice:
        st.session_state.notice = notice
    st.rerun()


def sidebar(kb):
    with st.sidebar:
        st.markdown('<div class="brand"><div class="brand-mark">↗</div><div><div class="brand-name">rotas ti</div><div class="brand-sub">Carreira começa com direção.</div></div></div>', unsafe_allow_html=True)
        for index, label in enumerate(STEPS):
            status = "active" if index == st.session_state.step else "done" if index < st.session_state.step else ""
            marker = "✓" if index < st.session_state.step else str(index + 1)
            st.markdown(f'<div class="step {status}"><b>{marker}</b><span>{label}</span></div>', unsafe_allow_html=True)
        st.divider()
        answered = sum(value is not None for value in st.session_state.answers.values())
        st.caption(f"{answered} de {len(kb['questions'])} afinidades e objetivos respondidos")
        st.progress(answered / len(kb["questions"]))
        st.caption("O progresso é atualizado ao salvar cada etapa.")
        with st.expander("Salvar ou retomar avaliação"):
            snapshot = export_assessment(kb, st.session_state.profile, st.session_state.answers, st.session_state.knowledge)
            st.download_button("Salvar progresso (.json)", snapshot, "progresso_rotas_ti.json", "application/json",
                               key="save_progress", width="stretch")
            st.caption("Salva as respostas confirmadas nos botões das etapas. Retome depois enviando esse arquivo.")
            upload = st.file_uploader("Abrir avaliação salva", type=["json"], key="restore_file")
            if st.button("Restaurar avaliação", disabled=upload is None, width="stretch"):
                try:
                    data = import_assessment(upload.getvalue(), kb)
                except ValueError as error:
                    st.error(str(error))
                else:
                    notice = "Avaliação restaurada. Revise seu perfil e avance quando quiser."
                    if data["version_changed"]:
                        notice += " A base foi atualizada; o resultado será recalculado com as regras atuais."
                    replace_assessment(data, notice=notice)
        if st.button("Nova avaliação", width="stretch"):
            replace_assessment(empty_assessment())
        st.caption("Seus dados ficam nesta sessão. Você decide o que baixar e compartilhar.")


def header():
    if st.session_state.step == 0:
        st.markdown('''<div class="hero"><div class="eyebrow">Seu futuro, um passo de cada vez</div>
        <h1>Existem muitas rotas em TI.<br>Encontre a sua.</h1>
        <p>Conecte o que você gosta ao que já sabe. Descubra caminhos possíveis e saia com um plano concreto para começar.</p>
        <div class="hero-tags"><span>10 trilhas para explorar</span><span>Recomendações explicadas</span><span>No seu ritmo</span></div></div>''', unsafe_allow_html=True)
    else:
        st.markdown('<div class="section-kicker">Rotas TI / Seu mapa de carreira</div>', unsafe_allow_html=True)
    st.progress((st.session_state.step + 1) / 4,
                text=f"Etapa {st.session_state.step + 1} de 4 · {STEPS[st.session_state.step]}")
    if notice := st.session_state.pop("notice", None):
        st.info(notice)


def profile_page(kb):
    with st.container(key="intro_overview"):
        for column, (title, body) in zip(st.columns(3), [
            ("01 · Descubra afinidades", "Diga quais atividades despertam sua curiosidade."),
            ("02 · Reconheça sua base", "Identifique o que já domina e o que falta praticar."),
            ("03 · Dê o próximo passo", "Receba uma sequência de estudos e um projeto para construir.")]):
            with column:
                st.markdown(f'<div class="overview"><strong>{title}</strong><p>{body}</p></div>', unsafe_allow_html=True)
    main, aside = st.columns([1.6, 1], gap="large")
    with main:
        st.subheader("Vamos começar por você")
        st.write("Seu momento e sua disponibilidade ajudam a organizar o plano.")
        with st.form("profile_form"):
            profile = st.session_state.profile
            name = st.text_input("Como você quer ser chamado(a)?", value=profile["name"], max_chars=100,
                                 placeholder="Seu nome (opcional)")
            experience = st.selectbox("Seu momento atual", EXPERIENCES, index=EXPERIENCES.index(profile["experience"]))
            hours = st.slider("Horas de estudo por semana", 1, 40, value=profile["hours"])
            st.caption("Escolha um ritmo que caiba na sua rotina. Você poderá ajustá-lo no resultado.")
            if st.form_submit_button("Continuar para afinidades", type="primary", width="stretch"):
                st.session_state.profile = {"name": name.strip(), "experience": experience, "hours": hours}
                move(1)
    with aside:
        with st.container(border=True):
            st.subheader("Não precisa ter todas as respostas")
            st.write("Você pode estar começando ou mudando de área. Use “Não sei” nos temas que ainda não explorou.")
            st.write("O resultado mostra possibilidades. Cada recomendação vem com os motivos e com o que você pode estudar a seguir.")
            st.caption("Afinidade é interesse. Competência é o que você consegue fazer hoje. Vamos observar as duas coisas separadamente.")
        with st.expander("Quer conhecer antes de preencher?"):
            demos = json.loads((ROOT / "data/perfis_exemplo.json").read_text(encoding="utf-8"))
            selected = st.selectbox("Perfil de demonstração", range(len(demos)), format_func=lambda index: demos[index]["label"])
            st.caption("Dados fictícios para explorar os gráficos e planos. Substitui o preenchimento desta sessão.")
            if st.button("Explorar demonstração", width="stretch"):
                replace_assessment(demos[selected], step=3, notice="Modo de demonstração: este resultado usa um perfil fictício. Use “Nova avaliação” para criar o seu.")


def question_inputs(kb, group):
    values = {}
    columns = st.columns(2, gap="large")
    for index, question in enumerate(q for q in kb["questions"] if q["group"] == group):
        with columns[index % 2]:
            values[question["id"]] = st.selectbox(
                question["label"], list(LIKERT),
                index=list(LIKERT).index(st.session_state.answers.get(question["id"])),
                format_func=LIKERT.get, key=f"question_{question['id']}")
            st.caption(question["prompt"])
    return values


def technical_page(kb):
    st.title("O que desperta seu interesse?")
    st.write("Pense nas atividades que você gostaria de fazer, mesmo que ainda não saiba como.")
    with st.form("technical_form"):
        interests, skills = st.tabs(["1. Meus interesses", "2. O que já sei fazer"])
        with interests:
            st.caption("1 = nenhuma afinidade · 3 = moderada · 5 = muito alta. “Não sei” mantém a pergunta em aberto.")
            answers = question_inputs(kb, "afinidades")
        with skills:
            st.subheader("Reconheça o que você já aprendeu")
            st.write("Abra cada grupo e ajuste os temas que você conhece. Os demais começam em 0: nunca estudei.")
            st.info("0 · Nunca estudei  |  1 · Conheço a teoria  |  2 · Faço com orientação  |  3 · Tenho autonomia  |  4 · Aprofundo e oriento")
            knowledge = {}
            categories = dict.fromkeys(spec.get("category", "Outras competências") for spec in kb["skills"].values())
            for category in categories:
                items = [(key, spec) for key, spec in kb["skills"].items() if spec.get("category", "Outras competências") == category]
                with st.expander(f"{category} · {len(items)} competências"):
                    columns = st.columns(2, gap="large")
                    for index, (skill, spec) in enumerate(items):
                        with columns[index % 2]:
                            knowledge[skill] = st.select_slider(spec["name"], options=list(range(5)),
                                value=st.session_state.knowledge.get(skill, 0), key=f"skill_{skill}",
                                help=spec.get("evidence", spec["study"]))
        st.divider()
        st.caption("Revise as duas abas. Suas respostas serão salvas ao avançar ou voltar.")
        left, right = st.columns(2)
        back = left.form_submit_button("Voltar ao perfil", width="stretch")
        forward = right.form_submit_button("Continuar para objetivos", type="primary", width="stretch")
        if back or forward:
            st.session_state.answers.update(answers)
            st.session_state.knowledge = knowledge
            move(0 if back else 2)


def goals_page(kb):
    st.title("Como você imagina seu dia a dia?")
    st.write("Agora pense no tipo de atividade que gostaria de ter na sua rotina profissional.")
    with st.form("goals_form"):
        answers = question_inputs(kb, "objetivos")
        st.divider()
        st.caption("Na próxima tela, você poderá comparar as dez carreiras e escolher qual plano explorar.")
        left, right = st.columns(2)
        back = left.form_submit_button("Voltar às afinidades", width="stretch")
        forward = right.form_submit_button("Gerar meu plano", type="primary", width="stretch")
        if back or forward:
            st.session_state.answers.update(answers)
            if forward:
                for key in ("chosen_track", "comparison_tracks", "plan_hours"):
                    st.session_state.pop(key, None)
            move(1 if back else 3)


def result_notices(kb, result):
    if not result["recommendation_available"]:
        st.warning("Informação insuficiente para recomendar uma trilha. O ranking é provisório: responda a mais perguntas. Você ainda pode explorar os planos.")
    elif result["low_compatibility"]:
        st.info("A compatibilidade geral ficou baixa. Experimente atividades curtas de diferentes áreas antes de escolher.")
    if len(result["close_tracks"]) > 1 and result["recommendation_available"]:
        names = [r["name"] for r in result["ranking"] if r["id"] in result["close_tracks"]]
        st.info(f"Há caminhos igualmente interessantes: {', '.join(names)}. A diferença é de até {kb['scoring']['tie_tolerance']} pontos. Compare as atividades e o que falta estudar.")


def recommendation_cards(result):
    for index, (column, row) in enumerate(zip(st.columns(3), result["top3"])):
        with column, st.container(border=True, key=f"recommendation_{index}"):
            st.caption(f"{index + 1:02d} / COMPATIBILIDADE")
            st.metric(row["name"], f"{row['score']:.1f}%")
            strengths = sorted([f for f in row["factors"] if f["answer"] is not None and f["answer"] >= 4],
                               key=lambda f: -f["points"])[:2]
            st.caption("Seus sinais: " + ", ".join(f["label"].lower() for f in strengths) if strengths else "Explore as atividades desta trilha para conhecer melhor sua afinidade.")
            st.progress(row["coverage"], text=f"{row['coverage']:.0%} das informações relevantes respondidas")
            if st.button("Explorar esta trilha", key=f"explore_{row['id']}", width="stretch"):
                st.session_state.chosen_track = row["id"]
                st.rerun()


def plan_panel(kb, plan):
    columns = st.columns(3)
    columns[0].metric("Competências iniciais", f"{plan['readiness']:.0f}%")
    columns[1].metric("Lacunas a trabalhar", str(len(plan["gaps"])))
    columns[2].metric("Estudo estimado", f"{plan['estimated_weeks']} semanas", help=f"{plan['total_hours']} horas, a {plan['hours_per_week']} h/semana. Projeto e exames são adicionais.")
    st.caption(kb["metadata"]["junior_definition"])
    if plan["inconsistencies"]:
        with st.expander("Vale revisar alguns pré-requisitos da sua autoavaliação", expanded=True):
            for item in plan["inconsistencies"]:
                st.write(f"Você declarou domínio inicial de {item['skill']}, mas ainda falta a base em {item['prerequisite']}. Revise seus níveis ou reforce esse fundamento.")
    if plan["roadmap"]:
        first = plan["roadmap"][0]
        st.markdown(f'<div class="next-action"><small>Seu primeiro passo</small><h3>{escape(first["name"])}</h3><p>{escape(first["study"])}</p><p><b>Entrega prática:</b> {escape(first["evidence"])}</p></div>', unsafe_allow_html=True)
        st.markdown(f"[Abrir material para começar →]({first['url']})")
    else:
        st.success("As metas iniciais estão cobertas. Seu próximo passo é demonstrar essas competências no projeto de portfólio.")
    roadmap, skills, portfolio = st.tabs(["Roteiro de estudos", "Minhas lacunas", "Projeto e certificações"])
    with roadmap:
        st.caption("Os fundamentos vêm antes das tecnologias que dependem deles. Estimativas incluem só as lacunas de estudo, sem portfólio ou exames.")
        for item in plan["roadmap"]:
            with st.expander(f"{item['order']:02d} · {item['name']} — semanas {item['start_week']}–{item['end_week']} · {item['hours']} h"):
                st.write(item["study"])
                if item["prerequisites"]:
                    st.caption("Base necessária: " + ", ".join(item["prerequisites"]))
                st.write("**Como demonstrar que aprendeu:** " + item["evidence"])
                st.markdown(f"[Estudar na fonte oficial]({item['url']})")
        if not plan["roadmap"]:
            st.write("Nenhuma etapa de estudo pendente para a referência inicial. Consulte a aba de projeto.")
    with skills:
        st.write("Compare o que você declarou com a meta inicial desta trilha.")
        rows = [{"Competência": r["name"], "Atual": r["current"], "Meta": r["target"],
                 "Falta evoluir": r["gap"], "Situação": "Praticar" if r["gap"] else "Meta atendida"}
                for r in sorted(plan["requirements"], key=lambda r: -r["gap"])]
        st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch",
                     column_config={"Atual": st.column_config.ProgressColumn(min_value=0, max_value=4, format="%d"),
                                    "Meta": st.column_config.NumberColumn(format="%d")})
    with portfolio:
        project = plan["portfolio"]
        st.subheader(project["title"])
        st.write(project["summary"])
        for item in project["deliverables"]:
            st.markdown(f"- {item}")
        if project["focus"]:
            st.info("Use o projeto para praticar: " + ", ".join(project["focus"]) + ".")
        st.caption("No GitHub, inclua README, instruções de execução e evidências das entregas. " + project["next_step"])
        st.subheader("Certificações para considerar depois")
        st.caption(kb["metadata"]["certification_note"])
        for cert in plan["certifications"]:
            with st.container(border=True):
                st.markdown(f"**[{cert['name']}]({cert['url']})**")
                st.write(cert["when"])


def comparison_panel(kb, result, chosen, hours):
    st.subheader("Compare possibilidades, além do primeiro lugar")
    st.caption("A barra mostra a aderência atual. O traço indica a faixa conservadora das respostas ainda desconhecidas; não é um intervalo estatístico.")
    st.altair_chart(compatibility_chart(result["ranking"], chosen), width="stretch")
    names = {r["id"]: r["name"] for r in result["ranking"]}
    ids = st.multiselect("Quais trilhas você quer comparar?", list(names),
                        default=[r["id"] for r in result["top3"]], format_func=names.get,
                        max_selections=3, key="comparison_tracks")
    if ids:
        rows = []
        for track_id in ids:
            row = next(r for r in result["ranking"] if r["id"] == track_id)
            plan = build_plan(kb, track_id, st.session_state.knowledge, hours)
            rows.append({**row, **plan})
        st.altair_chart(comparison_chart(rows), width="stretch")
        st.caption("Afinidade mede interesse. Competências iniciais medem o conhecimento declarado. Uma carreira pode atrair você e ainda exigir bastante estudo.")
        st.dataframe(pd.DataFrame([{"Trilha": r["name"], "Afinidade (%)": round(r["score"], 1),
                                     "Competências (%)": round(r["readiness"], 1), "Lacunas": len(r["gaps"]),
                                     "Horas de estudo": r["total_hours"], "Semanas": r["estimated_weeks"]} for r in rows]),
                     hide_index=True, width="stretch")
    else:
        st.info("Selecione até três trilhas para comparar afinidade, competências e esforço de estudo.")
    with st.expander("Matriz completa das dez trilhas"):
        st.dataframe(pd.DataFrame([{"Trilha": r["name"], "Compatibilidade (%)": round(r["score"], 1),
                                     "Base (%)": round(r["base_score"], 1), "Penalidade (p.p.)": r["penalty_points"],
                                     "Cobertura (%)": round(100 * r["coverage"], 1)} for r in result["ranking"]]),
                     hide_index=True, width="stretch")


def explanation_panel(kb, selected):
    st.subheader("Cada recomendação tem um motivo")
    st.write(f"A trilha **{selected['name']}** teve **{selected['base_score']:.1f}%** de pontuação ponderada e **{selected['penalty_points']:.0f} pontos** de penalidades, chegando a **{selected['score']:.1f}%**.")
    if selected["coverage"] < 1:
        st.info(f"Ainda há perguntas em aberto. Dependendo das respostas, a pontuação pode variar dentro da faixa conservadora de {selected['score_min']:.1f}% a {selected['score_max']:.1f}%.")
        unknown = [f["label"] for f in selected["factors"] if f["answer"] is None]
        st.write("Para conhecer melhor essa compatibilidade, explore: " + ", ".join(unknown) + ".")
    factors = [{"Atividade": f["label"], "Sua resposta": LIKERT[f["answer"]], "Peso": f["weight"],
                "Contribuição (p.p.)": round(f["points"], 2)} for f in sorted(selected["factors"], key=lambda f: -f["points"])]
    st.dataframe(pd.DataFrame(factors), hide_index=True, width="stretch")
    for penalty in selected["penalties"]:
        st.write(f"**−{penalty['points']} pontos:** {penalty['reason']}")
    if not selected["penalties"]:
        st.success("Nenhuma penalidade foi ativada para esta trilha.")
    with st.expander("Entenda a fórmula e os limites do modelo"):
        st.latex(r"C_t = \max(0,\min(100,100\frac{\sum_i w_{ti}n_i}{\sum_i w_{ti}} - \sum_j p_{tj}))")
        st.write("Cada resposta de 1 a 5 é convertida para 0 a 1. Os pesos representam a relevância da atividade para a trilha. Respostas desconhecidas usam 0,5 e não ativam penalidades.")
        st.write(f"Trilhas com até {kb['scoring']['tie_tolerance']} pontos de diferença do primeiro lugar são apresentadas como próximas. Empates exatos são ordenados pelo identificador, sem indicar preferência real.")
        st.caption(kb["metadata"]["method"])


def results_page(kb):
    result = rank_careers(kb, st.session_state.answers)
    st.title("Seu próximo passo começa aqui")
    if st.session_state.profile["name"]:
        st.write(st.session_state.profile["name"] + ", estas são as possibilidades que seu perfil aponta hoje.")
    st.caption("Percentuais expressam aderência ao modelo, não probabilidade de contratação. Todas as trilhas continuam disponíveis para explorar.")
    result_notices(kb, result)
    recommendation_cards(result)
    st.divider()
    left, right = st.columns([1.7, 1], gap="large")
    names = {t["id"]: t["name"] for t in kb["tracks"]}
    with left:
        chosen = st.selectbox("Escolha a trilha para detalhar o plano", [r["id"] for r in result["ranking"]],
                              format_func=names.get, key="chosen_track")
    with right:
        hours = st.slider("Ajustar horas de estudo por semana", 1, 40, value=st.session_state.profile["hours"], key="plan_hours")
        st.session_state.profile["hours"] = hours
    track = next(t for t in kb["tracks"] if t["id"] == chosen)
    selected = next(r for r in result["ranking"] if r["id"] == chosen)
    plan = build_plan(kb, chosen, st.session_state.knowledge, hours)
    st.subheader(track["name"])
    st.write(track["description"])
    plan_tab, comparison_tab, explanation_tab = st.tabs(["Meu plano de ação", "Comparar trilhas", "Por que este resultado?"])
    with plan_tab:
        plan_panel(kb, plan)
    with comparison_tab:
        comparison_panel(kb, result, chosen, hours)
    with explanation_tab:
        explanation_panel(kb, selected)
    st.divider()
    st.subheader("Leve seu plano com você")
    st.caption("O relatório reúne o roteiro e as justificativas. A avaliação JSON permite retomar e editar suas respostas depois.")
    left, middle, right = st.columns(3)
    left.download_button("Baixar relatório (.md)", report_markdown(kb, st.session_state.profile, result, plan),
                         "plano_carreira.md", "text/markdown; charset=utf-8", width="stretch")
    middle.download_button("Baixar avaliação (.json)", export_assessment(kb, st.session_state.profile,
        st.session_state.answers, st.session_state.knowledge, result=result, plan=plan),
        "avaliacao_carreira.json", "application/json", width="stretch")
    if right.button("Revisar minhas respostas", width="stretch"):
        move(0)


def run(kb):
    st.markdown("<style>" + (ROOT / "assets/style.css").read_text(encoding="utf-8") + "</style>", unsafe_allow_html=True)
    if "step" not in st.session_state:
        st.session_state.update(step=0, **empty_assessment())
    sidebar(kb)
    header()
    [profile_page, technical_page, goals_page, results_page][st.session_state.step](kb)
    st.markdown('<div class="app-footer">Rotas TI · Um mapa para explorar, aprender e construir. Feito para apoiar suas escolhas.</div>', unsafe_allow_html=True)
