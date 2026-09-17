from fastapi.testclient import TestClient

from api.main import app


TRAMO_VALIDO = {
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


def test_health_carga_modelo():
    with TestClient(app) as client:
        respuesta = client.get("/health")
        documentacion = client.get("/docs")
    assert respuesta.status_code == 200
    assert respuesta.json()["modelo_cargado"] is True
    assert documentacion.status_code == 200
    assert "swagger-ui" in documentacion.text


def test_predict_devuelve_probabilidad_y_percentil_reproducibles():
    with TestClient(app) as client:
        respuesta = client.post("/predict", json=TRAMO_VALIDO)
    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert 0 <= cuerpo["probabilidad_anual"] <= 1
    assert 0 <= cuerpo["percentil_2024"] <= 100
    assert cuerpo["tramo_id"] == TRAMO_VALIDO["TRAMO_ID"]
    assert cuerpo["version_modelo"] == "v1 | Random Forest | Base"


def test_predict_rechaza_proporcion_invalida():
    entrada = {**TRAMO_VALIDO, "proporcion_pesados": 1.5}
    with TestClient(app) as client:
        respuesta = client.post("/predict", json=entrada)
    assert respuesta.status_code == 422


def test_predict_batch_rechaza_identificadores_repetidos():
    with TestClient(app) as client:
        respuesta = client.post("/predict/batch", json=[TRAMO_VALIDO, TRAMO_VALIDO])
    assert respuesta.status_code == 422
    assert "TRAMO_ID" in respuesta.json()["detail"]
