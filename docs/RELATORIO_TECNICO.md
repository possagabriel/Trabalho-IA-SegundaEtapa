# Relatório técnico — Rotas TI

**Disciplina:** Inteligência Artificial  
**Curso:** Ciência da Computação — UNIPAC Barbacena  
**Professor:** Felipe Roncalli de Paula Carneiro  
**Enunciado:** Trabalho Etapa 2, de 22/10/2026

## 1. Objetivo e escopo

Construir um sistema especialista baseado em regras com tratamento de incerteza e pontuação ponderada. O sistema avalia dez trilhas de TI e produz uma orientação explicável, acompanhada de lacunas de competência e ações concretas de desenvolvimento.

As trilhas são Back-end, Front-end/UX, Cientista de Dados, Engenheiro de Dados, Cibersegurança, DevOps/SRE, Cloud Architecture, Mobile, QA e Product Management. O alvo padrão é a referência Júnior; também há metas de estudo Pleno e Sênior. Não se infere senioridade profissional a partir de afinidade.

## 2. Arquitetura

```mermaid
flowchart LR
    JSON[Base externa JSON] --> V[Validação]
    V --> M[Motor de inferência]
    UI[Wizard Streamlit] --> A[Afinidades e objetivos]
    A --> M
    M --> R[Ranking e explicações]
    UI --> C[Competências e horas semanais]
    R --> T[Escolha da trilha]
    T --> P[Análise de lacunas e roteiro]
    C --> P
    JSON --> P
    P --> O[Resultados e exportação]
    R --> O
```

O motor usa somente a biblioteca padrão do Python e pode ser executado independentemente. Streamlit controla a interação; Pandas organiza tabelas e o gráfico. A base JSON contém todo o conhecimento de domínio. Não foi necessário usar Experta porque o enunciado também permite um motor próprio de soma ponderada.

A interface foi separada em `career/ui.py`, os gráficos em `career/charts.py` e a importação/exportação de avaliações em `career/assessment.py`. `app.py` apenas configura a página, carrega a base e inicia a interface. Altair fornece gráficos com escala fixa de 0 a 100 e comparação de afinidade e cobertura de competências.

## 3. Fase 1 — Engenharia do conhecimento

Foram definidas 20 perguntas: 14 afinidades técnicas e seis preferências de atuação. As respostas conhecidas usam uma escala Likert de 1 a 5. A opção desconhecida é representada por `null`, distinguindo ausência de informação de baixa afinidade.

O catálogo tem 33 competências, compartilhadas entre trilhas, evitando perguntar repetidamente o nível do usuário em Git, SQL ou programação. Cada competência tem descrição, pré-requisitos, estimativa de horas por nível e fonte de estudo. Cada trilha reúne pesos, penalidades, metas, certificações e projeto.

Desde a base 1.1.0, as competências também recebem uma categoria de apresentação e uma entrega prática (`evidence`), usada como evidência de aprendizagem no roteiro e no relatório. Esses campos permanecem opcionais. A base atual exige esquema 2 e a configuração `seniority_levels`; arquivos de avaliação exportados anteriormente continuam compatíveis. Perfis fictícios de demonstração ficam em `data/perfis_exemplo.json`.

Os pesos de 1 a 5 representam relevância relativa dentro da trilha: 5 para atividades centrais; 3–4 para competências de forte apoio; 1–2 para aspectos complementares. Perguntas ausentes do mapa de pesos contribuem zero. A [matriz de pesos](MATRIZ_PESOS.md) permite revisar a modelagem.

Exemplos: matemática e análise de dados têm peso 5 em Ciência de Dados; design e empatia têm peso 5 em Front-end/UX; infraestrutura e automação têm peso 5 em DevOps/SRE. Cada trilha também possui dois fatores críticos que, com resposta baixa, ativam penalidades.

Esta é uma base heurística construída para o exercício, sem entrevistas com especialistas nem calibração empírica. Isso é declarado nos metadados e nos resultados. Recomendações e fontes oficiais não são evidência de validade dos pesos adotados.

### Estrutura do JSON

| Campo | Conteúdo |
|---|---|
| `schema_version` | Versão estrutural aceita pelo carregador |
| `metadata` | Identificação, versão, data e limitações do modelo |
| `scoring` | Escala, neutralidade, cobertura mínima e limiares |
| `knowledge_levels` | Interpretação dos níveis de competência |
| `seniority_levels` | Nome, piso de competência, descrição e orientação de portfólio por meta de senioridade |
| `questions` | Identificador, rótulo, pergunta e grupo |
| `skills` | Competências, pré-requisitos, esforço e materiais |
| `tracks[].weights` | Relação entre perguntas e pesos |
| `tracks[].penalties` | Condições SE–ENTÃO, pontos e justificativas |
| `tracks[].requirements` | Metas e importância de cada competência |
| `tracks[].certifications` | Certificações opcionais e momento sugerido |
| `tracks[].portfolio` | Projeto, descrição e entregáveis |

O carregador valida referências, duplicidades, soma de pesos, faixas numéricas e ciclos de pré-requisitos. Novas regras e trilhas podem ser adicionadas sem alterar as funções de inferência, desde que respeitem a estrutura.

