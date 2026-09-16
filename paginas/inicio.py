"""01 Inicio. Desactiva la objecion de cobertura antes de que nadie la formule:
el problema esta concentrado, y algo concentrado se puede abordar. Despues,
presenta el recorrido del producto."""
import streamlit as st

from baliza import componentes as ui
from baliza import datos, estilo

tramos = datos.tramos_puntuados()
maestra = datos.maestra_completa()
m24 = maestra[maestra.ANYO == datos.ANIO]

orden = m24.sort_values("N_ACC", ascending=False)
corte = max(1, int(len(orden) * 0.10))
concentracion = orden.head(corte).N_ACC.sum() / orden.N_ACC.sum()

ui.cabecera_pagina(
    "Inteligencia de riesgo vial",
    "El riesgo en carretera no está repartido",
    "Baliza puntúa cada tramo de la Red de Carreteras del Estado para saber dónde se "
    "concentra el riesgo antes de salir.",
    meta=[("Datos", "DGT 2016–2024"), ("Tramos puntuados", estilo.num(len(tramos))),
          ("Red medida", f"{estilo.num(m24.LONGITUD.sum())} km"),
          ("Cobertura", f"{m24.PROVINCIA.nunique()} provincias peninsulares")],
)

ui.rejilla([
    ui.tarjeta_cifra("De los accidentes de España", "11 %",
                     pie="ocurren en la red que medimos (2016–2024)"),
    ui.tarjeta_cifra("De los fallecidos de España", "24 %",
                     pie="uno de cada cuatro fallecidos a 30 días"),
    ui.tarjeta_cifra("Más letal que la media", "2,2", unidad="veces",
                     pie="y 5,4 veces más que un accidente urbano"),
    ui.tarjeta_cifra("Accidentes en el 10 % peor de tramos", estilo.pct(concentracion),
                     pie=f"calculado sobre {estilo.num(len(m24))} tramos de {datos.ANIO}"),
], plantilla="repeat(4, minmax(0, 1fr))")

# Mostrar la imagen
st.image("static/imagenes/accidente.jpg", use_container_width=True)

ui.cabecera_seccion("Qué puedes hacer con Baliza",
                    "En el orden en que alguien toma la decisión: dónde está el riesgo, por "
                    "dónde vas a pasar y qué te puede costar.")

MODULOS = [
    ("ruta", "Cuánto riesgo acumula un trayecto y dónde se concentra."),
    ("mapa", "Los tramos que más riesgo concentran, con filtros por criterio."),
    ("mapa_provincial", "Cómo se reparte el riesgo relativo entre provincias."),
    ("provincia", "El diagnóstico de una provincia frente a España."),
    ("noche", "Cuánto cambia la gravedad según cuándo y cómo sales."),
    ("flotas", "Puntúa las rutas de una empresa y pídelo desde tu sistema."),
    ("fiabilidad", "Cuánto acierta cada modelo y dónde están sus límites."),
    ("como", "Del dato en bruto a la puntuación de cada tramo."),
]
paginas = st.session_state.get("paginas", {})
for fila in range(0, len(MODULOS), 4):
    for columna, (clave, texto) in zip(st.columns(4, gap="small"), MODULOS[fila:fila + 4]):
        with columna, st.container(key=f"modulo_{clave}"):
            pagina = paginas.get(clave)
            if hasattr(pagina, "url_path"):
                st.page_link(pagina)
            else:
                st.markdown(f"**{clave}**")
            st.caption(texto)

st.write("")
with st.expander("Qué cubre Baliza"):
    st.markdown(
        "La Red de Carreteras del Estado: interurbana, sin calles de ciudad y sin carreteras "
        "autonómicas. Es una parte del total y aun así es donde muere uno de cada cuatro "
        "fallecidos del país. Sin Baleares, Canarias ni las carreteras forales del País Vasco: "
        "no las afora el Estado.")
