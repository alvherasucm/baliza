"""Mapa provincial. Coropletico de Anna con el indice de accidentes por
vehiculo-kilometro de 2024 (Espana = 100), convertido en herramienta: hover con
contexto, seleccion por clic y enlace al analisis de la provincia. Compara
provincias; no localiza tramos. Las provincias sin dato no se dibujan.

2D y no 3D: con altura, unas provincias tapan a otras y la perspectiva deforma
la comparacion, y la altura repetiria lo que ya dice el color."""
import altair as alt
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from baliza import componentes as ui
from baliza import datos, estilo

serie = datos.provincias()
p24 = serie[serie.ANYO == datos.ANIO].copy()
p24["cod_prov"] = p24.PROV.map(datos.CODIGO_PROVINCIA)
p24 = p24.dropna(subset=["cod_prov"]).reset_index(drop=True)
p24["Índice (España = 100)"] = p24.indice.round(1)
p24["Tasa por 100 M veh·km"] = p24.tasa.round(1)
p24["puesto"] = p24.indice.rank(ascending=False, method="min").astype(int)
p24["frente_espana"] = p24.indice.map(
    lambda v: f"{'+' if v >= 100 else '−'}{estilo.num(abs(v - 100))} % respecto a España")
p24["frente_corto"] = p24.indice.map(
    lambda v: f"{'+' if v >= 100 else '−'}{estilo.num(abs(v - 100))}\u00a0%")
p24["tasa_texto"] = p24.tasa.map(lambda v: estilo.num(v, 1))
por_codigo = dict(zip(p24.cod_prov, p24.PROV))
encima = int((p24.indice > 100).sum())

ui.cabecera_pagina(
    "Mapa provincial",
    f"{encima} provincias están por encima de la media de España",
    "Comparamos el riesgo observado con el esperado según el tráfico recorrido. Pulsa una "
    "provincia para ver su detalle.",
    meta=[("Año", str(datos.ANIO)), ("Provincias", str(len(p24))), ("Referencia", "España = 100")],
)

if "sel_provincia_mapa" not in st.session_state:
    st.session_state.sel_provincia_mapa = p24.loc[p24.indice.idxmax(), "PROV"]

izquierda, derecha = st.columns([2.1, 1], gap="medium")

with izquierda, ui.contenedor_grafico("mapa_provincial"):
    elegida = st.session_state.sel_provincia_mapa
    mapa = px.choropleth(
        p24, geojson=datos.geometria_provincias(), locations="cod_prov",
        featureidkey="properties.cod_prov", color="Índice (España = 100)",
        hover_name="PROV", custom_data=["frente_espana", "tasa_texto", "puesto"],
        color_continuous_scale=estilo.ESCALA_INDICE, color_continuous_midpoint=100,
    )
    mapa.update_traces(
        marker_line_color=estilo.SUPERFICIE, marker_line_width=0.8,
        hovertemplate=("<b>%{hovertext}</b><br>Índice de riesgo <b>%{z:.0f}</b><br>"
                       "%{customdata[0]}<br>Tasa por 100 M veh·km: %{customdata[1]}<br>"
                       "Puesto %{customdata[2]} de " + str(len(p24)) + "<extra></extra>"),
        selected=dict(marker=dict(opacity=1)), unselected=dict(marker=dict(opacity=1)))
    seleccion = p24[p24.PROV == elegida]
    mapa.add_trace(go.Choropleth(
        geojson=datos.geometria_provincias(), featureidkey="properties.cod_prov",
        locations=seleccion.cod_prov, z=[1] * len(seleccion),
        colorscale=[[0, "rgba(0,0,0,0)"], [1, "rgba(0,0,0,0)"]], showscale=False,
        marker_line_color=estilo.TINTA, marker_line_width=2.2, hoverinfo="skip"))
    mapa.update_geos(fitbounds="locations", visible=False, bgcolor="rgba(0,0,0,0)",
                     projection_type="conic conformal")
    estilo.tema_plotly(mapa)
    mapa.update_layout(
        height=600, dragmode=False, clickmode="event+select",
        coloraxis_colorbar=dict(title=dict(text="Índice · España = 100", side="top"),
                                orientation="h", thickness=8, len=0.45, x=0.5, xanchor="center",
                                y=-0.02, yanchor="top", outlinewidth=0,
                                tickfont=dict(color=estilo.TINTA_SUAVE)),
    )
    evento = st.plotly_chart(mapa, theme=None, key="mapa_provincial", on_select="rerun",
                             selection_mode="points",
                             config={"displayModeBar": False, "scrollZoom": False})

# Solo cuenta un clic nuevo: si despues se elige otra provincia en el desplegable,
# la seleccion que conserva el mapa no debe imponerse.
puntos = evento.selection.points if evento and evento.selection else []
codigo = puntos[0].get("location") if puntos else None
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
        st.caption("Evolución del índice · la línea discontinua es España")
        st.altair_chart(estilo.tema_altair((referencia + linea + puntos_linea)
                                           .properties(height=140)),
                        theme=None, use_container_width=True)
        if st.button(f"Ver análisis de {fila.PROV}  →", type="primary", width="stretch"):
            st.session_state["provincia_elegida"] = fila.PROV
            st.switch_page(st.session_state["paginas"]["provincia"])

ui.cabecera_seccion("Las cinco provincias con el índice más alto",
                    "Accidentes por kilómetro recorrido, con España = 100.")
lista, resumen = st.columns([2.1, 1], gap="medium")
with lista:
    ui.tabla(p24.nlargest(5, "indice"), [
        ui.columna("PROV", "Provincia", "fuerte"),
        ui.columna("indice", "Índice", "barra", maximo=float(p24.indice.max())),
        ui.columna("frente_corto", "Frente a España", "derecha"),
    ], ranking=True)
with resumen:
    ui.rejilla([ui.tarjeta_cifra(
        "Provincias por encima de España", str(encima), unidad=f"de {len(p24)}",
        extra=ui.cifras_compactas([(str(len(p24) - encima), "por debajo de 100"),
                                   (estilo.num(p24.indice.median()), "índice mediano")]))],
        plantilla="1fr")

st.write("")
with st.expander("Cómo calculamos este indicador"):
    st.markdown(
        "**Índice de riesgo.** Accidentes por vehículo-kilómetro de la provincia divididos por "
        "la media de España del mismo año, multiplicado por 100. Por encima de 100 hay más "
        "accidentes de los esperables para el tráfico recorrido.")
    st.markdown(
        "**Qué compara.** Solo provincias. Los tramos no se pueden dibujar porque los datos del "
        "proyecto no traen coordenadas de las carreteras. Geometría provincial: Code for "
        "America, licencia MIT.")
