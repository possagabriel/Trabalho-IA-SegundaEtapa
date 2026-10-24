# Validação da versão revisada

Verificação realizada em 22/10/2026, com Python 3.14.8, Streamlit 1.66.1, Pandas 3.1.0, Altair 6.3.0 e pytest 9.1.1. Outras versões de Python permitidas pelos requisitos não foram executadas neste ambiente.

## Testes automatizados

`python -m pytest -q`: **71 testes passaram**, sem avisos na suíte final.

Cobertura funcional: inferência ponderada, penalidades, intervalos de resultados, empates, perfis desconhecidos, pré-requisitos, entregas práticas, validação de arquivos, compatibilidade com exportações antigas, navegação, seleção de trilha, comparação e ajuste de disponibilidade semanal.

## Navegador real

O script `scripts/check_browser.py` foi executado com Chromium, em janelas desktop de 1440 pixels e mobile de 390 × 844 pixels.

- Fluxo com perfil demonstrativo e seleção da comparação.
- Downloads reais do relatório Markdown e da avaliação JSON, com conferência do conteúdo.
- Reinício e restauração do JSON exportado, preservando o perfil e permitindo regenerar o plano.
- Navegação das três etapas no celular até o resultado.
- Ausência de exceções da aplicação, erros JavaScript e rolagem horizontal da página.
- Capturas revisadas em `docs/images`.

## Verificações adicionais

- `python -m pip check`: nenhuma dependência quebrada.
- `python -m compileall -q app.py career scripts`: compilação sem erro.
- `bash -n iniciar.sh`: sintaxe válida.
- `git diff --check`: sem erros de espaços em branco.

As verificações demonstram o funcionamento nos cenários descritos; não equivalem a calibração dos pesos, validação profissional das recomendações ou avaliação de acessibilidade completa. Os testes mobile usam emulação de viewport no Chromium, não um aparelho físico.
