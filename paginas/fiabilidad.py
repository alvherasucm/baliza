"""06 Fiabilidad. Convertir la autocritica en credencial. Se cita de pasada en la
presentacion; existe para que el escepticismo tenga adonde ir."""
import pandas as pd
import streamlit as st

from baliza import componentes as ui
from baliza import datos, estilo

# Gravedad, opcion C: el test entero es la cifra oficial y el subconjunto
# interurbano peninsular va aparte, porque es la red sobre la que trabaja Baliza.
metricas = datos.metricas_gravedad()
carretera = datos.metricas_gravedad(datos.UNIVERSO_GRAVEDAD)
provincias = datos.metricas_provincias()
ingenua, jerarquico = provincias.loc["pred_naive"], provincias.loc["pred_jerarquico"]
error_provincia = (f"Error medio de {estilo.num(jerarquico.mae, 1)} frente a "
                   f"{estilo.num(ingenua.mae, 1)} (un {estilo.pct(jerarquico.mejora_mae)} menos)")

referencias = datos.referencias_tramos()
por_tipo = referencias["por_tipo_via"]
auc_modelo, auc_trafico, auc_historico = (
    referencias[clave]["roc_auc"] for clave in ("modelo_final", "solo_trafico", "historico"))


def auc(valor) -> str:
    return estilo.num(valor, 3)


def ventaja(valor) -> str:
    return f"{'+' if valor >= 0 else '−'}{auc(abs(valor))}"


def ventaja_priorizacion(valor) -> str:
    """Diferencia de ROC-AUC expresada como puntos porcentuales, no como acierto."""
    signo = "+" if valor >= 0 else "−"
    return f"{signo}{estilo.num(abs(valor) * 100, 1)} p.p."


ui.cabecera_pagina(
    "Fiabilidad",
    "Qué sabemos y qué no",
    "De dónde salen los datos, cómo se ha comprobado cada modelo y dónde están sus límites.",
    meta=[("Validación", "2024, un año que los modelos no vieron"),
          ("Datos", "2016-2024 sin 2020")],
)

ui.rejilla([
    ui.tarjeta_cifra("Provincia · error medio", estilo.num(jerarquico.mae, 1),
                     unidad="accidentes",
                     pie=f"frente a {estilo.num(ingenua.mae, 1)} de repetir el año anterior",
                     delta=f"−{estilo.pct(jerarquico.mejora_mae)}", tono="bueno"),
    ui.tarjeta_cifra(
        "Tramo · capacidad de priorización", estilo.pct(auc_modelo, 1),
        ayuda="Si se compara un tramo que registró al menos un accidente en 2024 con otro "
              "que no registró ninguno, el modelo asigna mayor riesgo al primero en el "
              f"{estilo.pct(auc_modelo, 1)} de las comparaciones. No es un porcentaje de "
              "predicciones acertadas.",
        pie=f"frente al {estilo.pct(auc_trafico, 1)} de ordenar solo por tráfico",
        delta=ventaja_priorizacion(auc_modelo - auc_trafico), tono="bueno"),
    ui.tarjeta_cifra("Gravedad · graves detectados", estilo.pct(metricas["recall"]),
                     pie=f"{estilo.pct(metricas['precision'])} de los avisos aciertan"),
])

ui.cabecera_seccion("Cómo se construyó")
ui.rejilla([
    ui.tarjeta_texto(
        "De dónde salen los datos",
        "Microdatos de accidentes con víctimas de la DGT de 2016 a 2024, cruzados con los "
        "aforos del Mapa de Tráfico del Ministerio. Cada fila es un tramo de carretera en un año, "
        "con su tráfico y sus accidentes. 2020 queda fuera de todo el estudio."),
    ui.tarjeta_texto(
        "Cómo se validó",
        "Se reservó 2024. Los modelos de tramo y de gravedad se entrenan con 2016-2022 y se "
        "ajustan con 2023; el de provincias se entrena con 2016-2023. Los tres se miden con "
        "2024, un año que no han visto, y de ahí salen todas las métricas de acierto de esta "
        "web."),
], plantilla="repeat(2, minmax(0, 1fr))")

