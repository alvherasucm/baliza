"""Banco de pruebas de integracion. Se pasa antes de cada despliegue.

Comprueba que los tres paquetes del equipo cargan y predicen en el mismo
entorno. Si algo falla aqui, falla en produccion.
"""
import json
import sys
import time
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(RAIZ / "baliza"))

DATOS = RAIZ / "datos"
MODELOS = RAIZ / "modelos"
fallos = []


def titulo(texto):
    print(f"\n{'=' * 70}\n{texto}\n{'=' * 70}")


def comprobar(nombre, condicion, detalle=""):
    print(f"  [{'OK ' if condicion else 'FALLO'}] {nombre}{' | ' + detalle if detalle else ''}")
    if not condicion:
        fallos.append(nombre)


titulo("0. Entorno")
import numpy
import scipy
import sklearn
import joblib
import catboost

print(f"  python {sys.version.split()[0]} | sklearn {sklearn.__version__} | "
      f"numpy {numpy.__version__} | pandas {pd.__version__} | scipy {scipy.__version__} | "
      f"joblib {joblib.__version__} | catboost {catboost.__version__}")
comprobar("scikit-learn es 1.9.0, el del joblib de Anna", sklearn.__version__ == "1.9.0",
          "con 1.6.1 o 1.8.0 el paquete no carga")

titulo("1. Modelo de tramos (Anna)")
from validador_entrada import cargar_paquete_modelo, preparar_para_modelo, validar_tramos
from preparacion_tramos import predecir_tramos

inicio = time.time()
paquete, errores = cargar_paquete_modelo(MODELOS / "modelo_final.joblib")
comprobar("carga del joblib", not errores, f"{time.time() - inicio:.1f} s")
if errores:
    print("  ", errores[0])
    sys.exit(1)

pred24 = pd.read_csv(DATOS / "predicciones_tramos_2024.csv", sep=";", encoding="utf-8-sig")
muestra = pred24[pred24.ESTADO_PREDICCION.eq("OK")].head(200)
recalculo = predecir_tramos(
    muestra[["TRAMO_ID", "anio", "provincia", "carretera", "pk_inicio_km",
             "pk_fin_km", "tipo_via", "imd_total", "proporcion_pesados"]], paquete)
diferencia = (recalculo.PROB_ACCIDENTE_TRAMO_ANIO.values
              - muestra.PROB_ACCIDENTE_TRAMO_ANIO.values)
comprobar("200 tramos reales reproducen el CSV entregado", abs(diferencia).max() < 1e-9,
          f"diferencia maxima {abs(diferencia).max():.2e}")

ejemplo = pd.DataFrame([{"provincia": "Madrid", "carretera": "A-4", "pk_inicio": 4,
                         "pk_fin": 10, "imd_total": 65000, "imd_pesados": 6500,
                         "tipo_via": "Autopista_autovia"}])
validacion = validar_tramos(ejemplo, paquete)
comprobar("una fila nueva pasa el validador", validacion.valido)
salida = predecir_tramos(preparar_para_modelo(validacion.datos, anio=2024), paquete)
comprobar("y se predice", len(salida) == 1,
          f"probabilidad {salida.PROB_ACCIDENTE_TRAMO_ANIO.iloc[0]:.3f}")

print("  casos limite que la pantalla debe rechazar sin lanzar excepcion:")
for nombre, cambio in {"PK invertido": {"pk_inicio": 100, "pk_fin": 90},
                       "IMD cero": {"imd_total": 0},
                       "pesados mayores que el total": {"imd_pesados": 99999},
                       "tipo de via inventado": {"tipo_via": "Autopista"},
                       "provincia inexistente": {"provincia": "Lisboa"}}.items():
    fila = ejemplo.copy()
    for columna, valor in cambio.items():
        fila[columna] = valor
    resultado = validar_tramos(fila, paquete)
    comprobar(f"rechaza {nombre}", not resultado.valido,
              resultado.errores[0] if resultado.errores else "")

titulo("2. Modelo de gravedad (Lourdes)")
from catboost import CatBoostClassifier

meta = json.loads((DATOS / "metadata_gravedad.json").read_text(encoding="utf-8"))
modelo = CatBoostClassifier()
inicio = time.time()
modelo.load_model(str(MODELOS / "modelo_gravedad.cbm"))
comprobar("carga del .cbm", True, f"{time.time() - inicio:.1f} s")
comprobar("el modelo declara las 19 columnas del metadata",
          list(modelo.feature_names_) == meta["entrada"]["columnas"])

caso = pd.DataFrame([{c: meta["entrada"]["defaults"][c] for c in meta["entrada"]["columnas"]}])
for columna in meta["entrada"]["categoricas"]:
    caso[columna] = caso[columna].astype(str)
score = modelo.predict_proba(caso[meta["entrada"]["columnas"]])[0][1]
comprobar("predice un caso completo", 0 <= score <= 1, f"score Severo {score:.4f}")
comprobar("el caso por defecto del metadata NO es un caso medio", score > 0.8,
          "esperado: los defaults son la moda de cada variable y juntos puntuan alto. "
          "Por eso la pantalla usa su propio caso de referencia.")

print("  entrega 2: capa de interpretacion")
import numpy as np
import streamlit.logger

streamlit.logger.set_log_level("error")
from baliza.datos import BLOQUES_GRAVEDAD


