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
app.py                      entrada: tema, estilos, logotipo y menú superior (desde estilo.PAGINAS)
paginas/                    las nueve pantallas, una por fichero
baliza/datos.py             carga cacheada de datos y modelos (lógica, sin nada visual)
baliza/estilo.py            valores de diseño para Python, formato español y temas de gráficos
baliza/estilos.css          sistema visual: variables --bz-* y clases de los componentes
baliza/componentes.py       componentes de interfaz reutilizables
baliza/PrediccionTramos.py  inferencia del modelo de tramos (Anna)
baliza/validador_entrada.py validación de entradas de usuario (Jose)
baliza/predecir_provincia.py previsión del modelo de provincias (Miki)
datos/                      tablas y contratos de los tres modelos, más corredores_extra.json
                            y comparativas.json (nuestros, no del equipo)
modelos/                    modelo_final.joblib, modelo_gravedad.cbm y coeficientes_provincias.json
static/fuentes/             tipografía Inter servida por la propia app (licencia OFL)
static/marca/               logotipo e icono en SVG
pruebas/                    integración de los modelos, arranque de las páginas y auditoría de corredores
api/                        servicio FastAPI del modelo de tramos (Anna), fuera de la app
```

## Reglas de trabajo

- **Los ficheros del equipo no se editan.** Si un formato cambia, se adapta en
  `baliza/datos.py` y ninguna página se entera.
- **Nadie toca el código de la app salvo Álvaro y Jose.** Quien necesite un cambio, lo pide.
- **Antes de desplegar**, `python pruebas/pruebas_integracion.py` y
  `python pruebas/pruebas_paginas.py`. El primero comprueba que los tres modelos cargan y
  predicen en el mismo entorno; el segundo, que ninguna página lanza una excepción.
  Si cambia `datos/corredores.json`, además
  `python pruebas/auditar_corredores.py datos/predicciones_tramos_2024.csv datos/corredores.json`.
  Si cambia algo de `api/` o del modelo de tramos, además `python -m pytest api/test_api.py -q`.

## Versiones

El `modelo_final.joblib` está serializado con **scikit-learn 1.9.0**. Con 1.6.1 o 1.8.0 no
carga. Las versiones exactas están en `requirements.txt` y no se tocan sin volver a pasar
las pruebas de integración.

## Reglas de producto

- **Nada de conteos absolutos como titular.** Tasa por 100 millones de vehículos-kilómetro,
  índice con media nacional igual a 100, o categorías de riesgo. Un número absoluto es
  indefendible porque el universo es parcial.
- **El color nunca va solo.** Los niveles de riesgo van de verde apagado a rojo y llevan
  siempre la etiqueta de texto.
- **Cada pantalla que da un número** lleva al lado qué haría cualquiera a ojo, qué dice el
  modelo y cuánto se equivoca cada uno.
- **El score de gravedad no está calibrado**: se enseña como puesto («más grave que 68 de
  cada 100»), nunca como porcentaje de probabilidad ni como cociente entre dos escenarios.
- **La gravedad se compara con la red que cubre Baliza**: los 32.562 accidentes
  interurbanos peninsulares del test de 2024, no los 101.996 del test entero, que es en dos
  tercios urbano y puntúa más bajo. Fiabilidad da las dos columnas.
- **Gravedad se compara con escenarios completos.** El usuario elige bloques coherentes
  (`BLOQUES_GRAVEDAD` en `baliza/datos.py`), nunca una variable suelta: el modelo trabaja
  con combinaciones.

## Contrato de gravedad

`datos/` lleva, sin modificar, la entrega de Lourdes: `caso_default_2024.json`,
`scores_test_2024.csv`, `metricas_test_2024.json`, `labels_categorias.json` y
`feature_importance.json`.

- `scores_test_2024.csv`: 101.996 filas en el orden de la entrega, con `score_severo`,
  `severo_real` (0/1) e `interurbano_peninsular` (True/False). Con la etiqueta dentro, el
  banco de pruebas no se cree el fichero de métricas: lo recalcula.
- `interurbano_peninsular`, definido por Lourdes: `ZONA` = 1 (Carretera, que en el modelo se
  distingue de Travesía, Calle y Autopista o autovía urbana) y `COD_PROVINCIA` fuera de 7, 35,
  38, 51 y 52 (Balears, Las Palmas, Santa Cruz de Tenerife, Ceuta y Melilla). Ojo al
  redactar: `ZONA` no filtra por titularidad, así que el subconjunto incluye carreteras
  autonómicas y provinciales y deja fuera las travesías. No es el mismo universo que el del
  modelo de tramos, que sí es Red del Estado.
- `metricas_test_2024.json`: dos bloques, `global` e `interurbano_peninsular`, cada uno con
  la matriz de confusión entera al umbral 0,5. `baliza/datos.py` traduce los nombres y
  sigue leyendo el formato plano anterior por si hiciera falta volver atrás.
- Corrección del 17/09: el JSON anterior daba 32.145 alertas frente a las 30.944 del CSV
  porque venía de otra ejecución. Las cifras oficiales pasan a ser recall 68,37 %,
  precisión 22,14 %, ROC-AUC 0,7910 y PR-AUC 0,4108.
- Si llega `datos/caso_default_2024_interurbano.json` (o `..._carretera.json`), la pantalla
  lo usa como caso de referencia sin tocar código; mientras no exista, se usa el caso
  urbano trasladado a autovía.

## Contrato de provincias

Entrega de Miki, sin modificar: `baliza/predecir_provincia.py`, sus coeficientes en
`modelos/coeficientes_provincias.json` (en su entrega se llama `coeficientes.json`),
`datos/provincias_2016_2024.csv` y `datos/predicciones_2024_4modelos.csv`.

- La serie usa la misma base que la tabla de modelado v2 de Anna: 72.806 accidentes. No
  cuadra con `tabla_maestra.csv`, y no tiene por qué.
- La previsión del año siguiente arrastra el tráfico, la IMD y la temperatura del último
  año y usa sus accidentes reales como punto de partida. Álava y Bizkaia no tienen 2024 y
  se quedan sin previsión.
- El índice previsto se calcula sobre la tasa (accidentes esperados entre vehículos-km),
  como el histórico. Con el conteo, Madrid saldría arriba solo por tener más tráfico.
- Si la previsión cambia más de un 20 % respecto al año anterior, la pantalla añade una
  nota de cautela. El texto es nuestro; el umbral es el mismo que usa la función.
- `COBERTURA_VEH_KM`: parte del tráfico medido en la Red del Estado de cada provincia y año
  que sigue en la v2 tras las exclusiones. Por debajo de 0,60 (`UMBRAL_COBERTURA`), Tu
  provincia y el mapa avisan de «Poca cobertura». Son 20 de 358 provincias-año; en 2024,
  Málaga y Barcelona. La previsión del año siguiente hereda el aviso del último año.
- Los índices se rotulan «Red del Estado = 100», no «España = 100»: solo se mide esa red.
- Reproducibilidad: `App/Miki/Final 2` trae el notebook final, los scripts y
  `datos_provincia_anyo_v2.csv`, reconstruido con este CSV más la meteorología de AEMET.

## Diseño

Capas separadas: `datos.py` (datos y modelos) → `componentes.py` (interfaz) → `paginas/`.
Las páginas no escriben colores, CSS ni HTML: componen con los componentes.

| Componente | Uso |
|---|---|
| `cabecera_pagina` | antetítulo, título, propósito y datos de contexto reales |
| `cabecera_seccion` | título de bloque con descripción opcional |
| `tarjeta_cifra`, `tarjeta_destacada`, `pila`, `rejilla` | cifras clave |
| `conclusiones` | insights numerados; la metodología va en un desplegable |
| `etiqueta_riesgo` | nivel de riesgo, siempre con texto |
| `filtros`, `panel`, `contenedor_grafico` | superficies para controles, gráficos y mapas |
| `tabla`, `columna` | tabla de producto con números alineados y etiquetas |
| `panel_info`, `en_desarrollo`, `estado_vacio` | contexto, trabajo pendiente y estados vacíos |

Las nueve páginas: Inicio, Tu ruta, Comparar rutas, Riesgo por tramo, Mapa provincial, Tu
provincia, Salir de noche, Fiabilidad y Cómo funciona.

- Valores de diseño en un solo sitio: variables `--bz-*` de `estilos.css` (colores,
  espaciado 4/8/12/16/24/32/48/64, radios, sombras y tipografía) y `.streamlit/config.toml`.
- Fondo en capas (`#F3F2EE` → `#F8F7F4` → blanco), acento azul petróleo `#0F3D4C`.
- Niveles de riesgo (tema oscuro): `#58A58C` → `#D9A55B` → `#E8743F` → `#F2483F`. El verde
  de «Bajo» tira a azul para separarse de Medio y Alto también con daltonismo.
  Índices con media 100: petróleo por debajo, terracota por encima.