ui.cabecera_seccion("Qué hace cada modelo y cuánto se equivoca")
ui.tabla(pd.DataFrame([
    {"Modelo": "Provincia", "Pregunta": "Cuántos accidentes esperar en una provincia",
     "Referencia": "Suponer que este año será como el anterior",
     "Resultado": error_provincia},
    {"Modelo": "Tramo", "Pregunta": "Si un tramo tendrá algún accidente este año",
     "Referencia": "Ordenar por tráfico o por los accidentes del año anterior",
     "Resultado": f"ROC-AUC {auc(auc_modelo)} frente a {auc(auc_trafico)} del tráfico "
                  f"y {auc(auc_historico)} del año anterior"},
    {"Modelo": "Gravedad", "Pregunta": "Si un accidente será grave o mortal",
     "Referencia": "Avisar siempre o no avisar nunca",
     "Resultado": f"Detecta el {estilo.pct(metricas['recall'])} de los graves; "
                  f"{estilo.pct(metricas['precision'])} de los avisos aciertan"},
]), [ui.columna("Modelo", "Modelo", "fuerte"),
     ui.columna("Pregunta", "Qué responde"),
     ui.columna("Referencia", "Contra qué se compara", "suave"),
     ui.columna("Resultado", "Resultado")], ajustar=True)

ui.cabecera_seccion(
    "Gravedad: el test completo y la carretera",
    f"La cifra oficial del modelo sale de los {estilo.num(metricas['n'])} accidentes con "
    f"víctimas de 2024, ciudad e islas incluidas. La pantalla de gravedad se mide solo con los "
    f"{estilo.num(carretera['n'])} que ocurrieron en carretera peninsular, que es donde "
    f"transcurre un viaje de los que planifica esta web.")
ui.tabla(pd.DataFrame([
    {"conjunto": "Test 2024 completo",
     "detalle": f"{estilo.num(metricas['n'])} accidentes · "
                f"{estilo.pct(metricas['tasa_base'], 1)} graves o mortales",
     "recall": metricas["recall"], "precision": metricas["precision"],
     "auc": metricas["roc_auc"]},
    {"conjunto": "Carretera interurbana peninsular",
     "detalle": f"{estilo.num(carretera['n'])} accidentes · "
                f"{estilo.pct(carretera['tasa_base'], 1)} graves o mortales",
     "recall": carretera["recall"], "precision": carretera["precision"],
     "auc": carretera["roc_auc"]},
]), [ui.columna("conjunto", "Conjunto", "fuerte", secundario="detalle"),
     ui.columna("recall", "Graves que detecta", "pct"),
     ui.columna("precision", "Avisos que aciertan", "pct"),
     ui.columna("auc", "ROC-AUC", "num", decimales=3)], ajustar=True)
st.write("")
ui.panel_info(
    f"En carretera el modelo acierta más: detecta el {estilo.pct(carretera['recall'])} de los "
    f"graves frente al {estilo.pct(metricas['recall'])}, y el ROC-AUC sube de "
    f"{auc(metricas['roc_auc'])} a {auc(carretera['roc_auc'])}. También parte de otro sitio, "
    f"porque ahí el accidente grave es menos raro: {estilo.pct(carretera['tasa_base'], 1)} de "
    f"los casos frente al {estilo.pct(metricas['tasa_base'], 1)} del conjunto. Las dos columnas "
    f"salen del mismo modelo, de la misma ejecución y con el mismo umbral, "
    f"{str(metricas['umbral']).replace('.', ',')}.",
    etiqueta="Por qué damos las dos")

ui.cabecera_seccion(
    "Tramos: el modelo frente a ordenar por tráfico",
    f"ROC-AUC sobre los mismos {estilo.num(referencias['n'])} tramos de 2024. Un 1 sería "
    "ordenarlos sin fallo y un 0,5, hacerlo al azar.")
tabla_tipos = pd.concat([
    pd.DataFrame([{"tipo_via": "Todos", "n": referencias["n"], "modelo": auc_modelo,
                   "trafico": auc_trafico, "ventaja": auc_modelo - auc_trafico}]),
    por_tipo,
], ignore_index=True)
tabla_tipos["nombre"] = tabla_tipos.tipo_via.map(
    {"Todos": "Todos los tramos", **datos.TIPO_VIA_PRESENTACION})
tabla_tipos["detalle"] = [
    f"{estilo.num(n)} tramos" + (" · muestra pequeña" if n < 500 else "")
    for n in tabla_tipos.n]
