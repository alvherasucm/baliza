"""09 Comparar rutas. Sustituye a Flotas. Para un mismo trayecto hay dos formas
de ir, y esta pantalla dice cual acumula menos riesgo y donde se pierde.

El indicador es el mismo indice de ruta de Tu ruta, sin cambiar nada: la
probabilidad anual de cada tramo ponderada por los kilometros que se recorren en
el, con la media nacional en 100. Por eso el catalogo solo trae trayectos cuyas
dos rutas son del mismo tipo de via: ese indice habla del tramo con todo su
trafico, asi que frente a una nacional vacia daria la vuelta al resultado.

La productivizacion sigue aqui: el cargador acepta el formato de ciudades, que
resuelve itinerarios, y el de tramos, que ejecuta el modelo sobre datos nuevos
del usuario con la validacion de Jose.
"""
from datetime import date

import altair as alt
import pandas as pd
import streamlit as st

from baliza import componentes as ui
from baliza import datos, estilo

TRAYECTOS = datos.comparativas()
acierto = datos.referencias_tramos()["modelo_final"]["roc_auc"]

# La columna paso es opcional: obliga a que la ruta atraviese esa ciudad. Se deja
# vacía en las dos primeras filas justo para que se vea que se puede omitir.
PLANTILLA_CIUDADES = pd.DataFrame([
    {"origen": "Madrid", "destino": "Sevilla", "paso": "", "viajes_semana": 10},
    {"origen": "Burgos", "destino": "Mérida", "paso": "", "viajes_semana": 4},
    {"origen": "Madrid", "destino": "Sevilla", "paso": "Córdoba", "viajes_semana": 2},
])
PLANTILLA_TRAMOS = pd.DataFrame([
    {"provincia": "Madrid", "carretera": "A-4", "pk_inicio": 4.0, "pk_fin": 10.0,
     "imd_total": 65000.0, "imd_pesados": 6500.0, "tipo_via": "Autopista_autovia",
     "viajes_semana": 10},
    {"provincia": "Sevilla", "carretera": "A-4", "pk_inicio": 520.0, "pk_fin": 535.0,
     "imd_total": 42000.0, "imd_pesados": 7200.0, "tipo_via": "Autopista_autovia",
     "viajes_semana": 4},
])

ORDENES = {
    "Riesgo de la ruta": ("indice", "El índice de la ruta recomendada, sin más."),
    "Riesgo × viajes a la semana": (
        "exposicion",
        "El índice multiplicado por las veces que se hace la ruta. Es una regla de Baliza "
        "para priorizar una flota, no una salida del modelo."),
}

def _puntos(diferencia: float) -> str:
    """«1 punto», no «1 puntos»."""
    redondeada = round(diferencia)
    return f"{redondeada:.0f} punto" + ("" if abs(redondeada) == 1 else "s")


ui.cabecera_pagina(
    "Rutas alternativas",
    "Dos formas de llegar, dos riesgos distintos",
    "Para un mismo trayecto, Baliza compara las rutas posibles con el índice de ruta y dice "
    "cuál acumula menos riesgo y en qué kilómetros se pierde la diferencia.",
    meta=[("Trayectos", str(len(TRAYECTOS))), ("Año", str(datos.ANIO)),
          ("Referencia", "media nacional = 100"),
          ("Ciudades en la red", str(len(datos.ciudades_red())))],
)

if not TRAYECTOS:
    ui.estado_vacio("No hay trayectos cargados",
                    "Falta **datos/comparativas.json**. Sin él esta pantalla no tiene "
                    "nada que comparar.")
    st.stop()

with ui.filtros():
    columna_trayecto, _ = st.columns([2, 2], gap="medium")
    elegido = columna_trayecto.selectbox(
        "Trayecto", TRAYECTOS,
        format_func=lambda t: f"{t['origen']} – {t['destino']}")
    st.caption(elegido["descripcion"])

