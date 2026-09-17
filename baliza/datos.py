"""Capa de datos y modelos. Todo lo que lee de disco pasa por aqui y se cachea.

Regla de la app: los ficheros del equipo no se tocan. Si un formato cambia, se
adapta en este modulo y ninguna pagina se entera.
"""
from pathlib import Path
import json
import sys

import numpy as np
import pandas as pd
import streamlit as st

RAIZ = Path(__file__).resolve().parent.parent
DATOS = RAIZ / "datos"
MODELOS = RAIZ / "modelos"

sys.path.insert(0, str(RAIZ / "baliza"))

ANIO = 2024

# Modelo de provincias de Miki: coeficientes en JSON y la funcion en
# baliza/predecir_provincia.py, los dos sin modificar.
COEFICIENTES_PROVINCIAS = MODELOS / "coeficientes_provincias.json"
# Mismo corte que el aviso de crecimiento de la funcion de Miki
UMBRAL_CAUTELA = 0.20
VARIANTES_PROVINCIAS = {
    "pred_naive": ("Repetir el año anterior",
                   "Los accidentes del año anterior, tal cual"),
    "pred_explicativo": ("Explicativo",
                         "Tráfico, región, año y temperatura, sin mirar el año anterior"),
    "pred_predictivo": ("Predictivo",
                        "Lo mismo, más los accidentes del año anterior"),
    "pred_jerarquico": ("Jerárquico (el de esta web)",
                        "El predictivo, con un ajuste propio para cada provincia"),
}

# Nombres descriptivos de la maestra frente a las tres categorias del modelo de Anna
TIPO_VIA_MODELO = {
    "Autopista libre y autovía": "Autopista_autovia",
    "Autopista de peaje": "Autopista_autovia",
    "Autovía": "Autopista_autovia",
    "Multicarril": "Multicarril",
    "Convencional": "Convencional",
}

# Las categorias que entiende el modelo son mas amplias que las descripciones
# administrativas de la tabla maestra. La interfaz usa estos tres nombres para
# no presentar como clases distintas variantes que el modelo trata igual.
TIPO_VIA_PRESENTACION = {
    "Autopista_autovia": "Autopista o autovía",
    "Multicarril": "Vía multicarril",
    "Convencional": "Carretera convencional",
}

# Codigo provincial del INE, usado para enlazar los indicadores del proyecto
# con la geometria del mapa. El enlace por codigo evita problemas con nombres
# bilingues como Araba/Alava o Alacant/Alicante.
CODIGO_PROVINCIA = {
    "Álava": "01", "Albacete": "02", "Alicante": "03", "Almería": "04",
    "Ávila": "05", "Badajoz": "06", "Barcelona": "08", "Burgos": "09",
    "Cáceres": "10", "Cádiz": "11", "Castellón": "12", "Ciudad Real": "13",
    "Córdoba": "14", "A Coruña": "15", "Cuenca": "16", "Girona": "17",
    "Granada": "18", "Guadalajara": "19", "Huelva": "21", "Huesca": "22",
    "Jaén": "23", "León": "24", "Lleida": "25", "La Rioja": "26",
    "Lugo": "27", "Madrid": "28", "Málaga": "29", "Murcia": "30",
    "Navarra": "31", "Ourense": "32", "Asturias": "33", "Palencia": "34",
    "Pontevedra": "36", "Salamanca": "37", "Cantabria": "39", "Segovia": "40",
    "Sevilla": "41", "Soria": "42", "Tarragona": "43", "Teruel": "44",
    "Toledo": "45", "Valencia": "46", "Valladolid": "47", "Bizkaia": "48",
    "Zamora": "49", "Zaragoza": "50",
}


