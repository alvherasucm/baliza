"""Baliza. Punto de entrada de la aplicacion.

Streamlit solo ejecuta el script de la pagina que se esta viendo, asi que los
tres modelos del equipo pueden convivir sin cargarse todos a la vez.
"""
import sys
from pathlib import Path

import streamlit as st

RAIZ = Path(__file__).resolve().parent
sys.path.insert(0, str(RAIZ))

st.set_page_config(page_title="Baliza", page_icon="•", layout="wide",
                   initial_sidebar_state="collapsed")

PAGINAS = {
    "inicio": st.Page("paginas/inicio.py", title="Inicio", default=True),
    "ruta": st.Page("paginas/ruta.py", title="Tu ruta"),
    "mapa": st.Page("paginas/mapa.py", title="Mapa de riesgo"),
    "provincia": st.Page("paginas/provincia.py", title="Tu provincia"),
    "noche": st.Page("paginas/noche.py", title="Salir de noche"),
    "fiabilidad": st.Page("paginas/fiabilidad.py", title="Fiabilidad"),
    "como": st.Page("paginas/como_funciona.py", title="Cómo funciona"),
    "flotas": st.Page("paginas/flotas.py", title="Flotas"),
}
st.session_state["paginas"] = PAGINAS

st.navigation(list(PAGINAS.values()), position="hidden").run()
