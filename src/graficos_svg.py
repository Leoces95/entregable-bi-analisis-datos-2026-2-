"""Libreria de graficos SVG para el proyecto de E-commerce.

El entorno de ejecucion no incluye matplotlib/seaborn/plotly, por lo que los
graficos se generan como SVG escrito a mano. Los SVG se muestran de forma nativa
en Jupyter/HTML y tambien se exportan como archivos independientes reutilizables
en el dashboard y en las diapositivas del video.

Convenciones:
  * Todos los graficos usan la paleta corporativa definida en PALETA.
  * Las cifras se formatean con separador de miles y sufijo $ / %.
  * Cada funcion devuelve una cadena SVG lista para `IPython.display.SVG`.
"""
from __future__ import annotations

import html
import math
from typing import Iterable, Sequence

# --------------------------------------------------------------------------
# Paleta y utilidades
# --------------------------------------------------------------------------
PALETA = {
    "tinta": "#12263A",
    "tinta_suave": "#5A6B7B",
    "rejilla": "#E3E8EE",
    "fondo": "#FFFFFF",
    "fondo_alt": "#F7F9FC",
    "primario": "#1F6FEB",
    "secundario": "#00A3A3",
    "acento": "#F2A63B",
    "alerta": "#D64550",
    "exito": "#2E9E5B",
    "violeta": "#7B5EA7",
}
CATEGORICOS = [PALETA["primario"], PALETA["secundario"], PALETA["acento"],
               PALETA["violeta"], PALETA["exito"], PALETA["alerta"]]
REGION_COLOR = {"West": "#1F6FEB", "East": "#00A3A3",
                "Central": "#F2A63B", "South": "#7B5EA7"}
CATEGORIA_COLOR = {"Technology": "#1F6FEB", "Furniture": "#F2A63B",
                   "Office Supplies": "#00A3A3"}
SEGMENTO_COLOR = {"Consumer": "#1F6FEB", "Corporate": "#F2A63B",
                  "Home Office": "#00A3A3"}


def dinero(v: float, dec: int = 0) -> str:
    return f"${v:,.{dec}f}"


def abrev(v: float) -> str:
    a = abs(v)
    if a >= 1_000_000:
        return f"${v/1_000_000:.1f}M"
    if a >= 1_000:
        return f"${v/1_000:.0f}K"
    return f"${v:.0f}"


def pct(v: float, dec: int = 1) -> str:
    return f"{v*100:.{dec}f}%"


def _esc(t: str) -> str:
    return html.escape(str(t))


def _svg(w: int, h: int, cuerpo: str, titulo: str, subtitulo: str = "") -> str:
    """Envuelve el cuerpo del grafico en un SVG con titulo y subtitulo."""
    cabecera = (
        f'<text x="16" y="26" font-family="Segoe UI, Arial, sans-serif" '
        f'font-size="16" font-weight="700" fill="{PALETA["tinta"]}">{_esc(titulo)}</text>'
    )
    if subtitulo:
        cabecera += (
            f'<text x="16" y="45" font-family="Segoe UI, Arial, sans-serif" '
            f'font-size="11.5" fill="{PALETA["tinta_suave"]}">{_esc(subtitulo)}</text>'
        )
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" '
        f'role="img" aria-label="{_esc(titulo)}" style="background:{PALETA["fondo"]};'
        f'font-family:Segoe UI, Arial, sans-serif">'
        f'<rect width="{w}" height="{h}" fill="{PALETA["fondo"]}"/>{cabecera}{cuerpo}</svg>'
    )


def _eje_y(lo: float, hi: float, x: float, y0: float, y1: float, n: int = 5,
           fmt=abrev, rejilla_hasta: float | None = None) -> tuple[str, float]:
    """Dibuja eje Y con rejilla. Devuelve (svg, funcion_de_escala)."""
    rejilla_hasta = x if rejilla_hasta is None else rejilla_hasta

    def esc(v: float) -> float:
        return y1 - (v - lo) / (hi - lo) * (y1 - y0)

    partes = []
    for i in range(n + 1):
        v = lo + (hi - lo) * i / n
        yy = esc(v)
        partes.append(
            f'<line x1="{x:.1f}" y1="{yy:.1f}" x2="{rejilla_hasta:.1f}" y2="{yy:.1f}" '
            f'stroke="{PALETA["rejilla"]}" stroke-width="1"/>'
        )
        partes.append(
            f'<text x="{x-8:.1f}" y="{yy+4:.1f}" text-anchor="end" font-size="10.5" '
            f'fill="{PALETA["tinta_suave"]}">{_esc(fmt(v))}</text>'
        )
    return "".join(partes), esc