rutas = []
for definicion in elegido["rutas"]:
    resumen = datos.evaluar_itinerario([tuple(e) for e in definicion["etapas"]])
    resumen["nombre"] = definicion["nombre"]
    resumen["detalle"] = definicion["detalle"]
    rutas.append(resumen)
rutas.sort(key=lambda r: r["indice"])
mejor, peor = rutas[0], rutas[-1]
diferencia = peor["indice"] - mejor["indice"]
empate = diferencia < datos.EMPATE_INDICE
sin_fiar = [r for r in rutas if not r["fiable"]]

# ------------------------------------------------------------------ resultado

st.write("")
tarjetas = []
for ruta in rutas:
    gana = ruta is mejor and not empate and not sin_fiar
    tarjetas.append(ui.tarjeta_cifra(
        f"{ruta['nombre']} · índice de ruta", f"{ruta['indice']:.0f}",
        ayuda="Media nacional = 100. Cada tramo pesa según los kilómetros que se recorren "
              "en él.",
        pie=ruta["detalle"],
        extra=ui.cifras_compactas([
            (f"{estilo.num(ruta['km_declarados'])} km", "de recorrido"),
            (str(ruta["n_tramos"]), "tramos"),
            (f"{ruta['en_lo_peor']}", "en nivel alto o muy alto"),
        ]),
        clase="bz-feature" if gana else ""))

if empate:
    veredicto = ui.tarjeta_cifra(
        "Diferencia", "≈", pie=f"Las dos rutas quedan a menos de "
        f"{estilo.num(datos.EMPATE_INDICE)} puntos de índice. Para Baliza son equivalentes.")
elif sin_fiar:
    veredicto = ui.tarjeta_cifra(
        "Diferencia", f"{diferencia:.0f}", unidad="puntos",
        pie="No se declara ganadora: una de las rutas tiene demasiados kilómetros sin aforo.")
else:
    ahorro = diferencia / peor["indice"]
    kilometros = mejor["km_declarados"] - peor["km_declarados"]
    if kilometros <= -1:
        coste = f"y {estilo.num(abs(kilometros))} km menos"
    elif kilometros >= 1:
        coste = f"a costa de {estilo.num(kilometros)} km más"
    else:
        coste = "con los mismos kilómetros"
    veredicto = ui.tarjeta_cifra(
        f"Conviene ir: {mejor['nombre']}", f"−{estilo.pct(ahorro)}", unidad="de índice",
        pie=f"**{diferencia:.0f} puntos** de índice menos que la otra, {coste}.",
        tono="bueno", clase="bz-feature")
ui.rejilla(tarjetas + [veredicto])

for ruta in rutas:
    ui.recorrido(ruta["provincias"], prefijo=f"{ruta['nombre']}:")

for ruta in sin_fiar:
    ui.panel_info(
        f"A «{ruta['nombre']}» le faltan {estilo.num(ruta['km_sin_medir'])} km con aforo "
        f"en {datos.ANIO}: solo se mide {estilo.pct(ruta['cobertura'])} del recorrido. Que un "
        "tramo no tenga nota no quiere decir que no tenga riesgo.",
        aviso=True, etiqueta="Cobertura insuficiente")

# -------------------------------------------------------------------- perfil

ui.cabecera_seccion(
    "Dónde se pierde la diferencia",
    "Cada bloque es un tramo real. El ancho son sus kilómetros y el alto, la probabilidad "
    "anual estimada. El eje es el kilómetro del viaje, para que las dos rutas se puedan "
    "mirar una encima de la otra.")

