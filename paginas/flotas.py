"""08 Flotas. Demostrar que hay alguien dispuesto a pagar por esto y que el
modelo es consumible desde fuera. El coste por parte lo pone el cliente: asi no
inventamos ninguna cifra economica. La prediccion y los porcentajes siguen las
decisiones de Anna; aqui solo cambia la presentacion."""
import pandas as pd
import streamlit as st

from baliza import componentes as ui
from baliza import datos, estilo

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

ui.cabecera_pagina(
    "Flotas",
    "Puntúa las rutas de tu flota",
    "Sube tus rutas habituales con cuántas veces por semana las haces. Baliza las ordena por "
    "exposición real: riesgo del tramo por frecuencia de paso.",
    meta=[("Formato", "CSV"), ("Modelo", f"tramos {datos.ANIO}"), ("Tamaño máximo", "5 MB")],
)

with ui.filtros("panel_carga"):
    c1, c2, c3 = st.columns([3, 1.2, 1.2], gap="medium", vertical_alignment="bottom")
    subido = c1.file_uploader("Tu tabla de rutas", type=["csv"])
    c2.download_button("Descargar plantilla", PLANTILLA.to_csv(index=False).encode("utf-8"),
                       "plantilla_rutas.csv", "text/csv", width="stretch",
                       icon=":material/download:")
    coste = c3.number_input("Coste medio por parte (€)", 0, 100_000, 1_200, step=100,
                            help="Lo pones tú. Nosotros no inventamos costes.")

tabla = PLANTILLA.copy()
if subido is not None:
    try:
        tabla = pd.read_csv(subido, sep=None, engine="python")
    except Exception:
        ui.panel_info("No se ha podido leer el archivo. Usa CSV y conserva los encabezados de "
                      "la plantilla.", aviso=True, etiqueta="Archivo no válido")
        st.stop()

ui.cabecera_seccion("Tus rutas",
                    "Puedes editar las filas aquí mismo o añadir nuevas antes de calcular." if
                    subido is None else f"{len(tabla)} filas cargadas de «{subido.name}».")
tabla = st.data_editor(tabla, num_rows="dynamic", width="stretch", hide_index=True)

if "viajes_semana" not in tabla.columns:
    ui.panel_info("Falta la columna viajes_semana. Descarga la plantilla y conserva sus "
                  "encabezados.", aviso=True, etiqueta="Falta una columna")
    st.stop()

validacion, prediccion, error = datos.predecir_tramos_usuario(tabla)
if error:
    ui.panel_info(error, aviso=True, etiqueta="No se ha podido calcular")
    st.stop()
for mensaje in validacion.errores:
    ui.panel_info(mensaje, aviso=True, etiqueta="Revisa esta fila")
for mensaje in validacion.advertencias:
    ui.panel_info(mensaje, etiqueta="Aviso")
if prediccion is None:
    st.stop()

prediccion = prediccion.reset_index(drop=True)
prediccion["viajes_semana"] = pd.to_numeric(tabla["viajes_semana"], errors="coerce").fillna(0).values
prediccion["exposicion"] = prediccion.PROB_ACCIDENTE_TRAMO_ANIO * prediccion.viajes_semana
prediccion = prediccion.sort_values("exposicion", ascending=False)

a_vigilar = int(prediccion.banda.isin(["Alto", "Muy alto"]).sum())
ui.cabecera_seccion("Resultado", "Ordenado por exposición: riesgo del tramo por viajes a la semana.")
ui.rejilla([
    ui.tarjeta_cifra("Rutas analizadas", str(len(prediccion))),
    ui.tarjeta_cifra("Entre el 20 % peor de España", str(a_vigilar),
                     unidad=f"de {len(prediccion)}", pie="con nivel alto o muy alto"),
    ui.tarjeta_cifra("Si evitas la ruta más expuesta",
                     estilo.pct(prediccion.exposicion.iloc[0] / prediccion.exposicion.sum()),
                     ayuda="Parte de tu exposición total que concentra esa sola ruta.",
                     pie="de tu exposición total desaparece"),
])

vista = prediccion.copy()
vista["Ruta"] = (vista.carretera + ", km " + vista.pk_inicio_km.round().astype(int).astype(str)
                 + " a " + vista.pk_fin_km.round().astype(int).astype(str))
vista["Riesgo"] = vista.banda.astype(str)
vista["peor_que"] = vista.percentil.map(lambda v: f"{v:.0f} % de España")
vista["fuera_rango"] = vista.FUERA_RANGO_TRAIN.map({True: "Sí", False: "No"})
st.write("")
ui.tabla(vista, [
    ui.columna("Ruta", "Ruta", "fuerte", secundario="provincia"),
    ui.columna("viajes_semana", "Viajes/semana", "num"),
    ui.columna("PROB_ACCIDENTE_TRAMO_ANIO", "Probabilidad anual", "barra", decimales=1, maximo=1),
    ui.columna("peor_que", "Peor que", "derecha"),
    ui.columna("Riesgo", "Nivel", "riesgo"),
    ui.columna("fuera_rango", "Fuera de rango", "suave"),
], ranking=True)
st.caption("Probabilidad anual: estimación de que el tramo registre al menos un accidente durante "
           "el año; no es el riesgo individual de un viaje. «Peor que» es el percentil del tramo "
           "dentro de los 7.248 de 2024, el mismo número que devuelve el campo percentil_2024 "
           "de la API.")

if coste:
    ui.panel_info(f"Con un coste medio de {estilo.num(coste)} € por parte, cada punto de esta "
                  "tabla que consigas bajar se traduce en partes que no ocurren. La cifra en "
                  "euros la pones tú.")

ui.cabecera_seccion("Pedirlo desde tu sistema",
                    "La misma puntuación se pide desde fuera, tramo a tramo, para que un motor de "
                    "rutas la use al calcular un itinerario.", eyebrow="API")
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

ui.en_desarrollo("La dirección de la API es de ejemplo: el servicio funciona en local y falta "
                 "publicarlo con https.")
