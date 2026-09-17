"""07 Como funciona. Cuatro pasos y tres explicaciones sin una sola sigla, para
que el oyente pueda repetirlo despues con sus palabras. Lo tecnico va en un
desplegable: el tribunal son profesores haciendo de perfil de negocio."""
import streamlit as st

from baliza import componentes as ui
from baliza import datos, estilo

ui.cabecera_pagina(
    "Cómo funciona",
    "De los datos a una puntuación por tramo",
    "Cómo se calcula cada número, en cuatro pasos.",
    meta=[("Modelos", "tramo · provincia · gravedad"), ("Validación", "test 2024")],
)

pasos = [
    ("Accidentes y tráfico, juntos",
     "Por un lado, los accidentes con víctimas de 2016 a 2024. Por otro, cuántos vehículos "
     "pasan cada día por cada tramo de carretera. Sin el tráfico, contar accidentes solo dice "
     "por dónde circula más gente."),
    ("La red se divide en tramos",
     "En 2024 son 7.250 tramos, cada uno con su longitud, su tráfico y su tipo de vía. Así se "
     "puede comparar un trozo de autovía en Madrid con uno de nacional en Soria."),
    ("El modelo aprende del pasado",
     "Se entrena con los años anteriores y se examina con 2024, que no ha visto. Si acierta "
     "ahí, ha aprendido algo más que memorizar los datos."),
    ("Cada tramo recibe una nota",
     "Es la probabilidad de que el tramo tenga al menos un accidente en el año. Con ella se "
     "construyen la ruta, el ranking de tramos y la página de flotas."),
]
ui.conclusiones(pasos, titulo="Cuatro pasos", eyebrow="El proceso", columnas=2)

ui.cabecera_seccion("Preguntas que suelen salir")

with st.expander("Por qué se divide por el tráfico"):
    prov = datos.provincias()
    anio = int(prov.ANYO.max())
    ultimo = prov[prov.ANYO == anio].assign(
        puesto=lambda d: d.indice.rank(ascending=False).astype(int))
    primeras = ultimo.nlargest(3, "N_ACC")
    nombres = ", ".join(primeras.PROV.iloc[:2]) + " y " + primeras.PROV.iloc[2]
    detalle = "; ".join(f"{f.PROV}, puesto {f.puesto} (índice {f.indice:.0f})"
                        for f in primeras.itertuples())
    st.write(
        f"Si solo cuentas accidentes, arriba salen las provincias con más tráfico: {nombres}. "
        "Eso refleja sobre todo por dónde circula más gente. Al dividir por los kilómetros "
        "recorridos, la pregunta pasa a ser cuánto riesgo tiene cada kilómetro, y el orden "
        f"cambia. En {anio}, de {len(ultimo)} provincias: {detalle}. España vale 100."
    )
with st.expander("Por qué un modelo y no una media"):
    st.write(
        "Una media resume lo que pasó en un tramo concreto. El modelo aprende cuánto pesan el "
        "tráfico, el tipo de vía, la longitud y la provincia, y con eso puede puntuar un tramo "
        "sin historial: basta con saber cuánto mide, en qué provincia está, qué tipo de vía es "
        "y cuánto tráfico tiene."
    )
with st.expander("Por qué probabilidad no es certeza"):
    st.write(
        "Un tramo con riesgo alto puede pasar el año sin accidentes. Lo que dice la nota es "
        "que, de cien tramos como ese, en la mayoría habría al menos uno. Sirve para decidir "
        "dónde mirar primero."
    )

ui.cabecera_seccion("Para quien quiera profundizar")
with st.expander("Detalle técnico"):
    ficha = datos.ficha_tramos()
    st.markdown(
        f"**Modelo de tramos.** {ficha['familia']}, unidad {ficha['unidad']}, objetivo "
        f"`{ficha['objetivo']}`. Predictores: {', '.join(ficha['predictores'])}. "
        f"Partición temporal: entrenamiento 2016-2022 sin 2020, validación 2023, test 2024 "
        f"({estilo.num(ficha['n_test_comun'])} observaciones). ROC-AUC 0,834 en test.")
    st.markdown(
        "**Modelo de provincias.** Regresión binomial negativa con offset logarítmico de "
        "vehículos-kilómetro y efectos jerárquicos por región con encogimiento. La "
        "sobredispersión provincial es de 15,2; por eso no sirve una Poisson."
    )
    st.markdown(
        "**Modelo de gravedad.** CatBoost binario, leve frente a grave o mortal, sobre el "
        "accidente individual con 19 variables de condiciones. La puntuación no está "
        "calibrada, así que solo se usa para ordenar."
    )
    st.markdown(
        "**Reproducibilidad.** Python 3.12, scikit-learn 1.9.0, CatBoost 1.2.10. "
        "`pruebas/pruebas_integracion.py` comprueba que los tres modelos cargan y predicen con "
        "esas versiones, y `pruebas/pruebas_paginas.py`, que las nueve páginas arrancan sin "
        "errores."
    )
