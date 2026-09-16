"""Componentes de interfaz de Baliza. Las paginas componen con estas piezas y no
escriben HTML ni colores propios. Todo texto dinamico se escapa antes de
entrar en el HTML."""
from __future__ import annotations

import html
import math

import pandas as pd
import streamlit as st

from baliza import estilo

CLASE_BANDA = {"Bajo": "bajo", "Medio": "medio", "Alto": "alto", "Muy alto": "muy-alto"}


def _e(valor) -> str:
    return html.escape(str(valor))


def _texto(valor) -> str:
    """Escapa y convierte **negrita** en <b>."""
    partes = _e(valor).split("**")
    return "".join(p if i % 2 == 0 else f"<b>{p}</b>" for i, p in enumerate(partes))


def _pintar(fragmento: str) -> None:
    st.html(fragmento)


# ------------------------------------------------------------- estructura

def aplicar_estilos() -> None:
    st.html(estilo.CSS)


def cabecera_pagina(eyebrow: str, titulo: str, descripcion: str | None = None,
                    meta: list[tuple[str, str]] | None = None) -> None:
    """PageHeader: antetitulo, titulo, proposito en una frase y contexto real."""
    desc = f'<p class="bz-page-desc">{_texto(descripcion)}</p>' if descripcion else ""
    datos = ""
    if meta:
        datos = '<div class="bz-meta">' + "".join(
            f"<span><b>{_e(k)}</b>{_e(v)}</span>" for k, v in meta) + "</div>"
    _pintar(f'<div class="bz-page-header"><div class="bz-eyebrow">{_e(eyebrow)}</div>'
            f'<h1 class="bz-page-title">{_e(titulo)}</h1>{desc}{datos}</div>')


def cabecera_seccion(titulo: str, descripcion: str | None = None,
                     eyebrow: str | None = None) -> None:
    ante = f'<div class="bz-eyebrow">{_e(eyebrow)}</div>' if eyebrow else ""
    desc = f"<p>{_texto(descripcion)}</p>" if descripcion else ""
    _pintar(f'<div class="bz-section">{ante}<h3>{_e(titulo)}</h3>{desc}</div>')


def filtros(clave: str = "filtros"):
    """FilterBar: un unico bloque para todos los controles de exploracion."""
    return st.container(key=clave)


def panel(clave: str):
    """Superficie elevada para agrupar controles (por ejemplo, un escenario)."""
    return st.container(key=f"panel_{clave}")


def contenedor_grafico(clave: str):
    """ChartContainer / MapContainer."""
    return st.container(key=f"grafico_{clave}")


# ----------------------------------------------------------------- piezas

def etiqueta_riesgo(banda) -> str:
    """RiskBadge. El color nunca va solo: siempre lleva el nivel escrito."""
    if banda is None or (isinstance(banda, float) and math.isnan(banda)) or str(banda) == "nan":
        return '<span class="bz-badge sin-dato">Sin dato</span>'
    clase = CLASE_BANDA.get(str(banda), "sin-dato")
    return f'<span class="bz-badge {clase}"><span class="bz-dot"></span>{_e(banda)}</span>'


def etiqueta_estado(texto: str, en_desarrollo: bool = False) -> str:
    clase = "bz-status dev" if en_desarrollo else "bz-status"
    return f'<span class="{clase}">{_e(texto)}</span>'


def tarjeta_cifra(titulo: str, valor: str, unidad: str | None = None, pie: str | None = None,
                  ayuda: str | None = None, delta: str | None = None,
                  tono: str = "neutro", extra: str = "", clase: str = "") -> str:
    """MetricCard. Devuelve HTML para componer varias en una rejilla."""
    ayuda_html = f'<span class="bz-help" title="{_e(ayuda)}">?</span>' if ayuda else ""
    unidad_html = f"<small>{_e(unidad)}</small>" if unidad else ""
    delta_html = f' <span class="bz-delta {tono}">{_e(delta)}</span>' if delta else ""
    pie_texto = _texto(pie) if pie else ""
    pie_html = f'<div class="bz-card-foot">{pie_texto}{delta_html}</div>' if pie or delta else ""
    return (f'<div class="bz-card {clase}"><div class="bz-card-title">{_e(titulo)}{ayuda_html}</div>'
            f'<div class="bz-kpi">{_e(valor)}{unidad_html}</div>{extra}{pie_html}</div>')


