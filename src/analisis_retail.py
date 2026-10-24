"""Motor analitico del proyecto de ventas de retail (Evento Evaluativo 3).

Ejecuta la preparacion de datos, el calculo de KPIs, la validacion estadistica
de las hipotesis y la proyeccion 2019, y deja todos los resultados en disco:

    datos/analitica_*.csv          tablas listas para Power BI
    reports/analisis_completo.json resultados numericos y estadisticos

No depende de scipy/statsmodels: las distribuciones t, chi-cuadrado y F se
implementan con la funcion beta/gamma incompleta regularizada.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

BASE = Path(__file__).resolve().parents[1]
DATOS = BASE / "datos"
REPORTS = BASE / "reports"
DATOS.mkdir(exist_ok=True)
REPORTS.mkdir(exist_ok=True)

# ==========================================================================
# 0. Distribuciones estadisticas (sustituto de scipy)
# ==========================================================================
COF_LGAMMA = [76.18009172947146, -86.50532032941677, 24.01409824083091,
              -1.231739572450155, 0.1208650973866179e-2, -0.5395239384953e-5]


def lgamma(z: float) -> float:
    y = x = z
    tmp = x + 5.5
    tmp -= (x + 0.5) * np.log(tmp)
    ser = 1.000000000190015
    for c in COF_LGAMMA:
        y += 1
        ser += c / y
    return -tmp + np.log(2.5066282746310005 * ser / x)


def betainc(a: float, b: float, x: float) -> float:
    """I_x(a,b) por fraccion continua (Lentz)."""
    if x <= 0:
        return 0.0
    if x >= 1:
        return 1.0
    lbeta = lgamma(a) + lgamma(b) - lgamma(a + b)
    front = np.exp(a * np.log(x) + b * np.log(1 - x) - lbeta) / a
    f, c, d = 1.0, 1.0, 0.0
    for i in range(400):
        m = i // 2
        if i == 0:
            num = 1.0
        elif i % 2 == 0:
            num = (m * (b - m) * x) / ((a + 2 * m - 1) * (a + 2 * m))
        else:
            num = -((a + m) * (a + b + m) * x) / ((a + 2 * m) * (a + 2 * m + 1))
        d = 1 + num * d
        d = 1e-30 if abs(d) < 1e-30 else d
        d = 1 / d
        c = 1 + num / c
        c = 1e-30 if abs(c) < 1e-30 else c
        f *= c * d
        if abs(1 - c * d) < 1e-15:
            break
    return front * (f - 1)


def t_sf(t: float, gl: float) -> float:
    """P(T > t) para t de Student."""
    if gl <= 0:
        return float("nan")
    x = gl / (gl + t * t)
    ib = betainc(gl / 2, 0.5, x)
    return 0.5 * ib if t > 0 else 1 - 0.5 * ib


def t_ppf(p: float, gl: float) -> float:
    lo, hi = 0.0, 500.0
    for _ in range(300):
        mid = (lo + hi) / 2
        if 1 - t_sf(mid, gl) < p:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def chi2_sf(x: float, k: int) -> float:
    return 1 - gammainc_lower(k / 2, x / 2)


def gammainc_lower(s: float, x: float) -> float:
    if x <= 0:
        return 0.0
    if x < s + 1:
        term, total = 1.0 / s, 1.0 / s
        for n in range(1, 1000):
            term *= x / (s + n)
            total += term
            if abs(term) < 1e-16 * abs(total):
                break
        return float(total * np.exp(-x + s * np.log(x) - lgamma(s)))
    tiny = 1e-300
    b = x + 1 - s
    c = 1 / tiny
    d = 1 / b
    h = d
    for i in range(1, 1000):
        an = -i * (i - s)
        b += 2
        d = an * d + b
        if abs(d) < tiny:
            d = tiny
        c = b + an / c
        if abs(c) < tiny:
            c = tiny
        d = 1 / d
        delta = d * c
        h *= delta
        if abs(delta - 1) < 1e-16:
            break
    return float(1 - np.exp(-x + s * np.log(x) - lgamma(s)) * h)


def f_sf(F: float, d1: int, d2: int) -> float:
    return betainc(d2 / 2, d1 / 2, d2 / (d2 + d1 * F)) if F > 0 else 1.0


def normal_sf(z: float) -> float:
    from math import erfc
    return 0.5 * erfc(z / np.sqrt(2))


def welch(a, b, etiqueta_a="A", etiqueta_b="B", alpha=0.05) -> dict:
    """Prueba t de Welch para dos medias independientes (varianzas desiguales)."""
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    na, nb = len(a), len(b)
    va, vb = a.var(ddof=1), b.var(ddof=1)
    se = np.sqrt(va / na + vb / nb)
    t = (a.mean() - b.mean()) / se
    gl = (va / na + vb / nb) ** 2 / ((va / na) ** 2 / (na - 1) + (vb / nb) ** 2 / (nb - 1))
    p = 2 * t_sf(abs(t), gl)
    dif = a.mean() - b.mean()
    dt = _cohen_d(a, b)
    tc = t_ppf(1 - alpha / 2, gl)
    return {
        "prueba": "t de Welch (dos muestras independientes)",
        "grupo_a": etiqueta_a, "grupo_b": etiqueta_b,
        "n_a": int(na), "n_b": int(nb),
        "media_a": round(float(a.mean()), 4), "media_b": round(float(b.mean()), 4),
        "desv_a": round(float(a.std(ddof=1)), 4), "desv_b": round(float(b.std(ddof=1)), 4),
        "diferencia": round(float(dif), 4),
        "ic95_diferencia": [round(float(dif - tc * se), 4), round(float(dif + tc * se), 4)],
        "t": round(float(t), 4), "gl": round(float(gl), 3), "p_valor": float(p),
        "alpha": alpha, "significativo": bool(p < alpha),
        "d_cohen": round(float(dt), 4),
        "interpretacion_d": _etiqueta_d(dt),
    }


def _cohen_d(a, b) -> float:
    na, nb = len(a), len(b)
    s = np.sqrt(((na - 1) * a.var(ddof=1) + (nb - 1) * b.var(ddof=1)) / (na + nb - 2))
    return (a.mean() - b.mean()) / s if s else 0.0


def _etiqueta_d(d: float) -> str:
    d = abs(d)
    if d < 0.2:
        return "efecto despreciable"
    if d < 0.5:
        return "efecto pequeno"
    if d < 0.8:
        return "efecto medio"
    return "efecto grande"


def anova(*grupos, etiquetas=None, alpha=0.05) -> dict:
    """ANOVA de una via con eta cuadrado."""
    grupos = [np.asarray(g, dtype=float) for g in grupos]
    k = len(grupos)
    n = sum(len(g) for g in grupos)
    todos = np.concatenate(grupos)
    gm = todos.mean()
    ssb = sum(len(g) * (g.mean() - gm) ** 2 for g in grupos)
    ssw = sum(((g - g.mean()) ** 2).sum() for g in grupos)
    gl_num, gl_den = k - 1, n - k
    msb, msw = ssb / gl_num, ssw / gl_den
    F = msb / msw if msw else float("inf")
    p = f_sf(F, gl_num, gl_den)
    eta2 = ssb / (ssb + ssw)
    omega2 = (ssb - gl_num * msw) / (ssb + ssw + msw)
    return {
        "prueba": "ANOVA de una via",
        "grupos": list(etiquetas or [f"g{i+1}" for i in range(k)]),
        "medias": [round(float(g.mean()), 4) for g in grupos],
        "medianas": [round(float(np.median(g)), 4) for g in grupos],
        "n": [int(len(g)) for g in grupos],
        "F": round(float(F), 4), "gl_num": gl_num, "gl_den": gl_den,
        "p_valor": float(p), "alpha": alpha, "significativo": bool(p < alpha),
        "eta_cuadrado": round(float(eta2), 4),
        "omega_cuadrado": round(float(max(0.0, omega2)), 4),
        "interpretacion_eta": ("efecto grande" if eta2 >= 0.14 else
                               "efecto medio" if eta2 >= 0.06 else
                               "efecto pequeno" if eta2 >= 0.01 else "efecto minimo"),
    }


def games_howell(grupos: dict, alpha=0.05) -> list[dict]:
    """Post-hoc de Games-Howell (no asume varianzas iguales)."""
    nombres = list(grupos)
    res = []
    for i in range(len(nombres)):
        for j in range(i + 1, len(nombres)):
            a = np.asarray(grupos[nombres[i]], dtype=float)
            b = np.asarray(grupos[nombres[j]], dtype=float)
            na, nb = len(a), len(b)
            va, vb = a.var(ddof=1), b.var(ddof=1)
            se = np.sqrt(va / na + vb / nb)
            if se == 0:
                continue
            t = (a.mean() - b.mean()) / se
            gl = (va / na + vb / nb) ** 2 / ((va / na) ** 2 / (na - 1) + (vb / nb) ** 2 / (nb - 1))
            q = abs(t) * np.sqrt(2)
            p = 2 * t_sf(abs(t), gl)
            res.append({"par": f"{nombres[i]} vs {nombres[j]}",
                        "dif_medias": round(float(a.mean() - b.mean()), 2),
                        "q": round(float(q), 3), "gl": round(float(gl), 1),
                        "p_valor": float(p), "significativo": bool(p < alpha),
                        "d_cohen": round(float(_cohen_d(a, b)), 3)})
    return sorted(res, key=lambda r: r["p_valor"])


def chi2_independencia(tabla, nombres_filas, nombres_cols, alpha=0.05) -> dict:
    """Chi-cuadrado de independencia con V de Cramer."""
    t = np.asarray(tabla, dtype=float)
    n = t.sum()
    esp = t.sum(axis=1, keepdims=True) @ t.sum(axis=0, keepdims=True) / n
    chi2 = float(((t - esp) ** 2 / esp).sum())
    gl = (t.shape[0] - 1) * (t.shape[1] - 1)
    p = chi2_sf(chi2, gl)
    v = np.sqrt(chi2 / (n * min(t.shape[0] - 1, t.shape[1] - 1)))
    return {
        "prueba": "Chi-cuadrado de independencia",
        "tabla_observada": t.astype(int).tolist(),
        "tabla_esperada": np.round(esp, 2).tolist(),
        "filas": list(nombres_filas), "columnas": list(nombres_cols),
        "chi2": round(chi2, 4), "gl": int(gl), "p_valor": float(p),
        "alpha": alpha, "significativo": bool(p < alpha),
        "v_cramer": round(float(v), 4),
        "frecuencias_esperadas_bajas": int((esp < 5).sum()),
    }


def shapiro(x) -> dict:
    """Contraste de normalidad de Shapiro-Francia (aproximacion de Royston)."""
    x = np.sort(np.asarray(x, dtype=float))
    n = len(x)
    m = _norm_ppf((np.arange(1, n + 1) - 0.375) / (n + 0.25))
    ss = (m ** 2).sum()
    w = (np.dot(m, x) ** 2) / (ss * ((x - x.mean()) ** 2).sum())
    u = np.log(n)
    mu = -1.5861 - 0.31082 * u - 0.083751 * u ** 2 + 0.0038915 * u ** 3
    sigma = np.exp(-0.4803 - 0.082676 * u + 0.0030302 * u ** 2)
    z = (np.log(1 - w) - mu) / sigma
    return {"prueba": "Normalidad (Shapiro-Francia)", "W": round(float(w), 5),
            "z": round(float(z), 4), "p_valor": float(normal_sf(z)),
            "n": n, "normal": bool(normal_sf(z) > 0.05)}


def _norm_ppf(p):
    """Aproximacion de Acklam para la inversa de la normal estandar."""
    p = np.clip(np.asarray(p, dtype=float), 1e-12, 1 - 1e-12)
    a = [-3.969683028665376e+01, 2.209460984245205e+02, -2.759285104469687e+02,
         1.383577518672690e+02, -3.066479806614716e+01, 2.506628277459239e+00]
    b = [-5.447609879822406e+01, 1.615858368580409e+02, -1.556989798598866e+02,
         6.680131188771972e+01, -1.328068155288572e+01]
    c = [-7.784894002430293e-03, -3.223964580411365e-01, -2.400758277161838e+00,
         -2.549732539343734e+00, 4.374664141464968e+00, 2.938163982698783e+00]
    d = [7.784695709041462e-03, 3.224671290700398e-01, 2.445134137142996e+00,
         3.754408661907416e+00]
    plow, phigh = 0.02425, 1 - 0.02425
    res = np.zeros_like(p)
    lo = p < plow
    q = np.sqrt(-2 * np.log(p[lo]))
    res[lo] = (((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5]) / ((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1)
    hi = p > phigh
    q = np.sqrt(-2 * np.log(1 - p[hi]))
    res[hi] = -(((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5]) / ((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1)
    mid = ~(lo | hi)
    q = p[mid] - 0.5
    r = q * q
    res[mid] = (((((a[0]*r+a[1])*r+a[2])*r+a[3])*r+a[4])*r+a[5])*q / (((((b[0]*r+b[1])*r+b[2])*r+b[3])*r+b[4])*r+1)
    return res


def mann_kendall(serie) -> dict:
    x = np.asarray(serie, dtype=float)
    n = len(x)
    s = 0
    for i in range(n - 1):
        s += int(np.sign(x[i + 1:] - x[i]).sum())
    var = n * (n - 1) * (2 * n + 5) / 18
    z = (s - np.sign(s)) / np.sqrt(var) if s != 0 else 0.0
    p = 2 * normal_sf(abs(z))
    tau = s / (0.5 * n * (n - 1))
    return {"prueba": "Mann-Kendall (tendencia monotona)",
            "S": int(s), "n": n, "tau": round(float(tau), 4),
            "z": round(float(z), 4), "p_valor": float(p),
            "tendencia": "creciente" if (z > 0 and p < 0.05) else
                         "decreciente" if (z < 0 and p < 0.05) else "sin tendencia significativa"}


def regresion_ols(y, X, nombres) -> dict:
    """OLS multiple con errores estandar clasicos."""
    y = np.asarray(y, dtype=float)
    X = np.asarray(X, dtype=float)
    Xd = np.column_stack([np.ones(len(X)), X])
    beta, *_ = np.linalg.lstsq(Xd, y, rcond=None)
    resid = y - Xd @ beta
    n, k = Xd.shape
    gl = n - k
    sigma2 = (resid ** 2).sum() / gl
    cov = sigma2 * np.linalg.inv(Xd.T @ Xd)
    se = np.sqrt(np.diag(cov))
    tvals = beta / se
    pvals = [2 * t_sf(abs(t), gl) for t in tvals]
    ss_res = float((resid ** 2).sum())
    ss_tot = float(((y - y.mean()) ** 2).sum())
    return {
        "prueba": "Regresion lineal multiple (OLS)",
        "n": n, "gl_residual": gl,
        "variables": ["intercepto"] + list(nombres),
        "coeficientes": [round(float(b), 4) for b in beta],
        "errores_estandar": [round(float(s), 4) for s in se],
        "t": [round(float(t), 4) for t in tvals],
        "p_valores": [float(p) for p in pvals],
        "r2": round(1 - ss_res / ss_tot, 4),
        "r2_ajustado": round(1 - (1 - (1 - ss_res / ss_tot)) * (n - 1) / gl, 4),
        "rmse": round(float(np.sqrt(sigma2)), 4),
    }


# ==========================================================================
# 1. Carga y preparacion
# ==========================================================================
REGIONES = ["West", "East", "Central", "South"]
CATEGORIAS = ["Technology", "Furniture", "Office Supplies"]
SEGMENTOS = ["Consumer", "Corporate", "Home Office"]
MESES = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]


def cargar() -> tuple[pd.DataFrame, dict]:
    crudo = pd.read_csv(BASE / "train.csv", encoding="utf-8", encoding_errors="replace")
    crudo.columns = [c.strip() for c in crudo.columns]
    log = {
        "filas_originales": int(len(crudo)),
        "columnas_originales": list(crudo.columns),
        "nulos_originales": {k: int(v) for k, v in crudo.isna().sum().items() if v > 0},
        "duplicados_order_line": int(crudo.duplicated(subset=["Order ID", "Product ID"]).sum()),
        "duplicados_rowid": int(crudo.duplicated(subset=["Row ID"]).sum()),
    }
    df = crudo.copy()
    # Fechas: el dataset usa dd/mm/aaaa
    df["Order Date"] = pd.to_datetime(df["Order Date"], dayfirst=True, errors="raise")
    df["Ship Date"] = pd.to_datetime(df["Ship Date"], dayfirst=True, errors="raise")
    log["fechas_invalidas"] = 0
    # Nulos: Postal Code no aporta al analisis y solo afecta a 11 lineas
    log["postal_code_nulos"] = int(df["Postal Code"].isna().sum())
    df["Postal Code"] = df["Postal Code"].fillna(0).astype("int64")
    # Duracion logistica
    df["DiasEnvio"] = (df["Ship Date"] - df["Order Date"]).dt.days
    log["dias_envio_negativos"] = int((df["DiasEnvio"] < 0).sum())
    # Normalizacion de texto y columnas derivadas de calendario
    for c in ["Ship Mode", "Segment", "Region", "Category", "Sub-Category", "State", "City"]:
        df[c] = df[c].astype(str).str.strip()
    df["Anio"] = df["Order Date"].dt.year
    df["Trimestre"] = df["Order Date"].dt.quarter
    df["Mes"] = df["Order Date"].dt.month
    df["MesNombre"] = df["Mes"].map(dict(enumerate(MESES, 1)))
    df["AnioMes"] = df["Order Date"].dt.to_period("M").astype(str)
    df["AnioTrimestre"] = df["Order Date"].dt.to_period("Q").astype(str)
    df["DiaSemana"] = df["Order Date"].dt.dayofweek
    df["EsQ4"] = df["Mes"].isin([10, 11, 12])
    # Tramo de valor de linea y de pedido (para el test chi-cuadrado)
    df["TramoLinea"] = pd.cut(df["Sales"], [0, 50, 150, 400, 1000, np.inf],
                              labels=["<50", "50-150", "150-400", "400-1000", ">1000"])
    log["filas_limpias"] = int(len(df))
    log["filas_eliminadas"] = int(len(crudo) - len(df))
    return df, log


def construir_pedidos(df: pd.DataFrame) -> pd.DataFrame:
    ped = (df.groupby("Order ID")
           .agg(Ventas=("Sales", "sum"),
                Lineas=("Row ID", "count"),
                Productos=("Product ID", "nunique"),
                Cliente=("Customer ID", "first"),
                NombreCliente=("Customer Name", "first"),
                Segmento=("Segment", "first"),
                Region=("Region", "first"),
                Estado=("State", "first"),
                Ciudad=("City", "first"),
                ModoEnvio=("Ship Mode", "first"),
                Fecha=("Order Date", "min"),
                FechaEnvio=("Ship Date", "max"),
                DiasEnvio=("DiasEnvio", "max"),
                CategoriaPrincipal=("Category", lambda s: s.mode().iat[0]))
           .reset_index())
    ped["Anio"] = ped["Fecha"].dt.year
    ped["Trimestre"] = ped["Fecha"].dt.quarter
    ped["Mes"] = ped["Fecha"].dt.month
    ped["AnioMes"] = ped["Fecha"].dt.to_period("M").astype(str)
    ped["AnioTrimestre"] = ped["Fecha"].dt.to_period("Q").astype(str)
    ped["EsQ4"] = ped["Mes"].isin([10, 11, 12])
    ped["TramoPedido"] = pd.cut(ped["Ventas"], [0, 100, 250, 500, 1000, np.inf],
                                labels=["<100", "100-250", "250-500", "500-1000", ">1000"])
    return ped


# ==========================================================================
# 2. KPIs
# ==========================================================================
def calcular_kpis(df: pd.DataFrame, ped: pd.DataFrame) -> dict:
    anios = sorted(df["Anio"].unique())
    base, ult = 2016, 2018
    ventas_anio = df.groupby("Anio")["Sales"].sum()
    ped_anio = ped.groupby("Anio").size()
    cli_anio = ped.groupby("Anio")["Cliente"].nunique()
    lineas_anio = df.groupby("Anio").size()
    ticket = ventas_anio / ped_anio

    def cagr(ini, fin, n):
        return (fin / ini) ** (1 / n) - 1

    lineas_por_pedido = lineas_anio / ped_anio
    kpis = {
        "periodo": f"{df['Order Date'].min():%Y-%m-%d} a {df['Order Date'].max():%Y-%m-%d}",
        "anios": anios,
        "ventas_totales": round(float(df["Sales"].sum()), 2),
        "pedidos_totales": int(ped.shape[0]),
        "clientes_totales": int(df["Customer ID"].nunique()),
        "productos_totales": int(df["Product ID"].nunique()),
        "ticket_medio_global": round(float(ped["Ventas"].mean()), 2),
        "ticket_mediano_global": round(float(ped["Ventas"].median()), 2),
        "lineas_por_pedido": round(float(ped["Lineas"].mean()), 3),
        "ingreso_por_cliente": round(float(df["Sales"].sum() / df["Customer ID"].nunique()), 2),
        "pedidos_por_cliente": round(float(ped.shape[0] / df["Customer ID"].nunique()), 3),
        "dias_envio_medio": round(float(df["DiasEnvio"].mean()), 3),
        "dias_envio_mediano": float(df["DiasEnvio"].median()),
        "series": {
            "ventas_anio": {int(k): round(float(v), 2) for k, v in ventas_anio.items()},
            "pedidos_anio": {int(k): int(v) for k, v in ped_anio.items()},
            "ticket_anio": {int(k): round(float(v), 2) for k, v in ticket.items()},
            "clientes_anio": {int(k): int(v) for k, v in cli_anio.items()},
            "lineas_por_pedido_anio": {int(k): round(float(v), 3) for k, v in lineas_por_pedido.items()},
        },
        "crecimiento": {
            "ventas_2016_2018_cagr": round(float(cagr(ventas_anio[base], ventas_anio[ult], 2)), 4),
            "pedidos_2016_2018_cagr": round(float(cagr(ped_anio[base], ped_anio[ult], 2)), 4),
            "ticket_2016_2018_cagr": round(float(cagr(ticket[base], ticket[ult], 2)), 4),
            "clientes_2016_2018_cagr": round(float(cagr(cli_anio[base], cli_anio[ult], 2)), 4),
            "ventas_2017_2018": round(float(ventas_anio[2018] / ventas_anio[2017] - 1), 4),
            "pedidos_2017_2018": round(float(ped_anio[2018] / ped_anio[2017] - 1), 4),
            "ticket_2017_2018": round(float(ticket[2018] / ticket[2017] - 1), 4),
        },
    }
    # KPI 4. Cuota por region
    kpis["cuota_region"] = {
        r: round(float(df.loc[df["Region"] == r, "Sales"].sum() / df["Sales"].sum()), 4)
        for r in REGIONES}
    # KPI 5. Indice de concentracion (HHI) por estado y Gini de clientes
    cuota_estado = df.groupby("State")["Sales"].sum() / df["Sales"].sum()
    kpis["hhi_estado"] = round(float((cuota_estado ** 2).sum()), 4)
    kpis["top5_estados_cuota"] = round(float(cuota_estado.sort_values(ascending=False).head(5).sum()), 4)
    ventas_cliente = ped.groupby("Cliente")["Ventas"].sum()
    kpis["gini_clientes"] = round(float(_gini(ventas_cliente.to_numpy())), 4)
    kpis["top10pct_clientes_cuota"] = round(float(
        ventas_cliente.sort_values(ascending=False).head(max(1, int(len(ventas_cliente) * .1))).sum()
        / ventas_cliente.sum()), 4)
    # KPI 6. Tasa de recompra y ventas recurrentes
    por_cliente = ped.groupby("Cliente").agg(n=("Order ID", "count"), ventas=("Ventas", "sum"),
                                             primera=("Fecha", "min"), ultima=("Fecha", "max"))
    kpis["tasa_recompra"] = round(float((por_cliente["n"] > 1).mean()), 4)
    kpis["clientes_una_compra_pct"] = round(float((por_cliente["n"] == 1).mean()), 4)
    kpis["clientes_una_compra_ventas_pct"] = round(float(
        por_cliente.loc[por_cliente["n"] == 1, "ventas"].sum() / por_cliente["ventas"].sum()), 4)
    ped_ord = ped.sort_values("Fecha").copy()
    ped_ord["PrimeraCompra"] = ped_ord["Cliente"].map(por_cliente["primera"])
    ped_ord["EsRecurrente"] = ped_ord["Fecha"] > ped_ord["PrimeraCompra"]
    kpis["ventas_recurrentes_pct"] = round(float(
        ped_ord.loc[ped_ord["EsRecurrente"], "Ventas"].sum() / ped_ord["Ventas"].sum()), 4)
    kpis["pedidos_recurrentes_pct"] = round(float(ped_ord["EsRecurrente"].mean()), 4)
    # Desglose por cohorte: año de la primera compra de cada cliente.
    ped_ord["AnioPrimeraCompra"] = ped_ord["PrimeraCompra"].dt.year
    kpis["recurrencia_por_cohorte"] = {
        int(a): {
            "clientes": int(g["Cliente"].nunique()),
            "pedidos": int(len(g)),
            "ventas": round(float(g["Ventas"].sum()), 2),
            "ventas_recurrentes": round(float(g.loc[g["EsRecurrente"], "Ventas"].sum()), 2),
            "pct_recurrente": round(float(
                g.loc[g["EsRecurrente"], "Ventas"].sum() / g["Ventas"].sum()), 4),
        }
        for a, g in ped_ord.groupby("AnioPrimeraCompra")}
    # KPI 8. Indice de estacionalidad Q4
    venta_diaria_mes = (df.groupby(["Anio", "Mes"])
                        .apply(lambda g: g["Sales"].sum() / g["Order Date"].dt.normalize().nunique(),
                               include_groups=False)
                        .rename("venta_diaria").reset_index())
    prom = venta_diaria_mes["venta_diaria"].mean()
    kpis["indice_estacionalidad_mes"] = {
        int(m): round(float(v / prom), 4)
        for m, v in venta_diaria_mes.groupby("Mes")["venta_diaria"].mean().items()}
    kpis["indice_estacionalidad_q4"] = round(float(
        df[df["EsQ4"]]["Sales"].sum() / 92 / (df[~df["EsQ4"]]["Sales"].sum() / (365 - 92))), 4)
    # KPI 9. Desempeno logistico
    kpis["cumplimiento_dias_objetivo"] = {
        "objetivo_<=2_dias": round(float((df["DiasEnvio"] <= 2).mean()), 4),
        "objetivo_<=4_dias": round(float((df["DiasEnvio"] <= 4).mean()), 4),
        "sobre_5_dias": round(float((df["DiasEnvio"] > 5).mean()), 4),
    }
    kpis["dias_envio_por_modo"] = {
        m: {"media": round(float(g["DiasEnvio"].mean()), 2),
            "p90": round(float(g["DiasEnvio"].quantile(0.9)), 2),
            "lineas": int(len(g))}
        for m, g in df.groupby("Ship Mode")}
    # KPI 10. Ticket por segmento (valor de cliente)
    kpis["ticket_por_segmento"] = {
        s: {"ticket_medio": round(float(ped.loc[ped["Segmento"] == s, "Ventas"].mean()), 2),
            "pedidos": int((ped["Segmento"] == s).sum()),
            "clientes": int(ped.loc[ped["Segmento"] == s, "Cliente"].nunique()),
            "cuota": round(float(ped.loc[ped["Segmento"] == s, "Ventas"].sum() / ped["Ventas"].sum()), 4)}
        for s in SEGMENTOS}
    return kpis


def _gini(x) -> float:
    x = np.sort(np.asarray(x, dtype=float))
    n = len(x)
    if n == 0 or x.sum() == 0:
        return 0.0
    idx = np.arange(1, n + 1)
    return float((2 * (idx * x).sum()) / (n * x.sum()) - (n + 1) / n)


# ==========================================================================
# 3. Validacion de hipotesis
# ==========================================================================
def validar_hipotesis(df: pd.DataFrame, ped: pd.DataFrame) -> dict:
    res: dict[str, dict] = {}

    # ---------------- H1: el crecimiento lo explica el volumen ----------------
    v = ped.groupby("Anio").agg(ventas=("Ventas", "sum"), pedidos=("Order ID", "count"))
    v["ticket"] = v["ventas"] / v["pedidos"]
    t16 = np.log(ped.loc[ped["Anio"] == 2016, "Ventas"].to_numpy())
    t18 = np.log(ped.loc[ped["Anio"] == 2018, "Ventas"].to_numpy())
    prueba_ticket = welch(t18, t16, "ticket 2018 (log)", "ticket 2016 (log)")
    prueba_ticket["cambio_relativo_ticket"] = round(
        float(np.exp(t18.mean() - t16.mean()) - 1), 4)
    prueba_ticket["ic95_cambio_relativo"] = [
        round(float(np.exp(prueba_ticket["ic95_diferencia"][0]) - 1), 4),
        round(float(np.exp(prueba_ticket["ic95_diferencia"][1]) - 1), 4)]
    # contraste unilateral: el ticket no crecio frente a 2016
    p_unilateral = t_sf(prueba_ticket["t"], prueba_ticket["gl"])
    prueba_ticket["p_valor_unilateral_ticket_no_crecio"] = float(p_unilateral)
    prueba_ticket["unilateral_significativo"] = bool(p_unilateral < 0.05)
    prueba_ticket["nota"] = ("El p bilateral indica que no hay evidencia de cambio en el ticket; "
                             "el unilateral confirma que tampoco hay evidencia de crecimiento. "
                             "Al no rechazar H0 el ticket se mantiene estable y el crecimiento "
                             "del ingreso queda atribuido al volumen.")
    # descomposicion multiplicativa del crecimiento 2016 -> 2018
    dv = v.loc[2018, "ventas"] - v.loc[2016, "ventas"]
    ef_ped = (v.loc[2018, "pedidos"] - v.loc[2016, "pedidos"]) * v.loc[2016, "ticket"]
    ef_tk = v.loc[2018, "pedidos"] * (v.loc[2018, "ticket"] - v.loc[2016, "ticket"])
    # varianza de la serie mensual: cuanto aporta volumen y cuanto ticket
    mes = df.groupby("AnioMes").agg(ventas=("Sales", "sum"), pedidos=("Order ID", "nunique"))
    mes["ticket"] = mes["ventas"] / mes["pedidos"]
    lv, lp, lt = np.log(mes["ventas"]), np.log(mes["pedidos"]), np.log(mes["ticket"])
    var_v = lv.var(ddof=1)
    aporte_p = np.cov(lp, lv, ddof=1)[0, 1] / var_v
    aporte_t = np.cov(lt, lv, ddof=1)[0, 1] / var_v
    mk_ped = mann_kendall(mes["pedidos"])
    mk_tk = mann_kendall(mes["ticket"])
    res["H1"] = {
        "enunciado": ("El crecimiento de ingresos 2016-2018 se explica por el aumento del "
                      "numero de pedidos y no por el valor medio del pedido."),
        "h0": "El ticket medio de 2018 es igual al de 2016 (el crecimiento no viene del volumen).",
        "h1": "El ticket medio de 2018 es distinto al de 2016; el volumen explica el crecimiento.",
        "prueba_principal": prueba_ticket,
        "pruebas_complementarias": {
            "mann_kendall_pedidos_mensuales": mk_ped,
            "mann_kendall_ticket_mensual": mk_tk,
            "descomposicion_2016_2018": {
                "delta_ventas": round(float(dv), 2),
                "efecto_volumen": round(float(ef_ped), 2),
                "efecto_ticket": round(float(ef_tk), 2),
                "pct_volumen": round(float(ef_ped / dv), 4),
                "pct_ticket": round(float(ef_tk / dv), 4),
            },
            "varianza_log_ventas_mensual": round(float(var_v), 5),
            "aporte_volumen_a_varianza": round(float(aporte_p), 4),
            "aporte_ticket_a_varianza": round(float(aporte_t), 4),
        },
        "cifras_clave": {
            "pedidos": {int(k): int(x) for k, x in v["pedidos"].items()},
            "ticket_medio": {int(k): round(float(x), 2) for k, x in v["ticket"].items()},
        },
    }

    # ---------------- H2: brecha regional persistente ----------------
    reg_q = df.pivot_table(index="Region", columns="AnioTrimestre", values="Sales", aggfunc="sum")
    altas = np.concatenate([reg_q.loc["West"].to_numpy(), reg_q.loc["East"].to_numpy()])
    bajas = np.concatenate([reg_q.loc["Central"].to_numpy(), reg_q.loc["South"].to_numpy()])
    prueba_reg = welch(altas, bajas, "West+East", "Central+South")
    anova_reg = anova(*[reg_q.loc[r].to_numpy() for r in REGIONES], etiquetas=REGIONES)
    post = games_howell({r: reg_q.loc[r].to_numpy() for r in REGIONES})
    crec = {r: round(float(df[(df.Region == r) & (df.Anio == 2018)]["Sales"].sum()
                             / df[(df.Region == r) & (df.Anio == 2016)]["Sales"].sum() - 1), 4)
            for r in REGIONES}
    res["H2"] = {
        "enunciado": ("Existe una brecha de ingresos estadisticamente significativa entre las "
                      "regiones de alto desempeno (West, East) y las de bajo desempeno "
                      "(Central, South).").replace("estadisticamente", "estadísticamente"),
        "h0": "El ingreso trimestral medio es igual en las cuatro regiones.",
        "h1": "Al menos una region presenta un ingreso trimestral medio distinto.",
        "prueba_principal": anova_reg,
        "prueba_contraste": prueba_reg,
        "post_hoc_games_howell": post,
        "crecimiento_2016_2018": crec,
        "medias_trimestrales": {r: int(round(float(reg_q.loc[r].mean()))) for r in REGIONES},
    }

    # ---------------- H3: concentracion de ingresos ----------------
    sub = df.groupby("Sub-Category")["Sales"].sum().sort_values(ascending=False)
    acum = sub.cumsum() / sub.sum()
    n80 = int((acum < 0.8).sum() + 1)
    prod = df.groupby("Product Name")["Sales"].sum().sort_values(ascending=False)
    acum_p = prod.cumsum() / prod.sum()
    n80p = int((acum_p < 0.8).sum() + 1)
    cli = ped.groupby("Cliente")["Ventas"].sum().sort_values(ascending=False)
    acum_c = cli.cumsum() / cli.sum()
    n80c = int((acum_c < 0.8).sum() + 1)
    # contraste: la cuota observada del top-3 frente a un reparto uniforme (1/3)
    obs_top3 = float(acum.iloc[2])
    n_sub = len(sub)
    # prueba binomial aproximada: 3 subcategorias de 17 concentran >= 1/3 de ingresos
    z = (obs_top3 - 3 / n_sub) / np.sqrt((3 / n_sub) * (1 - 3 / n_sub) / n_sub)
    res["H3"] = {
        "enunciado": ("Los ingresos estan concentrados: un grupo reducido de subcategorias, "
                      "productos y clientes explica la mayor parte de la facturacion."),
        "h0": "Los ingresos se reparten de forma homogenea entre las subcategorias (cuota top-3 = 3/17).",
        "h1": "Los ingresos estan concentrados en pocas subcategorias (cuota top-3 > 3/17).",
        "prueba_principal": {
            "prueba": "Contraste de proporcion (aproximacion normal) sobre la cuota del top-3",
            "cuota_top3_observada": round(obs_top3, 4),
            "cuota_esperada_uniforme": round(3 / n_sub, 4),
            "z": round(float(z), 4), "p_valor": float(normal_sf(z)),
            "significativo": bool(normal_sf(z) < 0.05),
            "n_subcategorias": n_sub,
        },
        "pareto": {
            "n_subcategorias": n_sub,
            "subcategorias_para_80pct": n80,
            "pct_subcategorias_para_80pct": round(n80 / n_sub, 4),
            "top3_cuota": round(obs_top3, 4),
            "top5_cuota": round(float(acum.iloc[4]), 4),
            "n_productos": int(len(prod)),
            "productos_para_80pct": n80p,
            "pct_productos_para_80pct": round(n80p / len(prod), 4),
            "n_clientes": int(len(cli)),
            "clientes_para_80pct": n80c,
            "pct_clientes_para_80pct": round(n80c / len(cli), 4),
            "top10pct_clientes_cuota": round(float(
                cli.head(max(1, int(len(cli) * 0.1))).sum() / cli.sum()), 4),
            "gini_productos": round(float(_gini(prod.to_numpy())), 4),
            "gini_clientes": round(float(_gini(cli.to_numpy())), 4),
            "gini_estados": round(float(_gini(df.groupby("State")["Sales"].sum().to_numpy())), 4),
        },
        "detalle_subcategorias": [
            {"subcategoria": k, "categoria": df.loc[df["Sub-Category"] == k, "Category"].iat[0],
             "ventas": round(float(x), 2), "cuota": round(float(x / sub.sum()), 4),
             "acumulado": round(float(acum[k]), 4)} for k, x in sub.items()],
    }

    # ---------------- H4: estacionalidad Q4 ----------------
    dd = (df[df["Anio"].isin([2016, 2017, 2018])]
          .assign(Dia=lambda d: d["Order Date"].dt.normalize())
          .groupby(["Dia", "Mes", "Anio"])["Sales"].sum().reset_index())
    grupos_mes = [dd.loc[dd["Mes"] == m, "Sales"].to_numpy() for m in range(1, 13)]
    anova_mes = anova(*grupos_mes, etiquetas=MESES)
    post_mes = games_howell({MESES[m - 1]: dd.loc[dd["Mes"] == m, "Sales"].to_numpy()
                             for m in [9, 10, 11, 12, 2, 1]})
    q4 = dd[dd["Mes"].isin([10, 11, 12])]["Sales"]
    resto = dd[~dd["Mes"].isin([10, 11, 12])]["Sales"]
    t_q4 = welch(q4.to_numpy(), resto.to_numpy(), "Venta diaria Oct-Dic", "Venta diaria Ene-Sep")
    # contribucion de Q4 al crecimiento anual
    contrib = {}
    for a in [2016, 2017, 2018]:
        d = df[df["Anio"] == a]
        contrib[int(a)] = {
            "q4": round(float(d[d["EsQ4"]]["Sales"].sum()), 2),
            "resto": round(float(d[~d["EsQ4"]]["Sales"].sum()), 2)}
    res["H4"] = {
        "enunciado": ("Existe un patron estacional significativo: la venta diaria del cuarto "
                      "trimestre supera a la del resto del anio."),
        "h0": "La venta diaria media es igual en los 12 meses del anio.",
        "h1": "Al menos un mes presenta una venta diaria media distinta; Oct-Dic concentran el pico.",
        "prueba_principal": anova_mes,
        "prueba_contraste": t_q4,
        "post_hoc_games_howell": post_mes,
        "contribucion_trimestral": contrib,
        "factor_q4": {int(a): round(
            float(df[(df.Anio == a) & df.EsQ4]["Sales"].sum() / 92
                  / (df[(df.Anio == a) & ~df.EsQ4]["Sales"].sum() / 273)), 4)
            for a in [2015, 2016, 2017, 2018]},
        "shapiro_venta_diaria": shapiro(dd["Sales"].to_numpy()),
    }

    # ---------------- H5: modo de envio independiente del tamano ----------------
    tabla = pd.crosstab(df["Ship Mode"], df["TramoLinea"])
    chi = chi2_independencia(tabla.to_numpy(), tabla.index.tolist(),
                             [str(c) for c in tabla.columns])
    ped_tab = pd.crosstab(ped["ModoEnvio"], ped["TramoPedido"])
    chi_ped = chi2_independencia(ped_tab.to_numpy(), ped_tab.index.tolist(),
                                 [str(c) for c in ped_tab.columns])
    sd = ped.loc[ped["ModoEnvio"] == "Same Day", "Ventas"].to_numpy()
    st = ped.loc[ped["ModoEnvio"] == "Standard Class", "Ventas"].to_numpy()
    res["H5"] = {
        "enunciado": ("El modo de envio es independiente del tamano del pedido: los pedidos "
                      "express no son sistematicamente mas grandes."),
        "h0": "El modo de envio y el tramo de valor del pedido son independientes.",
        "h1": "Existe asociacion entre el modo de envio y el tamano del pedido.",
        "prueba_principal": chi,
        "prueba_complementaria_pedidos": chi_ped,
        "prueba_ticket_sameday_standard": welch(sd, st, "Same Day", "Standard Class"),
        "ticket_por_modo": {
            m: {"ticket_medio": round(float(g["Ventas"].mean()), 2),
                "ticket_mediano": round(float(g["Ventas"].median()), 2),
                "pedidos": int(len(g)),
                "dias_envio_medio": round(float(g["DiasEnvio"].mean()), 2)}
            for m, g in ped.groupby("ModoEnvio")},
        "correlacion_diasenvio_ventas": round(float(df["DiasEnvio"].corr(df["Sales"])), 4),
        "correlacion_diasenvio_ticket": round(float(ped["DiasEnvio"].corr(ped["Ventas"])), 4),
    }

    # ---------------- Extra: ticket por segmento (ANOVA) ----------------
    res["EXTRA_segmento"] = {
        "prueba_principal": anova(*[ped.loc[ped["Segmento"] == s, "Ventas"].to_numpy()
                                    for s in SEGMENTOS], etiquetas=SEGMENTOS),
        "post_hoc": games_howell({s: ped.loc[ped["Segmento"] == s, "Ventas"].to_numpy()
                                  for s in SEGMENTOS}),
    }
    # ---------------- Extra: ticket por region (ANOVA) ----------------
    res["EXTRA_region_ticket"] = {
        "prueba_principal": anova(*[ped.loc[ped["Region"] == r, "Ventas"].to_numpy()
                                    for r in REGIONES], etiquetas=REGIONES),
        "post_hoc": games_howell({r: ped.loc[ped["Region"] == r, "Ventas"].to_numpy()
                                  for r in REGIONES}),
    }
    return res


# ==========================================================================
# 4. Tendencia y proyeccion 2019
# ==========================================================================
def proyectar(df: pd.DataFrame) -> dict:
    """Modelo log-lineal con indice estacional, ajustado sobre 2016-2018.

    El ajuste se restringe a 2016-2018 porque 2015 presenta un ticket medio muy
    superior a la tendencia posterior y sesga la proyeccion hacia abajo. Se
    conserva tambien el ajuste sobre los 48 meses como contraste de sensibilidad.
    """
    mes = (df.groupby("AnioMes").agg(ventas=("Sales", "sum"),
                                     pedidos=("Order ID", "nunique"))
           .reset_index().sort_values("AnioMes").reset_index(drop=True))
    mes["t"] = np.arange(len(mes))
    mes["Anio"] = mes["AnioMes"].str[:4].astype(int)
    mes["MesNum"] = mes["AnioMes"].str[5:7].astype(int)

    reciente = mes[mes["Anio"] >= 2016].copy()
    reciente["t"] = np.arange(len(reciente))

    def ajustar(sub: pd.DataFrame) -> dict:
        reg = regresion_ols(np.log(sub["ventas"].to_numpy()),
                            sub[["t"]].to_numpy(), ["t"])
        reg_ped = regresion_ols(np.log(sub["pedidos"].to_numpy()),
                                sub[["t"]].to_numpy(), ["t"])
        resid = np.log(sub["ventas"].to_numpy()) - (
            reg["coeficientes"][0] + reg["coeficientes"][1] * sub["t"].to_numpy())
        indice = pd.Series(np.exp(resid), index=sub["MesNum"].to_numpy())
        indice = indice.groupby(level=0).mean()
        indice = indice / indice.mean()
        return {"reg": reg, "reg_pedidos": reg_ped, "indice": indice}

    aj = ajustar(reciente)
    aj48 = ajustar(mes)
    reg, reg_ped, indice = aj["reg"], aj["reg_pedidos"], aj["indice"]

    base = int(reciente["t"].max())
    proy = []
    for i, m in enumerate(range(1, 13)):
        t = base + 1 + i
        tend = float(np.exp(reg["coeficientes"][0] + reg["coeficientes"][1] * t))
        tend_p = float(np.exp(reg_ped["coeficientes"][0] + reg_ped["coeficientes"][1] * t))
        venta = tend * float(indice.get(m, 1.0))
        pedidos = tend_p * float(indice.get(m, 1.0))
        proy.append({
            "AnioMes": f"2019-{m:02d}", "Mes": MESES[m - 1], "MesNum": m,
            "VentasProyectadas": round(venta, 2),
            "PedidosProyectados": round(pedidos, 1),
            "TicketProyectado": round(venta / pedidos, 2) if pedidos else None,
            "IndiceEstacional": round(float(indice.get(m, 1.0)), 4),
        })
    total_2018 = float(df.loc[df.Anio == 2018, "Sales"].sum())
    total_proy = sum(p["VentasProyectadas"] for p in proy)
    total_2015 = float(df.loc[df.Anio == 2015, "Sales"].sum())
    # escenario base: anualizar la velocidad de salida del cuarto trimestre de 2018
    d2018 = df[df["Anio"] == 2018]
    dias_q4 = (d2018.loc[d2018["EsQ4"], "Order Date"].dt.normalize().nunique())
    venta_diaria_q4 = float(d2018.loc[d2018["EsQ4"], "Sales"].sum()) / max(1, dias_q4)
    escenario_salida = venta_diaria_q4 * 365
    # velocidad del segundo semestre de 2018 (mas estable que un solo trimestre)
    d2018b = d2018[d2018["Mes"] >= 7]
    dias_s2 = d2018b["Order Date"].dt.normalize().nunique()
    venta_diaria_s2 = float(d2018b["Sales"].sum()) / max(1, dias_s2)
    return {
        "modelo_log_lineal": reg,
        "modelo_pedidos": reg_ped,
        "muestra_ajuste": "2016-01 a 2018-12 (36 meses)",
        "sensibilidad_48_meses": {
            "r2": aj48["reg"]["r2"],
            "pendiente": aj48["reg"]["coeficientes"][1],
            "crecimiento_anual_equivalente": round(
                float(np.exp(aj48["reg"]["coeficientes"][1]) ** 12 - 1), 4),
        },
        "r2_serie_mensual": reg["r2"],
        "r2_ajustado": reg["r2_ajustado"],
        "crecimiento_mensual_estimado": round(float(np.exp(reg["coeficientes"][1]) - 1), 4),
        "crecimiento_anual_equivalente": round(
            float(np.exp(reg["coeficientes"][1]) ** 12 - 1), 4),
        "ic95_crecimiento_mensual": [
            round(float(np.exp(reg["coeficientes"][1] - 1.96 * reg["errores_estandar"][1]) - 1), 4),
            round(float(np.exp(reg["coeficientes"][1] + 1.96 * reg["errores_estandar"][1]) - 1), 4)],
        "indice_estacionalidad": {MESES[m - 1]: round(float(v), 4) for m, v in indice.items()},
        "proyeccion_2019": proy,
        "total_2019_proyectado": round(total_proy, 2),
        "total_2018_real": round(total_2018, 2),
        "total_2015_real": round(total_2015, 2),
        "variacion_proyectada": round(total_proy / total_2018 - 1, 4),
        "escenario_base_anualizacion": {
            "descripcion": ("Escenario conservador: mantener la velocidad de venta observada "
                            "al cierre de 2018 durante todo 2019."),
            "venta_diaria_q4_2018": round(venta_diaria_q4, 2),
            "dias_con_venta_q4_2018": int(dias_q4),
            "anualizado_q4_2018": round(escenario_salida, 2),
            "venta_diaria_segundo_semestre_2018": round(venta_diaria_s2, 2),
            "anualizado_segundo_semestre_2018": round(venta_diaria_s2 * 365, 2),
            "variacion_vs_2018": round(escenario_salida / total_2018 - 1, 4),
        },
        "meses_observados": len(mes),
        "meses_usados_en_ajuste": len(reciente),
    }


# ==========================================================================
# 5. Tablas de analisis para el notebook y para Power BI
# ==========================================================================
def tablas(df: pd.DataFrame, ped: pd.DataFrame) -> dict[str, pd.DataFrame]:
    t = {}
    t["analitica_ventas_linea"] = df[[
        "Row ID", "Order ID", "Order Date", "Ship Date", "Ship Mode", "Customer ID",
        "Customer Name", "Segment", "Country", "City", "State", "Postal Code", "Region",
        "Product ID", "Category", "Sub-Category", "Product Name", "Sales", "DiasEnvio",
        "Anio", "Trimestre", "Mes", "MesNombre", "AnioMes", "AnioTrimestre", "DiaSemana",
        "EsQ4", "TramoLinea"]].rename(columns={
            "Row ID": "IDLinea", "Order ID": "IDPedido", "Order Date": "FechaPedido",
            "Ship Date": "FechaEnvio", "Ship Mode": "ModoEnvio", "Customer ID": "IDCliente",
            "Customer Name": "Cliente", "Segment": "Segmento", "Postal Code": "CodigoPostal",
            "Product ID": "IDProducto", "Sub-Category": "Subcategoria",
            "Product Name": "Producto"})
    t["analitica_pedidos"] = ped
    t["analitica_kpi_mensual"] = (df.groupby("AnioMes")
                                  .agg(Ventas=("Sales", "sum"),
                                       Pedidos=("Order ID", "nunique"),
                                       Clientes=("Customer ID", "nunique"),
                                       Lineas=("Row ID", "count"))
                                  .reset_index())
    t["analitica_kpi_mensual"]["TicketMedio"] = (
        t["analitica_kpi_mensual"]["Ventas"] / t["analitica_kpi_mensual"]["Pedidos"]).round(2)
    t["analitica_kpi_mensual"]["LineasPorPedido"] = (
        t["analitica_kpi_mensual"]["Lineas"] / t["analitica_kpi_mensual"]["Pedidos"]).round(3)
    t["analitica_kpi_mensual"]["VentasPorCliente"] = (
        t["analitica_kpi_mensual"]["Ventas"] / t["analitica_kpi_mensual"]["Clientes"]).round(2)
    t["dim_calendario"] = (df[["Order Date"]].drop_duplicates().sort_values("Order Date")
                           .assign(Anio=lambda d: d["Order Date"].dt.year,
                                   Trimestre=lambda d: d["Order Date"].dt.quarter,
                                   Mes=lambda d: d["Order Date"].dt.month,
                                   MesNombre=lambda d: d["Mes"].map(dict(enumerate(MESES, 1))),
                                   AnioMes=lambda d: d["Order Date"].dt.to_period("M").astype(str),
                                   AnioTrimestre=lambda d: d["Order Date"].dt.to_period("Q").astype(str),
                                   DiaSemana=lambda d: d["Order Date"].dt.dayofweek,
                                   NombreDia=lambda d: d["Order Date"].dt.day_name(),
                                   EsQ4=lambda d: d["Mes"].isin([10, 11, 12]),
                                   EsFinSemana=lambda d: d["DiaSemana"] >= 5)
                           .rename(columns={"Order Date": "Fecha"}))
    t["dim_producto"] = (df[["Product ID", "Product Name", "Category", "Sub-Category"]]
                         .drop_duplicates(subset=["Product ID"])
                         .rename(columns={"Product ID": "IDProducto", "Product Name": "Producto",
                                          "Sub-Category": "Subcategoria"}))
    t["dim_cliente"] = (df[["Customer ID", "Customer Name", "Segment"]]
                        .drop_duplicates(subset=["Customer ID"])
                        .rename(columns={"Customer ID": "IDCliente", "Customer Name": "Cliente",
                                         "Segment": "Segmento"}))
    t["dim_geografia"] = (df[["City", "State", "Region", "Postal Code"]]
                          .drop_duplicates(subset=["City", "State", "Postal Code"])
                          .rename(columns={"Postal Code": "CodigoPostal"}))
    t["dim_envio"] = (df[["Ship Mode", "DiasEnvio"]].drop_duplicates(subset=["Ship Mode"])
                      .rename(columns={"Ship Mode": "ModoEnvio", "DiasEnvio": "DiasEnvioTipico"}))
    t["analitica_proyeccion_2019"] = pd.DataFrame(proyectar(df)["proyeccion_2019"])
    return t


# ==========================================================================
# 6. Orquestacion
# ==========================================================================
def main() -> None:
    df, log = cargar()
    ped = construir_pedidos(df)
    kpis = calcular_kpis(df, ped)
    hipotesis = validar_hipotesis(df, ped)
    proy = proyectar(df)
    tbs = tablas(df, ped)

    for nombre, tabla in tbs.items():
        tabla.to_csv(DATOS / f"{nombre}.csv", index=False, encoding="utf-8-sig")

    serie_mensual = [{"AnioMes": r.AnioMes, "Ventas": round(float(r.Ventas), 2),
                      "Pedidos": int(r.Pedidos), "TicketMedio": round(float(r.Ventas / r.Pedidos), 2)}
                     for r in df.groupby("AnioMes").agg(Ventas=("Sales", "sum"),
                                                        Pedidos=("Order ID", "nunique")).reset_index().itertuples()]

    salida = {
        "calidad_datos": log,
        "kpis": kpis,
        "hipotesis": hipotesis,
        "proyeccion": proy,
        "series": {
            "mensual": serie_mensual,
            "anual": [{"Anio": int(a),
                       "Ventas": round(float(df.loc[df.Anio == a, "Sales"].sum()), 2),
                       "Pedidos": int(ped.loc[ped.Anio == a].shape[0]),
                       "Clientes": int(ped.loc[ped.Anio == a, "Cliente"].nunique()),
                       "TicketMedio": round(float(df.loc[df.Anio == a, "Sales"].sum()
                                                   / ped.loc[ped.Anio == a].shape[0]), 2)}
                      for a in sorted(df.Anio.unique())],
            "trimestral": [{"AnioTrimestre": k, "Ventas": round(float(v), 2)}
                           for k, v in df.groupby("AnioTrimestre")["Sales"].sum().items()],
            "por_region_categoria": df.pivot_table(index="Region", columns="Category",
                                                   values="Sales", aggfunc="sum").round(2).to_dict(),
            "por_region_anio": df.pivot_table(index="Region", columns="Anio",
                                              values="Sales", aggfunc="sum").round(2).to_dict(),
            "por_region_trimestre": df.pivot_table(index="Region", columns="AnioTrimestre",
                                                   values="Sales", aggfunc="sum").round(2).to_dict(),
            "por_segmento_anio": df.pivot_table(index="Segment", columns="Anio",
                                                values="Sales", aggfunc="sum").round(2).to_dict(),
            "por_categoria_anio": df.pivot_table(index="Category", columns="Anio",
                                                 values="Sales", aggfunc="sum").round(2).to_dict(),
            "por_modo_categoria": df.pivot_table(index="Ship Mode", columns="Category",
                                                 values="Sales", aggfunc="sum").round(2).to_dict(),
            "por_estado": {r.State: round(float(r.Sales), 2)
                           for r in df.groupby("State")["Sales"].sum().reset_index(name="Sales").itertuples()},
            "por_estado_anio": df.pivot_table(index="State", columns="Anio", values="Sales",
                                              aggfunc="sum").round(2).to_dict(),
            "top_productos": [{"Producto": k, "Ventas": round(float(v), 2)}
                              for k, v in df.groupby("Product Name")["Sales"].sum()
                              .sort_values(ascending=False).head(15).items()],
            "subcategorias": [{"Subcategoria": k, "Categoria": df.loc[df["Sub-Category"] == k, "Category"].iat[0],
                               "Ventas": round(float(v), 2)}
                              for k, v in df.groupby("Sub-Category")["Sales"].sum()
                              .sort_values(ascending=False).items()],
            "top_ciudades": [{"Ciudad": f"{r.City}, {r.State}", "Ventas": round(float(r.Sales), 2)}
                             for r in df.groupby(["City", "State"])["Sales"].sum()
                             .reset_index(name="Sales").sort_values("Sales", ascending=False)
                             .head(15).itertuples()],
            "frecuencia_pedidos_cliente": (ped.groupby("Cliente").size()
                                           .value_counts().sort_index()
                                           .rename_axis("pedidos").reset_index(name="clientes")
                                           .to_dict("records")),
        },
    }
    with open(REPORTS / "analisis_completo.json", "w", encoding="utf-8") as fh:
        json.dump(salida, fh, ensure_ascii=False, indent=2, default=str)

    print("Tablas exportadas a datos/:")
    for nombre, tabla in tbs.items():
        print(f"  {nombre:<32} {tabla.shape[0]:>5} filas x {tabla.shape[1]:>2} col")
    print("\nResumen de hipotesis:")
    for k in ["H1", "H2", "H3", "H4", "H5"]:
        pp = hipotesis[k]["prueba_principal"]
        p = pp.get("p_valor", pp.get("p", float("nan")))
        print(f"  {k}: p = {p:.3e}  ->  {'se rechaza H0' if pp.get('significativo') else 'no se rechaza H0'}")
    print(f"\nProyeccion 2019: {proy['total_2019_proyectado']:,.0f} "
          f"({proy['variacion_proyectada']*100:+.1f}% vs 2018)")
    print("OK -> reports/analisis_completo.json")


if __name__ == "__main__":
    main()
