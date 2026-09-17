"""Servicio HTTP para el modelo de ocurrencia anual por tramo de Baliza."""

from contextlib import asynccontextmanager
import json
import os
from pathlib import Path
import sys
from typing import Annotated

import joblib
import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import AliasChoices, BaseModel, ConfigDict, Field


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

DEFAULT_MODEL_PATH = PROJECT_ROOT / "modelos" / "modelo_final.joblib"
MODEL_PATH = Path(os.getenv("BALIZA_MODEL_PATH", str(DEFAULT_MODEL_PATH)))
FICHA_PATH = PROJECT_ROOT / "datos" / "ficha_modelo.json"
REFERENCIA_PATH = PROJECT_ROOT / "datos" / "predicciones_tramos_2024.csv"

from baliza.PrediccionTramos import predecir_tramos  # noqa: E402


class TramoEntrada(BaseModel):
    """Variables que necesita el modelo para puntuar un tramo-año."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    tramo_id: str = Field(min_length=1, alias="TRAMO_ID")
    anio_referencia_trafico: int = Field(
        ge=2000,
        le=2100,
        validation_alias=AliasChoices("anio_referencia_trafico", "anio"),
        description="Metadato de referencia; no es un predictor del modelo.",
    )
    provincia: str = Field(min_length=1)
    carretera: str = Field(min_length=1)
    pk_inicio_km: float = Field(ge=0)
    pk_fin_km: float = Field(gt=0)
    tipo_via: str = Field(min_length=1)
    imd_total: float = Field(gt=0, description="Intensidad media diaria de tráfico")
    proporcion_pesados: float = Field(ge=0, le=1)


class PrediccionSalida(BaseModel):
    tramo_id: str
    anio_referencia_trafico: int
    probabilidad_anual: float
    percentil_2024: float
    clasificacion_operativa: str
    umbral_modelo: float
    fuera_rango_entrenamiento: bool
    version_modelo: str
    advertencia: str


def cargar_modelo() -> tuple[dict, dict, np.ndarray]:
    for ruta, descripcion in (
        (MODEL_PATH, "modelo"),
        (FICHA_PATH, "ficha del modelo"),
        (REFERENCIA_PATH, "predicciones de referencia"),
    ):
        if not ruta.is_file():
            raise RuntimeError(f"No se encuentra {descripcion} en {ruta}")

    paquete = joblib.load(MODEL_PATH)
    ficha = json.loads(FICHA_PATH.read_text(encoding="utf-8"))
    referencia = pd.read_csv(REFERENCIA_PATH, sep=";", encoding="utf-8-sig")
    probabilidades_2024 = np.sort(
        referencia["PROB_ACCIDENTE_TRAMO_ANIO"].dropna().to_numpy(dtype=float)
    )
    if probabilidades_2024.size == 0:
        raise RuntimeError("La distribución de referencia de 2024 está vacía")
    return paquete, ficha, probabilidades_2024


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.paquete, app.state.ficha, app.state.probabilidades_2024 = cargar_modelo()
    yield


EJEMPLO = {
    "TRAMO_ID": "A4_245.5_250.7",
    "anio_referencia_trafico": 2025,
    "provincia": "Jaén",
    "carretera": "A-4",
    "pk_inicio_km": 245.5,
    "pk_fin_km": 250.7,
    "tipo_via": "Autopista_autovia",
    "imd_total": 31844,
    "proporcion_pesados": 0.14,
}

app = FastAPI(
    title="Baliza API",
    version="1.0.0",
    description="Inferencia de ocurrencia anual de accidentes por tramo de carretera.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost", "http://127.0.0.1"],
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict:
    return {
        "estado": "ok",
        "modelo_cargado": True,
        "version_modelo": _version_modelo(app.state.paquete),
    }


@app.post(
    "/predict",
    response_model=PrediccionSalida,
    openapi_extra={"requestBody": {"content": {"application/json": {"example": EJEMPLO}}}},
)
def predict(tramo: TramoEntrada) -> PrediccionSalida:
    return _predecir_lote([tramo])[0]


@app.post("/predict/batch", response_model=list[PrediccionSalida])
def predict_batch(
    tramos: Annotated[list[TramoEntrada], Field(min_length=1, max_length=1000)],
) -> list[PrediccionSalida]:
    return _predecir_lote(tramos)


def _predecir_lote(tramos: list[TramoEntrada]) -> list[PrediccionSalida]:
    filas = []
    for tramo in tramos:
        fila = tramo.model_dump()
        fila["TRAMO_ID"] = fila.pop("tramo_id")
        fila["anio"] = fila.pop("anio_referencia_trafico")
        filas.append(fila)
    entrada = pd.DataFrame(filas)
    try:
        resultados = predecir_tramos(entrada, app.state.paquete)
    except (ValueError, KeyError, TypeError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    umbral = float(app.state.paquete["umbral_descriptivo"])
    return [_formatear_salida(resultado, umbral) for _, resultado in resultados.iterrows()]


def _formatear_salida(resultado: pd.Series, umbral: float) -> PrediccionSalida:
    probabilidad = float(resultado["PROB_ACCIDENTE_TRAMO_ANIO"])
    referencia = app.state.probabilidades_2024
    izquierda = np.searchsorted(referencia, probabilidad, side="left")
    derecha = np.searchsorted(referencia, probabilidad, side="right")
    percentil = 100.0 * ((izquierda + derecha) / 2.0) / referencia.size
    return PrediccionSalida(
        tramo_id=str(resultado["TRAMO_ID"]),
        anio_referencia_trafico=int(resultado["anio"]),
        probabilidad_anual=probabilidad,
        percentil_2024=round(float(percentil), 2),
        clasificacion_operativa="positivo" if probabilidad >= umbral else "negativo",
        umbral_modelo=umbral,
        fuera_rango_entrenamiento=bool(resultado["FUERA_RANGO_TRAIN"]),
        version_modelo=_version_modelo(app.state.paquete),
        advertencia=(
            "Probabilidad de ocurrencia anual condicionada al tráfico; "
            "no representa el riesgo individual de un viaje."
        ),
    )


def _version_modelo(paquete: dict) -> str:
    return " | ".join(
        str(paquete.get(campo, "desconocido"))
        for campo in ("version_datos", "familia", "configuracion")
    )