largo = max(r["km_medidos"] for r in rutas)
with ui.contenedor_grafico("comparar"):
    for ruta in rutas:
        perfil = ruta["tramos"].dropna(subset=["PROB_ACCIDENTE_TRAMO_ANIO"]).copy()
        perfil["Probabilidad anual (%)"] = perfil.PROB_ACCIDENTE_TRAMO_ANIO * 100
        perfil["Nivel de riesgo"] = perfil.banda.astype(str)
        perfil["tramo_texto"] = (perfil.carretera + ", km "
                                 + perfil.pk_inicio_km.round().astype(int).astype(str)
                                 + " a " + perfil.pk_fin_km.round().astype(int).astype(str))
        perfil["prob_texto"] = perfil.PROB_ACCIDENTE_TRAMO_ANIO.map(
            lambda p: estilo.pct(p, 1))
        grafico = (
            alt.Chart(perfil)
            .mark_bar(stroke=estilo.SUPERFICIE, strokeWidth=1, cornerRadiusTopLeft=2,
                      cornerRadiusTopRight=2)
            .encode(
                x=alt.X("km_desde_salida:Q", title="Kilómetro del viaje",
                        scale=alt.Scale(domain=[0, largo]),
                        axis=alt.Axis(format="d")),
                x2="km_hasta_ahi:Q",
                y=alt.Y("Probabilidad anual (%):Q", scale=alt.Scale(domain=[0, 100]),
                        title="Probabilidad anual",
                        axis=alt.Axis(values=[0, 50, 100],
                                      labelExpr="datum.value + ' %'")),
                y2=alt.datum(0),
                color=alt.Color(
                    "Nivel de riesgo:N",
                    scale=alt.Scale(domain=datos.BANDAS,
                                    range=[estilo.COLOR_BANDA[n] for n in datos.BANDAS]),
                    legend=alt.Legend(title="Nivel de riesgo")),
                tooltip=[alt.Tooltip("tramo_texto:N", title="Tramo"),
                         alt.Tooltip("provincia:N", title="Provincia"),
                         alt.Tooltip("prob_texto:N", title="Probabilidad anual"),
                         alt.Tooltip("Nivel de riesgo:N")])
            .properties(height=150))
        st.caption(f"{ruta['nombre']} · índice {ruta['indice']:.0f} · "
                   f"{estilo.num(ruta['km_declarados'])} km")
        st.altair_chart(estilo.tema_altair(grafico), theme=None, use_container_width=True)

ui.cabecera_seccion(
    f"Los tramos que más pesan · {peor['nombre']}",
    "Los de mayor probabilidad anual de la ruta con más riesgo.")
peores = peor["tramos"].dropna(subset=["PROB_ACCIDENTE_TRAMO_ANIO"]).nlargest(
    3, "PROB_ACCIDENTE_TRAMO_ANIO")
ui.lista_riesgo([
    (f"{fila.carretera}, km {fila.pk_inicio_km:.0f} a {fila.pk_fin_km:.0f} · {fila.provincia}",
     # Suelo en el 1 %: el percentil 99,97 redondea a cero y «entre el 0 %» no
     # se entiende. Decir «el 1 % con más riesgo» sigue siendo cierto.
     f"Entre el {max(1, round(100 - fila.percentil))} % de tramos con más riesgo de "
     f"España · {estilo.num(fila.longitud_km, 1)} km",
     fila.banda)
    for _, fila in peores.iterrows()])

izquierda, derecha = st.columns([1, 1], gap="medium")
with izquierda:
    if st.button("Ver estos tramos en el ranking  →", type="primary",
                 width="stretch"):
        st.session_state["carreteras_elegidas"] = mejor["vias"]
        st.switch_page(st.session_state["paginas"]["mapa"])
with derecha:
    st.download_button(
        "Descargar la comparación", datos.texto_csv(pd.DataFrame([{
            "trayecto": f"{elegido['origen']} - {elegido['destino']}",
            "ruta": r["nombre"], "vias": " + ".join(r["vias"]),
            "km_recorrido": round(r["km_declarados"], 1),
            "km_con_aforo": round(r["km_medidos"], 1),
            "cobertura": round(r["cobertura"], 4),
            "indice_ruta": round(r["indice"], 1),
            "tramos": r["n_tramos"],
            "tramos_nivel_alto_o_muy_alto": r["en_lo_peor"],
            "recomendada": "Sí" if (r is mejor and not empate and not sin_fiar) else "No",
            "anio_modelo": datos.ANIO,
            "fecha_calculo": date.today().isoformat(),
        } for r in rutas])),
        f"baliza_{elegido['id']}_{date.today():%Y-%m-%d}.csv", "text/csv",
        icon=":material/download:", on_click="ignore", width="stretch")

