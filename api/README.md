# Baliza API

Servicio HTTP del modelo de ocurrencia anual por tramo. La API utiliza la única
copia de los artefactos incluida en el repositorio:

- `modelos/modelo_final.joblib`
- `datos/ficha_modelo.json`
- `datos/predicciones_tramos_2024.csv`
- `baliza/PrediccionTramos.py`

## Instalación

Desde la raíz del repositorio y con Python 3.12:

```console
python -m pip install -r api/requirements.txt
```

## Arrancar la API

Desde la raíz:

```console
python -m uvicorn api.main:app --reload
```

La documentación interactiva queda disponible en <http://127.0.0.1:8000/docs>
y contiene un ejemplo listo para ejecutar. El estado del servicio puede
consultarse en <http://127.0.0.1:8000/health>.

## Pasar los tests

Desde la raíz:

```console
python -m pytest api/test_api.py -q
```

## Ejemplo

```powershell
$body = @{
  TRAMO_ID = "A4_245.5_250.7"
  anio_referencia_trafico = 2025
  provincia = "Jaén"
  carretera = "A-4"
  pk_inicio_km = 245.5
  pk_fin_km = 250.7
  tipo_via = "Autopista_autovia"
  imd_total = 31844
  proporcion_pesados = 0.14
} | ConvertTo-Json

Invoke-RestMethod -Uri http://127.0.0.1:8000/predict `
  -Method Post -ContentType "application/json" -Body $body
```

`BALIZA_MODEL_PATH` puede utilizarse opcionalmente para probar otro fichero de
modelo. No es necesaria para el funcionamiento normal.

La probabilidad devuelta corresponde a que el tramo registre al menos un
accidente durante el año, condicionada al tráfico indicado. No es la
probabilidad de accidente de un conductor concreto. `percentil_2024` sitúa el
resultado frente a las 7.248 predicciones válidas de la referencia de 2024.
