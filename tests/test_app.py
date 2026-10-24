from pathlib import Path

from streamlit.testing.v1 import AppTest

APP = Path(__file__).resolve().parents[1] / "app.py"


def click(app, label):
    next(button for button in app.button if button.label == label).click().run()
    assert not app.exception


def reach_results(app):
    click(app, "Continuar para afinidades")
    for select in app.selectbox:
        select.set_value(4)
    app.select_slider(key="skill_git").set_value(2)
    click(app, "Continuar para objetivos")
    for select in app.selectbox:
        select.set_value(4)
    click(app, "Gerar meu plano")


def test_complete_wizard_alternate_track_and_review():
    app = AppTest.from_file(str(APP), default_timeout=20).run()
    assert not app.exception
    app.text_input[0].set_value("Pessoa de teste")
    app.slider[0].set_value(10)
    reach_results(app)
    assert app.session_state["step"] == 3
    assert app.session_state["knowledge"]["git"] == 2
    assert {m.label for m in app.metric} >= {"Competências iniciais", "Lacunas a trabalhar", "Estudo estimado"}
    assert len(app.get("download_button")) == 3
    app.selectbox(key="chosen_track").set_value("mobile").run()
    assert not app.exception
    assert any("Aplicativo offline" in item.value for item in app.subheader)
    click(app, "Revisar minhas respostas")
    assert app.text_input[0].value == "Pessoa de teste"
    assert app.slider[0].value == 10
    click(app, "Continuar para afinidades")
    assert app.selectbox(key="question_logica").value == 4
    assert app.select_slider(key="skill_git").value == 2


def test_unknown_profile_and_reset():
    app = AppTest.from_file(str(APP), default_timeout=20).run()
    click(app, "Continuar para afinidades")
    click(app, "Continuar para objetivos")
    click(app, "Gerar meu plano")
    assert any("Informação insuficiente" in warning.value for warning in app.warning)
    click(app, "Nova avaliação")
    assert app.session_state["step"] == 0
    assert app.session_state["answers"] == {}


def test_back_button_saves_current_answers():
    app = AppTest.from_file(str(APP), default_timeout=20).run()
    click(app, "Continuar para afinidades")
    app.selectbox(key="question_logica").set_value(5)
    click(app, "Voltar ao perfil")
    click(app, "Continuar para afinidades")
    assert app.selectbox(key="question_logica").value == 5


def test_demo_comparison_and_live_schedule():
    app = AppTest.from_file(str(APP), default_timeout=20).run()
    click(app, "Explorar demonstração")
    assert app.session_state["step"] == 3
    old_weeks = next(m.value for m in app.metric if m.label == "Estudo estimado")
    app.slider(key="plan_hours").set_value(20).run()
    assert not app.exception
    assert app.session_state["profile"]["hours"] == 20
    assert next(m.value for m in app.metric if m.label == "Estudo estimado") != old_weeks
    app.multiselect(key="comparison_tracks").set_value(["mobile", "qa"]).run()
    assert not app.exception
    comparison = next(frame.value for frame in app.dataframe if "Horas de estudo" in frame.value.columns)
    assert comparison["Trilha"].tolist() == ["Mobile", "QA"]
    app.multiselect(key="comparison_tracks").set_value([]).run()
    assert any("Selecione até três" in info.value for info in app.info)


def test_card_shortcut_and_new_result_selects_current_best():
    app = AppTest.from_file(str(APP), default_timeout=20).run()
    click(app, "Explorar demonstração")
    buttons = [button for button in app.button if button.label == "Explorar esta trilha"]
    buttons[1].click().run()
    assert not app.exception
    assert app.selectbox(key="chosen_track").value == buttons[1].key.removeprefix("explore_")
    app.selectbox(key="chosen_track").set_value("mobile").run()
    click(app, "Revisar minhas respostas")
    reach_results(app)
    assert app.selectbox(key="chosen_track").value == "backend"


def test_complete_knowledge_has_no_study_steps():
    app = AppTest.from_file(str(APP), default_timeout=20).run()
    click(app, "Continuar para afinidades")
    for widget in app.select_slider:
        widget.set_value(4)
    click(app, "Continuar para objetivos")
    click(app, "Gerar meu plano")
    assert next(m.value for m in app.metric if m.label == "Lacunas a trabalhar") == "0"
    assert next(m.value for m in app.metric if m.label == "Estudo estimado") == "0 semanas"