## 4. Fase 2 — Inferência ponderada e incerteza

Para resposta conhecida `rᵢ`, define-se `nᵢ = (rᵢ − 1) / 4`. Para resposta desconhecida, `nᵢ = 0,5`.

```text
Bₜ = 100 × Σ(wₜᵢ × nᵢ) / Σ(wₜᵢ)
Cₜ = max(0, min(100, Bₜ − Σ(penalidades ativadas)))
```

As penalidades são regras declarativas com uma ou mais condições ligadas por E lógico. O motor suporta `lte` (menor ou igual) e `gte` (maior ou igual). Na base inicial, cada trilha tem duas regras de 12 pontos para afinidade até 2 em fatores críticos. Uma condição desconhecida impede a ativação da regra.

Exemplo: em Back-end, a soma dos pesos é 26. Se todas as respostas forem 3, a base será 50%. Se programação for alterada para 1, seu peso 5 passa a contribuir zero: a base será `100 × 21 × 0,5 / 26 = 40,3846%`. A penalidade de 12 pontos resulta em `28,3846%`. Esse cálculo é verificado por teste independente.

A explicação mostra a resposta, o peso e a contribuição de cada pergunta, além das penalidades ativadas. Mantém-se precisão interna; arredondamento é feito somente para exibição.

### Informação incompleta e empates

A cobertura por trilha é a proporção do peso associada a respostas conhecidas. Também se calcula a proporção de perguntas globalmente respondidas. A recomendação é provisória se a cobertura global ou a da primeira trilha ficar abaixo de 50%.

Se todas as respostas forem desconhecidas, todas as trilhas recebem 50%, com cobertura zero e aviso de informação insuficiente. Se todas forem 3, todas recebem 50% com cobertura total e aviso de empate. Esses dois resultados têm o mesmo valor numérico, mas interpretações diferentes.

Trilhas até três pontos da primeira são consideradas próximas. O identificador é o critério determinístico para empates exatos, sem afirmar superioridade substantiva. Se a maior aderência ficar abaixo de 40%, há indicação de baixa compatibilidade geral.

Os valores não são probabilidades. O tratamento de incerteza adotado é gradual e heurístico; não se apresenta como inferência bayesiana ou fator de certeza estatisticamente calibrado.

### Faixa de resultados com respostas desconhecidas

Além da pontuação neutra, cada trilha tem um limite inferior e superior conservadores. O inferior usa somente as contribuições conhecidas e desconta todas as penalidades não descartadas pelas respostas conhecidas. O superior soma o máximo possível das contribuições pendentes e desconta somente penalidades confirmadas. Ambos ficam limitados a 0–100.

Esses limites contêm as pontuações possíveis, mas não precisam ser atingíveis simultaneamente quando regras interagem. Por isso são chamados de faixa conservadora, nunca de intervalo de confiança. Com todas as respostas conhecidas, ambos coincidem com o resultado. Testes enumeram combinações de respostas pendentes, inclusive regras `gte`, para verificar a inclusão dos resultados na faixa.

## 5. Fase 3 — Lacunas e roteiro

O nível atual vai de 0 a 4. Para a referência Júnior, a base inicial exige nível 2: realizar tarefas básicas com orientação. A lacuna de uma competência é `max(0, meta − nível atual)`.

Na base 1.2.0 (esquema 2), a meta efetiva é `max(meta da competência na trilha, piso da senioridade selecionada)`. Os pisos externos são 1 para Júnior (preserva as metas individuais, atualmente 2), 3 para Pleno e 4 para Sênior. Esses níveis representam estudo com orientação, autonomia e aprofundamento no mesmo catálogo; não modelam todos os requisitos profissionais desses cargos. A escolha altera o plano e a orientação do portfólio, mas não altera a afinidade. A interface, a comparação e os relatórios usam a mesma meta. Avaliações antigas sem esse campo continuam válidas e usam Júnior.

A cobertura de competências é:

```text
100 × Σ(min(nível atual, meta) × importância) / Σ(meta × importância)
```

Conhecimento excedente em uma habilidade não compensa a falta de outra. A ausência de lacunas produz “Metas iniciais atendidas” para Júnior ou “Metas de estudo atendidas” para as demais referências, sem atribuir senioridade profissional.

O roteiro usa uma ordenação topológica: primeiro seleciona lacunas cujos pré-requisitos diretos ou indiretos não estão pendentes; entre essas, escolhe a maior prioridade, calculada por `lacuna × importância`. Empates usam o identificador da competência. Competências já dominadas não geram etapas de estudo. Uma competência intermediária já dominada não elimina a necessidade de estudar os fundamentos pendentes antes de suas dependentes.

Cada etapa demanda `lacuna × horas por nível`. O calendário divide o esforço acumulado pela disponibilidade semanal e permite que duas etapas compartilhem a mesma semana. A soma corresponde apenas aos estudos faltantes; projeto e exames têm esforço adicional não estimado.

