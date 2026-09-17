"""04 Tu provincia. Diagnosticar y comparar, no adivinar. La prediccion pura es
lo mas atacable que tenemos, asi que va abajo y acompanada del reconocimiento
de cuanto mejora sobre no hacer nada. Los datos y cifras son de Miki; aqui solo
cambia la presentacion."""
import altair as alt
import streamlit as st

from baliza import componentes as ui
from baliza import datos, estilo

prov = datos.provincias()
ultimo = prov[prov.ANYO == prov.ANYO.max()].copy()
ultimo["puesto"] = ultimo.indice.rank(ascending=False).astype(int)

ui.cabecera_pagina(
    "Tu provincia",
    "El riesgo de tu provincia frente a España",
    "Compara el riesgo de una provincia con la media del país y mira cómo ha evolucionado.",
    meta=[("Año", str(int(prov.ANYO.max()))), ("Referencia", "España = 100"),
          ("Serie", "2016-2024 sin 2020")],
)

# Solo provincias con dato en el ultimo anio: sin el, no hay diagnostico que ensenar
opciones = sorted(ultimo.PROV.unique())
pedida = st.session_state.pop("provincia_elegida", None)
if pedida in opciones:
    st.session_state["sel_provincia"] = pedida
elif st.session_state.get("sel_provincia") not in opciones:
    st.session_state["sel_provincia"] = "Madrid"

with ui.filtros():
    elegida = st.columns([1, 2])[0].selectbox("Provincia", opciones, key="sel_provincia")

serie = prov[prov.PROV == elegida].sort_values("ANYO")
fila = ultimo[ultimo.PROV == elegida].iloc[0]
anterior = serie[serie.ANYO < serie.ANYO.max()]
variacion = fila.indice - anterior.iloc[-1].indice if len(anterior) else 0

st.write("")
ui.rejilla([
    ui.tarjeta_cifra("Índice de riesgo", f"{fila.indice:.0f}",
                     ayuda="Media nacional = 100. Por encima de 100, más accidentes por "
                           "kilómetro recorrido que la media del país.",
                     delta=f"{'+' if variacion >= 0 else '−'}{estilo.num(abs(variacion))} "
                           "respecto al año anterior",
                     tono="malo" if variacion > 0 else "bueno"),
    ui.tarjeta_cifra("Puesto en España", f"{fila.puesto}.º", unidad=f"de {len(ultimo)}",
                     pie="de más a menos riesgo relativo"),
    ui.tarjeta_cifra("Año", f"{int(fila.ANYO)}", pie="último año con datos"),
])
mas_accidentes = ultimo.loc[ultimo.N_ACC.idxmax()]
ui.panel_info(
    f"El índice cuenta accidentes por vehículo-kilómetro, así que separa cuánto tráfico hay de "
    f"cómo de arriesgado es cada kilómetro. {mas_accidentes.PROV} es la provincia con más "
    f"accidentes de {int(mas_accidentes.ANYO)}, pero por kilómetro recorrido queda en el puesto "
    f"{mas_accidentes.puesto} de {len(ultimo)}, con índice {mas_accidentes.indice:.0f}.")

izquierda, derecha = st.columns([3, 2], gap="medium")

with izquierda:
    ui.cabecera_seccion("Cómo ha evolucionado",
                        "Falta 2020: el año del confinamiento distorsiona cualquier serie y se "
                        "excluye en todo el estudio.")
    evolucion = serie.assign(anio=serie.ANYO.astype(int).astype(str), nacional=100.0)
    base = alt.Chart(evolucion).encode(
        x=alt.X("anio:O", title=None, axis=alt.Axis(labelAngle=0)))
    linea = base.mark_line(color=estilo.PRIMARIO, strokeWidth=2.2).encode(
        y=alt.Y("indice:Q", title="Índice", scale=alt.Scale(zero=True)))
    puntos = base.mark_circle(color=estilo.PRIMARIO, size=40).encode(
        y="indice:Q", tooltip=[alt.Tooltip("anio:O", title="Año"),
                               alt.Tooltip("indice:Q", title=elegida, format=".0f")])
    referencia = base.mark_line(color=estilo.TINTA_TENUE, strokeDash=[4, 4],
                                strokeWidth=1.2).encode(y="nacional:Q")
    with ui.contenedor_grafico("evolucion"):
        st.caption(f"{elegida} · la línea discontinua es la media nacional (100)")
        st.altair_chart(estilo.tema_altair((referencia + linea + puntos).properties(height=260)),
                        theme=None, use_container_width=True)

with derecha:
    ui.cabecera_seccion("Quién mejora y quién empeora",
                        f"Cambio del índice entre {int(prov.ANYO.max()) - 1} y "
                        f"{int(prov.ANYO.max())}.")
    cambio = (prov.pivot_table(index="PROV", columns="ANYO", values="indice")
              .loc[:, [prov.ANYO.max() - 1, prov.ANYO.max()]].dropna())
    cambio["cambio"] = cambio.iloc[:, 1] - cambio.iloc[:, 0]
    cambio = cambio.reset_index()
    cambio["cambio_texto"] = cambio.cambio.map(
        lambda v: f"{'+' if v >= 0 else '−'}{estilo.num(abs(v), 1)}")
    for titulo, tabla in [("Mejoran", cambio.nsmallest(5, "cambio")),
                          ("Empeoran", cambio.nlargest(5, "cambio"))]:
        ui.tabla(tabla, [ui.columna("PROV", titulo, "fuerte"),
                         ui.columna("cambio_texto", "Puntos", "derecha")])
        st.write("")

ui.cabecera_seccion("Previsión frente a lo que pasó", eyebrow="Modelo provincial")
if serie.pred_jerarquico.notna().any():
    ultima_pred = serie.dropna(subset=["pred_jerarquico"]).iloc[-1]
    error = abs(ultima_pred.pred_jerarquico - ultima_pred.N_ACC) / ultima_pred.N_ACC
    ui.panel_info(
        f"Para {int(ultima_pred.ANYO)} el modelo esperaba "
        f"**{estilo.num(ultima_pred.pred_jerarquico)}** accidentes en {elegida} y hubo "
        f"**{estilo.num(ultima_pred.N_ACC)}**. Se equivocó un **{estilo.pct(error)}**.")

ui.conclusiones([
    ("A ojo: repetir el año anterior",
     "Suponer que cada provincia tendrá los mismos accidentes que el año pasado ya funciona "
     "bastante bien: se equivoca en 21,6 accidentes de media."),
    ("Con el modelo: 18,3 de error",
     "El modelo tiene en cuenta el tráfico y agrupa las provincias por región. Con eso baja "
     "el error medio a 18,3 accidentes."),
    ("Cuánto mejora: un 15 %",
     "Es una mejora modesta. En una provincia, lo que pasó el año anterior explica casi todo "
     "lo que pasa al siguiente."),
])

st.write("")
ui.en_desarrollo(
    "Previsión de 2025 y comparación completa de las cuatro variantes del modelo, pendientes de "
    "la entrega de provincias.")