def tarjeta_destacada(eyebrow: str, titulo: str, subtitulo: str,
                      cifras: list[tuple[str, str]], banda=None, clase: str = "") -> str:
    """Tarjeta para el elemento principal de una vista: un tramo, una provincia."""
    stats = "".join(f'<div class="bz-stat"><b>{_e(v)}</b><span>{_e(k)}</span></div>'
                    for v, k in cifras)
    badge = etiqueta_riesgo(banda) if banda is not None else ""
    return (f'<div class="bz-card bz-feature {clase}"><div class="bz-feature-main"><div>'
            f'<div class="bz-eyebrow">{_e(eyebrow)}</div>'
            f'<div class="bz-feature-title">{_e(titulo)}</div>'
            f'<div class="bz-feature-sub">{_e(subtitulo)}</div></div>{badge}</div>'
            f'<div class="bz-stats">{stats}</div></div>')


def cifras_compactas(cifras: list[tuple[str, str]]) -> str:
    """Fila de cifras secundarias para el pie de una tarjeta."""
    celdas = "".join(f'<div class="bz-stat"><b>{_e(v)}</b><span>{_e(k)}</span></div>'
                     for v, k in cifras)
    return f'<div class="bz-stats compactas" style="--n:{len(cifras)}">{celdas}</div>'


def pila(tarjetas: list[str]) -> str:
    """Varias tarjetas apiladas en una misma celda de la rejilla."""
    return f'<div class="bz-stack">{"".join(tarjetas)}</div>'


def rejilla(tarjetas: list[str], plantilla: str | None = None) -> None:
    estilo_rejilla = f' style="--plantilla:{plantilla}"' if plantilla else ""
    _pintar(f'<div class="bz-grid"{estilo_rejilla}>{"".join(tarjetas)}</div>')


def conclusiones(items: list[tuple[str, str]], titulo: str = "Lo que dicen los datos",
                 eyebrow: str = "Insights del modelo", columnas: int | None = None) -> None:
    """InsightCards numeradas. La metodologia va aparte, en un desplegable."""
    cabecera_seccion(titulo, eyebrow=eyebrow)
    tarjetas = "".join(
        f'<div class="bz-card bz-insight"><div class="bz-insight-num">{i:02d}</div>'
        f'<div class="bz-insight-title">{_e(t)}</div>'
        f'<div class="bz-insight-body">{_texto(c)}</div></div>'
        for i, (t, c) in enumerate(items, start=1))
    plantilla = f"repeat({columnas or min(len(items), 3)}, minmax(0, 1fr))"
    _pintar(f'<div class="bz-grid" style="--plantilla:{plantilla}">{tarjetas}</div>')


def tarjeta_texto(titulo: str, cuerpo: str) -> str:
    return (f'<div class="bz-card bz-insight"><div class="bz-insight-title">{_e(titulo)}</div>'
            f'<div class="bz-insight-body">{_texto(cuerpo)}</div></div>')


def lista_simple(items: list[str]) -> str:
    filas = "".join(f"<li>{_texto(i)}</li>" for i in items)
    return f'<div class="bz-card"><ul class="bz-ul">{filas}</ul></div>'


def recorrido(provincias: list[str], prefijo: str = "Atraviesas") -> None:
    pasos = " <span class='suave'>→</span> ".join(f"<b>{_e(p)}</b>" for p in provincias)
    _pintar(f'<div class="bz-chain">{_e(prefijo)} {pasos}</div>')


def panel_info(texto: str, aviso: bool = False, etiqueta: str | None = None) -> None:
    """InfoPanel para contexto que el usuario necesita al lado del dato."""
    clase = "bz-info aviso" if aviso else "bz-info"
    icono = "!" if aviso else "i"
    cabeza = f"<b>{_e(etiqueta)}.</b> " if etiqueta else ""
    _pintar(f'<div class="{clase}"><span class="bz-info-icon">{icono}</span>'
            f'<div>{cabeza}{_texto(texto)}</div></div>')


