"""Comprueba que corredores.json es compatible con los tramos predichos de 2024."""

from __future__ import annotations

import json
from pathlib import Path
import sys

import pandas as pd


CARRETERAS = (
    "A-1", "A-2", "A-3", "A-4", "A-5", "AP-7", "A-6", "A-8", "A-66",
    "A-7", "A-23", "A-62", "N-232", "N-260", "N-432",
)

def _columna(tabla: pd.DataFrame, *candidatas: str) -> str:
    por_minusculas = {str(col).lower(): col for col in tabla.columns}
    for candidata in candidatas:
        if candidata.lower() in por_minusculas:
            return por_minusculas[candidata.lower()]
    raise ValueError(f"Falta una de estas columnas: {', '.join(candidatas)}")


def auditar(ruta_tabla: str | Path, ruta_json: str | Path) -> list[str]:
    tabla = pd.read_csv(ruta_tabla, sep=None, engine="python")
    corredores = json.loads(Path(ruta_json).read_text(encoding="utf-8"))
    problemas: list[str] = []

    if tuple(corredores) != CARRETERAS:
        problemas.append("Las carreteras o su orden no coinciden con la lista oficial de corredores.")

    col_carretera = _columna(tabla, "carretera", "VIA_NORM")
    col_pk_inicio = _columna(tabla, "pk_inicio_km", "PK_INICIO", "pk_inicio")
    col_pk_fin = _columna(tabla, "pk_fin_km", "PK_FIN", "pk_fin")

    col_provincia = _columna(tabla, "provincia", "PROVINCIA")

    base = tabla.copy()
    if any(str(col).lower() == "anyo" for col in tabla.columns):
        col_anio = _columna(tabla, "ANYO")
        base = base.loc[pd.to_numeric(base[col_anio], errors="coerce").eq(2024)]

    for carretera in CARRETERAS:
        tramos_carretera = base.loc[base[col_carretera].eq(carretera)].copy()
        provincia = corredores.get(carretera, {}).get("provincia")
        if provincia is not None and not isinstance(provincia, str):
            problemas.append(f"{carretera}: el campo provincia debe ser texto.")
            continue

        hitos = corredores.get(carretera, {}).get("hitos", [])
        pks = [hito.get("pk") for hito in hitos]
        if not pks or any(not isinstance(pk, (int, float)) for pk in pks):
            problemas.append(f"{carretera}: los hitos no contienen PK numéricos.")
            continue
        if pks != sorted(pks) or len(pks) != len(set(pks)):
            problemas.append(f"{carretera}: los PK deben ser crecientes y no repetirse.")

        pk_min_corredor = min(pks)
        pk_max_corredor = max(pks)
        inicios = pd.to_numeric(tramos_carretera[col_pk_inicio], errors="coerce")
        finales = pd.to_numeric(tramos_carretera[col_pk_fin], errors="coerce")
        limite_inferior = pd.concat([inicios, finales], axis=1).min(axis=1)
        limite_superior = pd.concat([inicios, finales], axis=1).max(axis=1)
        dentro_del_corredor = tramos_carretera.loc[
            limite_inferior.le(pk_max_corredor)
            & limite_superior.ge(pk_min_corredor)
        ]
        if not provincia:
            intervalos = pd.DataFrame({
                "pk_inicio": pd.to_numeric(
                    dentro_del_corredor[col_pk_inicio], errors="coerce"
                ),
                "pk_fin": pd.to_numeric(
                    dentro_del_corredor[col_pk_fin], errors="coerce"
                ),
            }).dropna().sort_values("pk_inicio")

            maximo_fin_anterior: float | None = None
            hay_solape = False
            for intervalo in intervalos.itertuples(index=False):
                pk_inicio = float(intervalo.pk_inicio)
                pk_fin = float(intervalo.pk_fin)
                if maximo_fin_anterior is not None and pk_inicio < maximo_fin_anterior:
                    hay_solape = True
                    break
                maximo_fin_anterior = (
                    pk_fin
                    if maximo_fin_anterior is None
                    else max(maximo_fin_anterior, pk_fin)
                )

            if hay_solape:
                problemas.append(
                    f"{carretera}: tramos con PK solapados entre provincias; "
                    "falta el campo provincia"
                )

        tramos = tramos_carretera
        if provincia:
            tramos = tramos.loc[tramos[col_provincia].eq(provincia)]
        if tramos.empty:
            problemas.append(f"{carretera}: no hay tramos en la tabla de 2024.")
            continue

        minimo = float(pd.to_numeric(tramos[col_pk_inicio], errors="coerce").min())
        maximo = float(pd.to_numeric(tramos[col_pk_fin], errors="coerce").max())
        fuera = [pk for pk in pks if not minimo <= pk <= maximo]
        if fuera:
            problemas.append(f"{carretera}: PK fuera de la cobertura 2024 ({minimo:g}-{maximo:g}): {fuera}.")

    return problemas


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("Uso: python auditar_corredores.py predicciones_tramos_2024.csv corredores.json")
    fallos = auditar(sys.argv[1], sys.argv[2])
    if fallos:
        print("\n".join(fallos))
        raise SystemExit(1)
    print("Corredores válidos frente a las predicciones de tramos de 2024.")