ui.conclusiones([
    ("A ojo: la más corta",
     f"Por kilómetros ganaría «{min(rutas, key=lambda r: r['km_declarados'])['nombre']}». "
     "La longitud es lo único que se puede comparar sin datos, y no distingue por dónde pasas."),
    (f"Con el modelo: {mejor['indice']:.0f} frente a {peor['indice']:.0f}",
     "Cada tramo del recorrido cuenta según los kilómetros que se hacen en él. Una ruta con "
     "índice 100 estaría en la media de España."),
    ("Cuánto se equivoca",
     "Si se compara un tramo que tuvo accidentes en 2024 con otro que no, el modelo da más "
     f"riesgo al primero en {acierto * 10:.0f} de cada 10 parejas "
     f"(ROC-AUC {estilo.num(acierto, 2)})."),
])

ui.panel_info(
    "Solo se comparan rutas del mismo tipo de vía. El índice mide la probabilidad de que un "
    "tramo registre algún accidente al año **con todo su tráfico**, así que una nacional "
    "vacía puntúa bajo aunque sea más peligrosa para quien pasa. Comparar una autovía con "
    "una nacional por este indicador daría la vuelta al resultado, y por eso no se ofrece.",
    etiqueta="Por qué el catálogo es corto")

# ------------------------------------------------------------------ tus rutas

ui.cabecera_seccion(
    "Tus propias rutas", "Sube un CSV y Baliza las puntúa y las ordena por riesgo.",
    eyebrow="Para flotas")

with ui.filtros("panel_carga"):
    c1, c2, c3 = st.columns([3, 1.3, 1.3], gap="medium", vertical_alignment="bottom")
    subido = c1.file_uploader("Tu tabla de rutas", type=["csv"])
    c2.download_button("Plantilla por ciudades",
                       datos.texto_csv(PLANTILLA_CIUDADES),
                       "plantilla_ciudades.csv", "text/csv", width="stretch",
                       icon=":material/download:")
    c3.download_button("Plantilla por tramos",
                       datos.texto_csv(PLANTILLA_TRAMOS),
                       "plantilla_tramos.csv", "text/csv", width="stretch",
                       icon=":material/download:")
    st.caption("Dos formatos, los dos con **coma** de separador. **origen, destino, paso, "
               "viajes_semana** resuelve el trayecto sobre los corredores; `paso` es opcional "
               "y obliga a que la ruta atraviese esa ciudad. El formato de tramos (provincia, "
               "carretera, PK, IMD, tipo de vía) ejecuta el modelo sobre tus propios datos. "
               "Puedes reordenar columnas, añadir las tuyas, quitar `paso` o `viajes_semana` "
               "y guardar desde Excel: el lector admite coma o punto y coma y decimales con "
               "coma.")

ui.panel_info(
    "La ruta que sale de un origen y un destino es la mejor que se puede armar con las "
    "carreteras que Baliza mide. Si tu trayecto real pasa por una vía que no está en la Red "
    "del Estado aforada, el kilometraje no coincidirá con el de un navegador: mira siempre la "
    "columna de kilómetros antes de dar por buena una ruta. Y entre dos rutas solo se compara "
    "cuando son del mismo tipo de vía, por la misma razón que en el catálogo de arriba.",
    etiqueta="Cómo leer estas rutas")

with st.expander(f"Las {len(datos.ciudades_red())} ciudades que puedes escribir"):
    st.write(", ".join(datos.ciudades_red()) + ".")
    st.caption("Son los hitos de los corredores. Si escribes otra cosa, la fila te lo dice y "
               "te propone la más parecida. Sirven igual para `origen`, `destino` y `paso`: "
               "por ejemplo Madrid → Sevilla con paso en Córdoba deja solo las rutas que "
               "pasan por allí.")

