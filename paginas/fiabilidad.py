"""06 Fiabilidad. Convertir la autocritica en credencial. Se cita de pasada en la
presentacion; existe para que el escepticismo tenga adonde ir."""
import streamlit as st

from baliza import datos, estilo

estilo.cabecera(st.session_state["paginas"])

st.subheader("Qué sabemos y qué no")

st.markdown("**De dónde salen los datos**")
st.write(
    "Microdatos de accidentes con víctimas de la DGT, 2016 a 2024, cruzados con los aforos "
    "del Mapa de Tráfico del Ministerio. Una fila es un tramo de carretera en un año, con su "
    "intensidad de tráfico y sus accidentes. 2020 queda fuera de todo el estudio."
)

st.markdown("**Cómo se validó**")
st.write(
    "Tapando 2024. Los modelos se entrenan con 2016 a 2022, se ajustan con 2023 y se miden "
    "contra un año que no han visto nunca. No hay ninguna cifra en esta web medida sobre los "
    "mismos datos con los que se entrenó."
)

st.divider()
st.markdown("**Qué hace cada modelo y cuánto se equivoca**")

metricas = datos.metricas_gravedad()
tabla = [
    {"Modelo": "Provincia", "Qué responde": "Cuántos accidentes esperar en una provincia",
     "Contra qué se compara": "Suponer que este año será como el anterior",
     "Resultado": "Error medio 18,3 frente a 21,6. Mejora un 15%"},
    {"Modelo": "Tramo", "Qué responde": "Si un tramo tendrá algún accidente este año",
     "Contra qué se compara": "Ordenar por intensidad de tráfico",
     "Resultado": "ROC-AUC 0,818 en 2024 frente a 0,800 del tráfico solo"},
    {"Modelo": "Gravedad", "Qué responde": "Si un accidente será grave o mortal",
     "Contra qué se compara": "Avisar siempre o no avisar nunca",
     "Resultado": f"Detecta el {metricas['recall_severo']:.0%} de los graves; "
                  f"{metricas['precision_severo']:.0%} de los avisos aciertan"},
]
st.dataframe(tabla, hide_index=True, width="stretch")

st.markdown("**El punto ciego**")
st.write(
    "El margen del modelo de tramos sobre ordenar por tráfico es estrecho: 0,818 contra 0,800. "
    "Lo decimos nosotros antes de que lo pregunte nadie. Lo que aporta el modelo por encima "
    "del tráfico es el tipo de vía, la longitud del tramo y la provincia, y ese margen se "
    "gana justo donde el tráfico engaña: carreteras convencionales poco transitadas."
)

st.divider()
st.markdown("**Lo que este sistema no puede hacer**")
st.markdown(
    "- No cubre calles de ciudad, carreteras autonómicas ni provinciales. Solo la Red de "
    "Carreteras del Estado, que es el 11% de los accidentes y el 24% de los fallecidos.\n"
    "- No cubre Baleares, Canarias ni las carreteras forales del País Vasco.\n"
    "- No predice que vayas a tener un accidente. Estima cuánto riesgo acumula un tramo al "
    "cabo de un año, y qué gravedad tendría un accidente si ocurriera.\n"
    "- No sustituye a la señalización ni a la DGT. No manda desviarse de ningún sitio.\n"
    "- No tiene coordenadas. Trabajamos con carretera y punto kilométrico, no con un mapa."
)

estilo.nota(
    "La honestidad no puede ser una página al final, por eso cada pantalla que da un número "
    "lleva al lado qué haría cualquiera a ojo y cuánto nos equivocamos. Esta página es el "
    "sitio donde está todo junto, no el sitio donde se confiesa."
)