@st.cache_data(show_spinner=False)
def tramos_puntuados() -> pd.DataFrame:
    """Los 7.250 tramos de 2024 con la probabilidad del modelo de Anna y el
    contexto de la maestra (accidentes, longitud, tasa por 100 M veh-km)."""
    pred = pd.read_csv(DATOS / "predicciones_tramos_2024.csv", sep=";", encoding="utf-8-sig")
    maestra = maestra_completa()
    m24 = maestra[maestra.ANYO == ANIO].copy()
    m24["clave"] = _clave(m24.PROVINCIA, m24.VIA_NORM, m24.PK_INICIO, m24.PK_FIN)
    pred["clave"] = _clave(pred.provincia, pred.carretera, pred.pk_inicio_km, pred.pk_fin_km)

    df = pred.merge(
        m24[["clave", "TIPO_VIA", "LONGITUD", "VEH_KM", "N_ACC", "TASA_100M"]],
        on="clave", how="left")
    df["longitud_km"] = df.pk_fin_km - df.pk_inicio_km
    df["acc_por_km"] = df.N_ACC / df.longitud_km.replace(0, np.nan)
    df["tipo_via_presentacion"] = (
        df["tipo_via"].map(TIPO_VIA_PRESENTACION).fillna("Tipo de vía no disponible")
    )
    df["tipo_via_detalle"] = df["TIPO_VIA"]
    df["banda"] = banda_riesgo(df.PROB_ACCIDENTE_TRAMO_ANIO)
    df["percentil"] = percentil_2024(df.PROB_ACCIDENTE_TRAMO_ANIO)
    return df


@st.cache_data(show_spinner=False)
def maestra_completa() -> pd.DataFrame:
    return pd.read_csv(DATOS / "tabla_maestra.csv", sep=None, engine="python",
                       encoding="utf-8-sig")


@st.cache_data(show_spinner=False)
def provincias() -> pd.DataFrame:
    """Serie provincia-anio de Miki con el indice base 100 ya calculado.

    Mismo universo que la tabla de modelado v2 de Anna (72.806 accidentes), no
    que la tabla maestra. El indice es la tasa por 100 M veh-km de la provincia
    dividida por la media nacional del mismo anio. Nunca se ensena el conteo
    absoluto como titular.
    """
    df = pd.read_csv(DATOS / "provincias_2016_2024.csv", sep=";", encoding="utf-8-sig")
    df["tasa"] = df.N_ACC / df.VEH_KM * 1e8
    nacional = df.groupby("ANYO").apply(
        lambda g: g.N_ACC.sum() / g.VEH_KM.sum() * 1e8, include_groups=False)
    df["tasa_nacional"] = df.ANYO.map(nacional)
    df["indice"] = df.tasa / df.tasa_nacional * 100
    return df


@st.cache_data(show_spinner=False)
def prevision_provincias() -> pd.DataFrame:
    """Prevision de Miki para el anio siguiente al ultimo con datos.

    Supuesto de la entrega: VEH_KM, IMD y temperatura se arrastran del ultimo
    anio y el lag son sus accidentes reales. Solo entran las provincias con dato
    ese anio (Alava y Bizkaia se quedan fuera).

    El indice se calcula sobre la tasa, igual que la serie historica: esperados
    entre VEH_KM de la provincia, frente a esperados entre VEH_KM del conjunto.
    Sobre el conteo, Madrid saldria arriba solo por tener mas trafico.
    """
    from predecir_provincia import predecir_provincia

    serie = provincias()
    ultimo = serie[serie.ANYO == serie.ANYO.max()]
    anio = int(ultimo.ANYO.iloc[0]) + 1
    esperados = [
        predecir_provincia(f.PROV, anio, veh_km=f.VEH_KM, imd_10000=f.IMD_MEDIA / 1e4,
                           lag1_n_acc=f.N_ACC, temperatura_media_c=f.TEMPERATURA_MEDIA_C,
                           ruta_json=COEFICIENTES_PROVINCIAS)["n_acc_esperado"]
        for f in ultimo.itertuples()
    ]
    df = pd.DataFrame({
        "PROV": ultimo.PROV.to_numpy(),
        "ANYO": anio,
        "N_ACC_ESPERADO": esperados,
        "VEH_KM": ultimo.VEH_KM.to_numpy(),
        "N_ACC_ANTERIOR": ultimo.N_ACC.to_numpy(),
        "indice_anterior": ultimo.indice.to_numpy(),
    })
    df["tasa"] = df.N_ACC_ESPERADO / df.VEH_KM * 1e8
    df["tasa_nacional"] = df.N_ACC_ESPERADO.sum() / df.VEH_KM.sum() * 1e8
    df["indice"] = df.tasa / df.tasa_nacional * 100
    df["cambio_acc"] = df.N_ACC_ESPERADO / df.N_ACC_ANTERIOR - 1
    df["cautela"] = df.cambio_acc.abs() > UMBRAL_CAUTELA
    return df


