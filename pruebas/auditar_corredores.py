"""Comprueba que corredores.json es compatible con los tramos predichos de 2024."""

from __future__ import annotations

import json
from pathlib import Path
import sys

import pandas as pd


SALTO_MAXIMO_KM = 120.0


def _columna(tabla: pd.DataFrame, *candidatas: str) -> str:
    por_minusculas = {str(col).lower(): col for col in tabla.columns}
    for candidata in candidatas:
        if candidata.lower() in por_minusculas:
            return por_minusculas[candidata.lower()]
    raise ValueError(f"Falta una de estas columnas: {', '.join(candidatas)}")


def _tabla_2024(ruta_tabla: str | Path) -> pd.DataFrame:
    tabla = pd.read_csv(ruta_tabla, sep=None, engine="python")
    tabla.columns = [str(col).replace("﻿", "") for col in tabla.columns]
    if any(str(col).lower() == "anyo" for col in tabla.columns):
        col_anio = _columna(tabla, "ANYO")
        tabla = tabla.loc[pd.to_numeric(tabla[col_anio], errors="coerce").eq(2024)]
    return tabla


def _tramos_del_corredor(tabla, carretera, definicion, cols):
    """Las filas que Tu ruta puede llegar a pintar en ese corredor."""
    col_carretera, col_pk_inicio, col_pk_fin, col_provincia = cols
    tramos = tabla.loc[tabla[col_carretera].eq(carretera)].copy()
    provincia = definicion.get("provincia")
    if provincia:
        tramos = tramos.loc[tramos[col_provincia].eq(provincia)]
    pks = [hito.get("pk") for hito in definicion.get("hitos", [])]
    inicios = pd.to_numeric(tramos[col_pk_inicio], errors="coerce")
    finales = pd.to_numeric(tramos[col_pk_fin], errors="coerce")
    limites = pd.concat([inicios, finales], axis=1)
    return tramos.loc[limites.min(axis=1).le(max(pks)) & limites.max(axis=1).ge(min(pks))]


def cobertura(ruta_tabla: str | Path, ruta_json: str | Path) -> dict:
    """Kilómetros ruteables: los que caen dentro de algún corredor, ya filtrados."""
    tabla = _tabla_2024(ruta_tabla)
    corredores = json.loads(Path(ruta_json).read_text(encoding="utf-8"))
    cols = (
        _columna(tabla, "carretera", "VIA_NORM"),
        _columna(tabla, "pk_inicio_km", "PK_INICIO", "pk_inicio"),
        _columna(tabla, "pk_fin_km", "PK_FIN", "pk_fin"),
        _columna(tabla, "provincia", "PROVINCIA"),
    )
    _, col_pk_inicio, col_pk_fin, _ = cols
    largo = lambda t: (
        pd.to_numeric(t[col_pk_fin], errors="coerce")
        - pd.to_numeric(t[col_pk_inicio], errors="coerce")
    ).abs().sum()
    dentro = sum(
        largo(_tramos_del_corredor(tabla, carretera, definicion, cols))
        for carretera, definicion in corredores.items()
    )
    return {"km_corredores": float(dentro), "km_red": float(largo(tabla)), "corredores": len(corredores)}


def auditar(ruta_tabla: str | Path, ruta_json: str | Path) -> list[str]:
    tabla = _tabla_2024(ruta_tabla)
    corredores = json.loads(Path(ruta_json).read_text(encoding="utf-8"))
    problemas: list[str] = []

    if not corredores:
        return ["corredores.json está vacío."]

    col_carretera = _columna(tabla, "carretera", "VIA_NORM")
    col_pk_inicio = _columna(tabla, "pk_inicio_km", "PK_INICIO", "pk_inicio")
    col_pk_fin = _columna(tabla, "pk_fin_km", "PK_FIN", "pk_fin")
    col_provincia = _columna(tabla, "provincia", "PROVINCIA")

    for carretera, definicion in corredores.items():
        tramos_carretera = tabla.loc[tabla[col_carretera].eq(carretera)].copy()
        provincia = definicion.get("provincia")
        if provincia is not None and not isinstance(provincia, str):
            problemas.append(f"{carretera}: el campo provincia debe ser texto.")
            continue

        hitos = definicion.get("hitos", [])
        pks = [hito.get("pk") for hito in hitos]
        if len(pks) < 2 or any(not isinstance(pk, (int, float)) for pk in pks):
            problemas.append(f"{carretera}: hacen falta al menos dos hitos con PK numérico.")
            continue
        if pks != sorted(pks) or len(pks) != len(set(pks)):
            problemas.append(f"{carretera}: los PK deben ser crecientes y no repetirse.")

        saltos = [
            (hitos[i]["ciudad"], hitos[i + 1]["ciudad"], pks[i + 1] - pks[i])
            for i in range(len(pks) - 1)
            if pks[i + 1] - pks[i] > SALTO_MAXIMO_KM
        ]
        for origen, destino, salto in saltos:
            problemas.append(
                f"{carretera}: de {origen} a {destino} hay {salto:g} km sin ninguna ciudad "
                f"intermedia (el máximo son {SALTO_MAXIMO_KM:g})."
            )

        dentro_del_corredor = _tramos_del_corredor(tabla, carretera, definicion,
                                                   (col_carretera, col_pk_inicio, col_pk_fin, col_provincia))
        if not provincia:
            intervalos = pd.DataFrame({
                "pk_inicio": pd.to_numeric(dentro_del_corredor[col_pk_inicio], errors="coerce"),
                "pk_fin": pd.to_numeric(dentro_del_corredor[col_pk_fin], errors="coerce"),
                "provincia": dentro_del_corredor[col_provincia],
            }).dropna().sort_values("pk_inicio")

            abiertos: list[tuple[float, str]] = []
            solape_entre_provincias = False
            for intervalo in intervalos.itertuples(index=False):
                pk_inicio = float(intervalo.pk_inicio)
                pk_fin = float(intervalo.pk_fin)
                abiertos = [(fin, prov) for fin, prov in abiertos if fin > pk_inicio]
                if any(prov != intervalo.provincia for _, prov in abiertos):
                    solape_entre_provincias = True
                    break
                abiertos.append((pk_fin, intervalo.provincia))

            if solape_entre_provincias:
                problemas.append(
                    f"{carretera}: tramos de provincias distintas comparten PK; "
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
    resumen = cobertura(sys.argv[1], sys.argv[2])
    miles = lambda n: f"{n:,.0f}".replace(",", ".")
    porcentaje = f"{100 * resumen['km_corredores'] / resumen['km_red']:.1f}".replace(".", ",")
    print(
        f"Corredores válidos frente a las predicciones de tramos de 2024. "
        f"{resumen['corredores']} corredores cubren {miles(resumen['km_corredores'])} km "
        f"de los {miles(resumen['km_red'])} de la red ({porcentaje} %)."
    )
