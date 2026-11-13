"""Base do laboratório cripto: carga, indicadores, motor de trades em R."""
from __future__ import annotations
from pathlib import Path
import numpy as np
import pandas as pd

DIR = Path(__file__).resolve().parents[3] / "data" / "cripto"
CUSTO_SPOT = 0.0015   # por lado: taxa 0,1% + slippage 0,05%
CUSTO_FUT = 0.0008    # por lado: taker 0,05% + slippage 0,03%
FUNDING_DIA = 0.0003  # longs pagam ~0,01%/8h; shorts: 0 (conservador)


def carregar(sym: str) -> pd.DataFrame:
    df = pd.read_csv(DIR / f"{sym}.csv", index_col="data", parse_dates=True)
    df = df[df["close"] > 0]
    return df[df.index < pd.Timestamp.now(tz="UTC").normalize().tz_localize(None)]


def rsi(c: pd.Series, n: int) -> pd.Series:
    d = c.diff()
    up = d.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean()
    dn = (-d.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean()
    return 100 - 100 / (1 + up / dn)


def atr(df: pd.DataFrame, n: int = 14) -> pd.Series:
    pc = df.close.shift()
    tr = pd.concat([df.high - df.low, (df.high - pc).abs(), (df.low - pc).abs()], axis=1).max(axis=1)
    return tr.ewm(alpha=1 / n, adjust=False).mean()


def ind(df: pd.DataFrame) -> pd.DataFrame:
    d = df.copy()
    c = d.close
    for n in (9, 20, 50, 100, 200):
        d[f"mm{n}"] = c.rolling(n).mean()
    d["mme9"] = c.ewm(span=9, adjust=False).mean()
    d["mme21"] = c.ewm(span=21, adjust=False).mean()
    d["atr"] = atr(d)
    d["rsi14"] = rsi(c, 14)
    d["rsi2"] = rsi(c, 2)
    for n in (10, 20, 55):
        d[f"hi{n}"] = d.high.rolling(n).max().shift()
        d[f"lo{n}"] = d.low.rolling(n).min().shift()
    return d


def stats(tr: pd.DataFrame, nome: str, ini=None, fim=None) -> dict:
    t = tr
    if ini:
        t = t[t.entrada >= ini]
    if fim:
        t = t[t.entrada <= fim]
    if len(t) == 0:
        return {"nome": nome, "n": 0}
    r = t.r
    eq = r.cumsum()
    dd = (eq - eq.cummax()).min()
    anos = max((pd.Timestamp(t.saida.max()) - pd.Timestamp(t.entrada.min())).days / 365.25, 0.5)
    return {"nome": nome, "n": len(t), "por_ano": round(len(t) / anos, 1), "acerto": round((r > 0).mean() * 100, 1),
            "media_R": round(r.mean(), 3), "total_R": round(r.sum(), 1), "dd_R": round(dd, 1),
            "pf": round(r[r > 0].sum() / -r[r < 0].sum(), 2) if (r < 0).any() else np.inf,
            "dias": round(t.dias.mean(), 1)}


def simular(d: pd.DataFrame, sinais: pd.Series, lado: int, stop_fn, saida_fn, custo: float, funding: bool,
            sym: str = "", max_dias: int = 400) -> pd.DataFrame:
    """sinais: bool no fechamento do dia t -> entra na abertura de t+1.
    stop_fn(d, i) -> preço de stop inicial; saida_fn(d, i_entrada, j, estado) -> (sair?, preço, novo_stop).
    R = resultado / risco inicial, com custos e funding descontados."""
    o, h, l, c = d.open.values, d.high.values, d.low.values, d.close.values
    idx = d.index
    out = []
    i = 0
    s = sinais.values
    n = len(d)
    while i < n - 1:
        if not s[i]:
            i += 1
            continue
        e_i = i + 1
        ent = o[e_i]
        stop = stop_fn(d, i)
        risco = (ent - stop) * lado
        if not np.isfinite(risco) or risco <= ent * 0.003:
            i += 1
            continue
        estado = {"stop": stop, "max": ent, "min": ent}
        saida = None
        for j in range(e_i, min(n, e_i + max_dias)):
            # stop intradiário (com gap)
            if lado == 1 and l[j] <= estado["stop"]:
                saida = (j, min(o[j], estado["stop"]) if j > e_i else estado["stop"]); break
            if lado == -1 and h[j] >= estado["stop"]:
                saida = (j, max(o[j], estado["stop"]) if j > e_i else estado["stop"]); break
            estado["max"] = max(estado["max"], h[j]); estado["min"] = min(estado["min"], l[j])
            sair, preco = saida_fn(d, e_i, j, estado, lado)
            if sair:
                saida = (j, preco); break
        if saida is None:
            j = min(n - 1, e_i + max_dias - 1)
            saida = (j, c[j])
        j, px = saida
        bruto = (px - ent) * lado
        custos = custo * (ent + px)
        if funding and lado == 1:
            custos += FUNDING_DIA * ent * (j - e_i)
        out.append({"sym": sym, "lado": lado, "entrada": idx[e_i], "saida": idx[j], "pe": ent, "ps": px,
                    "stop0": stop, "dias": j - e_i, "r": (bruto - custos) / risco, "ret": (bruto - custos) / ent})
        i = j + 1
    return pd.DataFrame(out)
