"""
Prediccion productivizada del modelo jerarquico de accidentes por provincia.

No depende del notebook ni de rutas de Drive: solo necesita 'coeficientes.json'
en el mismo directorio (o pasar su ruta explicitamente).

Uso:
    from predecir_provincia import predecir_provincia
    n_acc = predecir_provincia("Cuenca", 2024, veh_km=2.1e9, imd_10000=1.15,
                                lag1_n_acc=110, temperatura_media_c=14.2)
"""
import json
import math
from pathlib import Path

_RUTA_JSON_POR_DEFECTO = Path(__file__).parent / "coeficientes.json"


def _cargar_coeficientes(ruta_json=_RUTA_JSON_POR_DEFECTO):
    with open(ruta_json, encoding="utf-8") as f:
        return json.load(f)


def predecir_provincia(
    provincia: str,
    anyo: int,
    veh_km: float,
    imd_10000: float,
    lag1_n_acc: float,
    temperatura_media_c: float,
    ruta_json=_RUTA_JSON_POR_DEFECTO,
) -> dict:
    """
    Predice el numero esperado de accidentes de una provincia en un anyo dado.

    Parametros
    ----------
    provincia : nombre de la provincia (debe existir en 'provincia_a_region'
                del JSON de coeficientes; ver aviso mas abajo si no aparece).
    anyo : anyo a predecir. SI afecta al calculo: se usa para derivar
           anyo_num = anyo - 2016, que entra en el predictor lineal con su
           propio coeficiente (tendencia temporal).
    veh_km : vehiculos-kilometro recorridos en el anyo (exposicion real).
    imd_10000 : IMD media del anyo, YA DIVIDIDA por 10000.
    lag1_n_acc : accidentes reales del anyo disponible anterior en esa
                 provincia (escala cruda, no logaritmica).
    temperatura_media_c : temperatura media del anyo, en grados Celsius.
                          NOTA: sustituye a la precipitacion de la version
                          anterior del modelo, que dejo de ser significativa
                          con esta fuente de datos.

    Devuelve
    --------
    dict con:
      - 'n_acc_esperado': prediccion puntual (float)
      - 'aviso': None, o un mensaje si la provincia no tiene ajuste propio
                 (histórico insuficiente o inexistente)
    """
    coef = _cargar_coeficientes(ruta_json)

    region = coef["provincia_a_region"].get(provincia)
    if region is None:
        raise ValueError(
            f"Provincia '{provincia}' no reconocida. Esto puede deberse a que "
            f"no tiene datos en la fuente (p.ej. Gipuzkoa) o a un nombre mal "
            f"escrito. Provincias validas: {sorted(coef['provincia_a_region'])}"
        )

    anyo_num = anyo - 2016  # coherente con como se entreno el modelo

    # --- Predictor lineal: intercepto + region + resto de variables -------
    c = coef["coeficientes"]
    region_referencia = coef["region_referencia"]
    if region == region_referencia:
        coef_region = 0.0  # la region de referencia no tiene coeficiente propio, por diseno
    elif region in c["region"]:
        coef_region = c["region"][region]
    else:
        raise ValueError(
            f"La region '{region}' (de la provincia '{provincia}') no tiene "
            f"coeficiente en 'coeficientes.region' ni es la region de referencia "
            f"('{region_referencia}'). Esto indica una inconsistencia entre "
            f"'provincia_a_region' y 'coeficientes.region' en el JSON -- revisar "
            f"antes de usar el resultado, NO se asume 0 en silencio. "
            f"Regiones con coeficiente: {sorted(c['region'])}"
        )

    log_mu_region = (
        c["intercept"]
        + coef_region
        + c["imd_10000"] * imd_10000
        + c["anyo_num"] * anyo_num
        + c["lag1_n_acc"] * lag1_n_acc
        + c["temperatura_media_c"] * temperatura_media_c
        + math.log(veh_km)  # el offset
    )
    pred_region = math.exp(log_mu_region)

    # --- Ajuste jerarquico por provincia (shrinkage) -----------------------
    ajuste = coef["ajuste_por_provincia"].get(provincia)
    aviso = None
    if ajuste is None:
        desviacion_encogida = 0.0
        aviso = (
            f"'{provincia}' no tiene ajuste jerarquico propio calculado "
            f"(historico insuficiente en el entrenamiento). Se devuelve la "
            f"prediccion basada solo en su region ({region}), sin encogimiento "
            f"individual."
        )
    else:
        desviacion_encogida = ajuste["desviacion_encogida"]
        if ajuste["n_anyos_historico"] < 3:
            aviso = (
                f"'{provincia}' tiene poco historico ({ajuste['n_anyos_historico']} "
                f"anyos), su ajuste individual (peso={ajuste['peso']:.2f}) se apoya "
                f"mas en la region que en su propio patron."
            )

    n_acc_esperado = pred_region * math.exp(desviacion_encogida)

    # --- Aviso de crecimiento fuerte: el lag en escala cruda no revierte a
    # la media, así que un ano anterior alto en una provincia grande puede
    # amplificar la extrapolacion (ver caso Madrid 2019 y 2025 documentado
    # con el equipo de la app). Se avisa, no se corrige el numero.
    crecimiento = n_acc_esperado / lag1_n_acc if lag1_n_acc > 0 else None
    if crecimiento is not None and (crecimiento > 1.20 or crecimiento < 0.80):
        nota_crecimiento = (
            f"La prevision implica un cambio del {(crecimiento-1)*100:+.0f}% "
            f"respecto al ano anterior. En provincias grandes, un ano anterior "
            f"alto o bajo de lo habitual puede amplificarse en la extrapolacion; "
            f"interpretar con cautela."
        )
        aviso = f"{aviso} {nota_crecimiento}" if aviso else nota_crecimiento

    return {"n_acc_esperado": round(n_acc_esperado, 1), "aviso": aviso}


if __name__ == "__main__":
    resultado = predecir_provincia(
        "Cuenca", 2024, veh_km=1.5e9, imd_10000=0.9,
        lag1_n_acc=100, temperatura_media_c=14.0,
    )
    print(resultado)
