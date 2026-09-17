"""Mapa provincial. Coropletico de Anna con el indice de accidentes por
vehiculo-kilometro de 2024 (Red del Estado = 100), convertido en herramienta: hover con
contexto, seleccion por clic y enlace al analisis de la provincia. Compara
provincias; no localiza tramos. Las provincias sin dato no se dibujan.

Lo dibuja Leaflet a traves de folium, con mapa base de OpenStreetMap: las
provincias se apoyan sobre carreteras y ciudades reales y el mapa se arrastra y
se acerca. El color, la escala y las cifras son los mismos que con Plotly.

2D y no 3D: con altura, unas provincias tapan a otras y la perspectiva deforma
la comparacion, y la altura repetiria lo que ya dice el color."""
import altair as alt
import branca.colormap as bcm
import folium
import streamlit as st
from streamlit_folium import st_folium

from baliza import componentes as ui
from baliza import datos, estilo

serie = datos.provincias()
p24 = serie[serie.ANYO == datos.ANIO].copy()
p24["cod_prov"] = p24.PROV.map(datos.CODIGO_PROVINCIA)
p24 = p24.dropna(subset=["cod_prov"]).reset_index(drop=True)
p24["indice_mapa"] = p24.indice.round(1)
p24["puesto"] = p24.indice.rank(ascending=False, method="min").astype(int)
p24["frente_espana"] = p24.indice.map(
    lambda v: f"{'+' if v >= 100 else '−'}{estilo.num(abs(v - 100))} % respecto a la red")
p24["frente_corto"] = p24.indice.map(
    lambda v: f"{'+' if v >= 100 else '−'}{estilo.num(abs(v - 100))} %")
p24["tasa_texto"] = p24.tasa.map(lambda v: estilo.num(v, 1))
p24["cobertura_texto"] = [
    f"<br>Poca cobertura: {estilo.pct(c)} del tráfico medido" if f else ""
    for c, f in zip(p24.COBERTURA_VEH_KM, p24.poca_cobertura)]
p24["nota"] = p24.poca_cobertura.map({True: "Poca cobertura", False: float("nan")})
por_codigo = dict(zip(p24.cod_prov, p24.PROV))
encima = int((p24.indice > 100).sum())

# La escala es la que tenia el coropletico de Plotly: los siete colores de
# ESCALA_INDICE repartidos sobre un rango simetrico alrededor de 100, que es lo que
# hacia color_continuous_midpoint. Con el mismo rango los 44 colores salen identicos.
DISTANCIA = max(p24.indice_mapa.max() - 100, 100 - p24.indice_mapa.min())
MINIMO, MAXIMO = 100 - DISTANCIA, 100 + DISTANCIA
ESCALA = bcm.LinearColormap(
    [color for _, color in estilo.ESCALA_INDICE],
    index=[MINIMO + parada * (MAXIMO - MINIMO) for parada, _ in estilo.ESCALA_INDICE],
    vmin=MINIMO, vmax=MAXIMO)
p24["color"] = p24.indice_mapa.map(ESCALA.rgb_hex_str)

# Leaflet vive en un iframe, asi que estilos.css no le llega: los colores de la
# marca entran aqui.
#
# El filtro oscurece OpenStreetMap, que se sirve en tonos claros. Se aplica solo al
# panel de teselas: las provincias van en el panel de vectores y conservan su color
# exacto. Se usa OSM y no CartoDB porque las teselas de CartoDB ya piden clave de API
# y la presentacion no puede depender de eso.
CSS_MAPA = f"""<style>
.leaflet-container {{ background: {estilo.SUPERFICIE}; font-family: {estilo.FUENTE}; }}
.leaflet-tile-pane {{
  filter: invert(1) hue-rotate(180deg) brightness(.92) contrast(1.05) saturate(.6); }}
.leaflet-tooltip.foliumtooltip::before {{ border: none; }}
.leaflet-bar a, .leaflet-bar a:hover {{
  background: {estilo.SUPERFICIE_SUAVE}; color: {estilo.TINTA_2};
  border-bottom-color: {estilo.BORDE}; }}
.leaflet-bar a:hover {{ background: {estilo.BORDE}; color: {estilo.TINTA}; }}
.leaflet-control-attribution {{
  background: rgba(14, 20, 25, .72) !important; color: {estilo.TINTA_SUAVE} !important;
  font-size: 10px; padding: 1px 6px; }}
.leaflet-control-attribution a {{ color: {estilo.PRIMARIO} !important; }}
</style>"""

