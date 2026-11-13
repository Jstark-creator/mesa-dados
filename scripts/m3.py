"""Indicadores e detector de sinais da estratégia M3 (Playbook M3 v1.0).

Regras implementadas (tempo gráfico diário):
- Indicadores: MME 9, MMS 20, IFR 14 (Wilder).
- Filtro de tendência: compra só com MME9 > MMS20 e fechamento > MMS20;
  venda só com MME9 < MMS20 e fechamento < MMS20.
- Filtro de IFR: compra com IFR14 > 50; venda com IFR14 < 50.
- Padrão de compra ("mínima, mínima mais baixa, mínima mais alta"):
  c1, c2, c3 com mínima(c2) < mínima(c1) e mínima(c3) > mínima(c2).
  Gatilho: um candle (o próprio c3 ou o seguinte, c4) com máxima acima da abertura de c1.
- Padrão de venda (espelho): máxima(c2) > máxima(c1) e máxima(c3) < máxima(c2);
  gatilho: um candle com mínima abaixo da abertura de c1.
- Entrada: abertura de c1 (ordem de rompimento).
- Stop de preço: mínima de c2 (compra) / máxima de c2 (venda).
- Alvo: Fibonacci 200% sobre os 4 candles (3 do padrão + candle de rompimento):
  compra = mínima + 2 × (máxima − mínima); venda = máxima − 2 × (máxima − mínima).

Estados de saída:
- "armado": o padrão de 3 candles fechou hoje com os filtros ok e o gatilho ainda não
  aconteceu. Entrada sugerida para o próximo pregão no rompimento da abertura de c1.
- "acionado": o rompimento aconteceu no último candle (no c3 ou num c4).
"""
from __future__ import annotations

import math
from dataclasses import dataclass, asdict

import numpy as np
import pandas as pd


def indicadores(df: pd.DataFrame) -> pd.DataFrame:
    """Recebe OHLCV (colunas open, high, low, close, volume) e devolve com indicadores."""
    out = df.copy()
    out["mme9"] = out["close"].ewm(span=9, adjust=False).mean()
    out["mms20"] = out["close"].rolling(20).mean()
    delta = out["close"].diff()
    ganho = delta.clip(lower=0)
    perda = -delta.clip(upper=0)
    media_g = ganho.ewm(alpha=1 / 14, adjust=False, min_periods=14).mean()
    media_p = perda.ewm(alpha=1 / 14, adjust=False, min_periods=14).mean()
    rs = media_g / media_p.replace(0, np.nan)
    out["ifr14"] = 100 - 100 / (1 + rs)
    out.loc[media_p == 0, "ifr14"] = 100.0
    return out


@dataclass
class Sinal:
    ticker: str
    direcao: str          # "compra" | "venda"
    estado: str           # "armado" | "acionado"
    data: str             # data do último candle analisado
    data_c1: str
    entrada: float
    stop: float
    alvo: float
    fechamento: float
    ifr14: float
    mme9: float
    mms20: float
    risco_pct: float      # distância entrada→stop em % do preço
    retorno_pct: float    # distância entrada→alvo em % do preço
    rr: float             # retorno / risco no ativo


def _r(x: float, n: int = 4) -> float:
    return float(round(x, n)) if x is not None and not math.isnan(x) else float("nan")


def _tendencia_ok(row, direcao: str) -> bool:
    if any(pd.isna(row[k]) for k in ("mme9", "mms20", "ifr14")):
        return False
    if direcao == "compra":
        return row["mme9"] > row["mms20"] and row["close"] > row["mms20"] and row["ifr14"] > 50
    return row["mme9"] < row["mms20"] and row["close"] < row["mms20"] and row["ifr14"] < 50


