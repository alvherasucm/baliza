"""Valores de diseno de Baliza que necesita Python: colores para los graficos,
formato de numeros en espanol, temas de Altair y Plotly y el mapa de paginas.
Los mismos valores viven como variables CSS en estilos.css."""
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
CSS = Path(__file__).resolve().parent / "estilos.css"
LOGO = RAIZ / "static" / "marca" / "baliza_logo.svg"
ICONO = RAIZ / "static" / "marca" / "baliza_icono.svg"

MARCA = "Baliza"
TAGLINE = "Sabes por dónde vas antes de salir"
FUENTE = "Inter, system-ui, -apple-system, 'Segoe UI', sans-serif"

TINTA = "#17191C"
TINTA_2 = "#4F5358"
TINTA_SUAVE = "#6E7277"
TINTA_TENUE = "#9A9DA1"
SUPERFICIE = "#FFFFFF"
SUPERFICIE_SUAVE = "#F8F7F4"
BORDE = "#E3E1DB"
REJILLA = "#EEECE7"
PRIMARIO = "#0F3D4C"
PRIMARIO_2 = "#2E6275"

# Una sola gama, de terracota a granate: el orden se lee en la luminosidad y el
# granate queda para el 5% mas extremo. Validada como escala ordinal.
COLOR_BANDA = {
    "Bajo": "#D9A88C",
    "Medio": "#C27A5C",
    "Alto": "#9D4A34",
    "Muy alto": "#6B2118",
}

# Indices con media nacional = 100: petroleo por debajo, terracota por encima y
# gris neutro en el centro.
ESCALA_INDICE = [
    [0.00, "#0F3D4C"],
    [0.25, "#4A7384"],
    [0.45, "#BACBD1"],
    [0.50, "#ECEAE4"],
    [0.55, "#E6C7B4"],
    [0.75, "#C27A5C"],
    [1.00, "#6B2118"],
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
    return texto.replace(",", " ").replace(".", ",").replace(" ", ".")


def pct(fraccion, decimales: int = 0) -> str:
    """0.939 -> '94 %'. El espacio antes del signo es la norma en espanol."""
    return f"{num(fraccion * 100, decimales)} %"


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