ESTILO_FICHA = (f"background: {estilo.SUPERFICIE}; border: 1px solid {estilo.BORDE};"
                f"border-radius: 10px; box-shadow: 0 10px 28px rgba(0, 0, 0, .45);"
                f"color: {estilo.TINTA}; font-family: {estilo.FUENTE}; font-size: 13px;"
                "font-weight: 400; line-height: 1.5; padding: 10px 12px; white-space: nowrap;")


def ficha(fila) -> str:
    """Mismo contenido, en el mismo orden, que el hover que habia en Plotly."""
    return (f"<b>{fila.PROV}</b><br>Índice de riesgo <b>{fila.indice_mapa:.0f}</b>"
            f"<br>{fila.frente_espana}"
            f"<br>Tasa por 100 M veh·km: {fila.tasa_texto}"
            f"<br>Puesto {fila.puesto} de {len(p24)}{fila.cobertura_texto}")


GEOMETRIA = {rasgo["properties"]["cod_prov"]: rasgo["geometry"]
             for rasgo in datos.geometria_provincias()["features"]}
CAPA = {"type": "FeatureCollection", "features": [
    {"type": "Feature", "geometry": GEOMETRIA[fila.cod_prov],
     "properties": {"cod_prov": fila.cod_prov, "provincia": fila.PROV,
                    "color": fila.color, "ficha": ficha(fila)}}
    for fila in p24.itertuples() if fila.cod_prov in GEOMETRIA]}


def limites(capa: dict) -> list:
    """Encuadre sobre las provincias que se dibujan. Calcularlo sobre el fichero
    entero alejaria el mapa hasta Canarias, que no tiene dato en esta tabla."""
    def puntos(coordenadas):
        if isinstance(coordenadas[0], (int, float)):
            yield coordenadas
        else:
            for parte in coordenadas:
                yield from puntos(parte)

    longitudes, latitudes = [], []
    for rasgo in capa["features"]:
        for longitud, latitud in puntos(rasgo["geometry"]["coordinates"]):
            longitudes.append(longitud)
            latitudes.append(latitud)
    return [[min(latitudes), min(longitudes)], [max(latitudes), max(longitudes)]]


@st.cache_resource(show_spinner=False)
def mapa_base(_capa: dict, _encuadre: list, firma: int) -> folium.Map:
    """El mapa se construye una vez y se reutiliza. folium genera identificadores
    nuevos en cada llamada, y si el HTML cambia el componente rehace el mapa y
    pierde el zoom que tuviera el usuario. La provincia marcada va aparte."""
    mapa = folium.Map(tiles="OpenStreetMap", zoom_control=True, control_scale=False)
    mapa.get_root().header.add_child(folium.Element(CSS_MAPA))
    folium.GeoJson(
        _capa,
        style_function=lambda rasgo: {"fillColor": rasgo["properties"]["color"],
                                      "color": estilo.SUPERFICIE, "weight": 0.8,
                                      "opacity": 1, "fillOpacity": 1},
        highlight_function=lambda rasgo: {"color": estilo.TINTA_2, "weight": 1.8},
        tooltip=folium.GeoJsonTooltip(fields=["ficha"], labels=False, sticky=True,
                                      style=ESTILO_FICHA),
    ).add_to(mapa)
    mapa.fit_bounds(_encuadre, padding=(12, 12))
    return mapa