- Menú superior nativo (`st.navigation(position="top")`). El mapa provincial es 2D: con
  altura, unas provincias taparían a otras y la altura repetiría lo que ya dice el color.
- CSS con clases propias; los únicos ganchos de Streamlit son la cabecera, el contenedor
  principal y las clases `st-key-*` de los contenedores con clave.

## Tramos (Anna)

## Comparar rutas

`paginas/comparar.py` sustituye a la antigua hoja de Flotas. Para un mismo trayecto compara
las rutas posibles con el **mismo índice de ruta que «Tu ruta»**: la probabilidad anual de
cada tramo ponderada por los kilómetros que se recorren en él, con la media nacional en 100.
No hay indicador nuevo, y el cálculo vive una sola vez en `datos.evaluar_itinerario()`, que
usan las dos pantallas.

- **Solo se comparan rutas del mismo tipo de vía.** El índice mide el tramo con todo su
  tráfico, así que una nacional vacía puntúa bajo aunque sea peor para quien pasa: sin este
  filtro, Madrid–Sevilla recomendaría la N-630 frente a la A-66. En el catálogo la regla es
  curatorial; en el CSV la aplica `resolver_trayecto()` con `DIFERENCIA_TIPO_VIA`.
- **`datos/comparativas.json`** trae los trayectos del catálogo, cada uno con sus rutas y sus
  etapas `[carretera, PK de salida, PK de llegada]`. Entran solo pares con las dos rutas en
  autovía y al menos el 95 % de sus kilómetros aforados.
