"""01 Inicio. Desactiva la objecion de cobertura antes de que nadie la formule."""
import streamlit as st

from baliza import datos, estilo

estilo.cabecera(st.session_state["paginas"])

tramos = datos.tramos_puntuados()
maestra = datos.maestra_completa()
m24 = maestra[maestra.ANYO == datos.ANIO]

st.subheader("El riesgo no está repartido")

orden = m24.sort_values("N_ACC", ascending=False)
corte = max(1, int(len(orden) * 0.10))
concentracion = orden.head(corte).N_ACC.sum() / orden.N_ACC.sum()

a, b, c = st.columns(3)
a.metric("De los accidentes de España", "11%",
         help="Accidentes con víctimas de 2016-2024 que ocurren en la red que medimos.")
b.metric("De los fallecidos de España", "24%",
         help="La misma red concentra uno de cada cuatro fallecidos a 30 días.")
c.metric("Accidentes en el 10% peor de tramos", f"{concentracion:.0%}",
         help=f"Calculado sobre los {len(m24):,} tramos de {datos.ANIO}.".replace(",", "."))

st.write(
    "Medimos la Red de Carreteras del Estado: interurbana, sin calles de ciudad y sin "
    "carreteras autonómicas. Es una parte del total y aun así es donde muere uno de cada "
    "cuatro fallecidos del país. Un accidente aquí es 2,2 veces más letal que la media "
    "nacional y 5,4 veces más que uno urbano."
)

estilo.nota(
    "Esta pantalla no toca nada, se lee. El problema está concentrado, y algo concentrado "
    "se puede abordar. Si la objeción de cobertura la plantea el tribunal, todo lo que "
    "venga después se escucha con sospecha."
)

st.divider()
st.subheader("Qué tienes delante")

izquierda, derecha = st.columns(2)
with izquierda:
    st.markdown(
        "**Dónde está el riesgo** → *Tu provincia*  \n"
        "**Por dónde vas a pasar tú** → *Tu ruta* y *Mapa de riesgo*  \n"
        "**Qué te puede costar** → *Salir de noche*"
    )
    st.caption("No es un orden narrativo. Es el orden en que alguien toma la decisión.")
with derecha:
    st.markdown(
        f"**{len(tramos):,}".replace(",", ".") + " tramos puntuados** en " f"{datos.ANIO}  \n"
        f"**{m24.LONGITUD.sum():,.0f} km".replace(",", ".") + " de red medida**  \n"
        f"**{m24.PROVINCIA.nunique()} provincias** peninsulares"
    )
    st.caption("Sin Baleares, Canarias ni las carreteras forales del País Vasco: "
               "no las afora el Estado.")
