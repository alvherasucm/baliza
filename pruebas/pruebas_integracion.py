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

# Fiabilidad lee estas cifras del JSON de Anna. Si una entrega nueva cambia la
# particion o el modelo, esto avisa antes de que la pagina diga otra cosa.
ficha = json.loads((DATOS / "ficha_modelo.json").read_text(encoding="utf-8"))
referencias = json.loads((DATOS / "referencias_test_2024.json").read_text(encoding="utf-8"))
filas = {fila["id"]: fila for fila in referencias["referencias"]}
test_comun = pred24[pred24.EN_TEST_COMUN.astype(str).str.lower().eq("true")]
comprobar("las referencias se miden sobre el test común de la ficha",
          referencias["conjunto"]["n"] == ficha["n_test_comun"] == len(test_comun)
          and all(fila["n"] == len(test_comun) for fila in filas.values()),
          f"{len(test_comun)} tramos")
comprobar("el desglose por tipo de vía reparte esos mismos tramos",
          {f["tipo_via"]: f["n"] for f in referencias["por_tipo_via"]}
          == test_comun.tipo_via.value_counts().to_dict())
comprobar("las referencias son del modelo que se carga",
          referencias["conjunto"]["version_modelo"] == " | ".join(
              str(paquete.get(c)) for c in ("version_datos", "familia", "configuracion")),
          referencias["conjunto"]["version_modelo"])
comprobar("el ROC-AUC del modelo es el de metricas_finales.csv",
          abs(filas["modelo_final"]["roc_auc"] - 0.8335427455512922) < 1e-12,
          f"{filas['modelo_final']['roc_auc']:.4f} frente a "
          f"{filas['solo_trafico']['roc_auc']:.4f} (tráfico) y "
          f"{filas['historico']['roc_auc']:.4f} (histórico)")
comprobar("el modelo supera a ordenar por tráfico en los tres tipos de vía",
          all(f["modelo_final"]["roc_auc"] > f["solo_trafico"]["roc_auc"]
              for f in referencias["por_tipo_via"]),
          "lo afirma la página de Fiabilidad")

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
from predecir_provincia import predecir_provincia
from baliza.datos import (COEFICIENTES_PROVINCIAS, metricas_provincias,
                          prevision_provincias)

miki = pd.read_csv(DATOS / "provincias_2016_2024.csv", sep=";", encoding="utf-8-sig")
entradas = ["N_ACC", "VEH_KM", "IMD_MEDIA", "TEMPERATURA_MEDIA_C"]
comprobar("358 filas y entradas del modelo completas",
          len(miki) == 358 and miki[entradas].notna().all().all(), f"{len(miki)} filas")

# Mismo universo que la tabla de modelado v2 de Anna (Tabla_Modelado_IMD_Tramo_Anio_v2),
# no que la tabla maestra. Si una entrega nueva cambia la fuente, esto avisa.
ACCIDENTES_V2 = {2016: 7588, 2017: 9207, 2018: 10639, 2019: 9242,
                 2021: 7834, 2022: 8610, 2023: 10025, 2024: 9661}
por_anio = {int(k): int(v) for k, v in miki.groupby("ANYO").N_ACC.sum().items()}
comprobar("accidentes por año iguales a la tabla de modelado de Anna",
          por_anio == ACCIDENTES_V2, f"{sum(por_anio.values()):,} en total")

coef = json.loads(COEFICIENTES_PROVINCIAS.read_text(encoding="utf-8"))
regiones = set(coef["provincia_a_region"].values()) - {coef["region_referencia"]}
comprobar("toda región del mapeo tiene coeficiente y ninguno sobra",
          regiones == set(coef["coeficientes"]["region"]))
comprobar("toda provincia del CSV está en el mapeo y tiene ajuste",
          set(miki.PROV) == set(coef["provincia_a_region"]) == set(coef["ajuste_por_provincia"]))

