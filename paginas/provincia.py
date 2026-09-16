"""04 Tu provincia. Diagnosticar y comparar, no adivinar. La prediccion pura es
lo mas atacable que tenemos, asi que va abajo y acompanada del reconocimiento
de cuanto mejora sobre no hacer nada."""
import streamlit as st

from baliza import datos, estilo

estilo.cabecera(st.session_state["paginas"])

prov = datos.provincias()
ultimo = prov[prov.ANYO == prov.ANYO.max()].copy()
ultimo["puesto"] = ultimo.indice.rank(ascending=False).astype(int)

st.subheader("Tu provincia")
elegida = st.selectbox("Provincia", sorted(prov.PROV.unique()),
                       index=sorted(prov.PROV.unique()).index("Madrid"))

serie = prov[prov.PROV == elegida].sort_values("ANYO")
fila = ultimo[ultimo.PROV == elegida].iloc[0]
anterior = serie[serie.ANYO < serie.ANYO.max()]
variacion = fila.indice - anterior.iloc[-1].indice if len(anterior) else 0

a, b, c = st.columns(3)
a.metric("Índice de riesgo", f"{fila.indice:.0f}",
         delta=f"{variacion:+.0f} respecto al año anterior", delta_color="inverse",
         help="Media nacional = 100. Por encima de 100, más accidentes por kilómetro "
              "recorrido que la media del país.")
b.metric("Puesto en España", f"{fila.puesto} de {len(ultimo)}")
c.metric("Año", f"{int(fila.ANYO)}")

st.caption(
    "El índice compara accidentes por vehículo-kilómetro, no accidentes a secas. "
    "Madrid tiene muchísimos accidentes en total y aun así está entre las provincias con "
    "menos riesgo por kilómetro recorrido: es lo que pasa cuando separas cuánto tráfico "
    "hay de cómo de arriesgado es cada kilómetro."
)

st.divider()
izquierda, derecha = st.columns([3, 2])

with izquierda:
    st.markdown("**Cómo ha evolucionado**")
    grafico = serie.set_index("ANYO")[["indice"]].rename(columns={"indice": elegida})
    grafico["Media nacional"] = 100
    st.line_chart(grafico, height=260, color=["#b5332a", "#d1d5db"])
    st.caption("Falta 2020: el año del confinamiento distorsiona cualquier serie y se "
               "excluye en todo el estudio.")

with derecha:
    st.markdown("**Quién mejora y quién empeora**")
    cambio = (prov.pivot_table(index="PROV", columns="ANYO", values="indice")
              .loc[:, [prov.ANYO.max() - 1, prov.ANYO.max()]].dropna())
    cambio["cambio"] = cambio.iloc[:, 1] - cambio.iloc[:, 0]
    mejor = cambio.nsmallest(5, "cambio")[["cambio"]].round(1)
    peor = cambio.nlargest(5, "cambio")[["cambio"]].round(1)
    st.dataframe(mejor.rename(columns={"cambio": "Mejora"}), width="stretch")
    st.dataframe(peor.rename(columns={"cambio": "Empeora"}), width="stretch")

st.divider()
st.subheader("Lo que viene")

if serie.pred_jerarquico.notna().any():
    ultima_pred = serie.dropna(subset=["pred_jerarquico"]).iloc[-1]
    error = abs(ultima_pred.pred_jerarquico - ultima_pred.N_ACC) / ultima_pred.N_ACC
    st.write(
        f"Para {int(ultima_pred.ANYO)} el modelo esperaba **{ultima_pred.pred_jerarquico:,.0f}** "
        f"accidentes en {elegida} y hubo **{ultima_pred.N_ACC:,.0f}**. "
        f"Se equivocó un **{error:.0%}**.".replace(",", "."))

estilo.contraste(
    a_ojo="El año que viene se parecerá al pasado. Es la regla ingenua y acierta mucho: "
          "error medio de 21,6 accidentes por provincia.",
    modelo="Modelo jerárquico con exposición: error medio de 18,3.",
    error="Mejoramos un 15% sobre no hacer nada, no un 80%. A nivel provincial la inercia "
          "histórica manda casi por completo y conviene decirlo antes de que lo digan.",
)

estilo.pendiente(
    "El fichero de Miki trae la predicción de cada año pasado, no la de 2025. Para que esta "
    "sección prediga de verdad hace falta que nos pase la previsión del año siguiente, y el "
    "MAE de sus cuatro variantes para poder enseñar la comparación completa."
)
