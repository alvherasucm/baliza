"""02 Tu ruta. La pantalla estrella: convierte el estudio en algo que le afecta
al que escucha. El resumen de la ruta pondera la probabilidad de cada tramo por
los kilometros que se recorren en el. El mapa lineal y los porcentajes son
decisiones de Anna; aqui solo cambia la presentacion."""
import altair as alt
import numpy as np
import streamlit as st

from baliza import componentes as ui
from baliza import datos, estilo

corredores = datos.corredores()
tramos = datos.tramos_puntuados()

ui.cabecera_pagina(
    "Tu ruta",
    "Cuánto riesgo acumula tu trayecto",
    "Elige una carretera, de dónde sales y adónde vas. Baliza resume el riesgo del recorrido "
    "y te enseña en qué tramos se acumula.",
    meta=[("Corredores", str(len(corredores))), ("Año", str(datos.ANIO)),
          ("Referencia", "media nacional = 100")],
)

with ui.filtros():
    c1, c2, c3 = st.columns([2, 1, 1], gap="medium")
    via = c1.selectbox("Carretera", list(corredores),
                       format_func=lambda v: f"{v} · {corredores[v]['nombre']}")
    hitos = corredores[via]["hitos"]
    ciudades = [h["ciudad"] for h in hitos]
    origen = c2.selectbox("Salgo de", ciudades, index=0)
    destino = c3.selectbox("Voy a", ciudades, index=len(ciudades) - 1)

pk = {h["ciudad"]: h["pk"] for h in hitos}
pk0, pk1 = sorted([pk[origen], pk[destino]])

ruta = tramos[tramos.carretera == via].copy()
if via in datos.FILTRO_PROVINCIA:
    ruta = ruta[ruta.provincia == datos.FILTRO_PROVINCIA[via]]
ruta = ruta[(ruta.pk_fin_km > pk0) & (ruta.pk_inicio_km < pk1)].sort_values("pk_inicio_km")

if origen == destino or ruta.empty:
    st.write("")
    ui.estado_vacio("Elige un origen y un destino distintos",
                    "El trayecto necesita dos ciudades diferentes del mismo corredor.")
    st.stop()

ruta["km_en_ruta"] = (ruta.pk_fin_km.clip(upper=pk1) - ruta.pk_inicio_km.clip(lower=pk0))
valida = ruta[ruta.PROB_ACCIDENTE_TRAMO_ANIO.notna()]
media_pais = tramos.PROB_ACCIDENTE_TRAMO_ANIO.mean()
indice = (np.average(valida.PROB_ACCIDENTE_TRAMO_ANIO, weights=valida.km_en_ruta)
          / media_pais * 100)
km_cubiertos = ruta.km_en_ruta.sum()
sin_dato = max(0.0, (pk1 - pk0) - km_cubiertos)
en_peor = int(valida.banda.isin(["Alto", "Muy alto"]).sum())

st.write("")
ui.rejilla([
    ui.tarjeta_cifra("Índice de la ruta", f"{indice:.0f}",
                     ayuda="Media nacional = 100. Cada tramo pesa según los kilómetros que "
                           "haces en él.",
                     delta=f"{'+' if indice >= 100 else '−'}{estilo.num(abs(indice - 100))}"
                           " % respecto a España",
                     tono="malo" if indice > 100 else "bueno"),
    ui.tarjeta_cifra("Tramos que atraviesas", str(len(ruta)),
                     pie=f"{estilo.num(pk1 - pk0)} km entre {origen} y {destino}"),
    ui.tarjeta_cifra("Tramos en el 20 % peor", str(en_peor), unidad=f"de {len(valida)}",
                     ayuda="Los niveles salen de comparar con toda España: «Muy alto» es el "
                           "5 % de tramos con más riesgo.",
                     pie="con nivel alto o muy alto"),
])
ui.recorrido(list(dict.fromkeys(ruta.provincia)), prefijo="Provincias, en el orden en que las pasas:")

ui.cabecera_seccion(
    "Mapa lineal del recorrido",
    "Cada bloque ocupa los kilómetros reales del tramo. La altura es la probabilidad anual "
    "estimada y el color, su nivel frente al resto de España.")

perfil = valida[["pk_inicio_km", "pk_fin_km", "provincia", "carretera",
                 "PROB_ACCIDENTE_TRAMO_ANIO", "percentil", "banda"]].copy()
