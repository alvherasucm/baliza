"""07 Como funciona. Cuatro pasos y tres explicaciones sin una sola sigla, para
que el oyente pueda repetirlo despues con sus palabras. Lo tecnico va en un
desplegable: el tribunal son profesores haciendo de perfil de negocio."""
import streamlit as st

from baliza import datos, estilo

estilo.cabecera(st.session_state["paginas"])

st.subheader("Cómo funciona")

pasos = [
    ("Se junta lo que pasó con cuánta gente pasó",
     "Por un lado, todos los accidentes con víctimas de nueve años. Por otro, cuántos "
     "vehículos circulan cada día por cada trozo de carretera. Sin lo segundo, lo primero "
     "solo dice dónde hay tráfico."),
    ("Se parte España en trozos comparables",
     "Unos siete mil tramos, cada uno con su longitud, su tráfico y su tipo de vía. Un trozo "
     "de autovía en Madrid y uno de nacional en Soria dejan de ser incomparables."),
    ("Se aprende del pasado tapando el último año",
     "El sistema aprende con los años viejos y se examina con uno que no ha visto. Si acierta "
     "ahí, es que ha aprendido algo y no se ha limitado a memorizar."),
    ("Se devuelve una puntuación por trozo",
     "Y esa puntuación se puede pedir desde fuera, tramo a tramo, para que otro sistema la "
     "use al calcular una ruta."),
]
for i, (titulo, texto) in enumerate(pasos, start=1):
    st.markdown(f"**{i}. {titulo}**  \n{texto}")

st.divider()
st.markdown("**Tres cosas que conviene entender**")

with st.expander("Por qué se divide por el tráfico"):
    st.write(
        "Si cuentas accidentes a secas, el ranking te sale igual que el ranking de tráfico: "
        "arriba Madrid, Barcelona y Valencia. Eso no es un hallazgo, es aritmética. Dividiendo "
        "por los kilómetros que realmente se recorren, la pregunta cambia de dónde pasan más "
        "cosas a dónde es más peligroso cada kilómetro. Madrid tiene muchísimos accidentes y "
        "está entre las provincias con menos riesgo por kilómetro recorrido."
    )
with st.expander("Por qué un modelo y no una media"):
    st.write(
        "Una media dice lo que pasó. Un modelo separa cuánto de lo que pasó se explica por el "
        "tráfico, cuánto por el tipo de vía y cuánto por la provincia, y con eso puede puntuar "
        "un tramo del que todavía no sabemos nada: basta con decirle cuánto mide, por dónde "
        "va y cuánto tráfico tiene."
    )
with st.expander("Por qué probabilidad no es certeza"):
    st.write(
        "Que un tramo tenga riesgo alto no significa que vaya a pasar algo. Significa que si "
        "pusieras cien tramos como ese, en más de la mitad habría habido al menos un accidente "
        "este año. Es una herramienta para decidir dónde mirar primero, no un pronóstico."
    )

st.divider()
with st.expander("Detalle técnico"):
    ficha = datos.ficha_tramos()
    st.markdown(
        f"**Modelo de tramos.** {ficha['familia']}, unidad {ficha['unidad']}, objetivo "
        f"`{ficha['objetivo']}`. Predictores: {', '.join(ficha['predictores'])}. "
        f"Partición temporal: entrenamiento 2016-2022 sin 2020, validación 2023, test 2024 "
        f"({ficha['n_test_comun']:,} observaciones). ROC-AUC 0,834 en test.".replace(",", "."))
    st.markdown(
        "**Modelo de provincias.** Regresión binomial negativa con offset logarítmico de "
        "vehículos-kilómetro y efectos jerárquicos por región con encogimiento. La "
        "sobredispersión a nivel provincial es de 15,2, que es justo por lo que no vale "
        "una Poisson."
    )
    st.markdown(
        "**Modelo de gravedad.** CatBoost binario, leve frente a grave o mortal, sobre el "
        "accidente individual con 19 variables de condiciones. Score sin calibrar: se usa "
        "como orden relativo, nunca como probabilidad absoluta."
    )
    st.markdown(
        "**Reproducibilidad.** Python 3.12, scikit-learn 1.9.0, CatBoost 1.2.10. Las pruebas "
        "de integración de `pruebas/pruebas_integracion.py` comprueban que los tres modelos "
        "cargan y predicen en el mismo entorno antes de cada despliegue."
    )
