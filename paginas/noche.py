"""05 Salir de noche. El sistema no solo senala sitios, tambien momentos, que es
lo unico sobre lo que decide quien va a conducir.

El score de CatBoost no esta calibrado, asi que ni se ensena como porcentaje ni
se divide entre escenarios: solo se dice en que puesto queda cada salida frente
a los accidentes reales de 2024. La comparacion va contra los interurbanos
peninsulares, que son la red que cubre Baliza. El test entero es en dos tercios
urbano y puntua mas bajo, asi que colocaria cualquier salida por carretera mas
arriba de lo que le toca. El usuario elige bloques completos y no variables
sueltas, porque el modelo trabaja con combinaciones.
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
    """La salida A arranca en la opcion que mas se parece al caso de referencia;
    la B solo cambia la hora.

    Se busca el mejor encaje y no la coincidencia exacta. Un accidente real trae
    su hora y su mes concretos (las 13:00 de un lunes de agosto), y cada opcion
    lleva un valor representativo de su franja (las 17:00 de la tarde, julio para
    el verano). Con coincidencia exacta, un accidente de agosto arrancaba en
    invierno solo porque invierno es el primero de la lista."""
    if salida == "B" and bloque in DEFECTO_B:
        return DEFECTO_B[bloque]
    return max(BLOQUES[bloque],
               key=lambda opcion: sum(caso.get(variable) == valor for variable, valor
                                      in BLOQUES[bloque][opcion].items()))


def etiqueta(variable: str) -> str:
    codigo = caso[variable]
    return etiquetas.get(variable, {}).get(str(codigo), str(codigo))


ui.cabecera_pagina(
    "Salir de noche",
    "Cuánto cambia la gravedad según cuándo sales",
    "Compara dos salidas por la misma carretera y mira cómo cambia la gravedad de un "
    "accidente, si llega a ocurrir.",
    meta=[("Referencia",
           f"{estilo.num(datos.referencia_gravedad().size)} accidentes en carretera de 2024"),
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
        "más arriba en gravedad con las condiciones de B, si hay un accidente.")
elif diferencia <= -UMBRAL_IGUALES:
    lectura_valor, lectura_pie = f"−{-diferencia:.0f}", (
        "más abajo en gravedad con las condiciones de B, si hay un accidente. Esto no dice si "
        "es más o menos probable tenerlo.")
else:
    lectura_valor, lectura_pie = "≈", (
        f"Las dos salidas quedan a menos de {UMBRAL_IGUALES} puestos. Para el modelo son "
        f"casi iguales.")

ayuda = ("De cada 100 accidentes con víctimas en carretera interurbana de 2024, cuántos "
         "puntúa el modelo por debajo de esta salida. Es un puesto en una clasificación; el "
         "modelo no da probabilidades.")
ui.cabecera_seccion("Resultado",
                    "Puesto de cada salida frente a los accidentes reales en carretera de 2024.")
ui.rejilla([
    ui.tarjeta_cifra(f"Salida {salida} · más grave que", f"{puesto:.0f}", unidad="de cada 100",
                     ayuda=ayuda, extra=f'<div class="bz-card-foot">{ui.etiqueta_riesgo(banda)}</div>')
    for salida, puesto, banda in zip(["A", "B"], puestos, bandas)
] + [ui.tarjeta_cifra("Diferencia de B frente a A", lectura_valor,
                      unidad="puestos" if lectura_valor != "≈" else None,
                      pie=lectura_pie, clase="bz-feature")])

origen = ("un accidente real de 2024 de los más corrientes en esta red, con la gravedad "
          "mediana de su grupo" if es_de_carretera
          else "un accidente real de 2024 de gravedad mediana, pasado a carretera")
ui.panel_info(
    f"Todo lo que no eliges se toma de {origen}: "
    f"{etiqueta('TIPO_ACCIDENTE').lower()}, {int(caso['TOTAL_VEHICULOS'])} vehículos, "
    f"{etiqueta('VISIB_RESTRINGIDA_POR').lower()}, el tráfico en "
    f"{etiqueta('CONDICION_NIVEL_CIRCULA').lower()} y provincia de {etiqueta('COD_PROVINCIA')}.",
    etiqueta="Condiciones fijas")

# Las cifras del punto de operacion son las del mismo universo con el que se
# compara la pantalla, no las del test entero: en carretera el modelo acierta mas.
metricas = datos.metricas_gravedad(datos.UNIVERSO_GRAVEDAD)
ui.conclusiones([
    ("La madrugada es lo que más agrava",
     "Coincide con lo que esperaría cualquiera. De madrugada el accidente puntúa más grave "
     "que de día en casi todas las combinaciones de esta pantalla. De noche también, aunque "
     "no siempre: en unas tres de cada cuatro."),
    ("Con lluvia o nieve puntúa menos grave",
     "Va contra la intuición y se repite en todas las combinaciones de esta pantalla. El "
     "modelo no explica por qué."),
    ("Prefiere avisar de más",
     f"En carretera detecta {metricas['recall'] * 10:.0f} de cada 10 accidentes graves. El "
     f"precio es que solo acierta el {estilo.pct(metricas['precision'])} de los avisos: está "
     f"ajustado para que se le escapen pocos, aunque avise de más."),
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
        "El peso indica cuánto usa el modelo cada dato para ordenar los accidentes. No indica "
        "cuánto sube o baja la gravedad al cambiarlo, porque el modelo trabaja con "
        "combinaciones; por eso la pantalla compara salidas completas. Los datos fijos son los "
        "que no decide quien planifica un viaje, o los que, cambiados por separado, darían un "
        "escenario imposible.")

with st.expander("Cómo calculamos este indicador"):
    st.markdown(
        "**Puesto frente a 2024.** El modelo estima la gravedad de un accidente que ya ha "
        "ocurrido y no dice nada de si vas a tenerlo. Su puntuación no está calibrada como "
        "probabilidad, por eso no se muestra en porcentaje. Lo que se enseña es el puesto de "
        "cada salida entre los "
        f"{estilo.num(datos.referencia_gravedad().size)} accidentes con víctimas ocurridos en "
        "2024 en carretera interurbana peninsular: fuera de ciudad y sin islas, Ceuta ni "
        "Melilla. El test "
        f"completo tiene {estilo.num(datos.referencia_gravedad('global').size)} accidentes, dos "
        "tercios de ellos urbanos, que puntúan más bajo. Comparando contra ese conjunto, "
        "cualquier salida por carretera saldría mejor colocada de lo que le toca.")
    st.markdown(
        "**Niveles.** Los mismos cortes que en los tramos: Bajo por debajo del puesto 50, Medio "
        "hasta el 80, Alto hasta el 95 y Muy alto el 5\u00a0% más grave.")
