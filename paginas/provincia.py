"""04 Tu provincia. Diagnosticar y comparar, no adivinar. La prediccion pura es
lo mas atacable que tenemos, asi que va abajo y acompanada del reconocimiento
de cuanto mejora sobre no hacer nada. Los datos y cifras son de Miki; aqui solo
cambia la presentacion."""
import altair as alt
import streamlit as st

from baliza import componentes as ui
from baliza import datos, estilo

prov = datos.provincias()
ultimo = prov[prov.ANYO == prov.ANYO.max()].copy()
ultimo["puesto"] = ultimo.indice.rank(ascending=False).astype(int)

ui.cabecera_pagina(
    "Tu provincia",
    "El riesgo de tu provincia frente a la Red del Estado",
    "Compara el riesgo de una provincia con la media de la Red de Carreteras del Estado y mira "
    "cómo ha evolucionado.",
    meta=[("Año", str(int(prov.ANYO.max()))), ("Referencia", "Red del Estado = 100"),
          ("Serie", "2016-2024 sin 2020")],
)

# Solo provincias con dato en el ultimo anio: sin el, no hay diagnostico que ensenar
opciones = sorted(ultimo.PROV.unique())
pedida = st.session_state.pop("provincia_elegida", None)
if pedida in opciones:
    st.session_state["sel_provincia"] = pedida
elif st.session_state.get("sel_provincia") not in opciones:
    st.session_state["sel_provincia"] = "Madrid"

with ui.filtros():
    elegida = st.columns([1, 2])[0].selectbox("Provincia", opciones, key="sel_provincia")

serie = prov[prov.PROV == elegida].sort_values("ANYO")
fila = ultimo[ultimo.PROV == elegida].iloc[0]
anterior = serie[serie.ANYO < serie.ANYO.max()]
variacion = fila.indice - anterior.iloc[-1].indice if len(anterior) else 0

st.write("")
ui.rejilla([
    ui.tarjeta_cifra("Índice de riesgo", f"{fila.indice:.0f}",
                     ayuda="Media de la Red del Estado = 100. Por encima de 100, más "
                           "accidentes por kilómetro recorrido que la media de la red.",
                     delta=f"{'+' if variacion >= 0 else '−'}{estilo.num(abs(variacion))} "
                           "respecto al año anterior",
                     tono="malo" if variacion > 0 else "bueno"),
    ui.tarjeta_cifra("Puesto", f"{fila.puesto}.º", unidad=f"de {len(ultimo)} provincias",
                     pie="de más a menos riesgo relativo"),
    ui.tarjeta_cifra("Año", f"{int(fila.ANYO)}", pie="último año con datos"),
])
if fila.poca_cobertura:
    ui.panel_info(
        f"En {int(fila.ANYO)} solo entra en el cálculo el {estilo.pct(fila.COBERTURA_VEH_KM)} del "
        f"tráfico medido en la Red del Estado de {elegida}. En el resto de tramos no se pudieron "
        "situar todos los accidentes con seguridad y se dejaron fuera. Tómalo como una "
        "orientación, no como una comparación firme.", aviso=True, etiqueta="Poca cobertura")
mas_accidentes = ultimo.loc[ultimo.N_ACC.idxmax()]
ui.panel_info(
    f"El índice cuenta accidentes por vehículo-kilómetro, así que separa cuánto tráfico hay de "
    f"cómo de arriesgado es cada kilómetro. {mas_accidentes.PROV} es la provincia con más "
    f"accidentes de {int(mas_accidentes.ANYO)}, pero por kilómetro recorrido queda en el puesto "
    f"{mas_accidentes.puesto} de {len(ultimo)}, con índice {mas_accidentes.indice:.0f}.")

izquierda, derecha = st.columns([3, 2], gap="medium")

