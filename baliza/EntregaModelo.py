"""Genera de forma reproducible la entrega web del modelo de tramos v2.

No reentrena. Carga el artefacto v2, aplica su imputación aprendida a toda la
cobertura de 2024 y recalcula predicciones, etiquetas, métricas, referencias y
controles en una misma ejecución.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score, average_precision_score, brier_score_loss,
    confusion_matrix, f1_score, log_loss, precision_score, recall_score,
    roc_auc_score,
)

try:
    from .PrediccionTramos import predecir_tramos
except ImportError:  # Ejecución directa: python baliza/EntregaModelo.py ...
    from PrediccionTramos import predecir_tramos


VERSION = "v2 | Random Forest | Base"


def _metricas(y, score, umbral):
    pred = (score >= umbral).astype(int)
    tn, fp, fn, tp = confusion_matrix(y, pred).ravel()
    return {
        "Observaciones": int(len(y)), "Prevalencia": float(y.mean()),
        "ROC-AUC": float(roc_auc_score(y, score)),
        "Average precision": float(average_precision_score(y, score)),
        "Log-loss": float(log_loss(y, score)),
        "Brier": float(brier_score_loss(y, score)),
        "Accuracy": float(accuracy_score(y, pred)),
        "Precisión": float(precision_score(y, pred)),
        "Recall": float(recall_score(y, pred)), "F1": float(f1_score(y, pred)),
        "TN": int(tn), "FP": int(fp), "FN": int(fn), "TP": int(tp),
    }


def predecir_cobertura(entrada, paquete):
    """Puntúa las 7.250 filas con la imputación v2 guardada en el paquete."""
    salida = entrada.copy().reset_index(drop=True)
    salida["IMD_IMPUTADO"] = (
        salida.imd_total.isna() | salida.proporcion_pesados.isna())
    calculadas = predecir_tramos(salida, paquete).set_index("TRAMO_ID")
    for columna in (
        "PROB_ACCIDENTE_TRAMO_ANIO", "FUERA_RANGO_TRAIN",
        "INTERVALO_ID", "CLAVE_TRAMO_ANIO",
    ):
        salida[columna] = salida.TRAMO_ID.map(calculadas[columna])
    salida["ESTADO_PREDICCION"] = "OK"
    salida["VERSION_MODELO"] = VERSION
    if len(salida) != 7250 or salida.PROB_ACCIDENTE_TRAMO_ANIO.isna().any():
        raise ValueError("La v2 debe producir 7.250 probabilidades.")
    if int(salida.IMD_IMPUTADO.sum()) != 2:
        raise ValueError("Se esperaban exactamente dos tramos con IMD imputada.")
    return salida


def construir_entrega_v2(
    modelo, cobertura_base, test_v2, panel_v2, auditoria_v2, salida,
    ficha_base=None, metricas_base=None,
):
    """Genera todos los artefactos v2 y devuelve sus cifras de control."""
    modelo, cobertura_base, test_v2 = map(Path, (modelo, cobertura_base, test_v2))
    panel_v2, auditoria_v2, salida = map(Path, (panel_v2, auditoria_v2, salida))
    ficha_base = Path(ficha_base) if ficha_base else modelo.with_name("ficha_modelo.json")
    metricas_base = (Path(metricas_base) if metricas_base
                     else modelo.with_name("metricas_finales.csv"))
    for subdir in ("modelos", "datos", "baliza"):
        (salida / subdir).mkdir(parents=True, exist_ok=True)

    paquete = joblib.load(modelo)
    cobertura = pd.read_csv(cobertura_base, sep=";")
    test = pd.read_csv(test_v2, sep=";")
    panel = pd.read_csv(panel_v2, sep=";")
    auditoria = pd.read_csv(auditoria_v2, sep=";", low_memory=False)
    requeridas = [
        "TRAMO_ID", "anio", "provincia", "carretera", "pk_inicio_km",
        "pk_fin_km", "tipo_via", "imd_total", "proporcion_pesados",
    ]
    ausentes = sorted(set(requeridas) - set(cobertura.columns))
    if ausentes:
        raise ValueError(f"Faltan columnas en la cobertura: {ausentes}")
    pred = predecir_cobertura(cobertura, paquete)
    ids_test = set(test.TRAMO_ID)
    pred["EN_TEST_COMUN"] = pred.TRAMO_ID.isin(ids_test)
    motivos = (pred["MOTIVOS_EXCLUSION_EVALUACION"].fillna("")
               if "MOTIVOS_EXCLUSION_EVALUACION" in pred
               else pd.Series("FUERA_TEST_V2", index=pred.index))
    pred["MOTIVOS_EXCLUSION_EVALUACION"] = np.where(
        pred.EN_TEST_COMUN, "", motivos)
    if int(pred.EN_TEST_COMUN.sum()) != 6732:
        raise ValueError("El test v2 debe contener 6.732 tramos.")

    etiquetas = pred[["TRAMO_ID", "INTERVALO_ID"]].merge(
        test[["TRAMO_ID", "N_ACCIDENTES", "HUBO_ACCIDENTE"]],
        on="TRAMO_ID", how="left", validate="one_to_one")
    detalle = auditoria.loc[auditoria.anio.eq(2024)].set_index("TRAMO_ID")["tipo de via"]
    etiquetas["TIPO_VIA_DETALLE"] = etiquetas.TRAMO_ID.map(detalle)
    etiquetas["N_ACCIDENTES"] = pd.array(etiquetas.N_ACCIDENTES, dtype="Int64")
    etiquetas["HUBO_ACCIDENTE"] = pd.array(etiquetas.HUBO_ACCIDENTE, dtype="Int64")
    mascara_test = etiquetas.TRAMO_ID.isin(ids_test)
    if int(etiquetas.loc[mascara_test, "N_ACCIDENTES"].sum()) != 9661:
        raise ValueError("El test v2 debe sumar 9.661 accidentes.")
    if int(etiquetas.loc[mascara_test, "HUBO_ACCIDENTE"].sum()) != 3068:
        raise ValueError("El test v2 debe contener 3.068 positivos.")

    evaluacion = test.merge(
        pred[["TRAMO_ID", "PROB_ACCIDENTE_TRAMO_ANIO"]],
        on="TRAMO_ID", validate="one_to_one")
    y = evaluacion.HUBO_ACCIDENTE.astype(int)
    score = evaluacion.PROB_ACCIDENTE_TRAMO_ANIO.astype(float)
    umbral = float(paquete["umbral_descriptivo"])
    resumen = _metricas(y, score, umbral)
    anteriores = pd.read_csv(metricas_base, sep=";")
    anteriores = anteriores.loc[anteriores.Particion.ne("test")]
    filas_test = pd.DataFrame([
        {"Particion": "test", "Umbral": 0.5, **_metricas(y, score, 0.5)},
        {"Particion": "test", "Umbral": umbral, **resumen},
    ])
    metricas = pd.concat([anteriores, filas_test], ignore_index=True)

    previo = panel.loc[panel.anio.eq(2023), ["INTERVALO_ID", "N_ACCIDENTES"]]
    previo = previo.rename(columns={"N_ACCIDENTES": "historico"})
    evaluacion = evaluacion.merge(previo, on="INTERVALO_ID", how="left")
    sin_intervalo_2023 = int(evaluacion.historico.isna().sum())
    evaluacion["historico"] = evaluacion.historico.fillna(0)
    evaluacion["solo_trafico"] = evaluacion.log_imd_total

    def referencia(identificador, nombre, definicion, columna):
        return {
            "id": identificador, "nombre": nombre, "n": len(evaluacion),
            "definicion": definicion,
            "roc_auc": float(roc_auc_score(y, evaluacion[columna])),
            "average_precision": float(average_precision_score(y, evaluacion[columna])),
        }

    referencias = [
        referencia("modelo_final", "Modelo final",
                   "Probabilidad estimada por el Random Forest final v2.",
                   "PROB_ACCIDENTE_TRAMO_ANIO"),
        referencia("solo_trafico", "Solo tráfico",
                   "Ordena únicamente por la IMD total; en los dos tramos sin tráfico usa la misma imputación v2 del entrenamiento.",
                   "solo_trafico"),
        referencia("historico", "Histórico",
                   f"Ordena por el número de accidentes del mismo intervalo en 2023; {sin_intervalo_2023} de {len(evaluacion):,} tramos sin intervalo idéntico reciben valor cero.".replace(",", "."),
                   "historico"),
    ]
    nombres = {"Autopista_autovia": "Autopista o autovía",
               "Convencional": "Carretera convencional",
               "Multicarril": "Vía multicarril"}
    por_tipo = []
    for tipo, grupo in evaluacion.groupby("tipo_via_modelo"):
        objetivo = grupo.HUBO_ACCIDENTE.astype(int)
        por_tipo.append({
            "tipo_via": tipo, "nombre": nombres[tipo], "n": len(grupo),
            "modelo_final": {
                "roc_auc": float(roc_auc_score(objetivo, grupo.PROB_ACCIDENTE_TRAMO_ANIO)),
                "average_precision": float(average_precision_score(objetivo, grupo.PROB_ACCIDENTE_TRAMO_ANIO)),
            },
            "solo_trafico": {
                "roc_auc": float(roc_auc_score(objetivo, grupo.solo_trafico)),
                "average_precision": float(average_precision_score(objetivo, grupo.solo_trafico)),
            },
        })
    refs = {
        "conjunto": {"nombre": "Test v2 2024", "n": len(evaluacion),
                     "objetivo": "HUBO_ACCIDENTE", "prevalencia": float(y.mean()),
                     "version_modelo": VERSION},
        "referencias": referencias, "por_tipo_via": por_tipo,
        "proveniencia": {"etiquetas": test_v2.name,
                         "predicciones": "predicciones_tramos_2024.csv v2",
                         "criterio": "Mismas 6.732 observaciones para todas las referencias"},
    }

    ficha = json.loads(ficha_base.read_text(encoding="utf-8-sig"))
    ficha.update({
        "n_test_comun": 6732, "n_test_v2": 6732,
        "n_accidentes_test": 9661, "n_positivos_test": 3068,
        "n_cobertura": 7250,
        "estados_prediccion": {"OK": 7250, "DATOS_INSUFICIENTES": 0},
        "metricas": "Test v2 2024 sobre 6.732 tramos, incluidos dos con IMD imputada",
        "politica_faltantes": "IMD total y proporción de pesados se imputan por tipo de vía con parámetros aprendidos en entrenamiento; IMD_IMPUTADO identifica esos casos.",
        "fuente_cobertura": auditoria_v2.name,
        "fuente_sha256": hashlib.sha256(auditoria_v2.read_bytes()).hexdigest(),
    })
    control = {
        "version_modelo": VERSION, "tramos_cobertura": 7250,
        "tramos_test": 6732, "tramos_imd_imputada": 2,
        "accidentes_test": 9661, "positivos_test": 3068,
        "prevalencia": float(y.mean()), "roc_auc": resumen["ROC-AUC"],
        "average_precision": resumen["Average precision"],
    }

    pred.to_csv(salida / "datos" / "predicciones_tramos_2024.csv", sep=";",
                index=False, encoding="utf-8-sig")
    etiquetas.to_csv(salida / "datos" / "accidentes_tramos_2024.csv", sep=";",
                     index=False, encoding="utf-8-sig")
    metricas.to_csv(salida / "metricas_finales.csv", sep=";", index=False,
                    encoding="utf-8-sig")
    (salida / "datos" / "referencias_test_2024.json").write_text(
        json.dumps(refs, ensure_ascii=False, indent=2), encoding="utf-8")
    (salida / "datos" / "ficha_modelo.json").write_text(
        json.dumps(ficha, ensure_ascii=False, indent=2), encoding="utf-8")
    (salida / "cifras_control.json").write_text(
        json.dumps(control, ensure_ascii=False, indent=2), encoding="utf-8")
    shutil.copy2(modelo, salida / "modelos" / "modelo_final.joblib")
    for nombre in ("PrediccionTramos.py", "preparacion_tramos.py", "EntregaModelo.py"):
        origen = Path(__file__).with_name(nombre)
        destino = salida / "baliza" / nombre
        if origen.resolve() != destino.resolve():
            shutil.copy2(origen, destino)
    return control


def _argumentos():
    parser = argparse.ArgumentParser(description=__doc__)
    for nombre in ("modelo", "cobertura-base", "test-v2", "panel-v2",
                   "auditoria-v2", "salida"):
        parser.add_argument(f"--{nombre}", required=True)
    parser.add_argument("--ficha-base")
    parser.add_argument("--metricas-base")
    return parser.parse_args()


if __name__ == "__main__":
    args = _argumentos()
    print(json.dumps(construir_entrega_v2(
        modelo=args.modelo, cobertura_base=args.cobertura_base,
        test_v2=args.test_v2, panel_v2=args.panel_v2,
        auditoria_v2=args.auditoria_v2, salida=args.salida,
        ficha_base=args.ficha_base, metricas_base=args.metricas_base,
    ), ensure_ascii=False, indent=2))