def en_desarrollo(texto: str) -> None:
    panel_info(texto, aviso=True, etiqueta="En desarrollo")


def estado_vacio(titulo: str, cuerpo: str) -> None:
    _pintar(f'<div class="bz-empty"><div class="bz-empty-title">{_e(titulo)}</div>'
            f'<div class="bz-empty-body">{_texto(cuerpo)}</div></div>')


def lista_riesgo(items: list[tuple[str, str, object]]) -> None:
    filas = "".join(
        f'<div class="bz-list-item"><div><div class="principal">{_e(p)}</div>'
        f'<div class="detalle">{_e(d)}</div></div>{etiqueta_riesgo(b)}</div>'
        for p, d, b in items)
    _pintar(f'<div class="bz-list">{filas}</div>')


# ------------------------------------------------------------------ tabla

def columna(campo: str, titulo: str, tipo: str = "texto", decimales: int = 0,
            sufijo: str = "", maximo: float | None = None, secundario: str | None = None) -> dict:
    """Definicion de columna para tabla().

    tipo: texto | fuerte | suave | derecha | num | pct | riesgo | barra | percentil
    secundario: campo que se muestra debajo, en gris (texto y fuerte)
    """
    return dict(campo=campo, titulo=titulo, tipo=tipo, decimales=decimales,
                sufijo=sufijo, maximo=maximo, secundario=secundario)


def _celda(valor, col: dict) -> tuple[str, str]:
    tipo = col["tipo"]
    if tipo == "riesgo":
        return "", etiqueta_riesgo(valor)
    if tipo == "derecha":
        return "num", _e(valor)
    vacio = valor is None or (isinstance(valor, float) and math.isnan(valor))
    if tipo in ("num", "pct", "barra", "percentil"):
        if vacio:
            return "num suave", "—"
        if tipo == "num":
            return "num", _e(estilo.num(valor, col["decimales"]) + col["sufijo"])
        if tipo == "pct":
            return "num", _e(estilo.pct(valor, col["decimales"]))
        if tipo == "percentil":
            return "num", f"{valor:.0f}<span class='suave'> / 100</span>"
        maximo = col["maximo"] or 1
        ancho = max(0.0, min(100.0, valor / maximo * 100))
        texto = (estilo.pct(valor, col["decimales"]) if maximo == 1
                 else estilo.num(valor, col["decimales"]) + col["sufijo"])
        return "num", (f'<div class="bz-bar"><span>{_e(texto)}</span>'
                       f'<i><b style="width:{ancho:.1f}%"></b></i></div>')
    clase = {"fuerte": "fuerte", "suave": "suave"}.get(tipo, "")
    return clase, "—" if vacio else _e(valor)


def tabla(datos: pd.DataFrame, columnas: list[dict], alto: int | None = None,
          ranking: bool = False, ajustar: bool = False) -> None:
    """DataTable de producto: cabecera fija, numeros alineados, etiquetas de
    riesgo y filas compactas con hover."""
    cabecera = ('<th class="rank">#</th>' if ranking else "") + "".join(
        f'<th class="{"num" if c["tipo"] in ("num", "pct", "barra", "percentil", "derecha") else ""}">'
        f'{_e(c["titulo"])}</th>' for c in columnas)
    filas = []
    for i, (_, fila) in enumerate(datos.iterrows(), start=1):
        celdas = [f'<td class="rank">{i}</td>'] if ranking else []
        for c in columnas:
            clase, contenido = _celda(fila[c["campo"]], c)
            if c.get("secundario"):
                sub = fila[c["secundario"]]
                if not (isinstance(sub, float) and math.isnan(sub)):
                    contenido += f'<div class="sub">{_e(sub)}</div>'
            celdas.append(f'<td class="{clase}">{contenido}</td>')
        filas.append(f"<tr>{''.join(celdas)}</tr>")
    altura = f' style="--alto:{alto}px"' if alto else ""
    clase = "bz-table ajustar" if ajustar else "bz-table"
    _pintar(f'<div class="bz-table-wrap"{altura}><table class="{clase}"><thead><tr>{cabecera}'
            f'</tr></thead><tbody>{"".join(filas)}</tbody></table></div>')