@st.cache_data(show_spinner=False)
def predicciones_provincias() -> pd.DataFrame:
    """Las 44 provincias de 2024 con la prediccion de cada variante de Miki."""
    return pd.read_csv(DATOS / "predicciones_2024_4modelos.csv", sep=";", encoding="utf-8-sig")


@st.cache_data(show_spinner=False)
def metricas_provincias() -> pd.DataFrame:
    """Error en 2024 de las cuatro variantes de Miki, recalculado desde sus
    predicciones. La primera fila es la regla ingenua."""
    pred = predicciones_provincias()
    filas = []
    for clave, (nombre, descripcion) in VARIANTES_PROVINCIAS.items():
        error = pred.N_ACC - pred[clave]
        filas.append({"clave": clave, "Versión": nombre, "Qué usa": descripcion,
                      "mae": error.abs().mean(), "rmse": float(np.sqrt((error ** 2).mean()))})
    df = pd.DataFrame(filas)
    df["mejora_mae"] = 1 - df.mae / df.mae.iloc[0]
    df["mejora_rmse"] = 1 - df.rmse / df.rmse.iloc[0]
    return df.set_index("clave", drop=False)


@st.cache_data(show_spinner=False)
def corredores() -> dict:
    """Corredores de Jose. Las vias discontinuas (AP-7, A-7) traen el campo
    `provincia` y la ruta se recorta a ella: sin eso, un corredor de Malaga se
    comeria tramos de Tarragona. Lo vigila pruebas/auditar_corredores.py."""
    return json.loads((DATOS / "corredores.json").read_text(encoding="utf-8"))


@st.cache_data(show_spinner=False)
def ficha_tramos() -> dict:
    return json.loads((DATOS / "ficha_modelo.json").read_text(encoding="utf-8"))


@st.cache_data(show_spinner=False)
def metadata_gravedad() -> dict:
    return json.loads((DATOS / "metadata_gravedad.json").read_text(encoding="utf-8"))


@st.cache_data(show_spinner=False)
def metricas_gravedad() -> dict:
    return json.loads((DATOS / "metricas_test_2024.json").read_text(encoding="utf-8"))


@st.cache_data(show_spinner=False)
def geometria_provincias() -> dict:
    """Limites provinciales para el coropletico, incluidos en el repositorio
    para que la presentacion no dependa de una conexion a Internet."""
    return json.loads((DATOS / "provincias_espana.geojson").read_text(encoding="utf-8"))


@st.cache_resource(show_spinner="Cargando el modelo de tramos...")
def modelo_tramos():
    """Paquete de Anna. Solo se carga en las pantallas que predicen casos nuevos;
    el ranking y la ruta leen la tabla ya puntuada."""
    from validador_entrada import cargar_paquete_modelo
    paquete, errores = cargar_paquete_modelo(MODELOS / "modelo_final.joblib")
    return paquete, errores


@st.cache_resource(show_spinner="Cargando el modelo de gravedad...")
def modelo_gravedad():
    from catboost import CatBoostClassifier
    modelo = CatBoostClassifier()
    modelo.load_model(str(MODELOS / "modelo_gravedad.cbm"))
    return modelo


