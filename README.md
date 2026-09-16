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
- **El score de gravedad no está calibrado**: se enseña como cociente entre dos escenarios,
  nunca como porcentaje.
