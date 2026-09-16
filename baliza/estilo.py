"""Marca, escala de riesgo y piezas de interfaz que se repiten entre paginas."""
import streamlit as st

MARCA = "Baliza"
TAGLINE = "Sabes por dónde vas antes de salir"

# Amarillo a rojo. Nunca se usa el color sin la etiqueta de texto al lado.
COLOR_BANDA = {
    "Bajo": "#f2e8b0",
    "Medio": "#f6c453",
    "Alto": "#e8843c",
    "Muy alto": "#b5332a",
}
COLOR_TEXTO_BANDA = {
    "Bajo": "#5c5324",
    "Medio": "#5c4210",
    "Alto": "#ffffff",
    "Muy alto": "#ffffff",
}

CSS = """
<style>
  header[data-testid="stHeader"] {display: none;}
  .block-container {padding-top: 1.6rem; max-width: 1100px;}
  .baliza-marca {display:flex; align-items:baseline; gap:.7rem; margin-bottom:.2rem;}
  .baliza-marca h1 {font-size:1.6rem; margin:0; letter-spacing:-.02em;}
  .baliza-marca span {color:#6b7280; font-size:.95rem;}
  .baliza-nav {border-bottom:1px solid #e5e7eb; margin-bottom:1.4rem; padding-bottom:.4rem;}
  .baliza-nav button {border:none !important; background:transparent !important;
    color:#4b5563 !important; font-weight:500 !important; padding:.25rem .1rem !important;}
  .baliza-nav button:hover {color:#b5332a !important;}
  .baliza-etiqueta {display:inline-block; padding:.12rem .55rem; border-radius:999px;
    font-size:.78rem; font-weight:600;}
  .baliza-nota {background:#f9fafb; border-left:3px solid #d1d5db; padding:.7rem .9rem;
    color:#4b5563; font-size:.88rem; border-radius:0 4px 4px 0;}
  .baliza-pendiente {background:#fff7ed; border-left:3px solid #e8843c; padding:.7rem .9rem;
    color:#7c2d12; font-size:.88rem; border-radius:0 4px 4px 0;}
</style>
"""

PAGINAS = [
    ("inicio", "Inicio"),
    ("ruta", "Tu ruta"),
    ("mapa", "Mapa de riesgo"),
    ("provincia", "Tu provincia"),
    ("noche", "Salir de noche"),
    ("fiabilidad", "Fiabilidad"),
    ("como", "Cómo funciona"),
    ("flotas", "Flotas"),
]


def cabecera(paginas_streamlit: dict) -> None:
    """Marca y navegacion horizontal. La barra lateral de Streamlit queda oculta
    porque delata que esto es una demo de Streamlit y no un producto."""
    st.markdown(CSS, unsafe_allow_html=True)
    st.markdown(
        f'<div class="baliza-marca"><h1>{MARCA}</h1><span>{TAGLINE}</span></div>',
        unsafe_allow_html=True)
    st.markdown('<div class="baliza-nav">', unsafe_allow_html=True)
    columnas = st.columns(len(PAGINAS))
    for columna, (clave, etiqueta) in zip(columnas, PAGINAS):
        if columna.button(etiqueta, key=f"nav_{clave}", type="tertiary", width="stretch"):
            st.switch_page(paginas_streamlit[clave])
    st.markdown("</div>", unsafe_allow_html=True)


def etiqueta_banda(banda: str) -> str:
    fondo = COLOR_BANDA.get(banda, "#e5e7eb")
    texto = COLOR_TEXTO_BANDA.get(banda, "#374151")
    return (f'<span class="baliza-etiqueta" style="background:{fondo};color:{texto}">'
            f"{banda}</span>")


def _negritas(texto: str) -> str:
    """Los bloques van en HTML, asi que el ** de markdown no se interpreta solo."""
    partes = texto.split("**")
    return "".join(p if i % 2 == 0 else f"<b>{p}</b>" for i, p in enumerate(partes))


def nota(texto: str) -> None:
    st.markdown(f'<div class="baliza-nota">{_negritas(texto)}</div>', unsafe_allow_html=True)


def pendiente(texto: str) -> None:
    """Hueco conocido que espera una entrega del equipo. Visible a proposito:
    mejor que lo vea el equipo en la pantalla a que se olvide."""
    st.markdown(f'<div class="baliza-pendiente"><b>Pendiente:</b> {_negritas(texto)}</div>',
                unsafe_allow_html=True)


def contraste(a_ojo: str, modelo: str, error: str) -> None:
    """La honestidad no es una pagina al final. Cada cifra lleva al lado que
    haria cualquiera a ojo, que dice el modelo y cuanto se equivoca cada uno."""
    izquierda, centro, derecha = st.columns(3)
    izquierda.markdown(f"**A ojo**  \n{a_ojo}")
    centro.markdown(f"**El modelo**  \n{modelo}")
    derecha.markdown(f"**Nos equivocamos**  \n{error}")
