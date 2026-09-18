"""01 Inicio. Desactiva la objecion de cobertura antes de que nadie la formule:
el problema esta concentrado, y algo concentrado se puede abordar. Despues,
presenta el recorrido del producto."""
import streamlit as st

from baliza import componentes as ui
from baliza import datos, estilo

tramos = datos.tramos_puntuados()
con_recuento = tramos.dropna(subset=["N_ACC"])

orden = con_recuento.sort_values("N_ACC", ascending=False)
corte = max(1, int(len(orden) * 0.10))
concentracion = orden.head(corte).N_ACC.sum() / orden.N_ACC.sum()

ui.cabecera_pagina(
    "Riesgo vial",
    "El riesgo en carretera se concentra en pocos tramos",
    "Baliza puntúa cada tramo de la Red de Carreteras del Estado para que sepas dónde se "
    "acumula el riesgo antes de salir.",
    meta=[("Datos", "DGT 2016-2024"), ("Tramos puntuados", estilo.num(len(tramos))),
          ("Red medida", f"{estilo.num(tramos.longitud_km.sum())} km"),
          ("Cobertura", f"{tramos.provincia.nunique()} provincias peninsulares")],
)

ui.rejilla([
    ui.tarjeta_cifra("Accidentes de España", "11 %",
                     pie="ocurren en la red que medimos (2016-2024)"),
    ui.tarjeta_cifra("Fallecidos de España", "24 %",
                     pie="mueren en esa misma red (fallecidos a 30 días)"),
    ui.tarjeta_cifra("Letalidad frente a la media", "2,2", unidad="veces",
                     pie="y 5,4 veces la de un accidente urbano"),
    ui.tarjeta_cifra("Accidentes en solo el 10 % de los tramos", estilo.pct(concentracion),
                     pie=f"los {estilo.num(corte)} tramos con más accidentes, de los "
                         f"{estilo.num(len(con_recuento))} con recuento en {datos.ANIO}"),
], plantilla="repeat(4, minmax(0, 1fr))")

ui.imagen_portada(estilo.PORTADA_URL,
                 "Dos coches dañados tras un choque, junto a un cono de tráfico")

ui.cabecera_seccion("Qué puedes hacer con Baliza",
                    "Empieza por tu ruta. Desde ahí puedes bajar al detalle de un tramo, subir a "
                    "la provincia o comprobar cuánto fiarte de cada cifra.")

MODULOS = [
    ("ruta", "Cuánto riesgo acumula un trayecto y dónde se concentra."),
    ("comparar", "Dos formas de hacer el mismo viaje: cuál acumula menos riesgo."),
    ("mapa", "Ranking de tramos, con varios criterios para ordenarlos."),
    ("mapa_provincial", "El riesgo de cada provincia en un mapa, con la Red del Estado = 100."),
    ("provincia", "Una provincia frente a la media del país, año a año."),
    ("noche", "Cuánto cambia la gravedad según cuándo y cómo sales."),
    ("fiabilidad", "Cuánto acierta cada modelo y qué no puede hacer."),
    ("como", "Cómo se pasa de los datos de la DGT a la nota de cada tramo."),
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
        "Baliza cubre la Red de Carreteras del Estado, que es interurbana: no incluye calles "
        "ni carreteras autonómicas. Es solo una parte de la red, pero en ella muere uno de cada "
        "cuatro fallecidos del país. Tampoco entran Baleares, Canarias ni las carreteras forales "
        "de Navarra y el País Vasco, porque el Estado no mide su tráfico. De Navarra solo entra "
        "la AP-68, que sí es del Estado.")