with izquierda:
    ui.cabecera_seccion("Cómo ha evolucionado",
                        "Falta 2020: el año del confinamiento distorsiona cualquier serie y se "
                        "excluye en todo el estudio.")
    evolucion = serie.assign(anio=serie.ANYO.astype(int).astype(str), nacional=100.0)
    base = alt.Chart(evolucion).encode(
        x=alt.X("anio:O", title=None, axis=alt.Axis(labelAngle=0)))
    linea = base.mark_line(color=estilo.PRIMARIO, strokeWidth=2.2).encode(
        y=alt.Y("indice:Q", title="Índice", scale=alt.Scale(zero=True)))
    puntos = base.mark_circle(color=estilo.PRIMARIO, size=40).encode(
        y="indice:Q", tooltip=[alt.Tooltip("anio:O", title="Año"),
                               alt.Tooltip("indice:Q", title=elegida, format=".0f")])
    referencia = base.mark_line(color=estilo.TINTA_TENUE, strokeDash=[4, 4],
                                strokeWidth=1.2).encode(y="nacional:Q")
    with ui.contenedor_grafico("evolucion"):
        st.caption(f"{elegida} · la línea discontinua es la media de la Red del Estado (100)")
        st.altair_chart(estilo.tema_altair((referencia + linea + puntos).properties(height=260)),
                        theme=None, use_container_width=True)
        flojos = serie[serie.poca_cobertura]
        if len(flojos):
            st.caption("Años con poca cobertura (menos del 60 % del tráfico medido): "
                       + ", ".join(str(int(a)) for a in flojos.ANYO) + ".")

with derecha:
    ui.cabecera_seccion("Quién mejora y quién empeora",
                        f"Cambio del índice entre {int(prov.ANYO.max()) - 1} y "
                        f"{int(prov.ANYO.max())}.")
    cambio = (prov.pivot_table(index="PROV", columns="ANYO", values="indice")
              .loc[:, [prov.ANYO.max() - 1, prov.ANYO.max()]].dropna())
    cambio["cambio"] = cambio.iloc[:, 1] - cambio.iloc[:, 0]
    cambio = cambio.reset_index()
    flojas = set(prov[prov.ANYO >= prov.ANYO.max() - 1].query("poca_cobertura").PROV)
    cambio["nota"] = cambio.PROV.map(lambda p: "Poca cobertura" if p in flojas else float("nan"))
    cambio["cambio_texto"] = cambio.cambio.map(
        lambda v: f"{'+' if v >= 0 else '−'}{estilo.num(abs(v), 1)}")
    for titulo, tabla in [("Mejoran", cambio.nsmallest(5, "cambio")),
                          ("Empeoran", cambio.nlargest(5, "cambio"))]:
        ui.tabla(tabla, [ui.columna("PROV", titulo, "fuerte", secundario="nota"),
                         ui.columna("cambio_texto", "Puntos", "derecha")])
        st.write("")

ui.cabecera_seccion("Previsión frente a lo que pasó", eyebrow="Modelo provincial")
if serie.pred_jerarquico.notna().any():
    ultima_pred = serie.dropna(subset=["pred_jerarquico"]).iloc[-1]
    error = abs(ultima_pred.pred_jerarquico - ultima_pred.N_ACC) / ultima_pred.N_ACC
    ui.panel_info(
        f"Para {int(ultima_pred.ANYO)} el modelo esperaba "
        f"**{estilo.num(ultima_pred.pred_jerarquico)}** accidentes en {elegida} y hubo "
        f"**{estilo.num(ultima_pred.N_ACC)}**. Se equivocó un **{estilo.pct(error)}**.")

metricas = datos.metricas_provincias()
ingenua, modelo = metricas.loc["pred_naive"], metricas.loc["pred_jerarquico"]
pred24 = datos.predicciones_provincias()
peor = pred24.loc[(pred24.N_ACC - pred24.pred_naive).abs().idxmax()]
ui.conclusiones([
    ("A ojo: repetir el año anterior",
     f"Si das por hecho que cada provincia repetirá los accidentes del año anterior, te "
     f"equivocas en {estilo.num(ingenua.mae, 1)} de media. Y hay fallos enormes: en "
     f"{peor.PROV} habrías esperado {estilo.num(peor.pred_naive)} y hubo "
     f"{estilo.num(peor.N_ACC)}."),
    (f"Con el modelo: {estilo.num(modelo.mae, 1)} de error",
     "El modelo tiene en cuenta el tráfico, la temperatura, los accidentes del año anterior "
     "y la región de cada provincia. Así el error medio baja a "
     f"{estilo.num(modelo.mae, 1)} accidentes."),
    (f"Cuánto mejora: un {estilo.pct(modelo.mejora_mae)}",
     "Donde más se nota es en los fallos grandes. El RMSE, la medida que más los castiga, baja "
     f"un {estilo.pct(modelo.mejora_rmse)}."),
])