Cada trilha tem um projeto com entregáveis. A lista de competências faltantes torna explícito o foco de prática individual. Certificações são alternativas opcionais, algumas posteriores ao nível inicial. Por exemplo, CKA requer estudo posterior de Kubernetes; PSPO I trata de Product Ownership e não cobre toda a atuação em Product Management.

Cada etapa do roteiro inclui uma entrega verificável, como uma API CRUD com testes ou uma ingestão idempotente. O primeiro passo aparece em destaque. Conhecimento avançado declarado sem pré-requisitos suficientes produz um aviso de revisão da autoavaliação, sem alterar automaticamente os níveis informados.

## 6. Fase 4 — Interface

O wizard mantém perfil, respostas e competências em `st.session_state`, separados das chaves transitórias dos widgets. Cada formulário grava seus dados tanto ao avançar quanto ao voltar. Isso permite revisar o perfil sem perder as avaliações anteriores.

Os resultados incluem Top 3, gráfico horizontal, tabela comparativa, seleção de qualquer trilha, decomposição do cálculo, lacunas, roteiro, projeto e certificados opcionais. Há exportações Markdown e JSON. O JSON contém as entradas e saídas necessárias para auditar a avaliação.

A versão revisada organiza interesses e competências em abas e distribui as 33 competências em cinco grupos. Os resultados têm abas para plano, comparação e explicação. É possível comparar até três trilhas e alterar as horas semanais com recálculo imediato do cronograma. Os gráficos usam escala 0–100 e tabelas equivalentes para consulta dos dados.

A barra lateral permite salvar progresso confirmado e restaurar avaliações JSON de até 1 MB. A importação valida formato, nome, momento profissional, horas e todas as respostas antes de substituir a sessão. Resultados importados são ignorados e recalculados; diferenças de versão da base são informadas. Exportações legadas sem versão de formato permanecem aceitas.

Não há persistência em banco nem criação automática de repositórios GitHub. O GitHub aparece como destino sugerido para o portfólio. O uso da aplicação não depende de serviços pagos.

## 7. Fase 5 — Verificação

A suíte cobre os seguintes cenários:

| Cenário | Verificação |
|---|---|
| Cálculo conhecido | Soma ponderada e penalidade conferidas numericamente |
| Respostas mínimas e máximas | Pontuações contidas em 0–100 |
| Perfil neutro | Empate estável entre as dez trilhas |
| Perfil desconhecido | Neutralidade, cobertura zero e resultado provisório |
| Perfil misto dados/web | Ambas as áreas com alta aderência e alternativas próximas |
| Perfil de infraestrutura | DevOps/SRE na primeira posição |
| Competências parciais | Redução coerente das lacunas e das horas |
| Competências completas | Roteiro vazio e nenhuma senioridade inventada |
| Disponibilidade diferente | Calendário muda sem alterar conteúdo de estudo |
| Pré-requisitos | Ordem respeitada para todas as trilhas |
| Entradas inválidas | Rejeição de valores fora da escala, NaN, infinito e identificadores inexistentes |
| Base inválida | Detecção de ciclos, pesos nulos e referências quebradas |
| Mudança externa nas regras | Alteração no JSON modifica o resultado do motor |
| Wizard | Fluxo completo, navegação de retorno, persistência e reinício |
| Exploração | Troca de trilha e disponibilização das exportações |

Execute `python -m pytest -q` para obter o resultado no ambiente utilizado. Os testes da interface usam AppTest; não simulam cliques de download em um navegador real.

A suíte ampliada inclui importações inválidas, arquivos legados, resultados forjados, números extremos, intervalos de pontuação, pré-requisitos inconsistentes, comparação e recálculo de calendário. O script opcional `scripts/check_browser.py` complementa AppTest com Chromium real, fluxos de desktop e celular, verificação de rolagem horizontal, downloads de arquivos e restauração. Capturas ficam em `docs/images`.

## 8. Demonstração sugerida

1. Execute `python exemplo.py` para mostrar uma avaliação reproduzível de infraestrutura.
2. Abra o Streamlit e preencha um perfil com preferências altas para dados e desenvolvimento web.
3. Mostre que o ranking permite resultados próximos e explique uma contribuição ponderada.
4. Selecione uma trilha alternativa e compare as lacunas.
5. Aumente uma competência já estudada e observe a redução do roteiro.
6. Baixe o relatório, execute os testes e mostre que os pesos são externos.

O [relatório demonstrativo](EXEMPLO_RESULTADO.md) foi produzido pelo próprio motor, sem edição dos resultados.

## 9. Limitações e evolução

A autoavaliação pode subestimar ou superestimar conhecimentos. As metas de entrada variam entre empresas, e algumas trilhas, como arquitetura de nuvem, frequentemente requerem trajetória prévia. As horas de estudo são estimativas didáticas. A soma de pesos não modela todas as interações entre preferências, e a neutralidade imputada pode aproximar perfis incompletos.

Uma evolução seria revisar a base com profissionais de cada área, realizar avaliação prática de competências, testar sensibilidade dos pesos e comparar recomendações com avaliações independentes. Tais validações não foram realizadas neste trabalho.

As referências oficiais e os links consultados estão no [README](../README.md) e na base de conhecimento.