def _montar(ticker, direcao, estado, c1, c2, candles, ultimo) -> Sinal | None:
    entrada = float(c1["open"])
    lo = float(min(c["low"] for c in candles))
    hi = float(max(c["high"] for c in candles))
    amp = hi - lo
    if direcao == "compra":
        stop = float(c2["low"])
        alvo = lo + 2 * amp
        risco = entrada - stop
        retorno = alvo - entrada
    else:
        stop = float(c2["high"])
        alvo = hi - 2 * amp
        risco = stop - entrada
        retorno = entrada - alvo
    if risco <= 0 or retorno <= 0:
        return None
    return Sinal(
        ticker=ticker, direcao=direcao, estado=estado,
        data=str(ultimo.name.date()), data_c1=str(c1.name.date()),
        entrada=_r(entrada), stop=_r(stop), alvo=_r(alvo),
        fechamento=_r(float(ultimo["close"])), ifr14=_r(float(ultimo["ifr14"]), 2),
        mme9=_r(float(ultimo["mme9"])), mms20=_r(float(ultimo["mms20"])),
        risco_pct=_r(risco / entrada * 100, 2), retorno_pct=_r(retorno / entrada * 100, 2),
        rr=_r(retorno / risco, 2),
    )


def detectar(ticker: str, df: pd.DataFrame) -> list[Sinal]:
    """Procura sinais M3 que terminam no último candle do DataFrame (já com indicadores)."""
    sinais: list[Sinal] = []
    if len(df) < 30:
        return sinais
    n = len(df)
    ultimo = df.iloc[-1]

    # Caso A: padrão c1,c2,c3 onde c3 é o último candle (armado ou acionado no próprio c3)
    c1, c2, c3 = df.iloc[n - 3], df.iloc[n - 2], df.iloc[n - 1]
    # Caso B: padrão c1,c2,c3 terminando no penúltimo candle e rompimento no último (c4)
    b1, b2, b3, b4 = df.iloc[n - 4], df.iloc[n - 3], df.iloc[n - 2], df.iloc[n - 1]

    for direcao in ("compra", "venda"):
        if direcao == "compra":
            padrao = lambda a, b, c: b["low"] < a["low"] and c["low"] > b["low"]
            rompe = lambda a, x: x["high"] > a["open"]
        else:
            padrao = lambda a, b, c: b["high"] > a["high"] and c["high"] < b["high"]
            rompe = lambda a, x: x["low"] < a["open"]

        if padrao(c1, c2, c3) and _tendencia_ok(c3, direcao):
            if rompe(c1, c3):
                s = _montar(ticker, direcao, "acionado", c1, c2, [c1, c2, c3], ultimo)
            else:
                s = _montar(ticker, direcao, "armado", c1, c2, [c1, c2, c3], ultimo)
            if s:
                sinais.append(s)
                continue

        if padrao(b1, b2, b3) and _tendencia_ok(b3, direcao) and not rompe(b1, b3) and rompe(b1, b4):
            s = _montar(ticker, direcao, "acionado", b1, b2, [b1, b2, b3, b4], ultimo)
            if s:
                sinais.append(s)
    return sinais


def resumo(ticker: str, df: pd.DataFrame) -> dict:
    """Foto do ativo no último candle: preço, variação, IFR, tendência."""
    u = df.iloc[-1]
    ant = df.iloc[-2] if len(df) > 1 else u
    if pd.isna(u.get("mme9")) or pd.isna(u.get("mms20")):
        tendencia = "n/d"
    elif u["mme9"] > u["mms20"] and u["close"] > u["mms20"]:
        tendencia = "alta"
    elif u["mme9"] < u["mms20"] and u["close"] < u["mms20"]:
        tendencia = "baixa"
    else:
        tendencia = "lateral"
    return {
        "ticker": ticker,
        "data": str(u.name.date()),
        "fechamento": _r(float(u["close"])),
        "var_dia_pct": _r((u["close"] / ant["close"] - 1) * 100, 2) if ant["close"] else None,
        "ifr14": _r(float(u["ifr14"]), 2) if not pd.isna(u["ifr14"]) else None,
        "mme9": _r(float(u["mme9"])),
        "mms20": _r(float(u["mms20"])) if not pd.isna(u["mms20"]) else None,
        "tendencia": tendencia,
        "max_52s": _r(float(df["high"].tail(252).max())),
        "min_52s": _r(float(df["low"].tail(252).min())),
    }


def sinal_dict(s: Sinal) -> dict:
    return asdict(s)
