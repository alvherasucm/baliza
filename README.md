# Baliza

Sabes por dónde vas antes de salir.

Aplicación del TFM: sistema de riesgo vial sobre los microdatos de accidentes de la DGT
(2016-2024, sin 2020) cruzados con los aforos del Mapa de Tráfico del Ministerio.

## Arrancar en local

```bash
python -m venv .venv
.venv/Scripts/activate        # en Windows
pip install -r requirements.txt
streamlit run app.py
```

## Estructura

```
app.py                      navegación y entrada
paginas/                    las ocho pantallas, una por fichero
baliza/datos.py             carga cacheada de datos y modelos
baliza/estilo.py            marca, escala de riesgo y piezas comunes
baliza/PrediccionTramos.py  inferencia del modelo de tramos (Anna)
baliza/validador_entrada.py validación de entradas de usuario (Jose)
datos/                      tablas y contratos de los tres modelos
modelos/                    modelo_final.joblib y modelo_gravedad.cbm
pruebas/                    integración de los modelos y arranque de las páginas
```

## Reglas de trabajo

- **Los ficheros del equipo no se editan.** Si un formato cambia, se adapta en
  `baliza/datos.py` y ninguna página se entera.
- **Nadie toca el código de la app salvo Álvaro y Jose.** Quien necesite un cambio, lo pide.
- **Antes de desplegar**, `python pruebas/pruebas_integracion.py` y
  `python pruebas/pruebas_paginas.py`. El primero comprueba que los tres modelos cargan y
  predicen en el mismo entorno; el segundo, que ninguna página lanza una excepción.

## Versiones

El `modelo_final.joblib` está serializado con **scikit-learn 1.9.0**. Con 1.6.1 o 1.8.0 no
carga. Las versiones exactas están en `requirements.txt` y no se tocan sin volver a pasar
las pruebas de integración.

## Reglas de producto

- **Nada de conteos absolutos como titular.** Tasa por 100 millones de vehículos-kilómetro,
  índice con media nacional igual a 100, o categorías de riesgo. Un número absoluto es
  indefendible porque el universo es parcial.
- **El color nunca va solo.** La escala amarillo-rojo lleva siempre la etiqueta de texto.
- **Cada pantalla que da un número** lleva al lado qué haría cualquiera a ojo, qué dice el
  modelo y cuánto se equivoca cada uno.
- **El score de gravedad no está calibrado**: se enseña como puesto frente a los 101.996
  accidentes del test de 2024 («más grave que 68 de cada 100»), nunca como porcentaje de
  probabilidad ni como cociente entre dos escenarios.
- **Gravedad se compara con escenarios completos.** El usuario elige bloques coherentes
  (`BLOQUES_GRAVEDAD` en `baliza/datos.py`), nunca una variable suelta: el modelo trabaja
  con combinaciones.

## Contrato de gravedad

`datos/` lleva, sin modificar, la segunda entrega de Lourdes: `caso_default_2024.json`,
`scores_test_2024.csv`, `labels_categorias.json` y `feature_importance.json`. Si llega
`datos/caso_default_2024_carretera.json`, la pantalla lo usa como caso de referencia sin
tocar código; mientras no exista, se usa el caso urbano trasladado a autovía.