- **`datos/corredores_extra.json`** amplía los corredores de Jose sin tocar su fichero:
  `datos.corredores()` funde los dos y, cuando una ciudad está en los dos, manda su punto
  kilométrico. Cada hito que añadimos sale del propio fichero de tramos, no de una fuente
  externa: el primer o el último kilómetro aforado de la carretera, o un cambio de provincia.
  Los extremos son aproximaciones de unos pocos kilómetros al punto de la ciudad.
- **Por debajo de `COBERTURA_MINIMA_RUTA`** (90 % de kilómetros con aforo) el índice se
  enseña, pero la ruta no se declara ganadora. Por debajo de `EMPATE_INDICE` (8 puntos) las
  dos rutas se dan por equivalentes, igual que en «Salir de noche».
- **El CSV acepta dos formatos.** `origen, destino, paso, viajes_semana` resuelve el trayecto
  sobre los corredores y ordena por índice, o por índice × viajes; `paso` es opcional y obliga
  a que la ruta atraviese esa ciudad. El formato de tramos es el de la antigua hoja de Flotas y
  **ejecuta el modelo sobre los datos del usuario**, con la validación de Jose intacta: es la
  pieza de productivización y no se ha perdido.
- **Un solo formato de fichero.** Todo lo que la página descarga sale con coma de separador,
  punto decimal y BOM, que es lo que hace que Excel abra bien los acentos. `datos.texto_csv()`
  es el único sitio donde se escribe y `datos.leer_tabla_csv()` el único donde se lee. El
  lector quita el BOM (no hacerlo era lo que rompía la plantilla intacta: la primera columna
  llegaba como `\ufefforigen`), detecta coma, punto y coma o tabulador, admite UTF-8 y
  Windows-1252, normaliza los encabezados, acepta alias (`desde`, `hasta`, `por`,
  `frecuencia`), tolera columnas de más y en otro orden, y `datos.numerizar()` convierte los
  decimales con coma que devuelve Excel en español. `pruebas_integracion.py` comprueba el
  viaje de ida y vuelta de las dos plantillas.
- **El paso obligado se comprueba de verdad**, no por los enlaces: la A-4 atraviesa Córdoba sin
  cambiar de carretera, así que se mira si el PK de la ciudad cae dentro de algún tramo
  recorrido.
- **Límite conocido.** La ruta que sale de un origen y un destino es la mejor que se puede
  armar con las carreteras medidas. Cuando el enlace real entre dos ciudades no está en la red
  aforada (Zaragoza–Valencia, por ejemplo), el itinerario sale más largo que el de un
  navegador. Los kilómetros van siempre a la vista para que se note.

## Tramos (Anna)

Las cifras de acierto del modelo de tramos salen de `datos/referencias_test_2024.json`
(entrega de Anna, sin modificar): ROC-AUC del modelo, de ordenar solo por tráfico y de
ordenar por los accidentes del año anterior, sobre los 6.730 tramos del test común de 2024,
y el desglose por tipo de vía. Fiabilidad y Cómo funciona las leen de ahí; ninguna se
escribe a mano. `pruebas_integracion.py` comprueba que el JSON cuadra con la ficha y con el
modelo que se carga.

Las páginas «Tu ruta», «Riesgo por tramo», «Mapa provincial» y «Comparar rutas» siguen las
decisiones de `README_CAMBIOS.md` de Anna: tipos de vía con las tres categorías del modelo,
probabilidad anual en porcentaje, filtros del ranking, mapa lineal y coroplético
provincial. Cualquier cambio de lógica en estas páginas se consulta con ella antes.

## API

`api/` es un servicio FastAPI con el mismo modelo de tramos. La app no depende de él: es la
demostración de que el modelo se puede consumir desde fuera. Usa la única copia de los
ficheros del repositorio (`modelos/modelo_final.joblib`, `datos/ficha_modelo.json`,
`datos/predicciones_tramos_2024.csv` y `baliza/PrediccionTramos.py`) y no necesita
variables de entorno. Detalle y ejemplo en `api/README.md`.

Desde la raíz, con el entorno activado:

```bash
pip install -r api/requirements.txt
python -m uvicorn api.main:app --reload     # documentación en http://127.0.0.1:8000/docs
python -m pytest api/test_api.py -q
```

Streamlit Cloud solo instala `requirements.txt`, así que la API no cambia el despliegue.
