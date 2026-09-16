"""03 Mapa de riesgo. Ranking con selector de criterio: cada criterio responde a
un cliente distinto, asi que la objecion se contesta con un desplegable en vez
de con una explicacion."""
import streamlit as st

from baliza import datos, estilo

estilo.cabecera(st.session_state["paginas"])

tramos = datos.tramos_puntuados()

CRITERIOS = {
    "Más accidentes": ("N_ACC", "Accidentes en el tramo durante 2024. Ordena dónde invertir."),
    "Más accidentes por kilómetro": (
        "acc_por_km", "Accidentes divididos por la longitud. Ordena puntos negros."),
    "Más riesgo para el que pasa": (
        "TASA_100M", "Accidentes por cada 100 millones de vehículos-kilómetro. "
                     "Descuenta el tráfico, así que una carretera vacía puede salir arriba."),
}

st.subheader("Los peores tramos de España")

izquierda, centro, derecha = st.columns([2, 2, 1])
criterio = izquierda.selectbox("Ordenar por", list(CRITERIOS))
tipos = sorted(tramos.TIPO_VIA.dropna().unique())
tipo = centro.selectbox("Tipo de vía", ["Todos"] + tipos)
cuantos = derecha.number_input("Cuántos", 10, 100, 20, step=10)

columna, explicacion = CRITERIOS[criterio]
st.caption(explicacion)

datos_filtrados = tramos if tipo == "Todos" else tramos[tramos.TIPO_VIA == tipo]
ranking = datos_filtrados.dropna(subset=[columna]).nlargest(int(cuantos), columna).copy()
ranking["Tramo"] = (ranking.carretera + ", km " + ranking.pk_inicio_km.round().astype(int).astype(str)
                    + " a " + ranking.pk_fin_km.round().astype(int).astype(str))
ranking["Riesgo"] = ranking.banda.astype(str)

st.dataframe(
    ranking[["Tramo", "provincia", "TIPO_VIA", "N_ACC", "acc_por_km", "TASA_100M",
             "PROB_ACCIDENTE_TRAMO_ANIO", "Riesgo"]].rename(columns={
                 "provincia": "Provincia", "TIPO_VIA": "Tipo de vía",
                 "N_ACC": "Accidentes", "acc_por_km": "Por km",
                 "TASA_100M": "Por 100 M veh·km", "PROB_ACCIDENTE_TRAMO_ANIO": "Modelo"}),
    hide_index=True, width="stretch",
    column_config={
        "Por km": st.column_config.NumberColumn(format="%.2f"),
        "Por 100 M veh·km": st.column_config.NumberColumn(format="%.1f"),
        "Modelo": st.column_config.ProgressColumn(min_value=0, max_value=1, format="%.2f"),
    })

estilo.nota(
    "Cambia el criterio y cambia la lista entera. Por accidentes por kilómetro salen "
    "rondas urbanas; por riesgo para el que pasa salen nacionales largas y poco "
    "transitadas. No es que uno esté bien y otro mal: responden a clientes distintos. "
    "El que reparte presupuesto y el que va a conducir no buscan lo mismo."
)

st.divider()
estilo.contraste(
    a_ojo="Donde hay más tráfico hay más accidentes. Es verdad y por eso el ranking de "
          "accidentes se parece al de intensidad de tráfico.",
    modelo="Separar volumen de riesgo: el tercer criterio descuenta el tráfico y deja "
           "solo lo que aporta el tramo.",
    error="Sin exposición, un tramo de 200 metros con dos accidentes puede colarse arriba. "
          "Por eso el criterio por defecto no es ese.",
)