perfil["Probabilidad anual (%)"] = perfil.PROB_ACCIDENTE_TRAMO_ANIO * 100
perfil["Nivel de riesgo"] = perfil.banda.astype(str)
perfil["prob_texto"] = perfil.PROB_ACCIDENTE_TRAMO_ANIO.map(lambda p: estilo.pct(p, 1))
perfil["pk_texto"] = (perfil.pk_inicio_km.map(lambda v: estilo.num(v, 1)) + " a "
                      + perfil.pk_fin_km.map(lambda v: estilo.num(v, 1)))
perfil["percentil_texto"] = perfil.percentil.map(lambda v: f"{v:.0f} de 100")

grafico = (
    alt.Chart(perfil)
    .mark_bar(stroke=estilo.SUPERFICIE, strokeWidth=1, cornerRadiusTopLeft=2,
              cornerRadiusTopRight=2)
    .encode(
        x=alt.X("pk_inicio_km:Q", title="Punto kilométrico",
                axis=alt.Axis(format="d", tickMinStep=1)),
        x2="pk_fin_km:Q",
        y=alt.Y("Probabilidad anual (%):Q", scale=alt.Scale(domain=[0, 100]),
                title="Probabilidad anual",
                axis=alt.Axis(values=[0, 25, 50, 75, 100], labelExpr="datum.value + ' %'")),
        y2=alt.datum(0),
        color=alt.Color(
            "Nivel de riesgo:N",
            scale=alt.Scale(domain=datos.BANDAS,
                            range=[estilo.COLOR_BANDA[nivel] for nivel in datos.BANDAS]),
            legend=alt.Legend(title="Nivel de riesgo"),
        ),
        tooltip=[
            alt.Tooltip("carretera:N", title="Carretera"),
            alt.Tooltip("provincia:N", title="Provincia"),
            alt.Tooltip("pk_texto:N", title="Kilómetros"),
            alt.Tooltip("prob_texto:N", title="Probabilidad anual"),
            alt.Tooltip("percentil_texto:N", title="Percentil nacional"),
            alt.Tooltip("Nivel de riesgo:N"),
        ],
    )
    .properties(height=260)
)
with ui.contenedor_grafico("ruta"):
    st.altair_chart(estilo.tema_altair(grafico), theme=None, use_container_width=True)
    st.caption("Un 93,9 % quiere decir que el modelo da un 93,9 % de probabilidad a que en ese "
               "tramo haya al menos un accidente durante el año. Habla del tramo con todo su "
               "tráfico, y no de la probabilidad de que tú tengas un accidente al pasar.")

if sin_dato > 1:
    ui.panel_info(f"Hay {estilo.num(sin_dato)} km del recorrido sin tramo medido, porque en "
                  f"{datos.ANIO} no hay aforo de esos kilómetros. Que no tengan nota no quiere "
                  "decir que no tengan riesgo.")

ui.cabecera_seccion("Los tres puntos a vigilar",
                    "Los tramos del recorrido con mayor probabilidad anual.")
peores = valida.nlargest(3, "PROB_ACCIDENTE_TRAMO_ANIO")
ui.lista_riesgo([
    (f"{fila.carretera}, km {fila.pk_inicio_km:.0f} a {fila.pk_fin_km:.0f} · {fila.provincia}",
     f"Entre el {100 - fila.percentil:.0f} % de tramos con más riesgo de España · "
     f"{estilo.num(fila.longitud_km, 1)} km · {estilo.num(fila.imd_total)} vehículos al día",
     fila.banda)
    for _, fila in peores.iterrows()
])

ui.conclusiones([
    ("A ojo: más kilómetros, más riesgo",
     "La regla funciona hasta que comparas dos rutas de la misma longitud. Ahí solo sirve "
     "mirar tramo a tramo."),
    (f"Con el modelo: índice {indice:.0f}",
     "Cada tramo cuenta según los kilómetros que haces en él. Una ruta con índice 100 estaría "
     "en la media de España."),
    ("Cuánto se equivoca",
     "Si se compara un tramo que tuvo accidentes en 2024 con otro que no, el modelo da más "
     "riesgo al primero en 8 de cada 10 parejas (ROC-AUC 0,83)."),
])

st.write("")
with st.expander("Cómo calculamos este indicador"):
    st.markdown(
        "**Probabilidad anual.** Estimación del modelo de que el tramo registre al menos un "
        "accidente durante el año. No es la probabilidad individual de un viaje.")
    st.markdown(
        "**Índice de la ruta.** Media de la probabilidad de cada tramo, ponderada por los "
        "kilómetros que recorres en él, dividida por la media nacional y multiplicada por 100.")
    st.markdown(
        "**Niveles.** Cuantiles nacionales de 2024: Bajo por debajo del percentil 50, Medio hasta "
        "el 80, Alto hasta el 95 y Muy alto el 5 % superior.")
