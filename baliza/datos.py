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

# Carreteras con tramos discontinuos y PK solapados entre zonas: sin filtrar por
# provincia, un corredor de Malaga se comeria tramos de Tarragona. Comprobado
# sobre las 7.250 filas de 2024: ninguna otra de las 15 del JSON los tiene.
FILTRO_PROVINCIA = {"AP-7": "Málaga", "A-7": "Almería"}

# Nombres descriptivos de la maestra frente a las tres categorias del modelo de Anna
TIPO_VIA_MODELO = {
    "Autopista libre y autovía": "Autopista_autovia",
    "Autopista de peaje": "Autopista_autovia",
    "Autovía": "Autopista_autovia",
    "Multicarril": "Multicarril",
    "Convencional": "Convencional",
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

    El indice es la tasa por 100 M veh-km de la provincia dividida por la media
    nacional del mismo anio. Nunca se ensena el conteo absoluto como titular.
    """
    df = pd.read_csv(DATOS / "provincias_2016_2024.csv", sep=";", encoding="utf-8-sig")
    df["tasa"] = df.N_ACC / df.VEH_KM * 1e8
    nacional = df.groupby("ANYO").apply(
        lambda g: g.N_ACC.sum() / g.VEH_KM.sum() * 1e8, include_groups=False)
    df["tasa_nacional"] = df.ANYO.map(nacional)
    df["indice"] = df.tasa / df.tasa_nacional * 100
    return df


@st.cache_data(show_spinner=False)
def corredores() -> dict:
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
    referencia = referencia_2024()
    valores = pd.Series(prob).to_numpy(dtype=float)
    izquierda = np.searchsorted(referencia, valores, side="left")
    derecha = np.searchsorted(referencia, valores, side="right")
    return pd.Series(100.0 * (izquierda + derecha) / 2.0 / referencia.size,
                     index=pd.Series(prob).index).round(2)


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