tabla = PLANTILLA_CIUDADES.copy()
if subido is not None:
    tabla, fallo = datos.leer_tabla_csv(subido)
    if fallo:
        ui.panel_info(fallo, aviso=True, etiqueta="Archivo no válido")
        st.stop()

por_ciudades = {"origen", "destino"} <= set(tabla.columns)
por_tramos = {"carretera", "pk_inicio", "pk_fin"} <= set(tabla.columns)
if not por_ciudades and not por_tramos:
    ui.panel_info(
        "El archivo no tiene ni las columnas **origen** y **destino** ni las del formato de "
        "tramos. Encabezados encontrados: "
        + ", ".join(f"`{c}`" for c in tabla.columns) + ". Descarga una plantilla y conserva "
        "sus encabezados.", aviso=True, etiqueta="Formato no reconocido")
    st.stop()

tabla = datos.numerizar(tabla)
if "viajes_semana" not in tabla.columns:
    tabla["viajes_semana"] = 1
viajes = pd.to_numeric(tabla["viajes_semana"], errors="coerce").fillna(1)
if por_ciudades and "paso" not in tabla.columns:
    tabla["paso"] = ""

if por_ciudades:
    criterio = st.selectbox("Ordenar por", list(ORDENES))
    campo, explicacion = ORDENES[criterio]
    st.caption(explicacion)

    filas, avisos = [], []
    for posicion, fila in enumerate(tabla.itertuples()):
        resultado = datos.resolver_trayecto(fila.origen, fila.destino,
                                            paso=getattr(fila, "paso", None))
        salida = {"Trayecto": f"{resultado['origen']} → {resultado['destino']}",
                  "forzado": resultado.get("paso") or "",
                  "viajes": float(viajes.iloc[posicion]), "Estado": resultado["estado"]}
        if resultado["estado"] == "Ciudad no reconocida":
            salida["Trayecto"] = f"{fila.origen} → {fila.destino}"
        if resultado.get("aviso"):
            avisos.append((resultado["estado"], resultado["aviso"]))
        ruta, alterna = resultado.get("mejor"), resultado.get("alternativa")
        if ruta:
            salida.update({
                "Ruta": " + ".join(ruta["vias"]),
                "paso": f"por {ruta['paso']}" if ruta["paso"] else "directa",
                "indice": ruta["indice"], "Km": ruta["km_declarados"],
                "exposicion": ruta["indice"] * float(viajes.iloc[posicion]),
                "Alternativa": (f"{' + '.join(alterna['vias'])} · índice "
                                f"{alterna['indice']:.0f}") if alterna else "—",
                "Ventaja": (_puntos(alterna["indice"] - ruta["indice"])
                            if alterna else "—"),
                "cobertura": ruta["cobertura"]})
        filas.append(salida)

    resultados = pd.DataFrame(filas)
    for columna in ("Ruta", "paso", "forzado", "Alternativa", "Ventaja"):
        if columna not in resultados:
            resultados[columna] = "—"
    for columna in ("indice", "Km", "exposicion", "cobertura"):
        if columna not in resultados:
            resultados[columna] = float("nan")
    resueltas = resultados[resultados.indice.notna()]
    resultados = resultados.sort_values(campo, ascending=False, na_position="last")

    st.write("")
    ui.rejilla([
        ui.tarjeta_cifra("Trayectos del archivo", str(len(resultados))),
        ui.tarjeta_cifra("Resueltos", str(len(resueltas)),
                         unidad=f"de {len(resultados)}",
                         pie="el resto no tiene ruta dentro de la red cubierta"),
        ui.tarjeta_cifra(
            "Índice medio", f"{resueltas.indice.mean():.0f}" if len(resueltas) else "—",
            ayuda="Media simple de los índices resueltos. 100 es la media nacional."),
    ])
    for estado, mensaje in dict(avisos).items():
        ui.panel_info(mensaje, aviso=estado != "Resuelta", etiqueta=estado)

    ui.tabla(resultados, [
        ui.columna("Trayecto", "Trayecto", "fuerte", secundario="paso"),
        ui.columna("forzado", "Paso obligado", "suave"),
        ui.columna("Ruta", "Ruta recomendada"),
        ui.columna("indice", "Índice", "num"),
        ui.columna("Km", "Km", "num"),
        ui.columna("viajes", "Viajes/semana", "num"),
        ui.columna("Alternativa", "Otra forma de ir", "suave"),
        ui.columna("Ventaja", "Lo que ahorra", "derecha"),
        ui.columna("Estado", "Estado", "suave"),
    ], ranking=True, ajustar=True)

    descarga = resultados.rename(columns={
        "indice": "indice_ruta", "Km": "km_recorrido", "viajes": "viajes_semana",
        "exposicion": "indice_por_viajes", "cobertura": "cobertura_aforo"})
    descarga["anio_modelo"] = datos.ANIO
    descarga["fecha_calculo"] = date.today().isoformat()
    st.download_button(
        "Descargar resultados",
        datos.texto_csv(descarga),
        f"baliza_rutas_{date.today():%Y-%m-%d}.csv", "text/csv",
        icon=":material/download:", on_click="ignore")

