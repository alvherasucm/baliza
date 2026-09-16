"""02 Tu ruta. La pantalla estrella: convierte el estudio en algo que le afecta
al que escucha. El riesgo es aditivo a lo largo del itinerario y eso no lo
puede copiar ningun competidor que valore unidades sueltas."""
import numpy as np
import pandas as pd
import streamlit as st

from baliza import datos, estilo

estilo.cabecera(st.session_state["paginas"])

corredores = datos.corredores()
tramos = datos.tramos_puntuados()

st.subheader("Tu ruta")

izquierda, derecha = st.columns([1, 2])
with izquierda:
    via = st.selectbox("Carretera", list(corredores),
                       format_func=lambda v: f"{v} · {corredores[v]['nombre']}")
    hitos = corredores[via]["hitos"]
    ciudades = [h["ciudad"] for h in hitos]
    origen = st.selectbox("Salgo de", ciudades, index=0)
    destino = st.selectbox("Voy a", ciudades, index=len(ciudades) - 1)

pk = {h["ciudad"]: h["pk"] for h in hitos}
pk0, pk1 = sorted([pk[origen], pk[destino]])

ruta = tramos[tramos.carretera == via].copy()
if via in datos.FILTRO_PROVINCIA:
    ruta = ruta[ruta.provincia == datos.FILTRO_PROVINCIA[via]]
ruta = ruta[(ruta.pk_fin_km > pk0) & (ruta.pk_inicio_km < pk1)].sort_values("pk_inicio_km")

if origen == destino or ruta.empty:
    st.info("Elige un origen y un destino distintos.")
    st.stop()

ruta["km_en_ruta"] = (ruta.pk_fin_km.clip(upper=pk1) - ruta.pk_inicio_km.clip(lower=pk0))
valida = ruta[ruta.PROB_ACCIDENTE_TRAMO_ANIO.notna()]
media_pais = tramos.PROB_ACCIDENTE_TRAMO_ANIO.mean()
indice = (np.average(valida.PROB_ACCIDENTE_TRAMO_ANIO, weights=valida.km_en_ruta)
          / media_pais * 100)
km_cubiertos = ruta.km_en_ruta.sum()
sin_dato = max(0.0, (pk1 - pk0) - km_cubiertos)

with derecha:
    a, b, c = st.columns(3)
    a.metric("Índice de la ruta", f"{indice:.0f}",
             help="Media nacional = 100. Ponderado por los kilómetros que recorres.")
    b.metric("Tramos que atraviesas", f"{len(ruta)}")
    c.metric("Tramos en el 20% peor",
             f"{int(valida.banda.isin(['Alto', 'Muy alto']).sum())}",
             help="Las bandas son cuantiles nacionales: 'Muy alto' es el 5% peor del país.")
    st.caption("Provincias, en el orden en que las pasas: "
               + " → ".join(dict.fromkeys(ruta.provincia)))

st.divider()
st.subheader("Perfil del trayecto")
st.caption("Como el perfil de una etapa ciclista: no dónde está el riesgo en un mapa, "
           "sino cuándo te lo vas a encontrar.")

perfil = valida.set_index("pk_inicio_km")[["PROB_ACCIDENTE_TRAMO_ANIO"]]
perfil.columns = ["Riesgo del tramo"]
st.bar_chart(perfil, height=220, color="#b5332a")

st.markdown("**Los tres puntos a vigilar**")
peores = valida.nlargest(3, "PROB_ACCIDENTE_TRAMO_ANIO")
for _, fila in peores.iterrows():
    columna_a, columna_b = st.columns([3, 1])
    columna_a.markdown(
        f"**{fila.carretera}, km {fila.pk_inicio_km:.0f} a {fila.pk_fin_km:.0f}** "
        f"· {fila.provincia}  \n"
        f"<span style='color:#6b7280;font-size:.85rem'>"
        f"Entre el {100 - fila.percentil:.0f}% de tramos con más riesgo de España · "
        f"{fila.longitud_km:.1f} km · {fila.imd_total:,.0f} vehículos al día</span>"
        .replace(",", "."), unsafe_allow_html=True)
    columna_b.markdown(estilo.etiqueta_banda(str(fila.banda)), unsafe_allow_html=True)

if sin_dato > 1:
    estilo.nota(f"Hay {sin_dato:.0f} km del recorrido sin tramo medido. No son riesgo cero: "
                f"son kilómetros de los que no tenemos aforo en {datos.ANIO}.")

st.divider()
estilo.contraste(
    a_ojo="Cuanto más largo el viaje, peor. Es cierto y no distingue entre rutas.",
    modelo=f"Índice {indice:.0f} sobre 100, ponderado por los kilómetros que haces tú.",
    error="El modelo acierta 8 de cada 10 veces al separar tramos con y sin accidente "
          "(ROC-AUC 0,83 en 2024).",
)
