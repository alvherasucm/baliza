"""Validación de entradas de tramos para BALIZA.

La capa de interfaz puede mostrar ``errores`` y ``advertencias`` directamente.
Los errores de usuario se devuelven como texto y no se propagan como excepciones.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from difflib import get_close_matches
from pathlib import Path
from typing import Any, Mapping
import math
import unicodedata

import joblib
import numpy as np
import pandas as pd


COLUMNAS_REQUERIDAS = (
    "provincia",
    "carretera",
    "pk_inicio",
    "pk_fin",
    "imd_total",
    "imd_pesados",
    "tipo_via",
)

COLUMNAS_NUMERICAS = ("pk_inicio", "pk_fin", "imd_total", "imd_pesados")


@dataclass
class ResultadoValidacion:
    valido: bool
    datos: pd.DataFrame = field(default_factory=pd.DataFrame)
    errores: list[str] = field(default_factory=list)
    advertencias: list[str] = field(default_factory=list)


def _normalizar(texto: Any) -> str:
    limpio = "" if pd.isna(texto) else str(texto).strip()
    limpio = unicodedata.normalize("NFKD", limpio)
    return "".join(c for c in limpio if not unicodedata.combining(c)).casefold()


def _mapa_categorias(valores: Any) -> dict[str, str]:
    if valores is None:
        return {}
    return {_normalizar(valor): str(valor) for valor in valores if _normalizar(valor)}


def _sugerencia(valor: str, mapa: Mapping[str, str]) -> str | None:
    candidatas = get_close_matches(_normalizar(valor), list(mapa), n=1, cutoff=0.62)
    return mapa[candidatas[0]] if candidatas else None


def _rango(paquete: Mapping[str, Any], clave: str) -> tuple[float, float] | None:
    valor = paquete.get("rangos_train", {}).get(clave)
    if not isinstance(valor, (list, tuple)) or len(valor) != 2:
        return None
    try:
        minimo, maximo = float(valor[0]), float(valor[1])
    except (TypeError, ValueError):
        return None
    if not (math.isfinite(minimo) and math.isfinite(maximo) and minimo <= maximo):
        return None
    return minimo, maximo


def cargar_paquete_modelo(origen: str | Path | Mapping[str, Any]) -> tuple[Mapping[str, Any] | None, list[str]]:
    """Carga el paquete y convierte cualquier fallo de configuración en un mensaje."""
    if isinstance(origen, Mapping):
        return origen, []
    try:
        paquete = joblib.load(origen)
    except FileNotFoundError:
        return None, ["No se encontró el paquete del modelo. Revisa el archivo configurado."]
    except Exception:
        return None, [
            "No se pudo abrir el paquete del modelo. Comprueba el archivo y usa las mismas versiones "
            "de Python y scikit-learn con las que se exportó."
        ]
    if not isinstance(paquete, Mapping):
        return None, ["El paquete del modelo no tiene el formato esperado."]
    return paquete, []


def validar_tramos(datos: pd.DataFrame, paquete: Mapping[str, Any]) -> ResultadoValidacion:
    """Valida un lote sin lanzar excepciones por datos introducidos por el usuario."""
    errores: list[str] = []
    advertencias: list[str] = []

    if not isinstance(datos, pd.DataFrame):
        return ResultadoValidacion(False, errores=["La entrada debe ser una tabla de tramos."])

    faltantes = [columna for columna in COLUMNAS_REQUERIDAS if columna not in datos.columns]
    if faltantes:
        texto = ", ".join(faltantes)
        return ResultadoValidacion(
            False,
            datos=datos.copy(),
            errores=[f"Faltan estas columnas obligatorias: {texto}. Descarga la plantilla y conserva sus encabezados."],
        )

    limpio = datos.loc[:, COLUMNAS_REQUERIDAS].copy()
    categorias = paquete.get("categorias", {}) if isinstance(paquete, Mapping) else {}
    provincias = _mapa_categorias(categorias.get("provincia"))
    tipos_via = _mapa_categorias(categorias.get("tipo_via"))
    if not provincias or not tipos_via:
        return ResultadoValidacion(
            False,
            datos=limpio,
            errores=["El paquete del modelo no incluye las categorías necesarias para validar provincia y tipo de vía."],
        )

    # El número de fila coincide con la línea del CSV: la cabecera ocupa la fila 1.
    for posicion, (_, fila) in enumerate(limpio.iterrows(), start=2):
        etiqueta = f"Fila {posicion}"

        for columna in ("provincia", "carretera", "tipo_via"):
            if not _normalizar(fila[columna]):
                errores.append(f"{etiqueta}: falta {columna.replace('_', ' ')}.")

        for columna in COLUMNAS_NUMERICAS:
            valor = pd.to_numeric(pd.Series([fila[columna]]), errors="coerce").iloc[0]
            if pd.isna(valor) or not np.isfinite(valor):
                if columna == "imd_total":
                    errores.append(f"{etiqueta}: falta el IMD o no es un número. Sin tráfico no se puede estimar el riesgo.")
                else:
                    errores.append(f"{etiqueta}: {columna.replace('_', ' ')} debe ser un número y no puede estar vacío.")
            else:
                limpio.iat[posicion - 2, limpio.columns.get_loc(columna)] = float(valor)

        provincia = str(fila["provincia"]).strip() if not pd.isna(fila["provincia"]) else ""
        provincia_norm = _normalizar(provincia)
        if provincia_norm and provincia_norm not in provincias:
            sugerida = _sugerencia(provincia, provincias)
            extra = f" ¿Querías decir {sugerida}?" if sugerida else ""
            errores.append(f"{etiqueta}: la provincia '{provincia}' no está entre las conocidas.{extra}")
        elif provincia_norm:
            limpio.iat[posicion - 2, limpio.columns.get_loc("provincia")] = provincias[provincia_norm]

        tipo = str(fila["tipo_via"]).strip() if not pd.isna(fila["tipo_via"]) else ""
        tipo_norm = _normalizar(tipo)
        if tipo_norm and tipo_norm not in tipos_via:
            sugerido = _sugerencia(tipo, tipos_via)
            extra = f" ¿Querías decir {sugerido}?" if sugerido else ""
            errores.append(f"{etiqueta}: el tipo de vía '{tipo}' no está entre los conocidos.{extra}")
        elif tipo_norm:
            limpio.iat[posicion - 2, limpio.columns.get_loc("tipo_via")] = tipos_via[tipo_norm]

        valores = {c: pd.to_numeric(pd.Series([fila[c]]), errors="coerce").iloc[0] for c in COLUMNAS_NUMERICAS}
        if all(pd.notna(valores[c]) and np.isfinite(valores[c]) for c in ("pk_inicio", "pk_fin")):
            if valores["pk_inicio"] < 0 or valores["pk_fin"] < 0:
                errores.append(f"{etiqueta}: los puntos kilométricos no pueden ser negativos.")
            elif valores["pk_fin"] <= valores["pk_inicio"]:
                errores.append(f"{etiqueta}: el PK final debe ser mayor que el PK inicial.")

        if pd.notna(valores["imd_total"]) and np.isfinite(valores["imd_total"]):
            if valores["imd_total"] <= 0:
                errores.append(f"{etiqueta}: el IMD total debe ser mayor que cero.")
            rango_log = _rango(paquete, "log_imd_total")
            rango_directo = _rango(paquete, "imd_total")
            valor_comparado = math.log1p(valores["imd_total"]) if rango_log and valores["imd_total"] > -1 else valores["imd_total"]
            rango_imd = rango_log or rango_directo
            if rango_imd and not (rango_imd[0] <= valor_comparado <= rango_imd[1]):
                minimo = math.expm1(rango_imd[0]) if rango_log else rango_imd[0]
                maximo = math.expm1(rango_imd[1]) if rango_log else rango_imd[1]
                errores.append(
                    f"{etiqueta}: el IMD total ({valores['imd_total']:,.0f}) está fuera del rango aprendido por el modelo "
                    f"({minimo:,.0f} a {maximo:,.0f})."
                )

        if pd.notna(valores["imd_pesados"]) and np.isfinite(valores["imd_pesados"]):
            if valores["imd_pesados"] < 0:
                errores.append(f"{etiqueta}: el IMD de pesados no puede ser negativo.")
            if pd.notna(valores["imd_total"]) and valores["imd_pesados"] > valores["imd_total"]:
                errores.append(f"{etiqueta}: el IMD de pesados no puede superar el IMD total.")

        carretera = str(fila["carretera"]).strip().upper() if not pd.isna(fila["carretera"]) else ""
        if carretera:
            limpio.iat[posicion - 2, limpio.columns.get_loc("carretera")] = carretera

    if _rango(paquete, "log_imd_total") is None and _rango(paquete, "imd_total") is None:
        advertencias.append("El paquete no contiene un rango de IMD utilizable; esa comprobación no pudo realizarse.")

    return ResultadoValidacion(not errores, limpio, errores, advertencias)


def validar_archivo_csv(ruta: str | Path, origen_paquete: str | Path | Mapping[str, Any]) -> ResultadoValidacion:
    """Entrada segura para Streamlit: carga CSV y paquete sin mostrar trazas técnicas."""
    paquete, errores_paquete = cargar_paquete_modelo(origen_paquete)
    if errores_paquete:
        return ResultadoValidacion(False, errores=errores_paquete)
    try:
        datos = pd.read_csv(ruta, sep=None, engine="python")
    except pd.errors.EmptyDataError:
        return ResultadoValidacion(False, errores=["El archivo está vacío."])
    except Exception:
        return ResultadoValidacion(False, errores=["No se pudo leer el archivo. Usa CSV y conserva los encabezados de la plantilla."])
    return validar_tramos(datos, paquete)


def preparar_para_modelo(datos_validados: pd.DataFrame, anio: int = 2024) -> pd.DataFrame:
    """Adapta las siete columnas públicas a ``predecir_tramos`` del notebook."""
    salida = datos_validados.loc[:, COLUMNAS_REQUERIDAS].copy().reset_index(drop=True)
    salida.insert(0, "TRAMO_ID", [f"usuario_{i}" for i in range(1, len(salida) + 1)])
    salida.insert(1, "anio", int(anio))
    salida["proporcion_pesados"] = salida["imd_pesados"] / salida["imd_total"]
    salida = salida.rename(columns={"pk_inicio": "pk_inicio_km", "pk_fin": "pk_fin_km"})
    return salida[[
        "TRAMO_ID", "anio", "provincia", "carretera", "pk_inicio_km",
        "pk_fin_km", "tipo_via", "imd_total", "proporcion_pesados",
    ]]