else:
    st.caption("Formato de tramos: aquí el modelo se ejecuta sobre tus datos, no sobre los "
               "nuestros. Puedes editar las filas antes de calcular.")
    tabla = st.data_editor(tabla, num_rows="dynamic", width="stretch", hide_index=True)
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
    prediccion["viajes_semana"] = viajes.to_numpy()
    prediccion["exposicion"] = (prediccion.PROB_ACCIDENTE_TRAMO_ANIO
                                * prediccion.viajes_semana)
    prediccion = prediccion.sort_values("exposicion", ascending=False)
    a_vigilar = int(prediccion.banda.isin(["Alto", "Muy alto"]).sum())
    ui.rejilla([
        ui.tarjeta_cifra("Tramos analizados", str(len(prediccion))),
        ui.tarjeta_cifra("En el 20 % con más riesgo de España", str(a_vigilar),
                         unidad=f"de {len(prediccion)}", pie="con nivel alto o muy alto"),
        ui.tarjeta_cifra("Peso del primero",
                         estilo.pct(prediccion.exposicion.iloc[0]
                                    / prediccion.exposicion.sum())
                         if prediccion.exposicion.sum() else "—",
                         ayuda="Qué parte del total se concentra en el tramo que encabeza "
                               "la lista.",
                         pie="de la suma de probabilidad × viajes"),
    ])
    vista = prediccion.copy()
    vista["Tramo"] = (vista.carretera + ", km "
                      + vista.pk_inicio_km.round().astype(int).astype(str) + " a "
                      + vista.pk_fin_km.round().astype(int).astype(str))
    vista["Riesgo"] = vista.banda.astype(str)
    vista["peor_que"] = vista.percentil.map(lambda v: f"{v:.0f} % de España")
    vista["fuera_rango"] = vista.FUERA_RANGO_TRAIN.map({True: "Sí", False: "No"})
    ui.tabla(vista, [
        ui.columna("Tramo", "Tramo", "fuerte", secundario="provincia"),
        ui.columna("viajes_semana", "Viajes/semana", "num"),
        ui.columna("PROB_ACCIDENTE_TRAMO_ANIO", "Probabilidad anual", "barra",
                   decimales=1, maximo=1),
        ui.columna("peor_que", "Peor que", "derecha"),
        ui.columna("Riesgo", "Nivel", "riesgo"),
        ui.columna("fuera_rango", "Fuera de rango", "suave"),
    ], ranking=True)

    paquete, _ = datos.modelo_tramos()
    version = " | ".join(str(paquete.get(c, ""))
                         for c in ("version_datos", "familia", "configuracion"))
    descarga = pd.DataFrame({
        "puesto": range(1, len(prediccion) + 1),
        "provincia": prediccion.provincia, "carretera": prediccion.carretera,
        "pk_inicio": prediccion.pk_inicio_km, "pk_fin": prediccion.pk_fin_km,
        "tipo_via": prediccion.tipo_via, "imd_total": prediccion.imd_total,
        "proporcion_pesados": prediccion.proporcion_pesados.round(4),
        "viajes_semana": prediccion.viajes_semana,
        "probabilidad_anual": prediccion.PROB_ACCIDENTE_TRAMO_ANIO.round(4),
        "percentil_2024": prediccion.percentil,
        "nivel": prediccion.banda.astype(str),
        "fuera_rango_entrenamiento": vista.fuera_rango,
        "version_modelo": version, "fecha_calculo": date.today().isoformat(),
    })
    st.download_button(
        "Descargar resultados",
        datos.texto_csv(descarga),
        f"baliza_tramos_{date.today():%Y-%m-%d}.csv", "text/csv",
        icon=":material/download:", on_click="ignore")

