"""03 Riesgo por tramo. Ranking de Anna con selector de criterio: cada criterio
responde a un cliente distinto, asi que la objecion se contesta con un
desplegable en vez de con una explicacion. Los criterios, niveles y el calculo
del ranking son decisiones de Anna; aqui solo cambia la presentacion."""
import streamlit as st

from baliza import componentes as ui
from baliza import datos, estilo

tramos = datos.tramos_puntuados()

CRITERIOS = {
    "Mayor riesgo estimado": (
        "PROB_ACCIDENTE_TRAMO_ANIO",
        "Ordena por la estimación del modelo. El percentil indica la posición del tramo "
        "respecto a toda la red analizada en 2024."),
    "Más accidentes": ("N_ACC", "Accidentes en el tramo durante 2024. Ordena dónde invertir."),
    "Más accidentes por kilómetro": (
        "acc_por_km", "Accidentes divididos por la longitud. Ordena puntos negros."),
    "Más riesgo para el que pasa": (
        "TASA_100M", "Accidentes por cada 100 millones de vehículos-kilómetro. "
                     "Descuenta el tráfico, así que una carretera vacía puede salir arriba."),
}

NIVELES = {
    "Alto y muy alto": ["Alto", "Muy alto"],
    "Todos los niveles": datos.BANDAS,
    "Muy alto": ["Muy alto"],
    "Alto": ["Alto"],
    "Medio": ["Medio"],
    "Bajo": ["Bajo"],
}

ui.cabecera_pagina(
    "Riesgo por tramo",
    "Dónde se concentra el riesgo de la red",
    "La vista inicial muestra el 20 % de tramos con mayor riesgo estimado. Cambia el "
    "criterio, el tipo de vía o el nivel para explorar el resto.",
    meta=[("Año", str(datos.ANIO)), ("Red", "Carreteras del Estado"),
          ("Tramos", estilo.num(len(tramos))), ("Fuente", "DGT · Mapa de Tráfico")],
)

resumen = st.container()

with ui.filtros():
    c1, c2, c3, c4 = st.columns([3, 2, 2, 2], gap="medium")
    criterio = c1.selectbox("Ordenar por", list(CRITERIOS))
    tipos = sorted(tramos.tipo_via_presentacion.dropna().unique())
    tipo = c2.selectbox("Tipo de vía", ["Todos"] + tipos)
    nivel = c3.selectbox("Nivel de riesgo", list(NIVELES))
    cuantos = c4.slider("Tramos en la lista", 10, 100, 20, step=10)
    columna, explicacion = CRITERIOS[criterio]
    st.caption(explicacion)

datos_filtrados = tramos[tramos.banda.astype(str).isin(NIVELES[nivel])]
if tipo != "Todos":
    datos_filtrados = datos_filtrados[datos_filtrados.tipo_via_presentacion == tipo]
ranking = datos_filtrados.dropna(subset=[columna]).nlargest(int(cuantos), columna).copy()
ranking["Tramo"] = (ranking.carretera + ", km " + ranking.pk_inicio_km.round().astype(int).astype(str)
                    + " a " + ranking.pk_fin_km.round().astype(int).astype(str))
ranking["Riesgo"] = ranking.banda.astype(str)
ranking["Percentil nacional"] = ranking.percentil


def _valor(numero, decimales=0):
    return "—" if numero != numero else estilo.num(numero, decimales)


with resumen:
    if ranking.empty:
        ui.estado_vacio("Ningún tramo cumple estos filtros",
                        "Prueba con «Todos los niveles» o con otro tipo de vía.")
    else:
        primero = ranking.iloc[0]
        destacada = ui.tarjeta_destacada(
            f"Primero de la lista · {criterio}",
            f"{primero.carretera} · km {primero.pk_inicio_km:.0f}–{primero.pk_fin_km:.0f}",
            f"{primero.provincia} · {primero.tipo_via_presentacion}",
            [(_valor(primero.N_ACC), "accidentes en 2024"),
             (_valor(primero.acc_por_km, 2), "accidentes por km"),
             (_valor(primero.TASA_100M, 1), "por 100 M veh·km"),
             (f"{primero.percentil:.0f} / 100", "percentil nacional")],
            banda=primero.banda, clase="bz-ancho")
        km_seleccion = datos_filtrados.longitud_km.sum()
        ui.rejilla([destacada, ui.pila([
            ui.tarjeta_cifra("Tramos en la selección", estilo.num(len(datos_filtrados)),
                             pie=f"de {estilo.num(len(tramos))} puntuados en {datos.ANIO}"),
            ui.tarjeta_cifra("Red en la selección", estilo.num(km_seleccion), unidad="km",
                             pie=f"{estilo.pct(km_seleccion / tramos.longitud_km.sum())} "
                                 "de la red medida"),
        ])], plantilla="minmax(0, 2fr) minmax(0, 1fr)")

ui.cabecera_seccion("Explorador de tramos",
                    f"{len(ranking)} tramos ordenados por «{criterio.lower()}».")
if not ranking.empty:
    ui.tabla(ranking, [
        ui.columna("Tramo", "Tramo", "fuerte", secundario="provincia"),
        ui.columna("tipo_via_presentacion", "Tipo de vía", secundario="tipo_via_detalle"),
        ui.columna("N_ACC", "Accidentes", "num"),
        ui.columna("acc_por_km", "Por km", "num", decimales=2),
        ui.columna("TASA_100M", "Por 100 M veh·km", "num", decimales=1),
        ui.columna("Percentil nacional", "Percentil", "percentil"),
        ui.columna("Riesgo", "Nivel", "riesgo"),
    ], alto=560, ranking=True)

if not ranking.empty:
    provincia_top = ranking.provincia.value_counts()
    titulo_1 = (f"{provincia_top.iloc[0]} de los {len(ranking)} tramos de la lista están en "
                f"{provincia_top.index[0]}")
else:
    titulo_1 = "El tráfico explica buena parte del ranking"
ui.conclusiones([
    (titulo_1,
     "Donde hay más tráfico hay más accidentes. Es verdad, y por eso el ranking de accidentes "
     "se parece al de intensidad de tráfico."),
    ("La exposición cambia el orden",
     "«Más riesgo para el que pasa» descuenta el tráfico y deja solo lo que aporta el tramo. "
     "Por accidentes por kilómetro salen rondas urbanas; por riesgo para el que pasa, "
     "nacionales largas y poco transitadas."),
    ("Cada criterio responde a una pregunta distinta",
     "Quien reparte presupuesto y quien va a conducir no buscan lo mismo. Sin exposición, un "
     "tramo de 200 metros con dos accidentes puede colarse arriba: por eso el criterio por "
     "defecto no es ese."),
])

st.write("")
with st.expander("Cómo calculamos este indicador"):
    for nombre, (_, texto) in CRITERIOS.items():
        st.markdown(f"**{nombre}.** {texto}")
    st.markdown(
        "**Tipo de vía.** Es la categoría que utiliza el modelo. La descripción original se "
        "conserva en la tabla para distinguir, por ejemplo, una autopista de peaje de una "
        "autovía.")
    st.markdown(
        f"**Percentil y nivel.** Posición relativa dentro de los "
        f"{estilo.num(datos.referencia_2024().size)} tramos puntuados en {datos.ANIO}. Los "
        "niveles son cuantiles nacionales: Bajo por debajo del percentil 50, Medio hasta el "
        "80, Alto hasta el 95 y Muy alto el 5 % superior.")
