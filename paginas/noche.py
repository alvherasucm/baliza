"""05 Salir de noche. El sistema no solo senala sitios, tambien momentos, que es
lo unico sobre lo que decide quien va a conducir.

El score de CatBoost no esta calibrado, asi que ni se ensena como porcentaje ni
se divide entre escenarios: solo se dice en que puesto queda cada salida frente
a los accidentes reales de 2024. Y el usuario elige bloques completos, no
variables sueltas, porque el modelo trabaja con combinaciones.
"""
import streamlit as st

from baliza import componentes as ui
from baliza import datos, estilo

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


ui.cabecera_pagina(
    "Salir de noche",
    "Cuánto cambia la gravedad según cuándo sales",
    "Compara dos salidas por la misma carretera. Si hay un accidente, ¿cuánto cambia que sea "
    "grave o mortal?",
    meta=[("Referencia", f"{estilo.num(datos.referencia_gravedad().size)} accidentes de 2024"),
          ("Modelo", "gravedad leve / grave o mortal")],
)

escenarios = {}
for columna, salida in zip(st.columns(2, gap="medium"), ["A", "B"]):
    with columna, ui.panel(f"salida_{salida.lower()}"):
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

if diferencia >= UMBRAL_IGUALES:
    lectura_valor, lectura_pie = f"+{diferencia:.0f}", (
        "de cada 100 sube la gravedad con las condiciones de B, si hay accidente.")
elif diferencia <= -UMBRAL_IGUALES:
    lectura_valor, lectura_pie = f"−{-diferencia:.0f}", (
        "de cada 100 baja la gravedad con las condiciones de B, si hay accidente. No dice nada "
        "de la probabilidad de tenerlo.")
else:
    lectura_valor, lectura_pie = "≈", (
        f"Para el modelo, las dos salidas son prácticamente iguales: menos de "
        f"{UMBRAL_IGUALES} puestos de diferencia.")

ayuda = ("Accidentes con víctimas de 2024 que el modelo puntúa por debajo de esta salida. "
         "Es un puesto, no una probabilidad.")
ui.cabecera_seccion("Resultado", "Puesto de cada salida frente a los accidentes reales de 2024.")
ui.rejilla([
    ui.tarjeta_cifra(f"Salida {salida} · más grave que", f"{puesto:.0f}", unidad="de cada 100",
                     ayuda=ayuda, extra=f'<div class="bz-card-foot">{ui.etiqueta_riesgo(banda)}</div>')
    for salida, puesto, banda in zip(["A", "B"], puestos, bandas)
] + [ui.tarjeta_cifra("Diferencia de B frente a A", lectura_valor,
                      unidad="puestos" if lectura_valor != "≈" else None,
                      pie=lectura_pie, clase="bz-feature")])

origen = ("un accidente real en carretera de 2024, el de gravedad mediana" if es_de_carretera
          else "un accidente real de 2024 de gravedad mediana, trasladado a carretera")
ui.panel_info(
    f"Lo que no eliges se queda como en {origen}: "
    f"{etiqueta('TIPO_ACCIDENTE').lower()}, {int(caso['TOTAL_VEHICULOS'])} vehículos, "
    f"{etiqueta('VISIB_RESTRINGIDA_POR').lower()}, circulación en "
    f"{etiqueta('CONDICION_NIVEL_CIRCULA').lower()} y provincia de {etiqueta('COD_PROVINCIA')}.",
    etiqueta="Condiciones fijas")

metricas = datos.metricas_gravedad()
ui.conclusiones([
    ("De noche, más grave",
     "Es lo que diría cualquiera, y el modelo coincide: de noche o de madrugada el accidente "
     "puntúa más grave en la gran mayoría de combinaciones."),
    ("Con lluvia, menos grave",
     "Aquí el modelo discrepa de la intuición: con lluvia o nieve puntúa el accidente como menos "
     "grave, en cualquier combinación de esta pantalla."),
    ("Avisa de más, a propósito",
     f"De cada 10 accidentes graves reales detecta 7, y de cada 10 avisos que da, "
     f"{metricas['precision_severo'] * 10:.0f} acaban siendo graves. No avisar de un grave "
     f"cuesta más que avisar de más."),
])

st.write("")
with st.expander("En qué se fija el modelo"):
    importancia = datos.importancia_gravedad()
    elegibles = {variable for opciones in BLOQUES.values()
                 for valores in opciones.values() for variable in valores}
    pesos = importancia.reset_index()
    pesos.columns = ["variable", "peso"]
    pesos["dato"] = pesos.variable.map(lambda v: NOMBRES.get(v, v))
    pesos["peso"] = pesos.peso / 100
    pesos["uso"] = pesos.variable.map(lambda v: "Lo eliges" if v in elegibles else "Fijo")
    ui.tabla(pesos, [ui.columna("dato", "Dato", "fuerte"),
                     ui.columna("peso", "Peso en el modelo", "barra", decimales=1),
                     ui.columna("uso", "En esta pantalla", "suave")], alto=420)
    st.caption(
        "Mide cuánto usa el modelo cada dato para ordenar los accidentes, no cuánto cambia la "
        "gravedad si lo cambias: el modelo trabaja con combinaciones, por eso aquí se comparan "
        "salidas completas. Lo que aparece como fijo no lo decide quien planifica el viaje, o no "
        "se puede cambiar sin crear un escenario que no existe.")

with st.expander("Cómo calculamos este indicador"):
    st.markdown(
        "**Puesto frente a 2024.** El modelo estima la gravedad **si hay un accidente**; no dice "
        "que vayas a tenerlo. Su puntuación no es una probabilidad, así que no se enseña como "
        "porcentaje: solo se dice en qué puesto queda cada salida frente a los "
        f"{estilo.num(datos.referencia_gravedad().size)} accidentes con víctimas de 2024.")
    st.markdown(
        "**Niveles.** Los mismos cortes que en los tramos: Bajo por debajo del puesto 50, Medio "
        "hasta el 80, Alto hasta el 95 y Muy alto el 5\u00a0% más grave.")