st.write("")
with st.expander("Cómo calculamos este indicador"):
    st.markdown(
        "**Índice de ruta.** Media de la probabilidad anual de cada tramo del recorrido, "
        "ponderada por los kilómetros que se hacen en él, dividida por la media nacional y "
        "multiplicada por 100. Es el mismo cálculo que en «Tu ruta», encadenando varias "
        "carreteras.")
    st.markdown(
        "**Probabilidad anual.** Estimación del modelo de que el tramo registre al menos un "
        "accidente con víctimas durante el año, con todo su tráfico. No es la probabilidad "
        "de que tú tengas un accidente al pasar.")
    st.markdown(
        "**Qué rutas se comparan.** Solo itinerarios cuyas dos opciones son del mismo tipo "
        "de vía y tienen al menos el "
        f"{estilo.pct(datos.COBERTURA_MINIMA_RUTA)} de sus kilómetros aforados. Por debajo "
        "de esa cobertura el índice se enseña, pero la ruta no se declara ganadora.")
    st.markdown(
        f"**Empate.** Por debajo de {estilo.num(datos.EMPATE_INDICE)} puntos de índice las "
        "dos rutas se dan por equivalentes, igual que en «Salir de noche».")
    st.markdown(
        "**Cómo se arma una ruta del CSV.** Se encadenan hasta cuatro carreteras y se descarta "
        "cualquier itinerario que se aleje más de un 30 % del más corto, que es lo que evita "
        "los rodeos. Los corredores son los de `corredores.json`, ampliados en "
        "`corredores_extra.json` con hitos deducidos del propio fichero de tramos: el primer y "
        "el último kilómetro aforado de cada carretera, y los cambios de provincia.")
    st.markdown(
        "**Paso obligado.** La columna `paso` del CSV deja solo las rutas que atraviesan esa "
        "ciudad. Se comprueba de verdad, no por los enlaces: la A-4 pasa por Córdoba sin "
        "cambiar de carretera, y aun así Madrid → Sevilla con paso en Córdoba la encuentra.")
    st.markdown(
        "**Formato de los ficheros.** Todo lo que la página descarga sale con coma de "
        "separador y punto decimal. Al leer se admite coma, punto y coma o tabulador, "
        "decimales con coma o con punto, acentos en UTF-8 o en Windows, y los encabezados en "
        "cualquier orden y en mayúsculas o minúsculas.")
    st.markdown(
        "**Qué no puede hacer.** Solo une ciudades que son hito de algún corredor, y solo por "
        "carreteras medidas. Cuando el enlace real entre dos ciudades no está en la red "
        "aforada, la ruta que sale es más larga que la que daría un navegador. Por eso los "
        "kilómetros van siempre a la vista.")
