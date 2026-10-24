"""Execute com: python -m streamlit run app.py."""

import streamlit as st

from career.engine import load_knowledge
from career.ui import run

st.set_page_config(page_title="Rotas TI · Seu próximo passo", page_icon="🧭", layout="wide")

try:
    knowledge_base = load_knowledge()
except ValueError as error:
    st.error(str(error))
    st.stop()

run(knowledge_base)