# --------------------------------------------------------------------------
# 1. Linea temporal (multi-serie)
# --------------------------------------------------------------------------
def linea(x: Sequence, series: dict[str, Sequence[float]], titulo: str,
          subtitulo: str = "", w: int = 900, h: int = 400, colores: dict | None = None,
          fmt=abrev, anotaciones: Sequence[dict] | None = None,
          banda: tuple[int, int] | None = None, fmt_x=None) -> str:
    """Grafico de lineas con marcadores, leyenda y anotaciones opcionales."""
    izq, der, arriba, abajo = 78, 24, 62, 52
    x0, x1, y0, y1 = izq, w - der, arriba, h - abajo
    # Se descartan los huecos (None/NaN) para el cálculo de la escala.
    limpios = [v for s in series.values() for v in s
               if v is not None and not (isinstance(v, float) and math.isnan(v))]
    if not limpios:
        raise ValueError("La serie no contiene valores representables")
    hi = max(limpios) * 1.15
    lo = min(0, min(limpios) * 1.05)
    rejilla, esc = _eje_y(lo, hi, x0, y0, y1, fmt=fmt)
    n = len(x)
    pos = {k: x0 + (x1 - x0) * (i / (n - 1) if n > 1 else 0.5) for i, k in enumerate(x)}
    cuerpo = [rejilla]
    # banda de resaltado (p. ej. Q4)
    if banda:
        for i, k in enumerate(x):
            if banda[0] <= i <= banda[1]:
                xx = pos[k]
                ancho = (x1 - x0) / max(1, n - 1)
                cuerpo.append(
                    f'<rect x="{xx-ancho/2:.1f}" y="{y0}" width="{ancho:.1f}" '
                    f'height="{y1-y0}" fill="{PALETA["acento"]}" opacity="0.10"/>')
    # eje X con etiquetas seleccionadas
    salto = max(1, n // 12)
    for i, k in enumerate(x):
        if i % salto == 0 or i == n - 1:
            cuerpo.append(
                f'<text x="{pos[k]:.1f}" y="{y1+18:.1f}" text-anchor="middle" font-size="10.5" '
                f'fill="{PALETA["tinta_suave"]}">'
                f'{_esc(fmt_x(k) if fmt_x else k)}</text>')
    cuerpo.append(f'<line x1="{x0}" y1="{y1}" x2="{x1}" y2="{y1}" '
                  f'stroke="{PALETA["tinta_suave"]}" stroke-width="1"/>')
    # series (los puntos con valor nulo se omiten, permitiendo series parciales)
    for j, (nombre, vals) in enumerate(series.items()):
        color = (colores or {}).get(nombre) or CATEGORICOS[j % len(CATEGORICOS)]
        puntos = [(pos[k], esc(v)) for k, v in zip(x, vals)
                  if v is not None and not (isinstance(v, float) and math.isnan(v))]
        if not puntos:
            continue
        pts = " ".join(f"{px:.1f},{py:.1f}" for px, py in puntos)
        cuerpo.append(f'<polyline points="{pts}" fill="none" stroke="{color}" '
                      f'stroke-width="2.6" stroke-linejoin="round"/>')
        for px, py in puntos:
            cuerpo.append(f'<circle cx="{px:.1f}" cy="{py:.1f}" r="3.2" '
                          f'fill="{color}" stroke="#fff" stroke-width="1.2"/>')
    # leyenda
    lx = x0
    for j, nombre in enumerate(series):
        color = (colores or {}).get(nombre) or CATEGORICOS[j % len(CATEGORICOS)]
        cuerpo.append(f'<rect x="{lx}" y="{arriba-30}" width="22" height="4" rx="2" fill="{color}"/>')
        cuerpo.append(f'<text x="{lx+28}" y="{arriba-25}" font-size="11" '
                      f'fill="{PALETA["tinta"]}">{_esc(nombre)}</text>')
        lx += 34 + len(str(nombre)) * 7.2
    # anotaciones
    for an in (anotaciones or []):
        xx, vy = pos[an["x"]], esc(an["y"])
        dy = an.get("dy", -18)
        cuerpo.append(
            f'<line x1="{xx:.1f}" y1="{vy:.1f}" x2="{xx:.1f}" y2="{vy+dy:.1f}" '
            f'stroke="{PALETA["tinta_suave"]}" stroke-width="1" stroke-dasharray="3 2"/>')
        cuerpo.append(
            f'<text x="{xx:.1f}" y="{vy+dy-4:.1f}" text-anchor="middle" font-size="10.5" '
            f'font-weight="600" fill="{PALETA["tinta"]}">{_esc(an["texto"])}</text>')
    return _svg(w, h, "".join(cuerpo), titulo, subtitulo)


# --------------------------------------------------------------------------
# 2. Barras verticales (simples o agrupadas)
# --------------------------------------------------------------------------
def barras(cats: Sequence[str], series: dict[str, Sequence[float]], titulo: str,
           subtitulo: str = "", w: int = 900, h: int = 400, colores: dict | None = None,
           fmt=abrev, horizontal: bool = False, etiquetas: bool = True,
           linea_meta: tuple[float, str] | None = None) -> str:
    """Barras verticales simples/agrupadas. Con `horizontal=True` gira el grafico."""
    if horizontal:
        return _barras_h(cats, series, titulo, subtitulo, w, h, colores, fmt, etiquetas)
    izq, der, arriba, abajo = 78, 24, 66, 58
    x0, x1, y0, y1 = izq, w - der, arriba, h - abajo
    todos = [v for s in series.values() for v in s]
    hi = max(todos) * 1.16
    rejilla, esc = _eje_y(0, hi, x0, y0, y1, fmt=fmt)
    cuerpo = [rejilla]
    n = len(cats)
    ancho_grupo = (x1 - x0) / n
    m = len(series)
    ancho_barra = min(58.0, ancho_grupo * 0.68 / m)
    for i, c in enumerate(cats):
        centro = x0 + ancho_grupo * (i + 0.5)
        for j, (nombre, vals) in enumerate(series.items()):
            v = vals[i]
            color = (colores or {}).get(nombre) or CATEGORICOS[j % len(CATEGORICOS)]
            bx = centro - (m * ancho_barra) / 2 + j * ancho_barra
            by = esc(v)
            cuerpo.append(f'<rect x="{bx:.1f}" y="{by:.1f}" width="{ancho_barra-3:.1f}" '
                          f'height="{max(0.6, y1-by):.1f}" rx="2.5" fill="{color}">'
                          f'<title>{_esc(nombre)} · {_esc(c)}: {_esc(fmt(v))}</title></rect>')
            if etiquetas and m == 1:
                cuerpo.append(f'<text x="{bx+(ancho_barra-3)/2:.1f}" y="{by-6:.1f}" '
                              f'text-anchor="middle" font-size="10.5" font-weight="600" '
                              f'fill="{PALETA["tinta"]}">{_esc(fmt(v))}</text>')
        cuerpo.append(f'<text x="{centro:.1f}" y="{y1+20:.1f}" text-anchor="middle" '
                      f'font-size="11" fill="{PALETA["tinta"]}">{_esc(c)}</text>')
    if len(series) > 1:
        lx = x0
        for j, nombre in enumerate(series):
            color = (colores or {}).get(nombre) or CATEGORICOS[j % len(CATEGORICOS)]
            cuerpo.append(f'<rect x="{lx}" y="{arriba-30}" width="12" height="12" rx="2" fill="{color}"/>')
            cuerpo.append(f'<text x="{lx+18}" y="{arriba-19}" font-size="11" '
                          f'fill="{PALETA["tinta"]}">{_esc(nombre)}</text>')
            lx += 26 + len(str(nombre)) * 7.2
    if linea_meta:
        vy = esc(linea_meta[0])
        cuerpo.append(f'<line x1="{x0}" y1="{vy:.1f}" x2="{x1}" y2="{vy:.1f}" '
                      f'stroke="{PALETA["alerta"]}" stroke-width="1.8" stroke-dasharray="6 3"/>')
        cuerpo.append(f'<text x="{x1-4}" y="{vy-6:.1f}" text-anchor="end" font-size="10.5" '
                      f'font-weight="600" fill="{PALETA["alerta"]}">{_esc(linea_meta[1])}</text>')
    return _svg(w, h, "".join(cuerpo), titulo, subtitulo)


def _barras_h(cats, series, titulo, subtitulo, w, h, colores, fmt, etiquetas):
    izq, der, arriba, abajo = 210, 90, 60, 40
    x0, x1, y0, y1 = izq, w - der, arriba, h - abajo
    nombre, vals = next(iter(series.items()))
    hi = max(vals) * 1.12
    n = len(cats)
    alto = (y1 - y0) / n

    def esc(v):
        return x0 + v / hi * (x1 - x0)

    cuerpo = []
    for i in range(6):
        v = hi * i / 5
        cuerpo.append(f'<line x1="{esc(v):.1f}" y1="{y0}" x2="{esc(v):.1f}" y2="{y1}" '
                      f'stroke="{PALETA["rejilla"]}" stroke-width="1"/>')
        cuerpo.append(f'<text x="{esc(v):.1f}" y="{y1+16}" text-anchor="middle" font-size="10.5" '
                      f'fill="{PALETA["tinta_suave"]}">{_esc(fmt(v))}</text>')
    for i, c in enumerate(cats):
        v = vals[i]
        yb = y0 + alto * i + alto * 0.16
        color = (colores or {}).get(c) or CATEGORICOS[i % len(CATEGORICOS)]
        cuerpo.append(f'<rect x="{x0}" y="{yb:.1f}" width="{max(1.0, esc(v)-x0):.1f}" '
                      f'height="{alto*0.68:.1f}" rx="3" fill="{color}">'
                      f'<title>{_esc(c)}: {_esc(fmt(v))}</title></rect>')
        cuerpo.append(f'<text x="{x0-10}" y="{yb+alto*0.44:.1f}" text-anchor="end" font-size="11" '
                      f'fill="{PALETA["tinta"]}">{_esc(c)}</text>')
        if etiquetas:
            cuerpo.append(f'<text x="{esc(v)+8:.1f}" y="{yb+alto*0.44:.1f}" font-size="10.5" '
                          f'font-weight="600" fill="{PALETA["tinta"]}">{_esc(fmt(v))}</text>')
    return _svg(w, h, "".join(cuerpo), titulo, subtitulo)


# --------------------------------------------------------------------------
# 3. Barras apiladas 100 %
# --------------------------------------------------------------------------
def apiladas(cats: Sequence[str], series: dict[str, Sequence[float]], titulo: str,
             subtitulo: str = "", w: int = 900, h: int = 400, colores: dict | None = None,
             normalizar: bool = True) -> str:
    izq, der, arriba, abajo = 78, 24, 66, 54
    x0, x1, y0, y1 = izq, w - der, arriba, h - abajo
    cuerpo = []
    if normalizar:
        totales = [sum(series[k][i] for k in series) for i in range(len(cats))]
        for i in range(6):
            yy = y1 - (y1 - y0) * i / 5
            cuerpo.append(f'<line x1="{x0}" y1="{yy:.1f}" x2="{x1}" y2="{yy:.1f}" '
                          f'stroke="{PALETA["rejilla"]}"/>')
            cuerpo.append(f'<text x="{x0-8}" y="{yy+4:.1f}" text-anchor="end" font-size="10.5" '
                          f'fill="{PALETA["tinta_suave"]}">{i*20}%</text>')
    n = len(cats)
    ancho_grupo = (x1 - x0) / n
    ancho = min(80.0, ancho_grupo * 0.62)
    for i, c in enumerate(cats):
        cx = x0 + ancho_grupo * (i + 0.5)
        acum = 0.0
        total = sum(series[k][i] for k in series) if normalizar else 1.0
        for j, nombre in enumerate(series):
            v = series[nombre][i]
            frac = v / total if normalizar else v
            color = (colores or {}).get(nombre) or CATEGORICOS[j % len(CATEGORICOS)]
            alto = frac * (y1 - y0)
            yy = y1 - acum - alto
            cuerpo.append(f'<rect x="{cx-ancho/2:.1f}" y="{yy:.1f}" width="{ancho:.1f}" '
                          f'height="{alto:.1f}" fill="{color}">'
                          f'<title>{_esc(nombre)} · {_esc(c)}: {pct(frac)}</title></rect>')
            if alto > 15:
                cuerpo.append(f'<text x="{cx:.1f}" y="{yy+alto/2+4:.1f}" text-anchor="middle" '
                              f'font-size="10.5" font-weight="700" fill="#fff">{pct(frac,0)}</text>')
            acum += alto
        cuerpo.append(f'<text x="{cx:.1f}" y="{y1+20:.1f}" text-anchor="middle" font-size="11" '
                      f'fill="{PALETA["tinta"]}">{_esc(c)}</text>')
    lx = x0
    for j, nombre in enumerate(series):
        color = (colores or {}).get(nombre) or CATEGORICOS[j % len(CATEGORICOS)]
        cuerpo.append(f'<rect x="{lx}" y="{arriba-30}" width="12" height="12" rx="2" fill="{color}"/>')
        cuerpo.append(f'<text x="{lx+18}" y="{arriba-19}" font-size="11" '
                      f'fill="{PALETA["tinta"]}">{_esc(nombre)}</text>')
        lx += 26 + len(str(nombre)) * 7.2
    return _svg(w, h, "".join(cuerpo), titulo, subtitulo)


# --------------------------------------------------------------------------
# 4. Pareto (barras + curva acumulada)
# --------------------------------------------------------------------------
def pareto(cats: Sequence[str], vals: Sequence[float], titulo: str, subtitulo: str = "",
           w: int = 960, h: int = 420, umbral: float = 0.8) -> str:
    izq, der, arriba, abajo = 84, 64, 66, 96
    x0, x1, y0, y1 = izq, w - der, arriba, h - abajo
    total = sum(vals)
    hi = max(vals) * 1.15
    rejilla, esc = _eje_y(0, hi, x0, y0, y1, fmt=abrev)

    def esc_p(p):
        return y1 - p * (y1 - y0) / 1.0

    cuerpo = [rejilla]
    for i in range(5):
        p = (i + 1) / 5
        cuerpo.append(f'<text x="{w-der+8}" y="{esc_p(p)+4:.1f}" font-size="10.5" '
                      f'fill="{PALETA["secundario"]}">{pct(p,0)}</text>')
    n = len(cats)
    ancho_grupo = (x1 - x0) / n
    ancho = min(64.0, ancho_grupo * 0.66)
    acum = []
    s = 0.0
    for v in vals:
        s += v
        acum.append(s / total)
    corte = next((i for i, a in enumerate(acum) if a >= umbral), n - 1)
    for i, c in enumerate(cats):
        cx = x0 + ancho_grupo * (i + 0.5)
        by = esc(vals[i])
        color = PALETA["primario"] if i <= corte else "#B9C6D4"
        cuerpo.append(f'<rect x="{cx-ancho/2:.1f}" y="{by:.1f}" width="{ancho:.1f}" '
                      f'height="{max(0.6, y1-by):.1f}" rx="2" fill="{color}">'
                      f'<title>{_esc(c)}: {_esc(dinero(vals[i]))} · acum {pct(acum[i])}</title></rect>')
        cuerpo.append(f'<text x="{cx:.1f}" y="{y1+14:.1f}" text-anchor="end" font-size="9.5" '
                      f'fill="{PALETA["tinta_suave"]}" '
                      f'transform="rotate(-38 {cx:.1f} {y1+14:.1f})">{_esc(c)}</text>')
    pts = " ".join(f"{x0+ancho_grupo*(i+0.5):.1f},{esc_p(a):.1f}" for i, a in enumerate(acum))
    cuerpo.append(f'<polyline points="{pts}" fill="none" stroke="{PALETA["secundario"]}" '
                  f'stroke-width="2.4"/>')
    for i, a in enumerate(acum):
        cx = x0 + ancho_grupo * (i + 0.5)
        cuerpo.append(f'<circle cx="{cx:.1f}" cy="{esc_p(a):.1f}" r="3" fill="{PALETA["secundario"]}"/>')
    cuerpo.append(f'<line x1="{x0}" y1="{esc_p(umbral):.1f}" x2="{x1}" y2="{esc_p(umbral):.1f}" '
                  f'stroke="{PALETA["alerta"]}" stroke-dasharray="6 3" stroke-width="1.6"/>')
    cuerpo.append(f'<text x="{x1-4}" y="{esc_p(umbral)-6:.1f}" text-anchor="end" font-size="10.5" '
                  f'font-weight="600" fill="{PALETA["alerta"]}">Umbral 80% (regla de Pareto)</text>')
    cuerpo.append(f'<text x="{x0}" y="{arriba-32}" font-size="11" fill="{PALETA["primario"]}">'
                  f'■ Ingresos por subcategoria</text>')
    cuerpo.append(f'<text x="{x0+230}" y="{arriba-32}" font-size="11" fill="{PALETA["secundario"]}">'
                  f'● Acumulado</text>')
    return _svg(w, h, "".join(cuerpo), titulo, subtitulo)


# --------------------------------------------------------------------------
# 5. Mapa de calor matricial
# --------------------------------------------------------------------------
def heatmap(filas: Sequence[str], columnas: Sequence[str], valores: Sequence[Sequence[float]],
            titulo: str, subtitulo: str = "", w: int = 900, h: int = 380,
            fmt=abrev, paleta=None) -> str:
    izq, arriba, der, abajo = 176, 74, 96, 46
    x0, y0 = izq, arriba
    x1, y1 = w - der, h - abajo
    paleta = paleta or ["#EAF2FE", "#9DC3F5", "#4A90E2", "#1F6FEB", "#0B3E8C"]
    aplanado = [v for f in valores for v in f]
    lo, hi = min(aplanado), max(aplanado)

    def color(v):
        if hi == lo:
            return paleta[2]
        t = (v - lo) / (hi - lo)
        idx = min(len(paleta) - 1, int(t * len(paleta)))
        return paleta[idx]

    ancho = (x1 - x0) / len(columnas)
    alto = (y1 - y0) / len(filas)
    cuerpo = []
    for i, f in enumerate(filas):
        for j, c in enumerate(columnas):
            v = valores[i][j]
            cuerpo.append(
                f'<rect x="{x0+ancho*j:.1f}" y="{y0+alto*i:.1f}" width="{ancho-2:.1f}" '
                f'height="{alto-2:.1f}" rx="3" fill="{color(v)}">'
                f'<title>{_esc(f)} · {_esc(c)}: {_esc(fmt(v))}</title></rect>')
            claro = (v - lo) / (hi - lo) if hi > lo else 0.5
            cuerpo.append(
                f'<text x="{x0+ancho*(j+0.5):.1f}" y="{y0+alto*(i+0.6):.1f}" text-anchor="middle" '
                f'font-size="11" font-weight="600" fill="{"#fff" if claro>0.55 else PALETA["tinta"]}">'
                f'{_esc(fmt(v))}</text>')
        cuerpo.append(f'<text x="{x0-10}" y="{y0+alto*(i+0.6):.1f}" text-anchor="end" font-size="11.5" '
                      f'fill="{PALETA["tinta"]}">{_esc(f)}</text>')
    for j, c in enumerate(columnas):
        cuerpo.append(f'<text x="{x0+ancho*(j+0.5):.1f}" y="{y0-12}" text-anchor="middle" '
                      f'font-size="11.5" font-weight="600" fill="{PALETA["tinta"]}">{_esc(c)}</text>')
    return _svg(w, h, "".join(cuerpo), titulo, subtitulo)


# --------------------------------------------------------------------------
# 6. Dispersion con linea de tendencia
# --------------------------------------------------------------------------
def dispersion(xv: Sequence[float], yv: Sequence[float], titulo: str, subtitulo: str = "",
               w: int = 900, h: int = 420, etiqueta_x: str = "", etiqueta_y: str = "",
               color: str | None = None, tamaño: Sequence[float] | None = None,
               grupos: Sequence[str] | None = None, colores_grupo: dict | None = None,
               xticks: Sequence[float] | None = None, yticks: Sequence[float] | None = None,
               fmt_x=None, fmt_y=None, log_x: bool = False) -> str:
    izq, der, arriba, abajo = 84, 30, 66, 62
    x0, x1, y0, y1 = izq, w - der, arriba, h - abajo
    fmt_x = fmt_x or (lambda v: f"{v:,.0f}")
    fmt_y = fmt_y or (lambda v: f"{v:,.0f}")

    def tx(v):
        if log_x:
            lo, hi = math.log10(min(xv)), math.log10(max(xv))
            return x0 + (math.log10(v) - lo) / (hi - lo) * (x1 - x0)
        lo, hi = min(xv), max(xv)
        return x0 + (v - lo) / (hi - lo) * (x1 - x0)

    ylo, yhi = min(yv), max(yv)
    margen = (yhi - ylo) * 0.08 or 1
    ylo, yhi = ylo - margen, yhi + margen

    def ty(v):
        return y1 - (v - ylo) / (yhi - ylo) * (y1 - y0)

    cuerpo = []
    for i in range(6):
        v = ylo + (yhi - ylo) * i / 5
        cuerpo.append(f'<line x1="{x0}" y1="{ty(v):.1f}" x2="{x1}" y2="{ty(v):.1f}" '
                      f'stroke="{PALETA["rejilla"]}"/>')
        cuerpo.append(f'<text x="{x0-8}" y="{ty(v)+4:.1f}" text-anchor="end" font-size="10.5" '
                      f'fill="{PALETA["tinta_suave"]}">{_esc(fmt_y(v))}</text>')
    ticks_x = xticks or [min(xv) + (max(xv) - min(xv)) * i / 5 for i in range(6)]
    for v in ticks_x:
        cuerpo.append(f'<text x="{tx(v):.1f}" y="{y1+18:.1f}" text-anchor="middle" font-size="10.5" '
                      f'fill="{PALETA["tinta_suave"]}">{_esc(fmt_x(v))}</text>')
    colores_grupo = colores_grupo or {}
    for i in range(len(xv)):
        g = grupos[i] if grupos else None
        c = colores_grupo.get(g) if g else (color or PALETA["primario"])
        r = 4.0 if not tamaño else max(3.0, min(14.0, tamaño[i]))
        cuerpo.append(f'<circle cx="{tx(xv[i]):.1f}" cy="{ty(yv[i]):.1f}" r="{r:.1f}" '
                      f'fill="{c}" opacity="0.55" stroke="{c}" stroke-width="0.8">'
                      f'<title>{_esc(g + " · " if g else "")}{_esc(fmt_x(xv[i]))} → {_esc(fmt_y(yv[i]))}</title>'
                      f'</circle>')
    # tendencia OLS
    n = len(xv)
    mx, my = sum(xv) / n, sum(yv) / n
    sxx = sum((a - mx) ** 2 for a in xv)
    if sxx > 0:
        b = sum((a - mx) * (c - my) for a, c in zip(xv, yv)) / sxx
        a0 = my - b * mx
        xs = [min(xv), max(xv)]
        pts = " ".join(f"{tx(v):.1f},{ty(a0+b*v):.1f}" for v in xs)
        cuerpo.append(f'<polyline points="{pts}" fill="none" stroke="{PALETA["tinta"]}" '
                      f'stroke-width="2" stroke-dasharray="7 4"/>')
        ss_res = sum((c - (a0 + b * a)) ** 2 for a, c in zip(xv, yv))
        ss_tot = sum((c - my) ** 2 for c in yv)
        r2 = 1 - ss_res / ss_tot if ss_tot else 0
        cuerpo.append(f'<text x="{x1-6}" y="{y0+16}" text-anchor="end" font-size="11" '
                      f'font-weight="600" fill="{PALETA["tinta"]}">'
                      f'R² = {r2:.3f} · pendiente = {b:,.2f}</text>')
    if grupos:
        lx = x0
        vistos = []
        for g in grupos:
            if g in vistos:
                continue
            vistos.append(g)
            c = colores_grupo.get(g, PALETA["primario"])
            cuerpo.append(f'<circle cx="{lx+5}" cy="{arriba-26}" r="5" fill="{c}"/>')
            cuerpo.append(f'<text x="{lx+16}" y="{arriba-22}" font-size="11" '
                          f'fill="{PALETA["tinta"]}">{_esc(g)}</text>')
            lx += 30 + len(str(g)) * 7.2
    if etiqueta_x:
        cuerpo.append(f'<text x="{(x0+x1)/2:.1f}" y="{h-16}" text-anchor="middle" font-size="11" '
                      f'font-weight="600" fill="{PALETA["tinta_suave"]}">{_esc(etiqueta_x)}</text>')
    if etiqueta_y:
        cuerpo.append(f'<text x="18" y="{(y0+y1)/2:.1f}" text-anchor="middle" font-size="11" '
                      f'font-weight="600" fill="{PALETA["tinta_suave"]}" '
                      f'transform="rotate(-90 18 {(y0+y1)/2:.1f})">{_esc(etiqueta_y)}</text>')
    return _svg(w, h, "".join(cuerpo), titulo, subtitulo)


# --------------------------------------------------------------------------
# 7. Histograma
# --------------------------------------------------------------------------
def histograma(conteos: Sequence[float], bordes: Sequence[float], titulo: str,
               subtitulo: str = "", w: int = 900, h: int = 380, etiquetas=None,
               color: str | None = None, fmt=abrev) -> str:
    izq, der, arriba, abajo = 84, 24, 66, 62
    x0, x1, y0, y1 = izq, w - der, arriba, h - abajo
    hi = max(conteos) * 1.18
    rejilla, esc = _eje_y(0, hi, x0, y0, y1, fmt=lambda v: f"{v:,.0f}")
    cuerpo = [rejilla]
    n = len(conteos)
    ancho = (x1 - x0) / n
    for i, c in enumerate(conteos):
        by = esc(c)
        cuerpo.append(f'<rect x="{x0+ancho*i+1.5:.1f}" y="{by:.1f}" width="{ancho-3:.1f}" '
                      f'height="{max(0.6, y1-by):.1f}" fill="{color or PALETA["primario"]}" '
                      f'opacity="0.9"><title>{_esc(etiquetas[i] if etiquetas else "")}: '
                      f'{c:,.0f}</title></rect>')
        cuerpo.append(f'<text x="{x0+ancho*(i+0.5):.1f}" y="{y1+18:.1f}" text-anchor="middle" '
                      f'font-size="10" fill="{PALETA["tinta_suave"]}">'
                      f'{_esc(etiquetas[i] if etiquetas else "")}</text>')
    return _svg(w, h, "".join(cuerpo), titulo, subtitulo)


# --------------------------------------------------------------------------
# 8. Boxplot comparativo
# --------------------------------------------------------------------------
def boxplot(grupos: dict[str, Sequence[float]], titulo: str, subtitulo: str = "",
            w: int = 900, h: int = 400, colores: dict | None = None, fmt=abrev,
            log_y: bool = False) -> str:
    izq, der, arriba, abajo = 90, 30, 66, 58
    x0, x1, y0, y1 = izq, w - der, arriba, h - abajo

    def stats(v):
        s = sorted(v)
        n = len(s)
        q1 = s[int(0.25 * (n - 1))]
        med = s[int(0.5 * (n - 1))]
        q3 = s[int(0.75 * (n - 1))]
        iqr = q3 - q1
        inf = min(v for v in s if v >= q1 - 1.5 * iqr) if any(v >= q1 - 1.5 * iqr for v in s) else s[0]
        sup = max(v for v in s if v <= q3 + 1.5 * iqr) if any(v <= q3 + 1.5 * iqr for v in s) else s[-1]
        return q1, med, q3, inf, sup

    todos = [v for g in grupos.values() for v in g]
    lo, hi = min(todos), max(todos)
    pad = (hi - lo) * 0.08
    lo, hi = lo - pad, hi + pad

    def esc(v):
        return y1 - (v - lo) / (hi - lo) * (y1 - y0)

    cuerpo = []
    for i in range(6):
        v = lo + (hi - lo) * i / 5
        cuerpo.append(f'<line x1="{x0}" y1="{esc(v):.1f}" x2="{x1}" y2="{esc(v):.1f}" '
                      f'stroke="{PALETA["rejilla"]}"/>')
        cuerpo.append(f'<text x="{x0-8}" y="{esc(v)+4:.1f}" text-anchor="end" font-size="10.5" '
                      f'fill="{PALETA["tinta_suave"]}">{_esc(fmt(v))}</text>')
    n = len(grupos)
    ancho_grupo = (x1 - x0) / n
    cuerpo.append(f'<polygon points="{" ".join(f"{x0+i*ancho_grupo:.1f},{esc(0):.1f}" for i in range(n+1))}" '
                  f'fill="none"/>') if False else None
    for i, (nombre, vals) in enumerate(grupos.items()):
        q1, med, q3, inf, sup = stats(vals)
        cx = x0 + ancho_grupo * (i + 0.5)
        ancho = min(96.0, ancho_grupo * 0.5)
        color = (colores or {}).get(nombre) or CATEGORICOS[i % len(CATEGORICOS)]
        cuerpo.append(f'<line x1="{cx:.1f}" y1="{esc(inf):.1f}" x2="{cx:.1f}" y2="{esc(sup):.1f}" '
                      f'stroke="{color}" stroke-width="1.8"/>')
        cuerpo.append(f'<line x1="{cx-ancho/4:.1f}" y1="{esc(sup):.1f}" x2="{cx+ancho/4:.1f}" '
                      f'y2="{esc(sup):.1f}" stroke="{color}" stroke-width="1.8"/>')
        cuerpo.append(f'<line x1="{cx-ancho/4:.1f}" y1="{esc(inf):.1f}" x2="{cx+ancho/4:.1f}" '
                      f'y2="{esc(inf):.1f}" stroke="{color}" stroke-width="1.8"/>')
        cuerpo.append(f'<rect x="{cx-ancho/2:.1f}" y="{esc(q3):.1f}" width="{ancho:.1f}" '
                      f'height="{max(1.0, esc(q1)-esc(q3)):.1f}" fill="{color}" opacity="0.22" '
                      f'stroke="{color}" stroke-width="1.6" rx="3">'
                      f'<title>{_esc(nombre)} · mediana {_esc(fmt(med))} · n={len(vals)}</title></rect>')
        cuerpo.append(f'<line x1="{cx-ancho/2:.1f}" y1="{esc(med):.1f}" x2="{cx+ancho/2:.1f}" '
                      f'y2="{esc(med):.1f}" stroke="{color}" stroke-width="3"/>')
        cuerpo.append(f'<text x="{cx:.1f}" y="{y1+20:.1f}" text-anchor="middle" font-size="11" '
                      f'fill="{PALETA["tinta"]}">{_esc(nombre)}</text>')
        cuerpo.append(f'<text x="{cx:.1f}" y="{esc(med)-9:.1f}" text-anchor="middle" font-size="10.5" '
                      f'font-weight="700" fill="{PALETA["tinta"]}">{_esc(fmt(med))}</text>')
    return _svg(w, h, "".join(p for p in cuerpo if p), titulo, subtitulo)


# --------------------------------------------------------------------------
# 9. Small multiples (rejilla de mini lineas)
# --------------------------------------------------------------------------
def small_multiples(series: dict[str, tuple[Sequence, Sequence[float]]], titulo: str,
                    subtitulo: str = "", w: int = 920, columnas: int = 2,
                    alto_panel: int = 150, colores: dict | None = None, fmt=abrev,
                    fmt_x=None) -> str:
    filas = math.ceil(len(series) / columnas)
    h = 72 + filas * alto_panel
    ancho_panel = (w - 32) / columnas
    cuerpo = []
    for idx, (nombre, (x, y)) in enumerate(series.items()):
        r, c = divmod(idx, columnas)
        px = 16 + c * ancho_panel
        py = 62 + r * alto_panel
        color = (colores or {}).get(nombre) or CATEGORICOS[idx % len(CATEGORICOS)]
        cuerpo.append(f'<rect x="{px}" y="{py}" width="{ancho_panel-14:.1f}" '
                      f'height="{alto_panel-22}" rx="6" fill="{PALETA["fondo_alt"]}" '
                      f'stroke="{PALETA["rejilla"]}"/>')
        cuerpo.append(f'<text x="{px+10}" y="{py+18}" font-size="11.5" font-weight="700" '
                      f'fill="{PALETA["tinta"]}">{_esc(nombre)}</text>')
        ix0, ix1 = px + 52, px + ancho_panel - 28
        iy0, iy1 = py + 30, py + alto_panel - 40
        lo, hi = 0, max(y) * 1.12
        pts = " ".join(
            f"{ix0 + (ix1-ix0)*(i/(len(y)-1)):.1f},{iy1 - (v-lo)/(hi-lo)*(iy1-iy0):.1f}"
            for i, v in enumerate(y))
        for k in range(3):
            vv = lo + (hi - lo) * k / 2
            yy = iy1 - (vv - lo) / (hi - lo) * (iy1 - iy0)
            cuerpo.append(f'<line x1="{ix0}" y1="{yy:.1f}" x2="{ix1}" y2="{yy:.1f}" '
                          f'stroke="{PALETA["rejilla"]}"/>')
            cuerpo.append(f'<text x="{ix0-5}" y="{yy+3.5:.1f}" text-anchor="end" font-size="9" '
                          f'fill="{PALETA["tinta_suave"]}">{_esc(fmt(vv))}</text>')
        cuerpo.append(f'<polyline points="{pts}" fill="none" stroke="{color}" stroke-width="2.2"/>')
        cuerpo.append(f'<text x="{ix1}" y="{iy1+14}" text-anchor="end" font-size="9.5" '
                      f'fill="{PALETA["tinta_suave"]}">'
                      f'{_esc(fmt_x(x[-1]) if fmt_x else x[-1])}</text>')
        cuerpo.append(f'<text x="{ix0}" y="{iy1+14}" font-size="9.5" '
                      f'fill="{PALETA["tinta_suave"]}">'
                      f'{_esc(fmt_x(x[0]) if fmt_x else x[0])}</text>')
    return _svg(w, h, "".join(cuerpo), titulo, subtitulo)


# --------------------------------------------------------------------------
# 10. Cascada (waterfall)
# --------------------------------------------------------------------------
def cascada(etapas: Sequence[str], valores: Sequence[float], titulo: str, subtitulo: str = "",
            w: int = 900, h: int = 420, fmt=abrev) -> str:
    izq, der, arriba, abajo = 84, 24, 66, 64
    x0, x1, y0, y1 = izq, w - der, arriba, h - abajo
    acumulados = []
    acc = 0.0
    for v in valores:
        acumulados.append((acc, acc + v))
        acc += v
    todos = [a for par in acumulados for a in par] + [0, acc]
    lo, hi = min(todos), max(todos)
    pad = (hi - lo) * 0.15
    lo, hi = lo - pad, hi + pad

    def esc(v):
        return y1 - (v - lo) / (hi - lo) * (y1 - y0)

    cuerpo = []
    for i in range(6):
        v = lo + (hi - lo) * i / 5
        cuerpo.append(f'<line x1="{x0}" y1="{esc(v):.1f}" x2="{x1}" y2="{esc(v):.1f}" '
                      f'stroke="{PALETA["rejilla"]}"/>')
        cuerpo.append(f'<text x="{x0-8}" y="{esc(v)+4:.1f}" text-anchor="end" font-size="10.5" '
                      f'fill="{PALETA["tinta_suave"]}">{_esc(fmt(v))}</text>')
    cuerpo.append(f'<line x1="{x0}" y1="{esc(0):.1f}" x2="{x1}" y2="{esc(0):.1f}" '
                  f'stroke="{PALETA["tinta_suave"]}" stroke-width="1.2"/>')
    n = len(etapas)
    ancho_grupo = (x1 - x0) / n
    ancho = min(92.0, ancho_grupo * 0.6)
    for i, (nombre, v) in enumerate(zip(etapas, valores)):
        a, b = acumulados[i]
        cx = x0 + ancho_grupo * (i + 0.5)
        color = PALETA["exito"] if v >= 0 else PALETA["alerta"]
        if i == n - 1:
            color = PALETA["primario"]
            a, b = 0, b
        cuerpo.append(f'<rect x="{cx-ancho/2:.1f}" y="{esc(max(a,b)):.1f}" width="{ancho:.1f}" '
                      f'height="{abs(esc(b)-esc(a)):.1f}" rx="3" fill="{color}" opacity="0.92">'
                      f'<title>{_esc(nombre)}: {_esc(dinero(v))}</title></rect>')
        cuerpo.append(f'<text x="{cx:.1f}" y="{esc(max(a,b))-7:.1f}" text-anchor="middle" '
                      f'font-size="10.5" font-weight="700" fill="{PALETA["tinta"]}">'
                      f'{_esc(fmt(v))}</text>')
        cuerpo.append(f'<text x="{cx:.1f}" y="{y1+20:.1f}" text-anchor="middle" font-size="10.5" '
                      f'fill="{PALETA["tinta"]}">{_esc(nombre)}</text>')
        if i < n - 1:
            cuerpo.append(f'<line x1="{cx+ancho/2:.1f}" y1="{esc(b):.1f}" '
                          f'x2="{x0+ancho_grupo*(i+1.5)-ancho/2:.1f}" y2="{esc(b):.1f}" '
                          f'stroke="{PALETA["tinta_suave"]}" stroke-width="1" stroke-dasharray="3 2"/>')
    return _svg(w, h, "".join(cuerpo), titulo, subtitulo)


# --------------------------------------------------------------------------
# 11. Treemap (squarified simplificado)
# --------------------------------------------------------------------------
def treemap(datos: dict[str, float], titulo: str, subtitulo: str = "", w: int = 920,
            h: int = 440, colores: dict | None = None) -> str:
    x0, y0, x1, y1 = 16, 62, w - 16, h - 16
    items = sorted(datos.items(), key=lambda kv: -kv[1])
    total = sum(datos.values())

    def layout(vals, x, y, dx, dy):
        """Squarify recursivo: devuelve [(valor, x, y, dx, dy)]."""
        if not vals:
            return []
        if len(vals) == 1:
            return [(vals[0], x, y, dx, dy)]
        mitad = sum(vals) / 2
        acc = 0.0
        corte = 1
        for i, v in enumerate(vals):
            if acc + v / 2 >= mitad:
                corte = i + 1
                break
            acc += v
        corte = max(1, min(len(vals) - 1, corte))
        a, b = vals[:corte], vals[corte:]
        fa = sum(a) / sum(vals)
        if dx >= dy:
            return (layout(a, x, y, dx * fa, dy) + layout(b, x + dx * fa, y, dx * (1 - fa), dy))
        return (layout(a, x, y, dx, dy * fa) + layout(b, x, y + dy * fa, dx, dy * (1 - fa)))

    cuerpo = []
    paleta = list((colores or {}).values()) or CATEGORICOS
    cajas = layout([v for _, v in items], x0, y0, x1 - x0, y1 - y0)
    for i, ((nombre, v), caja) in enumerate(zip(items, cajas)):
        _, cx, cy, cdx, cdy = caja
        color = (colores or {}).get(nombre) or CATEGORICOS[i % len(CATEGORICOS)]
        cuerpo.append(f'<rect x="{cx+1:.1f}" y="{cy+1:.1f}" width="{max(0,cdx-2):.1f}" '
                      f'height="{max(0,cdy-2):.1f}" rx="4" fill="{color}" opacity="0.9" '
                      f'stroke="#fff" stroke-width="1.5">'
                      f'<title>{_esc(nombre)}: {_esc(dinero(v))} ({pct(v/total)})</title></rect>')
        if cdx > 74 and cdy > 38:
            cuerpo.append(f'<text x="{cx+9:.1f}" y="{cy+20:.1f}" font-size="11.5" font-weight="700" '
                          f'fill="#fff">{_esc(nombre)}</text>')
            cuerpo.append(f'<text x="{cx+9:.1f}" y="{cy+36:.1f}" font-size="10.5" fill="#fff" '
                          f'opacity="0.92">{_esc(dinero(v))} · {pct(v/total,0)}</text>')
    return _svg(w, h, "".join(cuerpo), titulo, subtitulo)


# --------------------------------------------------------------------------
# 12. Grafico de embudo
# --------------------------------------------------------------------------
def embudo(etapas: Sequence[tuple[str, float, str]], titulo: str, subtitulo: str = "",
           w: int = 900, h: int = 300) -> str:
    izq, der, arriba = 220, 150, 62
    x0, x1 = izq, w - der
    alto = (h - arriba - 16) / len(etapas)
    cuerpo = []
    for i, (nombre, valor, nota) in enumerate(etapas):
        color = CATEGORICOS[i % len(CATEGORICOS)]
        yb = arriba + alto * i
        cuerpo.append(f'<rect x="{x0}" y="{yb+2:.1f}" width="{x1-x0:.1f}" '
                      f'height="{alto-6:.1f}" rx="4" fill="{color}" opacity="0.16"/>')
        cuerpo.append(f'<rect x="{x0}" y="{yb+2:.1f}" width="{(x1-x0)*valor:.1f}" '
                      f'height="{alto-6:.1f}" rx="4" fill="{color}"/>')
        cuerpo.append(f'<text x="{x0-12}" y="{yb+alto/2+4:.1f}" text-anchor="end" font-size="11.5" '
                      f'font-weight="600" fill="{PALETA["tinta"]}">{_esc(nombre)}</text>')
        cuerpo.append(f'<text x="{x1+10}" y="{yb+alto/2+4:.1f}" font-size="11" '
                      f'fill="{PALETA["tinta"]}">{_esc(nota)}</text>')
    return _svg(w, h, "".join(cuerpo), titulo, subtitulo)


# --------------------------------------------------------------------------
# 13. Mapa coropletico en rejilla de EE. UU.
# --------------------------------------------------------------------------
REJILLA_US = {
    "AK": (0, 0), "ME": (11, 0),
    "VT": (10, 1), "NH": (11, 1),
    "WA": (1, 2), "ID": (2, 2), "MT": (3, 2), "ND": (4, 2), "MN": (5, 2), "IL": (6, 2),
    "WI": (7, 2), "MI": (8, 2), "NY": (9, 2), "RI": (10, 2), "MA": (11, 2),
    "OR": (1, 3), "NV": (2, 3), "WY": (3, 3), "SD": (4, 3), "IA": (5, 3), "IN": (6, 3),
    "OH": (7, 3), "PA": (8, 3), "NJ": (9, 3), "CT": (10, 3),
    "CA": (1, 4), "UT": (2, 4), "CO": (3, 4), "NE": (4, 4), "MO": (5, 4), "KY": (6, 4),
    "WV": (7, 4), "VA": (8, 4), "MD": (9, 4), "DE": (10, 4),
    "AZ": (2, 5), "NM": (3, 5), "KS": (4, 5), "AR": (5, 5), "TN": (6, 5), "NC": (7, 5),
    "SC": (8, 5), "DC": (9, 5),
    "OK": (4, 6), "LA": (5, 6), "MS": (6, 6), "AL": (7, 6), "GA": (8, 6),
    "HI": (0, 7), "TX": (4, 7), "FL": (9, 7),
}
NOMBRE_A_ABREV = {
    "Alabama": "AL", "Arizona": "AZ", "Arkansas": "AR", "California": "CA", "Colorado": "CO",
    "Connecticut": "CT", "Delaware": "DE", "District of Columbia": "DC", "Florida": "FL",
    "Georgia": "GA", "Hawaii": "HI", "Idaho": "ID", "Illinois": "IL", "Indiana": "IN",
    "Iowa": "IA", "Kansas": "KS", "Kentucky": "KY", "Louisiana": "LA", "Maine": "ME",
    "Maryland": "MD", "Massachusetts": "MA", "Michigan": "MI", "Minnesota": "MN",
    "Mississippi": "MS", "Missouri": "MO", "Montana": "MT", "Nebraska": "NE", "Nevada": "NV",
    "New Hampshire": "NH", "New Jersey": "NJ", "New Mexico": "NM", "New York": "NY",
    "North Carolina": "NC", "North Dakota": "ND", "Ohio": "OH", "Oklahoma": "OK",
    "Oregon": "OR", "Pennsylvania": "PA", "Rhode Island": "RI", "South Carolina": "SC",
    "South Dakota": "SD", "Tennessee": "TN", "Texas": "TX", "Utah": "UT", "Vermont": "VT",
    "Virginia": "VA", "Washington": "WA", "West Virginia": "WV", "Wisconsin": "WI",
    "Wyoming": "WY",
}


def mapa_estados(valores: dict[str, float], titulo: str, subtitulo: str = "", w: int = 920,
                 h: int = 470, fmt=abrev, etiqueta: str = "Ingresos") -> str:
    """Coropletico en rejilla (tile grid map) para los 49 estados del dataset."""
    cw, ch = 66, 46
    ox, oy = 52, 86
    vals = list(valores.values())
    lo, hi = min(vals), max(vals)
    paleta = ["#EAF2FE", "#BCD6F7", "#7FAEEE", "#3D82DB", "#1F6FEB", "#123E7C"]

    def color(v):
        t = (v - lo) / (hi - lo) if hi > lo else 0.5
        return paleta[min(len(paleta) - 1, int(t * len(paleta)))]

    cuerpo = []
    for abrevi, dato in valores.items():
        pos = REJILLA_US.get(abrevi)
        if not pos:
            continue
        col, fila = pos
        x, y = ox + col * cw, oy + fila * ch
        cuerpo.append(f'<rect x="{x}" y="{y}" width="{cw-6}" height="{ch-6}" rx="4" '
                      f'fill="{color(dato)}" stroke="#fff" stroke-width="1.5">'
                      f'<title>{_esc(abrevi)}: {_esc(fmt(dato))}</title></rect>')
        cuerpo.append(f'<text x="{x+(cw-6)/2:.1f}" y="{y+16}" text-anchor="middle" font-size="10.5" '
                      f'font-weight="700" fill="{"#fff" if color(dato) in paleta[3:] else PALETA["tinta"]}">'
                      f'{_esc(abrevi)}</text>')
        cuerpo.append(f'<text x="{x+(cw-6)/2:.1f}" y="{y+31}" text-anchor="middle" font-size="9.5" '
                      f'fill="{"#fff" if color(dato) in paleta[3:] else PALETA["tinta"]}" opacity="0.9">'
                      f'{_esc(fmt(dato))}</text>')
    # leyenda anclada al borde inferior del lienzo
    lx, ly = ox, h - 52
    cuerpo.append(f'<text x="{lx}" y="{ly+14}" font-size="10.5" fill="{PALETA["tinta_suave"]}">'
                  f'{_esc(fmt(lo))}</text>')
    for i, c in enumerate(paleta):
        cuerpo.append(f'<rect x="{lx+58+i*30}" y="{ly+2}" width="28" height="13" fill="{c}"/>')
    cuerpo.append(f'<text x="{lx+58+len(paleta)*30+6}" y="{ly+14}" font-size="10.5" '
                  f'fill="{PALETA["tinta_suave"]}">{_esc(fmt(hi))}</text>')
    cuerpo.append(f'<text x="{lx+58}" y="{ly+30}" font-size="10.5" font-weight="600" '
                  f'fill="{PALETA["tinta"]}">{_esc(etiqueta)} por estado</text>')
    return _svg(w, h, "".join(cuerpo), titulo, subtitulo)


# --------------------------------------------------------------------------
# 14. Lollipop (ranking)
# --------------------------------------------------------------------------
def lollipop(cats: Sequence[str], vals: Sequence[float], titulo: str, subtitulo: str = "",
             w: int = 900, h: int | None = None, fmt=abrev, color: str | None = None) -> str:
    h = h or 90 + len(cats) * 30
    izq, der, arriba = 300, 110, 62
    x0, x1 = izq, w - der
    hi = max(vals) * 1.1
    cuerpo = []
    for i in range(5):
        v = hi * i / 4
        xx = x0 + (x1 - x0) * i / 4
        cuerpo.append(f'<line x1="{xx:.1f}" y1="{arriba}" x2="{xx:.1f}" y2="{h-16}" '
                      f'stroke="{PALETA["rejilla"]}"/>')
        cuerpo.append(f'<text x="{xx:.1f}" y="{h-2}" text-anchor="middle" font-size="10" '
                      f'fill="{PALETA["tinta_suave"]}">{_esc(fmt(v))}</text>')
    for i, (c, v) in enumerate(zip(cats, vals)):
        y = arriba + 12 + i * ((h - arriba - 30) / len(cats))
        xx = x0 + (x1 - x0) * v / hi
        col = color or CATEGORICOS[i % len(CATEGORICOS)]
        cuerpo.append(f'<line x1="{x0}" y1="{y:.1f}" x2="{xx:.1f}" y2="{y:.1f}" '
                      f'stroke="{col}" stroke-width="2" opacity="0.55"/>')
        cuerpo.append(f'<circle cx="{xx:.1f}" cy="{y:.1f}" r="6" fill="{col}">'
                      f'<title>{_esc(c)}: {_esc(fmt(v))}</title></circle>')
        etiqueta = c if len(c) <= 42 else c[:40] + "…"
        cuerpo.append(f'<text x="{x0-12}" y="{y+4:.1f}" text-anchor="end" font-size="10.5" '
                      f'fill="{PALETA["tinta"]}">{_esc(etiqueta)}</text>')
        cuerpo.append(f'<text x="{xx+12:.1f}" y="{y+4:.1f}" font-size="10.5" font-weight="600" '
                      f'fill="{PALETA["tinta"]}">{_esc(fmt(v))}</text>')
    return _svg(w, h, "".join(cuerpo), titulo, subtitulo)


# --------------------------------------------------------------------------
# 15. Tarjetas KPI (para el dashboard ejecutivo)
# --------------------------------------------------------------------------
def tarjetas_kpi(kpis: Sequence[dict], titulo: str = "", subtitulo: str = "", w: int = 920,
                 columnas: int = 4) -> str:
    """Cada KPI: {nombre, valor, delta (opcional), nota (opcional), color (opcional),
    positivo (bool)}."""
    filas = math.ceil(len(kpis) / columnas)
    h = (48 if titulo else 16) + filas * 108
    ancho = (w - 16 * (columnas + 1)) / columnas
    cuerpo = []
    for i, k in enumerate(kpis):
        r, c = divmod(i, columnas)
        x = 16 + c * (ancho + 16)
        y = (52 if titulo else 14) + r * 108
        color = k.get("color", PALETA["primario"])
        cuerpo.append(f'<rect x="{x}" y="{y}" width="{ancho:.1f}" height="94" rx="8" '
                      f'fill="{PALETA["fondo_alt"]}" stroke="{PALETA["rejilla"]}"/>')
        cuerpo.append(f'<rect x="{x}" y="{y}" width="4.5" height="94" rx="2" fill="{color}"/>')
        cuerpo.append(f'<text x="{x+16}" y="{y+24}" font-size="11" font-weight="600" '
                      f'fill="{PALETA["tinta_suave"]}">{_esc(k["nombre"])}</text>')
        cuerpo.append(f'<text x="{x+16}" y="{y+56}" font-size="24" font-weight="700" '
                      f'fill="{PALETA["tinta"]}">{_esc(k["valor"])}</text>')
        if k.get("delta"):
            pos = k.get("positivo", True)
            dc = PALETA["exito"] if pos else PALETA["alerta"]
            flecha = "▲" if pos else "▼"
            cuerpo.append(f'<text x="{x+16}" y="{y+78}" font-size="11.5" font-weight="700" '
                          f'fill="{dc}">{flecha} {_esc(k["delta"])}</text>')
        if k.get("nota"):
            cuerpo.append(f'<text x="{x+16+len(str(k.get("delta","")))*7+18}" y="{y+78}" '
                          f'font-size="10.5" fill="{PALETA["tinta_suave"]}">{_esc(k["nota"])}</text>')
    return _svg(w, h, "".join(cuerpo), titulo, subtitulo)


# --------------------------------------------------------------------------
# 16. Grafico de barras de contribucion (positivo/negativo divergente)
# --------------------------------------------------------------------------
def divergente(cats: Sequence[str], vals: Sequence[float], titulo: str, subtitulo: str = "",
               w: int = 900, h: int | None = None, fmt=abrev) -> str:
    h = h or 90 + len(cats) * 34
    centro = w * 0.56
    izq, arriba = 300, 62
    hi = max(abs(v) for v in vals) * 1.15

    def esc(v):
        return centro + v / hi * (w - centro - 120)

    cuerpo = [f'<line x1="{centro}" y1="{arriba-8}" x2="{centro}" y2="{h-24}" '
              f'stroke="{PALETA["tinta_suave"]}" stroke-width="1.2"/>']
    for i, (c, v) in enumerate(zip(cats, vals)):
        y = arriba + 10 + i * ((h - arriba - 34) / len(cats))
        color = PALETA["exito"] if v >= 0 else PALETA["alerta"]
        x1, x2 = sorted([centro, esc(v)])
        cuerpo.append(f'<rect x="{x1:.1f}" y="{y:.1f}" width="{max(1.0, x2-x1):.1f}" height="19" '
                      f'rx="3" fill="{color}" opacity="0.9">'
                      f'<title>{_esc(c)}: {_esc(dinero(v))}</title></rect>')
        cuerpo.append(f'<text x="{izq-12}" y="{y+14:.1f}" text-anchor="end" font-size="10.5" '
                      f'fill="{PALETA["tinta"]}">{_esc(c)}</text>')
        tx = esc(v) + (8 if v >= 0 else -8)
        anclaje = "start" if v >= 0 else "end"
        cuerpo.append(f'<text x="{tx:.1f}" y="{y+14:.1f}" text-anchor="{anclaje}" font-size="10.5" '
                      f'font-weight="600" fill="{PALETA["tinta"]}">{_esc(fmt(v))}</text>')
    return _svg(w, h, "".join(cuerpo), titulo, subtitulo)
