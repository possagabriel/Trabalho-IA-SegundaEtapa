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
    assert len(app.metric) == 4
    assert len(app.get("download_button")) == 2
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