def marca(elegida: str) -> folium.FeatureGroup:
    """Contorno de la provincia seleccionada. Properties propias: folium escribe el
    estilo calculado dentro del rasgo y no debe tocar los de la capa de color."""
    grupo = folium.FeatureGroup(name="seleccion")
    rasgos = [{"type": "Feature", "geometry": rasgo["geometry"], "properties": {}}
              for rasgo in CAPA["features"] if rasgo["properties"]["provincia"] == elegida]
    folium.GeoJson(
        {"type": "FeatureCollection", "features": rasgos},
        style_function=lambda rasgo: {"fill": False, "fillOpacity": 0,
                                      "color": estilo.TINTA, "weight": 2.2, "opacity": 1},
        interactive=False,
    ).add_to(grupo)
    return grupo


def barra_escala() -> str:
    """Sustituye a la barra de color de Plotly. Fuera del iframe, con el CSS de la app."""
    tramos = ", ".join(f"{color} {parada * 100:.0f}%" for parada, color in estilo.ESCALA_INDICE)
    def sitio(valor):
        return (valor - MINIMO) / (MAXIMO - MINIMO) * 100
    extremos = (p24.indice_mapa.min(), p24.indice_mapa.max())
    return (
        '<div style="margin-top:14px">'
        f'<div style="height:8px;border-radius:4px;background:linear-gradient(90deg,{tramos})">'
        '</div>'
        f'<div style="position:relative;height:16px;margin-top:7px;font-size:11px;'
        f'color:{estilo.TINTA_SUAVE}">'
        f'<span style="position:absolute;left:{sitio(extremos[0]):.1f}%;'
        f'transform:translateX(-50%)">{estilo.num(extremos[0])}</span>'
        f'<span style="position:absolute;left:50%;transform:translateX(-50%);'
        f'color:{estilo.TINTA_2}">100 · media de la red</span>'
        f'<span style="position:absolute;right:0">{estilo.num(extremos[1])}</span>'
        '</div></div>')


ui.cabecera_pagina(
    "Mapa provincial",
    f"{encima} provincias están por encima de la media de la Red del Estado",
    "Comparamos el riesgo observado con el esperado según el tráfico recorrido. Mueve y "
    "acerca el mapa; pulsa una provincia para ver su detalle.",
    meta=[("Año", str(datos.ANIO)), ("Provincias", str(len(p24))), ("Referencia", "Red del Estado = 100")],
)

if "sel_provincia_mapa" not in st.session_state:
    st.session_state.sel_provincia_mapa = p24.loc[p24.indice.idxmax(), "PROV"]

izquierda, derecha = st.columns([2.1, 1], gap="medium")

with izquierda, ui.contenedor_grafico("mapa_provincial"):
    mapa = mapa_base(CAPA, limites(CAPA), hash(tuple(zip(p24.cod_prov, p24.color))))
    evento = st_folium(mapa, key="mapa_provincial", height=600, use_container_width=True,
                       feature_group_to_add=marca(st.session_state.sel_provincia_mapa),
                       returned_objects=["last_active_drawing"])
    st.html(barra_escala())

# Solo cuenta un clic nuevo: si despues se elige otra provincia en el desplegable,
# la seleccion que conserva el mapa no debe imponerse.
dibujo = (evento or {}).get("last_active_drawing") or {}
codigo = dibujo.get("properties", {}).get("cod_prov")
if codigo != st.session_state.get("ultimo_clic_mapa"):
    st.session_state["ultimo_clic_mapa"] = codigo
    if codigo in por_codigo:
        st.session_state.sel_provincia_mapa = por_codigo[codigo]
        st.rerun()