tabla_tipos["diferencia"] = tabla_tipos.ventaja.map(ventaja)
ui.tabla(tabla_tipos, [
    ui.columna("nombre", "Tipo de vía", "fuerte", secundario="detalle"),
    ui.columna("modelo", "Modelo", "num", decimales=3),
    ui.columna("trafico", "Solo tráfico", "num", decimales=3),
    ui.columna("diferencia", "Ventaja del modelo", "derecha"),
], ajustar=True)
convencional = por_tipo.set_index("tipo_via").loc["Convencional"]
st.write("")
ui.panel_info(
    f"Ordenar los tramos solo por tráfico ya acierta bastante: {auc(auc_trafico)}. El modelo "
    f"llega a {auc(auc_modelo)} porque añade el tipo de vía, la longitud del tramo, el peso "
    "de los camiones y la provincia. Gana en los tres tipos de vía, y la diferencia es clara "
    f"en las carreteras convencionales, que son {round(convencional.n / referencias['n'] * 10)} "
    f"de cada 10 tramos: {auc(convencional.modelo)} frente a {auc(convencional.trafico)}.",
    etiqueta="Dónde gana el modelo")

ui.cabecera_seccion(
    "Provincias: cuatro versiones del modelo",
    "Las cuatro aprenden con 2016-2023 y se comparan en 2024 sobre las mismas "
    f"{len(datos.predicciones_provincias())} provincias.")
variantes = provincias.assign(
    frente=[("referencia" if clave == "pred_naive" else
             f"{'−' if v > 0 else '+'}{estilo.pct(abs(v))}")
            for clave, v in zip(provincias.clave, provincias.mejora_mae)])
ui.tabla(variantes, [
    ui.columna("Versión", "Versión", "fuerte"),
    ui.columna("Qué usa", "Qué tiene en cuenta", "suave"),
    ui.columna("mae", "Error medio", "num", decimales=1),
    ui.columna("rmse", "RMSE", "num", decimales=1),
    ui.columna("frente", "Error frente a repetir el año", "derecha"),
], ajustar=True)
explicativo, predictivo = provincias.loc["pred_explicativo"], provincias.loc["pred_predictivo"]
st.write("")
ui.panel_info(
    "El explicativo sirve para ver qué factores pesan, pero prevé peor que repetir el "
    f"año anterior ({estilo.num(explicativo.mae, 1)} frente a {estilo.num(ingenua.mae, 1)}). "
    "El salto grande llega al añadir los accidentes del año anterior: el error baja a "
    f"{estilo.num(predictivo.mae, 1)}. El ajuste por provincia lo deja en "
    f"{estilo.num(jerarquico.mae, 1)}. En el RMSE, que castiga más los fallos grandes, la "
    f"distancia con la regla ingenua es mayor: {estilo.num(jerarquico.rmse, 1)} frente a "
    f"{estilo.num(ingenua.rmse, 1)}.",
    etiqueta="Qué aporta cada paso")

ui.cabecera_seccion("Lo que este sistema no puede hacer")
ui.rejilla([ui.lista_simple([
    "No cubre calles de ciudad, carreteras autonómicas ni provinciales. Solo la Red de "
    "Carreteras del Estado, que es el 11 % de los accidentes y el 24 % de los "
    "fallecidos.",
    "No cubre Baleares, Canarias ni las carreteras forales de Navarra y el País Vasco. "
    "De Navarra solo entra la AP-68, que es del Estado. El modelo de gravedad sí aprendió "
    "de toda España, islas incluidas. Por eso sus cifras se dan además sobre la carretera "
    "peninsular, que es por donde pasa una ruta de esta web.",
    "No predice que vayas a tener un accidente. Estima cuánto riesgo acumula un tramo al cabo "
    "de un año, y qué gravedad tendría un accidente si ocurriera.",
    "Solo cuenta accidentes con víctimas. Los de daños materiales no están en los datos.",
    "No sabe cuánto tráfico hay a cada hora: el tráfico es una media diaria del año. Por eso "
    "no dice a qué hora es más probable tener un accidente, solo cómo de grave sería.",
    "No sustituye a la señalización ni a la DGT, y no manda desviarse de ningún sitio.",
    "No sitúa los tramos en un mapa. Trabaja con carretera y punto kilométrico, sin "
    "coordenadas.",
])], plantilla="1fr")

ui.panel_info("Las pantallas con cifras enseñan al lado qué haría cualquiera a ojo y cuánto se "
              "equivoca el modelo. Esta página lo reúne todo.")
