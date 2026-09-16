"""05 Salir de noche. Simulador de condiciones: el sistema no solo senala sitios,
tambien momentos, que es lo unico sobre lo que el usuario puede actuar.

El score de CatBoost no esta calibrado y ademas los perfiles realistas puntuan
todos alto, asi que aqui nunca se ensena el numero crudo: se ensena la razon
entre dos salidas. Un cociente no obliga a aceptar ninguna premisa.
"""
import pandas as pd
import streamlit as st

from baliza import datos, estilo

estilo.cabecera(st.session_state["paginas"])

meta = datos.metadata_gravedad()
COLUMNAS = meta["entrada"]["columnas"]
CATEGORICAS = meta["entrada"]["categoricas"]

# Caso de referencia. No son los defaults del metadata: esa combinacion es la moda
# de cada variable por separado y junta puntua 0,907, el percentil 99 del modelo.
BASE = dict(meta["entrada"]["defaults"])
BASE.update({
    "FRANJA_HORARIA": "Tarde", "FIN_DE_SEMANA": "No", "ESTACION": "Primavera",
    "TIPO_VIA_AGRUPADO": "Autopista_Autovia", "TOTAL_VEHICULOS": 2.0,
})

EXPUESTAS = {
    "FRANJA_HORARIA": "Momento del día",
    "FIN_DE_SEMANA": "¿Fin de semana?",
    "ESTACION": "Estación",
    "TIPO_VIA_AGRUPADO": "Tipo de vía",
    "REGION": "Región",
}


def escenario(cambios: dict) -> float:
    caso = dict(BASE)
    caso.update(cambios)
    fila = pd.DataFrame([caso])[COLUMNAS]
    for columna in CATEGORICAS:
        fila[columna] = fila[columna].astype(str)
    return float(datos.modelo_gravedad().predict_proba(fila)[0][1])


st.subheader("Salir de noche")
st.caption("Dos salidas, mismas carreteras. Cuánto cambia que el accidente, si ocurre, "
           "sea grave o mortal.")

izquierda, derecha = st.columns(2)
salidas = {}
for columna, titulo, prefijo in [(izquierda, "Salida A", "a"), (derecha, "Salida B", "b")]:
    with columna:
        st.markdown(f"**{titulo}**")
        elegido = {}
        for variable, etiqueta in EXPUESTAS.items():
            opciones = meta["entrada"]["categorias"][variable]
            defecto = opciones.index(BASE[variable]) if BASE[variable] in opciones else 0
            if prefijo == "b" and variable == "FRANJA_HORARIA":
                defecto = opciones.index("Madrugada")
            elegido[variable] = st.selectbox(etiqueta, opciones, index=defecto,
                                             key=f"{prefijo}_{variable}")
        salidas[prefijo] = elegido

score_a, score_b = escenario(salidas["a"]), escenario(salidas["b"])
razon = score_b / score_a if score_a > 0 else float("nan")

st.divider()
a, b = st.columns([1, 2])
a.metric("Salida B frente a salida A", f"×{razon:.1f}")
with b:
    if razon >= 1.15:
        st.markdown(f"Con las condiciones de **B**, si hay un accidente es **{razon:.1f} veces "
                    f"más probable** que sea grave o mortal que con las de **A**.")
    elif razon <= 0.87:
        st.markdown(f"Las condiciones de **B** son **más seguras**: {1 / razon:.1f} veces menos "
                    f"probable que el accidente sea grave o mortal.")
    else:
        st.markdown("Las dos salidas son prácticamente equivalentes para el modelo.")

st.markdown("**Qué pesa más**")
pesos = []
for variable, etiqueta in EXPUESTAS.items():
    valores = meta["entrada"]["categorias"][variable]
    puntuaciones = {v: escenario({**salidas["a"], variable: v}) for v in valores}
    mejor, peor = min(puntuaciones, key=puntuaciones.get), max(puntuaciones, key=puntuaciones.get)
    pesos.append({"Factor": etiqueta, "Mejor caso": mejor, "Peor caso": peor,
                  "Cuánto multiplica": puntuaciones[peor] / max(puntuaciones[mejor], 1e-9)})
st.dataframe(pd.DataFrame(pesos).sort_values("Cuánto multiplica", ascending=False),
             hide_index=True, width="stretch",
             column_config={"Cuánto multiplica": st.column_config.NumberColumn(format="×%.2f")})

metricas = datos.metricas_gravedad()
estilo.contraste(
    a_ojo="De noche y con lluvia es peor. Todo el mundo lo sabe y nadie sabe cuánto.",
    modelo="El modelo pone una cifra al cuánto, condición a condición.",
    error=f"De cada 10 accidentes graves reales detecta 7, y de cada 10 avisos que da, "
          f"{metricas['precision_severo'] * 10:.0f} acaba siendo grave. Avisa de más a "
          f"propósito: no avisar de un grave cuesta más que avisar de más.",
)

estilo.nota(
    "El modelo estima la gravedad **dado que hay un accidente**. No dice que vayas a tener "
    "uno. Y el número que devuelve no está calibrado, por eso enseñamos cocientes entre dos "
    "salidas y no porcentajes."
)

estilo.pendiente(
    "Solo se pueden elegir cinco condiciones. El resto (meteorología, iluminación, trazado, "
    "estado del firme) llegan codificadas como 1, 2, 998 y no se pueden poner en un "
    "desplegable hasta que Lourdes mande los nombres legibles. También falta la distribución "
    "del score sobre el test de 2024 para poder decir en qué percentil cae un caso."
)