# ------------------------------------------------------ gravedad (Lourdes)

# Lo que elige el usuario, traducido a los codigos del modelo. Cada opcion fija
# a la vez todas las variables que dependen entre si: una hora de madrugada con
# luz de dia o una autovia en zona urbana son escenarios que no existen, y el
# modelo trabaja con combinaciones. Las horas y los meses se eligen dentro de
# cualquier definicion razonable de franja y estacion.
BLOQUES_GRAVEDAD = {
    "Momento del día": {
        "Por la mañana (10:00)": {"FRANJA_HORARIA": "Mañana", "HORA": "10",
                                  "CONDICION_ILUMINACION": "1"},
        "Por la tarde (17:00)": {"FRANJA_HORARIA": "Tarde", "HORA": "17",
                                 "CONDICION_ILUMINACION": "1"},
        "De noche (23:00)": {"FRANJA_HORARIA": "Noche", "HORA": "23",
                             "CONDICION_ILUMINACION": "6"},
        "De madrugada (4:00)": {"FRANJA_HORARIA": "Madrugada", "HORA": "4",
                                "CONDICION_ILUMINACION": "6"},
    },
    "Día": {
        "Entre semana": {"DIA_SEMANA": "2", "FIN_DE_SEMANA": "No"},
        "Sábado": {"DIA_SEMANA": "6", "FIN_DE_SEMANA": "Sí"},
        "Domingo": {"DIA_SEMANA": "7", "FIN_DE_SEMANA": "Sí"},
    },
    "Época del año": {
        "Invierno": {"MES": "1", "ESTACION": "Invierno"},
        "Primavera": {"MES": "4", "ESTACION": "Primavera"},
        "Verano": {"MES": "7", "ESTACION": "Verano"},
        "Otoño": {"MES": "11", "ESTACION": "Otoño"},
    },
    "Tiempo": {
        "Despejado": {"CONDICION_METEO": "1", "CONDICION_FIRME": "1"},
        "Nublado": {"CONDICION_METEO": "2", "CONDICION_FIRME": "1"},
        "Lluvia débil": {"CONDICION_METEO": "3", "CONDICION_FIRME": "3"},
        "Lluvia fuerte": {"CONDICION_METEO": "4", "CONDICION_FIRME": "3"},
        "Nieve": {"CONDICION_METEO": "6", "CONDICION_FIRME": "6"},
    },
    "Carretera": {
        "Autovía": {"ZONA": "1", "TIPO_VIA": "3.0",
                    "TIPO_VIA_AGRUPADO": "Autopista_Autovia", "TRAZADO_PLANTA": "1"},
        "Autopista de peaje": {"ZONA": "1", "TIPO_VIA": "1.0",
                               "TIPO_VIA_AGRUPADO": "Autopista_Autovia", "TRAZADO_PLANTA": "1"},
        "Convencional": {"ZONA": "1", "TIPO_VIA": "6.0",
                         "TIPO_VIA_AGRUPADO": "Carretera", "TRAZADO_PLANTA": "1"},
        "Convencional, en curva": {"ZONA": "1", "TIPO_VIA": "6.0",
                                   "TIPO_VIA_AGRUPADO": "Carretera", "TRAZADO_PLANTA": "2"},
    },
}

# Algunas etiquetas del diccionario de la DGT llegan cortadas a 50 caracteres
ETIQUETAS_CORREGIDAS = {
    "CONDICION_ILUMINACION": {
        "4": "Sin luz natural, con alumbrado encendido",
        "5": "Sin luz natural, con alumbrado apagado",
    },
}


