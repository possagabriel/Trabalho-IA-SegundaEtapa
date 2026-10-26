"""Teste opcional em navegador real. Requer requirements-browser.txt e servidor ativo."""

import argparse
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from playwright.sync_api import expect, sync_playwright


def check_no_overflow(page):
    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth"), "Página com rolagem horizontal"
    expect(page.get_by_test_id("stException")).to_have_count(0)


def desktop_capture(page, path):
    # Streamlit rola dentro do elemento main, por isso full_page sozinho
    # captura apenas a janela. Aumenta a janela para documentar todo o plano.
    height = page.get_by_test_id("stMain").evaluate("element => element.scrollHeight")
    page.set_viewport_size({"width": 1440, "height": min(2600, max(1050, height + 100))})
    page.get_by_test_id("stMain").evaluate("element => element.scrollTop = 0")
    expect(page.locator(".brand")).to_be_visible()
    if path.name == "inicio-desktop.png":
        expect(page.locator(".hero")).to_be_visible()
        expect(page.get_by_role("textbox", name="Como você quer ser chamado(a)?")).to_be_visible()
    expect(page.locator(".app-footer")).to_be_visible()
    page.screenshot(path=str(path), full_page=True)
    page.set_viewport_size({"width": 1440, "height": 1050})


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:8501")
    parser.add_argument("--screenshots", default="docs/images")
    args = parser.parse_args()
    screenshots = Path(args.screenshots)
    screenshots.mkdir(parents=True, exist_ok=True)
    errors = []
    with sync_playwright() as playwright, TemporaryDirectory() as temporary:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 1050}, device_scale_factor=1)
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto(args.url)
        expect(page.get_by_text("Vamos começar por você", exact=True)).to_be_visible()
        desktop_capture(page, screenshots / "inicio-desktop.png")
        check_no_overflow(page)
        page.get_by_text("Quer conhecer antes de preencher?", exact=True).click()
        page.get_by_role("button", name="Explorar demonstração", exact=True).click()
        expect(page.get_by_role("heading", name="Seu próximo passo começa aqui")).to_be_visible()
        expect(page.get_by_text("Seu primeiro passo", exact=True)).to_be_visible()
        desktop_capture(page, screenshots / "plano-desktop.png")
        check_no_overflow(page)
        page.get_by_role("tab", name="Comparar trilhas", exact=True).click()
        expect(page.get_by_text("Compare possibilidades, além do primeiro lugar", exact=True)).to_be_visible()
        expect(page.locator("canvas").first).to_be_visible()
        desktop_capture(page, screenshots / "comparacao-desktop.png")
        page.get_by_test_id("stSelectbox").filter(has_text="Meta de senioridade para os estudos").get_by_role("combobox").click()
        page.get_by_role("option", name="Sênior", exact=True).click()
        expect(page.get_by_text("Meta de estudo: Sênior.", exact=False)).to_be_attached()
        with page.expect_download() as downloaded:
            page.get_by_role("button", name="Baixar avaliação (.json)", exact=True).click()
        export_path = Path(temporary) / "avaliacao.json"
        downloaded.value.save_as(export_path)
        data = json.loads(export_path.read_text())
        assert len(data["result"]["ranking"]) == 10
        assert data["plan"]["roadmap"][0]["evidence"]
        assert data["profile"]["target_level"] == data["plan"]["target_level"] == "senior"
        assert all(row["target"] == 4 for row in data["plan"]["requirements"])
        with page.expect_download() as downloaded:
            page.get_by_role("button", name="Baixar relatório (.md)", exact=True).click()
        report_path = Path(temporary) / "relatorio.md"
        downloaded.value.save_as(report_path)
        assert "Evidência de aprendizagem" in report_path.read_text()
        assert "Meta de estudo: Sênior" in report_path.read_text()
        page.get_by_role("button", name="Nova avaliação", exact=True).click()
        expect(page.get_by_text("Vamos começar por você", exact=True)).to_be_visible()
        page.get_by_text("Salvar ou retomar avaliação", exact=True).click()
        page.get_by_test_id("stFileUploader").locator('input[type="file"]').set_input_files(export_path)
        page.get_by_role("button", name="Restaurar avaliação", exact=True).click()
        expect(page.get_by_role("textbox", name="Como você quer ser chamado(a)?")).to_have_value("Demonstração")
        page.get_by_role("button", name="Continuar para afinidades", exact=True).click()
        page.get_by_role("tab", name="2. O que já sei fazer", exact=True).click()
        expect(page.get_by_text("Fundamentos e desenvolvimento · 7 competências", exact=True)).to_be_visible()
        page.get_by_role("button", name="Continuar para objetivos", exact=True).click()
        page.get_by_role("button", name="Gerar meu plano", exact=True).click()
        expect(page.get_by_role("heading", name="Seu próximo passo começa aqui")).to_be_visible()
        expect(page.get_by_text("Meta de estudo: Sênior.", exact=False)).to_be_visible()
        check_no_overflow(page)
        mobile = browser.new_page(viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True)
        mobile.on("pageerror", lambda error: errors.append(str(error)))
        mobile.goto(args.url)
        expect(mobile.get_by_text("Vamos começar por você", exact=True)).to_be_visible()
        expect(mobile.locator(".hero")).to_be_visible()
        expect(mobile.get_by_role("textbox", name="Como você quer ser chamado(a)?")).to_be_visible()
        expect(mobile.get_by_role("slider")).to_be_visible()
        expect(mobile.locator(".overview").first).to_be_hidden()
        mobile.screenshot(path=str(screenshots / "inicio-mobile.png"), full_page=True)
        check_no_overflow(mobile)
        mobile.get_by_role("button", name="Continuar para afinidades", exact=True).click()
        expect(mobile.get_by_role("heading", name="O que desperta seu interesse?")).to_be_visible()
        check_no_overflow(mobile)
        mobile.get_by_role("button", name="Continuar para objetivos", exact=True).click()
        mobile.get_by_role("button", name="Gerar meu plano", exact=True).click()
        expect(mobile.get_by_role("heading", name="Seu próximo passo começa aqui")).to_be_visible()
        expect(mobile.get_by_test_id("stMetricValue").first).to_be_visible()
        check_no_overflow(mobile)
        mobile.screenshot(path=str(screenshots / "plano-mobile.png"), full_page=True)
        browser.close()
    assert not errors, errors
    print("Navegador: desktop, celular, comparação, senioridade, downloads e restauração verificados.")


if __name__ == "__main__":
    main()
