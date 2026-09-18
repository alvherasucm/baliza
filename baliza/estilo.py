"""Valores de diseno de Baliza que necesita Python: colores para los graficos,
formato de numeros en espanol, temas de Altair y Plotly y el mapa de paginas.
Los mismos valores viven como variables CSS en estilos.css."""
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
CSS = Path(__file__).resolve().parent / "estilos.css"
LOGO = RAIZ / "static" / "marca" / "baliza_logo.svg"
ICONO = RAIZ / "static" / "marca" / "baliza_icono.svg"
# Servida por Streamlit desde static/ (enableStaticServing en config.toml)
PORTADA_URL = "app/static/imagenes/accidente.jpg"
MAPA_CONCENTRACION = RAIZ / "static" / "mapa_concentracion_2024.png"

MARCA = "Baliza"
TAGLINE = "Sabes por dónde vas antes de salir"
FUENTE = "Inter, system-ui, -apple-system, 'Segoe UI', sans-serif"

# Tema oscuro. Contraste medido sobre la tarjeta (#172026): los textos pasan de
# 4,5 y las marcas de los graficos, de 3.
TINTA = "#F8F9FA"
TINTA_2 = "#CFD4D9"
TINTA_SUAVE = "#8A9499"
TINTA_TENUE = "#7C8990"

SUPERFICIE = "#0E1419"
SUPERFICIE_SUAVE = "#172026"
BORDE = "#2C3942"
REJILLA = "#1F2930"

# PRIMARIO para texto, lineas y barras; PRIMARIO_2 para rellenos con texto blanco
PRIMARIO = "#7DB3C8"
PRIMARIO_2 = "#3A7890"

# Sobre fondo oscuro, lo que mas resalta es el color mas saturado, no el mas
# oscuro. De verde apagado a rojo, para que «Muy alto» sea lo primero que se ve.
# El verde tira a azul a proposito: con daltonismo se separa de Medio y Alto
# mejor que el gris anterior. Siempre va con su etiqueta de texto.
COLOR_BANDA = {
    "Bajo": "#58A58C",
    "Medio": "#D9A55B",
    "Alto": "#E8743F",
    "Muy alto": "#F2483F",
}

# Indices con media nacional = 100: azul por debajo, rojo por encima y un gris
# apagado en el centro, para que resalten los extremos y no la media.
ESCALA_INDICE = [
    [0.00, "#6FA8C2"],
    [0.25, "#4F8BA3"],
    [0.45, "#3B5664"],
    [0.50, "#465058"],
    [0.55, "#6B4A3E"],
    [0.75, "#C8623F"],
    [1.00, "#F2483F"],
]

# (clave, etiqueta, fichero, icono, grupo). app.py construye la navegacion
# desde aqui; el orden es el recorrido del producto.
PAGINAS = [
    ("inicio", "Inicio", "paginas/inicio.py", ":material/home:", ""),
    ("ruta", "Tu ruta", "paginas/ruta.py", ":material/route:", "Explorar"),
    ("mapa", "Riesgo por tramo", "paginas/mapa.py", ":material/table_rows:", "Explorar"),
    ("mapa_provincial", "Mapa provincial", "paginas/mapa_provincial.py", ":material/map:",
     "Explorar"),
    ("provincia", "Tu provincia", "paginas/provincia.py", ":material/location_on:", "Explorar"),
    ("noche", "Salir de noche", "paginas/noche.py", ":material/dark_mode:", "Explorar"),
    ("fiabilidad", "Fiabilidad", "paginas/fiabilidad.py", ":material/verified:", "Confianza"),
    ("como", "Cómo funciona", "paginas/como_funciona.py", ":material/account_tree:",
     "Confianza"),
    ("flotas", "Flotas", "paginas/flotas.py", ":material/local_shipping:", "Empresas"),
]


def num(valor, decimales: int = 0) -> str:
    """1234567.8 -> '1.234.568'; con decimales, coma decimal."""
    texto = f"{valor:,.{decimales}f}"
    return texto.replace(",", " ").replace(".", ",").replace(" ", ".")


def pct(fraccion, decimales: int = 0) -> str:
    """0.939 -> '94 %'. El espacio antes del signo es la norma en espanol."""
    return f"{num(fraccion * 100, decimales)} %"


def tema_altair(grafico):
    """Rejilla y ejes discretos, misma tipografia que la pagina."""
    return (grafico
            .configure(font=FUENTE, background="transparent")
            .configure_view(stroke=None)
            .configure_axis(labelColor=TINTA_SUAVE, titleColor=TINTA_2,
                            gridColor=REJILLA, domainColor=BORDE, tickColor=BORDE,
                            labelFontSize=11, titleFontSize=12, titleFontWeight=500,
                            titlePadding=10, labelPadding=6)
            .configure_legend(labelColor=TINTA_2, titleColor=TINTA_2, labelFontSize=12,
                              titleFontSize=11, titleFontWeight=600, symbolType="square",
                              orient="top", direction="horizontal", titleOrient="left")
            .configure_axisX(grid=False))


def tema_plotly(figura):
    figura.update_layout(
        font=dict(family=FUENTE, color=TINTA_2, size=12),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        hoverlabel=dict(bgcolor=SUPERFICIE, bordercolor=BORDE,
                        font=dict(family=FUENTE, color=TINTA, size=13)),
        margin=dict(l=0, r=0, t=0, b=0),
        separators=",.",
    )
    return figura