@st.cache_data(show_spinner=False)
def caso_referencia_gravedad() -> tuple[dict, bool]:
    """Caso real del test 2024 con el score mas cercano a la mediana.

    Devuelve (caso, es_de_carretera). Si Lourdes entrega el caso de carretera se
    usa tal cual. Mientras tanto, el suyo es urbano y se traslada a autovia
    cambiando solo el bloque de carretera.
    """
    carretera = DATOS / "caso_default_2024_carretera.json"
    es_de_carretera = carretera.exists()
    origen = carretera if es_de_carretera else DATOS / "caso_default_2024.json"
    caso = json.loads(origen.read_text(encoding="utf-8"))
    caso.pop("score_severo", None)
    if not es_de_carretera:
        caso.update(BLOQUES_GRAVEDAD["Carretera"]["Autovía"])
    return caso, es_de_carretera


@st.cache_data(show_spinner=False)
def etiquetas_gravedad() -> dict:
    etiquetas = json.loads((DATOS / "labels_categorias.json").read_text(encoding="utf-8"))
    etiquetas["DIA_SEMANA"] = {k: v.capitalize() for k, v in etiquetas["DIA_SEMANA"].items()}
    for variable, cambios in ETIQUETAS_CORREGIDAS.items():
        etiquetas[variable].update(cambios)
    return etiquetas


@st.cache_data(show_spinner=False)
def importancia_gravedad() -> pd.Series:
    """Importancia nativa de CatBoost. Dice cuanto usa el modelo cada variable,
    no cuanto cambia la gravedad al moverla."""
    valores = json.loads((DATOS / "feature_importance.json").read_text(encoding="utf-8"))
    return pd.Series(valores, dtype=float).sort_values(ascending=False)


@st.cache_data(show_spinner=False)
def referencia_gravedad() -> np.ndarray:
    """Los 101.996 scores del test 2024, ordenados."""
    scores = pd.read_csv(DATOS / "scores_test_2024.csv").score_severo
    return np.sort(scores.to_numpy(dtype=float))


def puntuar_gravedad(escenarios: list[dict]) -> np.ndarray:
    """Score Severo de varios escenarios completos en una sola llamada."""
    entrada = metadata_gravedad()["entrada"]
    tabla = pd.DataFrame(escenarios)[entrada["columnas"]]
    for columna in entrada["categoricas"]:
        tabla[columna] = tabla[columna].astype(str)
    return modelo_gravedad().predict_proba(tabla)[:, 1]


def percentil_gravedad(scores) -> np.ndarray:
    """Puesto de cada escenario frente a los accidentes reales de 2024, de 0 a 100.
    El score no esta calibrado: el orden es lo unico que se puede defender."""
    return _rango_percentil(referencia_gravedad(), scores)


def banda_gravedad(percentiles) -> list:
    """Mismas bandas que los tramos: 'Muy alto' es el 5% mas grave de 2024."""
    cortes = [-0.01] + [c * 100 for c in CUANTILES] + [100.01]
    return list(pd.cut(np.asarray(percentiles, dtype=float), bins=cortes,
                       labels=BANDAS, right=False))


def predecir_tramos_usuario(tabla: pd.DataFrame, anio: int = ANIO):
    """Valida y predice una tabla introducida por el usuario.

    Devuelve (resultado_validacion, predicciones o None, mensaje de error o None).
    predecir_tramos lanza excepciones; aqui se convierten en texto para que la
    pantalla nunca muestre una traza.
    """
    from validador_entrada import preparar_para_modelo, validar_tramos
    from preparacion_tramos import predecir_tramos

    paquete, errores = modelo_tramos()
    if errores:
        return None, None, errores[0]
    validacion = validar_tramos(tabla, paquete)
    if not validacion.valido:
        return validacion, None, None

    entrada = preparar_para_modelo(validacion.datos, anio=anio)
    # Una flota con dos rutas que comparten un trozo de via manda ese tramo dos
    # veces. predecir_tramos rechaza el intervalo repetido, asi que se predice
    # sobre los distintos y el resultado se reparte a las filas originales.
    clave = _clave(entrada.provincia, entrada.carretera,
                   entrada.pk_inicio_km, entrada.pk_fin_km) + "|" + str(anio)
    distintos = entrada[~clave.duplicated()]
    try:
        predichos = predecir_tramos(distintos, paquete)
    except Exception:
        return validacion, None, ("No se ha podido calcular la prediccion con estos datos. "
                                  "Revisa los kilometros y el trafico de cada fila.")

    salida = (predichos.set_index(clave[~clave.duplicated()].to_numpy())
              .reindex(clave.to_numpy()).reset_index(drop=True))
    salida["TRAMO_ID"] = entrada.TRAMO_ID.to_numpy()
    salida["banda"] = banda_riesgo(salida.PROB_ACCIDENTE_TRAMO_ANIO)
    salida["percentil"] = percentil_2024(salida.PROB_ACCIDENTE_TRAMO_ANIO)
    return validacion, salida, None