# Las predicciones del CSV salen de la funcion con las entradas del propio CSV.
# El lag es el ultimo anio disponible: 2021 usa 2019.
miki = miki.sort_values(["PROV", "ANYO"])
miki["LAG1"] = miki.groupby("PROV").N_ACC.shift(1)
con_pred = miki[miki.pred_jerarquico.notna()]
recalculo = [predecir_provincia(f.PROV, f.ANYO, f.VEH_KM, f.IMD_MEDIA / 1e4, f.LAG1,
                                f.TEMPERATURA_MEDIA_C, ruta_json=COEFICIENTES_PROVINCIAS)
             ["n_acc_esperado"] for f in con_pred.itertuples()]
diferencia = (pd.Series(recalculo, index=con_pred.index) - con_pred.pred_jerarquico).abs()
comprobar(f"las {len(con_pred)} predicciones del CSV se reproducen", diferencia.max() < 2,
          f"diferencia maxima {diferencia.max():.2f}, redondeo de coeficientes")

madrid = predecir_provincia("Madrid", 2025, veh_km=1.689e10, imd_10000=6.5213,
                            lag1_n_acc=1390, temperatura_media_c=15.38,
                            ruta_json=COEFICIENTES_PROVINCIAS)
comprobar("Madrid 2025 da la cifra confirmada por Miki y avisa del salto",
          abs(madrid["n_acc_esperado"] - 1745.4) < 0.1 and "+26%" in (madrid["aviso"] or ""),
          f"{madrid['n_acc_esperado']}")
try:
    predecir_provincia("Gipuzkoa", 2025, 1e9, 1, 10, 14, ruta_json=COEFICIENTES_PROVINCIAS)
    comprobar("Gipuzkoa se rechaza con un error explicado", False)
except ValueError:
    comprobar("Gipuzkoa se rechaza con un error explicado", True)

variantes = pd.read_csv(DATOS / "predicciones_2024_4modelos.csv", sep=";",
                        encoding="utf-8-sig")
cruce = variantes.merge(miki[miki.ANYO == 2024], on="PROV", suffixes=("", "_serie"))
comprobar("las 4 variantes cubren las mismas 44 provincias de 2024",
          len(variantes) == len(cruce) == 44 and cruce.N_ACC.eq(cruce.N_ACC_serie).all())
comprobar("la regla ingenua es el año anterior y el jerárquico coincide con la serie",
          cruce.pred_naive.eq(cruce.LAG1).all()
          and cruce.pred_jerarquico.eq(cruce.pred_jerarquico_serie).all())
errores = metricas_provincias()
print("  error en 2024 (MAE / RMSE): " + " · ".join(
    f"{f.clave.removeprefix('pred_')} {f.mae:.2f} / {f.rmse:.2f}" for f in errores.itertuples()))
comprobar("el jerárquico mejora a la regla ingenua en MAE y en RMSE",
          errores.mejora_mae["pred_jerarquico"] > 0 and errores.mejora_rmse["pred_jerarquico"] > 0,
          f"{errores.mejora_mae['pred_jerarquico']:.0%} y "
          f"{errores.mejora_rmse['pred_jerarquico']:.0%}")

prevision = prevision_provincias()
media = (prevision.indice * prevision.VEH_KM).sum() / prevision.VEH_KM.sum()
comprobar("la previsión cubre las 44 provincias con dato en 2024", len(prevision) == 44)
comprobar("el índice previsto se calcula sobre la tasa: su media ponderada por tráfico es 100",
          abs(media - 100) < 1e-9, f"{media:.6f}")
comprobar("Madrid en la previsión coincide con la función",
          abs(prevision.set_index("PROV").N_ACC_ESPERADO["Madrid"] - 1745.3) < 0.2,
          f"{int(prevision.cautela.sum())} provincias con nota de cautela")

titulo("RESUMEN")
print("Sin fallos: los tres modelos conviven en el mismo entorno."
      if not fallos else f"{len(fallos)} fallos: {fallos}")
sys.exit(1 if fallos else 0)