def puntuar(escenarios):
    tabla = pd.DataFrame(escenarios)[meta["entrada"]["columnas"]]
    for columna in meta["entrada"]["categoricas"]:
        tabla[columna] = tabla[columna].astype(str)
    return modelo.predict_proba(tabla)[:, 1]


metricas = json.loads((DATOS / "metricas_test_2024.json").read_text(encoding="utf-8"))
scores = pd.read_csv(DATOS / "scores_test_2024.csv").score_severo
comprobar("scores del test completos y sin nulos",
          len(scores) == metricas["total_accidentes"] and scores.notna().all(),
          f"{len(scores):,} filas")
alertas = int((scores >= metricas["umbral"]).sum())
if alertas != metricas["alertas_totales"]:
    print(f"  [AVISO] {alertas:,} scores >= {metricas['umbral']} frente a "
          f"{metricas['alertas_totales']:,} alertas en las metricas: preguntado a Lourdes")

for nombre in ["caso_default_2024.json", "caso_default_2024_carretera.json"]:
    if not (DATOS / nombre).exists():
        continue
    referencia = json.loads((DATOS / nombre).read_text(encoding="utf-8"))
    esperado = referencia.pop("score_severo")
    obtenido = puntuar([referencia])[0]
    comprobar(f"{nombre} reproduce su score", abs(obtenido - esperado) < 1e-9,
              f"{obtenido:.8f}")

etiquetas = json.loads((DATOS / "labels_categorias.json").read_text(encoding="utf-8"))
sin_etiqueta = {v: sorted(set(meta["entrada"]["categorias"][v]) - set(etiquetas[v]))
                for v in etiquetas}
comprobar("toda categoria del modelo tiene etiqueta legible",
          not any(sin_etiqueta.values()), str({v: c for v, c in sin_etiqueta.items() if c}))

invalidos = [(bloque, opcion, variable, valor)
             for bloque, opciones in BLOQUES_GRAVEDAD.items()
             for opcion, valores in opciones.items()
             for variable, valor in valores.items()
             if valor not in meta["entrada"]["categorias"][variable]]
comprobar("los bloques de la pantalla solo usan categorias del modelo", not invalidos,
          str(invalidos[:3]))

# El texto de la pantalla afirma dos cosas del modelo. Si una entrega nueva las
# cambia, esta prueba avisa antes de que lo haga el tribunal.
fichero_base = next(DATOS / n for n in ["caso_default_2024_carretera.json",
                                        "caso_default_2024.json"] if (DATOS / n).exists())
base = json.loads(fichero_base.read_text(encoding="utf-8"))
base.pop("score_severo")
nombres = list(BLOQUES_GRAVEDAD)
combinaciones = [dict(zip(nombres, eleccion)) for eleccion in
                 pd.MultiIndex.from_product([list(BLOQUES_GRAVEDAD[b]) for b in nombres])]


def escenario(eleccion):
    caso_bloques = dict(base)
    for bloque, opcion in eleccion.items():
        caso_bloques.update(BLOQUES_GRAVEDAD[bloque][opcion])
    return caso_bloques


def comparar(bloque, peor, mejor):
    otros = [c for c in combinaciones if c[bloque] == mejor]
    s_mejor = puntuar([escenario(c) for c in otros])
    s_peor = puntuar([escenario({**c, bloque: peor}) for c in otros])
    return float(np.mean(s_peor > s_mejor))


lluvia = min(comparar("Tiempo", "Despejado", opcion)
             for opcion in ["Lluvia débil", "Lluvia fuerte", "Nieve"])
comprobar("con lluvia o nieve puntua menos grave en todas las combinaciones", lluvia == 1.0,
          f"{lluvia:.0%}")
noche = min(comparar("Momento del día", opcion, "Por la mañana (10:00)")
            for opcion in ["De noche (23:00)", "De madrugada (4:00)"])
comprobar("de noche o de madrugada puntua mas grave en la gran mayoria", noche >= 0.85,
          f"{noche:.0%} de las combinaciones")

titulo("3. Provincias (Miki)")
miki = pd.read_csv(DATOS / "provincias_2016_2024.csv", sep=";", encoding="utf-8-sig")
maestra = pd.read_csv(DATOS / "tabla_maestra.csv", sep=None, engine="python",
                      encoding="utf-8-sig")
agregado = maestra.groupby(["PROVINCIA", "ANYO"], as_index=False).agg(
    N_ACC_M=("N_ACC", "sum"), VEH_KM_M=("VEH_KM", "sum"))
cruce = miki.merge(agregado, left_on=["PROV", "ANYO"], right_on=["PROVINCIA", "ANYO"],
                   how="left")
comprobar("todas las filas existen en la maestra", cruce.N_ACC_M.notna().all())
comprobar("N_ACC cuadra", cruce.N_ACC.eq(cruce.N_ACC_M).all(),
          f"{int(cruce.N_ACC.eq(cruce.N_ACC_M).sum())}/{len(cruce)} filas")
comprobar("VEH_KM cuadra",
          ((cruce.VEH_KM - cruce.VEH_KM_M).abs() / cruce.VEH_KM_M).max() < 0.01)

titulo("RESUMEN")
print("Sin fallos: los tres modelos conviven en el mismo entorno."
      if not fallos else f"{len(fallos)} fallos: {fallos}")
sys.exit(1 if fallos else 0)