# --------------------------------------------------------------- utilidades

BANDAS = ["Bajo", "Medio", "Alto", "Muy alto"]
# Cuantiles nacionales, no cortes fijos. Con cortes en 0,25 / 0,50 / 0,75 casi
# todos los tramos salian "muy alto": la probabilidad de que un tramo tenga algun
# accidente en todo un anio es alta por construccion. "Muy alto" tiene que
# significar el 5% peor de Espana, no un numero redondo.
CUANTILES = [0.50, 0.80, 0.95]


@st.cache_data(show_spinner=False)
def referencia_2024() -> np.ndarray:
    """Las 7.248 probabilidades validas de 2024, ordenadas. Es la misma
    distribucion que usa la API de Anna para su campo percentil_2024."""
    prob = pd.read_csv(DATOS / "predicciones_tramos_2024.csv", sep=";",
                       encoding="utf-8-sig").PROB_ACCIDENTE_TRAMO_ANIO
    return np.sort(prob.dropna().to_numpy(dtype=float))


@st.cache_data(show_spinner=False)
def cortes_riesgo() -> list:
    prob = pd.read_csv(DATOS / "predicciones_tramos_2024.csv", sep=";",
                       encoding="utf-8-sig").PROB_ACCIDENTE_TRAMO_ANIO
    return [-0.01] + list(prob.quantile(CUANTILES)) + [1.01]


def percentil_2024(prob) -> pd.Series:
    """Posicion del tramo dentro de la red de 2024, de 0 a 100.

    Rango percentil con posicion media en los empates: el mismo criterio que la
    API, para que los dos devuelvan el mismo numero hasta el segundo decimal.
    """
    serie = pd.Series(prob)
    return pd.Series(_rango_percentil(referencia_2024(), serie),
                     index=serie.index).round(2)


def _rango_percentil(referencia: np.ndarray, valores) -> np.ndarray:
    """Rango percentil con posicion media en los empates, sobre una referencia
    ya ordenada. Un valor nulo sigue siendo nulo: sin dato no es riesgo cero."""
    valores = np.asarray(valores, dtype=float)
    izquierda = np.searchsorted(referencia, valores, side="left")
    derecha = np.searchsorted(referencia, valores, side="right")
    rango = 100.0 * (izquierda + derecha) / 2.0 / referencia.size
    return np.where(np.isnan(valores), np.nan, rango)


def banda_riesgo(prob: pd.Series) -> pd.Series:
    """Cuatro categorias con etiqueta de texto. El color nunca va solo: uno de
    cada doce hombres no distingue el verde del rojo."""
    return pd.cut(prob, bins=cortes_riesgo(), labels=BANDAS, right=False)


def _clave(provincia, via, pk0, pk1) -> pd.Series:
    """Clave de contenido tramo-anio. El TRAMO_ID de la maestra es un indice de
    fila y no identifica el mismo tramo entre anios."""
    return (provincia.astype(str) + "|" + via.astype(str) + "|"
            + pd.to_numeric(pk0).map(lambda n: format(n, ".12g")) + "|"
            + pd.to_numeric(pk1).map(lambda n: format(n, ".12g")))
