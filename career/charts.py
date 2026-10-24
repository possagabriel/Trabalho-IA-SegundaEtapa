"""Gráficos com escalas explícitas e dados acessíveis em tabelas na interface."""

import altair as alt
import pandas as pd


def compatibility_chart(ranking, chosen):
    frame = pd.DataFrame([{"Trilha": r["name"], "Compatibilidade": r["score"],
                           "Mínimo": r["score_min"], "Máximo": r["score_max"],
                           "Cobertura": r["coverage"], "Escolhida": r["id"] == chosen}
                          for r in ranking])
    order = [r["name"] for r in ranking]
    base = alt.Chart(frame).encode(
        y=alt.Y("Trilha:N", sort=order, title=None, axis=alt.Axis(labelLimit=190)),
        x=alt.X("Compatibilidade:Q", scale=alt.Scale(domain=[0, 100]), title="Compatibilidade (%)"),
        tooltip=[alt.Tooltip("Trilha:N"), alt.Tooltip("Compatibilidade:Q", format=".1f"),
                 alt.Tooltip("Cobertura:Q", format=".0%", title="Perguntas respondidas"),
                 alt.Tooltip("Mínimo:Q", format=".1f"), alt.Tooltip("Máximo:Q", format=".1f")])
    bars = base.mark_bar(cornerRadiusEnd=5, height=18).encode(
        color=alt.condition(alt.datum.Escolhida, alt.value("#176c58"), alt.value("#b3c9c3")))
    intervals = base.mark_rule(color="#506f66", strokeWidth=2).encode(x="Mínimo:Q", x2="Máximo:Q")
    # Rótulos percentuais são apresentados também na tabela e nos tooltips.
    return (bars + intervals).properties(height=350).configure_view(strokeWidth=0)


def comparison_chart(rows):
    frame = pd.DataFrame([{"Trilha": r["name"], "Medida": measure, "Percentual": value}
                          for r in rows for measure, value in
                          [("Afinidade", r["score"]), ("Competências iniciais", r["readiness"])]])
    return alt.Chart(frame).mark_bar(cornerRadiusEnd=4).encode(
        x=alt.X("Percentual:Q", scale=alt.Scale(domain=[0, 100]), title="Percentual (%)"),
        y=alt.Y("Trilha:N", title=None, sort=[r["name"] for r in rows]),
        yOffset="Medida:N",
        color=alt.Color("Medida:N", scale=alt.Scale(domain=["Afinidade", "Competências iniciais"],
                                                   range=["#176c58", "#8573b9"]), legend=alt.Legend(title=None, orient="bottom")),
        tooltip=["Trilha:N", "Medida:N", alt.Tooltip("Percentual:Q", format=".1f")]
    ).properties(height=max(130, len(rows) * 76)).configure_view(strokeWidth=0)
