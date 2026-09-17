"""06 Fiabilidad. Convertir la autocritica en credencial. Se cita de pasada en la
presentacion; existe para que el escepticismo tenga adonde ir."""
import pandas as pd
import streamlit as st

from baliza import componentes as ui
from baliza import datos, estilo

metricas = datos.metricas_gravedad()
provincias = datos.metricas_provincias()
ingenua, jerarquico = provincias.loc["pred_naive"], provincias.loc["pred_jerarquico"]
error_provincia = (f"Error medio de {estilo.num(jerarquico.mae, 1)} frente a "
                   f"{estilo.num(ingenua.mae, 1)} (un {estilo.pct(jerarquico.mejora_mae)} menos)")

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
    ui.tarjeta_cifra("Tramo · ROC-AUC", "0,818",
                     pie="frente a 0,800 de ordenar solo por tráfico"),
    ui.tarjeta_cifra("Gravedad · graves detectados", estilo.pct(metricas["recall_severo"]),
                     pie=f"{estilo.pct(metricas['precision_severo'])} de los avisos aciertan"),
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
     "Referencia": "Ordenar por intensidad de tráfico",
     "Resultado": "ROC-AUC 0,818 frente a 0,800 del tráfico solo"},
    {"Modelo": "Gravedad", "Pregunta": "Si un accidente será grave o mortal",
     "Referencia": "Avisar siempre o no avisar nunca",
     "Resultado": f"Detecta el {estilo.pct(metricas['recall_severo'])} de los graves; "
                  f"{estilo.pct(metricas['precision_severo'])} de los avisos aciertan"},
]), [ui.columna("Modelo", "Modelo", "fuerte"),
     ui.columna("Pregunta", "Qué responde"),
     ui.columna("Referencia", "Contra qué se compara", "suave"),
     ui.columna("Resultado", "Resultado")], ajustar=True)

st.write("")
ui.panel_info(
    "El modelo de tramos supera por poco a ordenar solo por tráfico: 0,818 frente a 0,800. "
    "Lo que añade es el tipo de vía, la longitud y la provincia, y esa ventaja aparece sobre "
    "todo en carreteras convencionales con poco tráfico, donde el tráfico por sí solo engaña.",
    etiqueta="El punto ciego")

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
    "No cubre Baleares, Canarias ni las carreteras forales del País Vasco.",
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