with derecha:
    with ui.panel("provincia_mapa"):
        opciones = sorted(p24.PROV)
        st.selectbox("Provincia seleccionada", opciones, key="sel_provincia_mapa")
        fila = p24[p24.PROV == st.session_state.sel_provincia_mapa].iloc[0]
        historia = serie[serie.PROV == fila.PROV].sort_values("ANYO")
        previo = historia[historia.ANYO < datos.ANIO]
        cambio = fila.indice - previo.iloc[-1].indice if len(previo) else None
        cifras = [(f"{fila.puesto}.º", f"de {len(p24)} provincias"),
                  (estilo.num(fila.tasa, 1), "por 100 M veh·km")]
        if cambio is not None:
            cifras.append((f"{'+' if cambio >= 0 else '−'}{estilo.num(abs(cambio))}",
                           f"puntos vs {int(previo.iloc[-1].ANYO)}"))
        ui.rejilla([ui.tarjeta_cifra(
            "Índice de riesgo", f"{fila.indice:.0f}", delta=fila.frente_espana,
            tono="malo" if fila.indice > 100 else "bueno",
            extra=ui.cifras_compactas(cifras))], plantilla="1fr")
        if fila.poca_cobertura:
            ui.panel_info(f"Solo entra el {estilo.pct(fila.COBERTURA_VEH_KM)} del tráfico medido "
                          "en su red. Tómalo como una orientación.", aviso=True,
                          etiqueta="Poca cobertura")

        evolucion = historia.assign(anio=historia.ANYO.astype(int).astype(str),
                                    nacional=100.0)
        base = alt.Chart(evolucion).encode(
            x=alt.X("anio:O", title=None, axis=alt.Axis(labelAngle=0, labelFontSize=10)))
        linea = base.mark_line(color=estilo.PRIMARIO, strokeWidth=2).encode(
            y=alt.Y("indice:Q", title=None, scale=alt.Scale(zero=False),
                    axis=alt.Axis(tickCount=4)))
        puntos_linea = base.mark_circle(color=estilo.PRIMARIO, size=30).encode(
            y="indice:Q", tooltip=[alt.Tooltip("anio:O", title="Año"),
                                   alt.Tooltip("indice:Q", title="Índice", format=".0f")])
        referencia = base.mark_line(color=estilo.TINTA_TENUE, strokeDash=[4, 4],
                                    strokeWidth=1).encode(y="nacional:Q")
        st.caption("Evolución del índice · la línea discontinua es la media de la red")
        st.altair_chart(estilo.tema_altair((referencia + linea + puntos_linea)
                                           .properties(height=140)),
                        theme=None, use_container_width=True)
        if st.button(f"Ver análisis de {fila.PROV}  →", type="primary", width="stretch"):
            st.session_state["provincia_elegida"] = fila.PROV
            st.switch_page(st.session_state["paginas"]["provincia"])

ui.cabecera_seccion("Las cinco provincias con el índice más alto",
                    "Accidentes por kilómetro recorrido, con la Red del Estado = 100.")
lista, resumen = st.columns([2.1, 1], gap="medium")
with lista:
    ui.tabla(p24.nlargest(5, "indice"), [
        ui.columna("PROV", "Provincia", "fuerte", secundario="nota"),
        ui.columna("indice", "Índice", "barra", maximo=float(p24.indice.max())),
        ui.columna("frente_corto", "Frente a la red", "derecha"),
    ], ranking=True)
with resumen:
    ui.rejilla([ui.tarjeta_cifra(
        "Provincias por encima de la media", str(encima), unidad=f"de {len(p24)}",
        extra=ui.cifras_compactas([(str(len(p24) - encima), "por debajo de 100"),
                                   (estilo.num(p24.indice.median()), "índice mediano")]))],
        plantilla="1fr")

st.write("")
with st.expander("Cómo calculamos este indicador"):
    st.markdown(
        "**Índice de riesgo.** Accidentes por vehículo-kilómetro de la provincia divididos por "
        "la media de la Red de Carreteras del Estado del mismo año, multiplicado por 100. Por encima de 100 hay más "
        "accidentes de los esperables para el tráfico recorrido.")
    st.markdown(
        "**Qué compara.** Solo provincias. Los tramos no se pueden dibujar porque los datos del "
        "proyecto no traen coordenadas de las carreteras. Geometría provincial: Code for "
        "America, licencia MIT.")
    st.markdown(
        "**Mapa base.** Cartografía de OpenStreetMap, oscurecida para esta web. El fondo se descarga al "
        "abrir la página: sin conexión las provincias se dibujan igual, pero sin carreteras ni "
        "ciudades debajo.")
    st.markdown(
        "**Poca cobertura.** Se avisa cuando entra en el cálculo menos del 60 % del tráfico "
        "medido en la red de la provincia. El resto son tramos donde no se pudieron situar "
        "todos los accidentes con seguridad.")
