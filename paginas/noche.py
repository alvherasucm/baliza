"""05 Salir de noche. El sistema no solo senala sitios, tambien momentos, que es
lo unico sobre lo que decide quien va a conducir.

El score de CatBoost no esta calibrado, asi que ni se ensena como porcentaje ni
se divide entre escenarios: solo se dice en que puesto queda cada salida frente
a los accidentes reales de 2024. Y el usuario elige bloques completos, no
variables sueltas, porque el modelo trabaja con combinaciones.
"""
import pandas as pd
import streamlit as st

from baliza import datos, estilo

estilo.cabecera(st.session_state["paginas"])

BLOQUES = datos.BLOQUES_GRAVEDAD
DEFECTO_B = {"Momento del día": "De madrugada (4:00)"}
UMBRAL_IGUALES = 5

NOMBRES = {
    "COD_PROVINCIA": "Provincia", "TIPO_ACCIDENTE": "Tipo de accidente",
    "CONDICION_NIVEL_CIRCULA": "Nivel de circulación", "VISIB_RESTRINGIDA_POR": "Visibilidad",
    "REGION": "Región", "TOTAL_VEHICULOS": "Vehículos implicados", "HORA": "Hora",
    "MES": "Mes", "DIA_SEMANA": "Día de la semana", "CONDICION_ILUMINACION": "Iluminación",
    "ZONA": "Zona", "TRAZADO_PLANTA": "Trazado", "FRANJA_HORARIA": "Franja horaria",
    "CONDICION_METEO": "Meteorología", "CONDICION_FIRME": "Estado del firme",
    "ESTACION": "Estación", "TIPO_VIA_AGRUPADO": "Tipo de vía (grupo)",
    "TIPO_VIA": "Tipo de vía", "FIN_DE_SEMANA": "Fin de semana",
}

caso, es_de_carretera = datos.caso_referencia_gravedad()
etiquetas = datos.etiquetas_gravedad()


def opcion_inicial(bloque: str, salida: str) -> str:
    """La salida A arranca en el caso de referencia; la B solo cambia la hora."""
    if salida == "B" and bloque in DEFECTO_B:
        return DEFECTO_B[bloque]
    for opcion, valores in BLOQUES[bloque].items():
        if all(caso.get(variable) == valor for variable, valor in valores.items()):
            return opcion
    return next(iter(BLOQUES[bloque]))


def etiqueta(variable: str) -> str:
    codigo = caso[variable]
    return etiquetas.get(variable, {}).get(str(codigo), str(codigo))


st.subheader("Salir de noche")
st.caption("Dos salidas por la misma carretera. Si hay un accidente, ¿cuánto cambia que "
           "sea grave o mortal?")

escenarios = {}
for columna, salida in zip(st.columns(2), ["A", "B"]):
    with columna:
        st.markdown(f"**Salida {salida}**")
        escenario = dict(caso)
        for bloque, opciones in BLOQUES.items():
            nombres = list(opciones)
            elegida = st.selectbox(bloque, nombres,
                                   index=nombres.index(opcion_inicial(bloque, salida)),
                                   key=f"{salida}_{bloque}")
            escenario.update(opciones[elegida])
        escenarios[salida] = escenario

puestos = datos.percentil_gravedad(datos.puntuar_gravedad(list(escenarios.values())))
bandas = datos.banda_gravedad(puestos)
diferencia = puestos[1] - puestos[0]

st.divider()
*columnas_salida, columna_lectura = st.columns(3)
for columna, salida, puesto, banda in zip(columnas_salida, ["A", "B"], puestos, bandas):
    columna.metric(f"Salida {salida}: más grave que", f"{puesto:.0f} de cada 100",
                   help="Accidentes con víctimas de 2024 que el modelo puntúa por debajo de "
                        "esta salida. Es un puesto, no una probabilidad.")
    columna.markdown(f"Gravedad: {estilo.etiqueta_banda(str(banda))}", unsafe_allow_html=True)

with columna_lectura:
    if diferencia >= UMBRAL_IGUALES:
        st.markdown(f"Con las condiciones de **B**, el accidente, si ocurre, sube "
                    f"**{diferencia:.0f} puestos de cada 100** en gravedad respecto a **A**.")
    elif diferencia <= -UMBRAL_IGUALES:
        st.markdown(f"Con las condiciones de **B**, el accidente, si ocurre, baja "
                    f"**{-diferencia:.0f} puestos de cada 100** en gravedad respecto a **A**. "
                    f"Ojo: eso no dice nada de la probabilidad de tenerlo.")
    else:
        st.markdown(f"Para el modelo, las dos salidas son prácticamente iguales: menos de "
                    f"{UMBRAL_IGUALES} puestos de diferencia.")

origen = ("un accidente real en carretera de 2024, el de gravedad mediana" if es_de_carretera
          else "un accidente real de 2024 de gravedad mediana, trasladado a carretera")
estilo.nota(
    f"Lo que no eliges se queda como en {origen}: "
    f"{etiqueta('TIPO_ACCIDENTE').lower()}, {int(caso['TOTAL_VEHICULOS'])} vehículos, "
    f"{etiqueta('VISIB_RESTRINGIDA_POR').lower()}, circulación en "
    f"{etiqueta('CONDICION_NIVEL_CIRCULA').lower()} y provincia de {etiqueta('COD_PROVINCIA')}."
)

st.divider()
metricas = datos.metricas_gravedad()
estilo.contraste(
    a_ojo="De noche es peor y con lluvia también. Todo el mundo lo dice y nadie sabe cuánto.",
    modelo="En la noche coincide. En la lluvia, no: con lluvia o nieve puntúa el accidente "
           "como menos grave, en cualquier combinación de esta pantalla.",
    error=f"De cada 10 accidentes graves reales detecta 7, y de cada 10 avisos que da, "
          f"{metricas['precision_severo'] * 10:.0f} acaban siendo graves. Avisa de más a "
          f"propósito: no avisar de un grave cuesta más que avisar de más.",
)

estilo.nota(
    "El modelo estima la gravedad **si hay un accidente**. No dice que vayas a tenerlo. Y su "
    "puntuación no es una probabilidad, así que no la enseñamos como porcentaje: solo decimos "
    f"en qué puesto queda cada salida frente a los "
    f"{format(datos.referencia_gravedad().size, ',').replace(',', '.')} accidentes con "
    "víctimas de 2024."
)

with st.expander("En qué se fija el modelo"):
    importancia = datos.importancia_gravedad()
    elegibles = {variable for opciones in BLOQUES.values()
                 for valores in opciones.values() for variable in valores}
    st.dataframe(
        pd.DataFrame({
            "Dato": [NOMBRES.get(v, v) for v in importancia.index],
            "Peso en el modelo": importancia.to_numpy(),
            "En esta pantalla": ["Lo eliges" if v in elegibles else "Fijo"
                                 for v in importancia.index],
        }),
        hide_index=True, width="stretch",
        column_config={"Peso en el modelo": st.column_config.ProgressColumn(
            min_value=0.0, max_value=float(importancia.max()), format="%.1f%%")})
    st.caption(
        "Mide cuánto usa el modelo cada dato para ordenar los accidentes, no cuánto cambia la "
        "gravedad si lo cambias: el modelo trabaja con combinaciones, por eso aquí se comparan "
        "salidas completas. Lo que aparece como fijo no lo decide quien planifica el viaje, o no "
        "se puede cambiar sin crear un escenario que no existe."
    )
