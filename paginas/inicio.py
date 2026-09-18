"""01 Inicio. Desactiva la objecion de cobertura antes de que nadie la formule:
el problema esta concentrado, y algo concentrado se puede abordar. Despues,
presenta el recorrido del producto.

La cifra de concentracion se recalcula al abrir la pagina, como todas las de la
app: si Anna vuelve a generar las predicciones, el titular se mueve solo."""
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

ui.imagen_portada(estilo.PORTADA_URL,
                  "Dos coches dañados tras un choque, junto a un cono de tráfico")

# El titular y el mapa son la misma idea, asi que van en la misma fila: la frase
# a la izquierda y la prueba a la derecha. El mapa entra en un contenedor de
# grafico para que tenga la misma superficie, borde y aire que el resto de piezas
# visuales de la app, en vez de flotar suelto sobre el fondo.
# Tope de altura del mapa, calibrado para que con el desplegable abierto las dos
# columnas acaben a la misma altura.
ALTO_MAPA = 268

st.write("")
tesis, mapa = st.columns([1.2, 1], gap="medium", vertical_alignment="top")
with tesis:
    ui.rejilla([ui.tarjeta_destacada(
        "La concentración",
        f"{concentracion * 10:.0f} de cada 10 accidentes ocurren en el "
        f"{estilo.pct(0.10)} de los tramos",
    )], plantilla="1fr")
    # El desplegable vive aqui y no al final de la pagina: relleno el hueco que
    # dejaba la tarjeta, que es mucho mas baja que el mapa. Abierto, las dos
    # columnas quedan a la misma altura.
    with st.expander("Qué cubre Baliza"):
        st.markdown(
            "Baliza cubre la Red de Carreteras del Estado, que es interurbana: no incluye "
            "calles ni carreteras autonómicas. Es solo una parte de la red, pero en ella "
            "muere uno de cada cuatro fallecidos del país. Tampoco entran Baleares, Canarias "
            "ni las carreteras forales de Navarra y el País Vasco, porque el Estado no mide "
            "su tráfico. De Navarra solo entra la AP-68, que sí es del Estado.")
with mapa:
    with ui.contenedor_grafico("mapa_concentracion"):
        # El tope de altura cuadra el mapa con la columna de la izquierda cuando el
        # desplegable esta abierto: la imagen se encoge y se centra, no se recorta.
        ui.imagen(estilo.MAPA_CONCENTRACION,
                  "Mapa de la Red de Carreteras del Estado con el 10 % de tramos de mayor "
                  "siniestralidad resaltados en rojo", alto_maximo=ALTO_MAPA)
        st.caption(
            f"Red de Carreteras del Estado en {datos.ANIO}. En rojo, el "
            f"{estilo.pct(0.10)} de tramos con más accidentes; en gris, el resto de la red "
            "que Baliza mide.")

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