# Prevision del anio siguiente. El titular es el indice sobre la tasa; el conteo
# va como detalle, nunca como cifra principal.
prevision = datos.prevision_provincias()
anio_prev = int(prevision.ANYO.iloc[0])
prevision["puesto"] = prevision.indice.rank(ascending=False, method="min").astype(int)
futura = prevision[prevision.PROV == elegida].iloc[0]
salto = futura.indice - futura.indice_anterior
if round(salto) == 0:
    flecha, tono = f"= igual que en {anio_prev - 1}", "neutro"
else:
    flecha = (f"{'↑ sube' if salto > 0 else '↓ baja'} {estilo.num(abs(salto))} puntos "
              f"frente a {anio_prev - 1}")
    tono = "malo" if salto > 0 else "bueno"

ui.cabecera_seccion(
    f"Previsión para {anio_prev}",
    f"La previsión da por hecho que el tráfico y la temperatura serán los de {anio_prev - 1}. "
    f"Álava y Bizkaia no tienen datos de {anio_prev - 1}, así que se quedan sin previsión.",
    eyebrow="Lo que viene")
ui.rejilla([
    ui.tarjeta_cifra(
        f"Índice previsto para {anio_prev}", f"{futura.indice:.0f}",
        ayuda="Accidentes esperados por kilómetro recorrido, comparados con el conjunto de "
              "provincias con previsión, que vale 100.",
        delta=flecha, tono=tono,
        extra=ui.cifras_compactas([
            (estilo.num(futura.N_ACC_ESPERADO), "accidentes esperados"),
            (estilo.num(futura.N_ACC_ANTERIOR), f"accidentes en {anio_prev - 1}"),
            (f"{futura.puesto}.º", f"de {len(prevision)} provincias"),
        ])),
    ui.tarjeta_texto(
        "De dónde sale",
        f"Con los datos de {elegida} en {anio_prev - 1}, el modelo estima los accidentes de "
        f"{anio_prev}. Esa cifra se divide entre los kilómetros recorridos, como en el índice "
        "de arriba, para que ninguna provincia salga peor solo por tener más tráfico. Cuando "
        f"tocó prever {anio_prev - 1}, el modelo se equivocó en {estilo.num(modelo.mae, 1)} "
        "accidentes de media por provincia."),
], plantilla="repeat(2, minmax(0, 1fr))")

if futura.poca_cobertura:
    ui.panel_info(
        f"La previsión usa el tráfico de {anio_prev - 1}, y ese año solo entró el "
        f"{estilo.pct(futura.COBERTURA_VEH_KM)} del tráfico medido en {elegida}.",
        aviso=True, etiqueta="Poca cobertura")
if futura.cautela:
    nota = (f"La previsión supone un {estilo.pct(abs(futura.cambio_acc))} "
            f"{'más' if futura.cambio_acc > 0 else 'menos'} de accidentes que en "
            f"{anio_prev - 1}. El modelo parte de lo que pasó el año anterior, y si ese año se "
            "salió de lo normal, la previsión puede exagerar el cambio.")
    if futura.N_ACC_ANTERIOR < 50:
        partida = ("un solo accidente" if futura.N_ACC_ANTERIOR == 1
                   else f"{estilo.num(futura.N_ACC_ANTERIOR)} accidentes")
        nota += f" Además, partiendo de {partida}, cualquier diferencia pesa mucho en porcentaje."
    ui.panel_info(nota, aviso=True, etiqueta="Tómalo con cautela")
