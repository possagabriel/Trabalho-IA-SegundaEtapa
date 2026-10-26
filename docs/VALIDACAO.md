# Validação da versão revisada

## Revisão dos requisitos em 26/10/2026

Base 1.2.0, esquema 2. A suíte `python -m pytest -q` passou com **99 testes**. Também passaram a compilação de `app.py`, `career` e `scripts`, a verificação de dependências (`pip check`) e `git diff --check`.

Além dos cenários anteriores, foram verificados:

- Metas Júnior, Pleno e Sênior nas dez trilhas, com lacunas e esforço crescentes para o mesmo conhecimento atual.
- Regras de senioridade carregadas do JSON, validação de entradas inválidas e inclusão da meta no relatório.
- Preservação da meta ao exportar/importar e ao revisar o wizard; arquivos antigos continuam assumindo Júnior.
- Ranking de afinidades preservado quando somente a meta de estudo muda.
- Respeito a pré-requisitos indiretos, inclusive quando uma competência intermediária já está dominada.

Os níveis representam referências didáticas no catálogo atual, sem certificar senioridade profissional.

O teste `scripts/check_browser.py` também passou com Chromium: fluxo desktop e celular, comparação, seleção de Sênior, downloads Markdown/JSON e restauração preservando essa meta. Não houve exceções da aplicação, erros JavaScript nem rolagem horizontal nos cenários testados. As capturas desta execução foram gravadas em `/tmp/rotas-ti-validation`; a captura desktop do plano e a captura mobile foram inspecionadas visualmente. O teste de celular usa viewport emulado, não aparelho físico.

## Registro anterior — 22/10/2026

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
