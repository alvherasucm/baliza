"""08 Flotas. Demostrar que hay alguien dispuesto a pagar por esto y que el
modelo es consumible desde fuera. El coste por parte lo pone el cliente: asi no
inventamos ninguna cifra economica."""
import pandas as pd
import streamlit as st

from baliza import datos, estilo

estilo.cabecera(st.session_state["paginas"])

st.subheader("Flotas")
st.caption("Sube tus rutas habituales con cuántas veces por semana las haces. "
           "Riesgo por frecuencia, ordenado por exposición real.")

PLANTILLA = pd.DataFrame([
    {"provincia": "Madrid", "carretera": "A-4", "pk_inicio": 4.0, "pk_fin": 10.0,
     "imd_total": 65000.0, "imd_pesados": 6500.0, "tipo_via": "Autopista_autovia",
     "viajes_semana": 10},
    {"provincia": "Sevilla", "carretera": "A-4", "pk_inicio": 520.0, "pk_fin": 535.0,
     "imd_total": 42000.0, "imd_pesados": 7200.0, "tipo_via": "Autopista_autovia",
     "viajes_semana": 4},
    {"provincia": "Málaga", "carretera": "AP-7", "pk_inicio": 170.0, "pk_fin": 180.0,
     "imd_total": 58000.0, "imd_pesados": 5200.0, "tipo_via": "Autopista_autovia",
     "viajes_semana": 2},
])

izquierda, derecha = st.columns([3, 1])
with izquierda:
    subido = st.file_uploader("Tu tabla de rutas (CSV)", type=["csv"])
with derecha:
    st.download_button("Descargar plantilla", PLANTILLA.to_csv(index=False).encode("utf-8"),
                       "plantilla_rutas.csv", "text/csv", width="stretch")
    coste = st.number_input("Coste medio por parte (€)", 0, 100_000, 1_200, step=100,
                            help="Lo pones tú. Nosotros no inventamos costes.")

tabla = PLANTILLA.copy()
if subido is not None:
    try:
        tabla = pd.read_csv(subido, sep=None, engine="python")
    except Exception:
        st.error("No se ha podido leer el archivo. Usa CSV y conserva los encabezados "
                 "de la plantilla.")
        st.stop()

tabla = st.data_editor(tabla, num_rows="dynamic", width="stretch", hide_index=True)

if "viajes_semana" not in tabla.columns:
    st.error("Falta la columna viajes_semana. Descarga la plantilla y conserva sus encabezados.")
    st.stop()

validacion, prediccion, error = datos.predecir_tramos_usuario(tabla)
if error:
    st.error(error)
    st.stop()
for mensaje in validacion.errores:
    st.error(mensaje)
for mensaje in validacion.advertencias:
    st.warning(mensaje)
if prediccion is None:
    st.stop()

prediccion = prediccion.reset_index(drop=True)
prediccion["viajes_semana"] = pd.to_numeric(tabla["viajes_semana"], errors="coerce").fillna(0).values
prediccion["exposicion"] = prediccion.PROB_ACCIDENTE_TRAMO_ANIO * prediccion.viajes_semana
prediccion = prediccion.sort_values("exposicion", ascending=False)

st.divider()
a, b, c = st.columns(3)
a.metric("Rutas analizadas", len(prediccion))
a_vigilar = int(prediccion.banda.isin(["Alto", "Muy alto"]).sum())
b.metric("Entre el 20% peor de España", a_vigilar)
c.metric("Si evitas el peor tramo", f"{prediccion.exposicion.iloc[0] / prediccion.exposicion.sum():.0%}",
         help="Parte de tu exposición total que concentra esa sola ruta.")

vista = prediccion.copy()
vista["Ruta"] = (vista.carretera + ", km " + vista.pk_inicio_km.round().astype(int).astype(str)
                 + " a " + vista.pk_fin_km.round().astype(int).astype(str))
vista["Riesgo"] = vista.banda.astype(str)
vista["Peor que"] = vista.percentil
st.dataframe(
    vista[["Ruta", "provincia", "viajes_semana", "PROB_ACCIDENTE_TRAMO_ANIO", "Peor que",
           "Riesgo", "FUERA_RANGO_TRAIN"]].rename(columns={
               "provincia": "Provincia", "viajes_semana": "Viajes/semana",
               "PROB_ACCIDENTE_TRAMO_ANIO": "Riesgo del tramo",
               "FUERA_RANGO_TRAIN": "Fuera de rango"}),
    hide_index=True, width="stretch",
    column_config={
        "Riesgo del tramo": st.column_config.ProgressColumn(
            min_value=0, max_value=1, format="%.2f"),
        "Peor que": st.column_config.NumberColumn(
            format="%.0f%% de España",
            help="Percentil del tramo dentro de los 7.248 de 2024. Es el mismo "
                 "número que devuelve el campo percentil_2024 de la API.")})

if coste:
    st.caption(f"Con un coste medio de {coste:,} € por parte, cada punto de esta tabla que "
               f"consigas bajar se traduce en partes que no ocurren. La cifra en euros la "
               f"pones tú.".replace(",", "."))

st.divider()
st.subheader("Pedirlo desde tu sistema")
st.write("La misma puntuación que ves aquí se pide desde fuera, tramo a tramo, para que un "
         "motor de rutas la use al calcular un itinerario.")
st.code("""curl -X POST https://api.baliza.example/predict \\
  -H "Content-Type: application/json" \\
  -d '{
    "provincia": "Jaén",
    "carretera": "A-4",
    "pk_inicio_km": 245.5,
    "pk_fin_km": 250.7,
    "tipo_via": "Autopista_autovia",
    "imd_total": 31844,
    "proporcion_pesados": 0.14
  }'""", language="bash")

estilo.pendiente(
    "La URL es de ejemplo. Anna tiene una API en FastAPI funcionando en local; falta el "
    "código y hospedarla con https para poder enseñarla de verdad."
)
