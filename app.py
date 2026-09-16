"""Baliza. Punto de entrada: tema, estilos, marca y navegacion comunes.

Streamlit solo ejecuta el script de la pagina que se esta viendo, asi que los
tres modelos del equipo pueden convivir sin cargarse todos a la vez.
"""
import sys
from pathlib import Path

import streamlit as st

RAIZ = Path(__file__).resolve().parent
sys.path.insert(0, str(RAIZ))

from baliza import componentes, estilo  # noqa: E402

st.set_page_config(page_title="Baliza · Riesgo vial", page_icon=str(estilo.ICONO),
                   layout="wide", initial_sidebar_state="collapsed")
st.logo(str(estilo.LOGO), size="large")
componentes.aplicar_estilos()

PAGINAS = {}
SECCIONES = {}
for clave, etiqueta, fichero, icono, grupo in estilo.PAGINAS:
    pagina = st.Page(fichero, title=etiqueta, icon=icono, url_path=Path(fichero).stem,
                     default=clave == "inicio")
    PAGINAS[clave] = pagina
    SECCIONES.setdefault(grupo, []).append(pagina)
st.session_state["paginas"] = PAGINAS

actual = st.navigation(list(PAGINAS.values()), position="top")
st.session_state["pagina_actual"] = next(
    clave for clave, pagina in PAGINAS.items() if pagina.url_path == actual.url_path)
actual.run()
