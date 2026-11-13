"""Escolha da estrutura de opções para os sinais da M3 v2.1.

EUA: usa a cadeia de opções real do Yahoo (yfinance): IV de cada contrato, bid/ask e open interest.
     - call ATM (delta ~0,50) com vencimento mais próximo de 60 dias (mín. 45)
     - trava de alta com put: vende delta ~0,30, compra delta ~0,15; calcula crédito, R/R e POP
BR:  não há cadeia gratuita; sugere strikes TEÓRICOS (Black-Scholes com a volatilidade realizada),
     para o Gustavo conferir na Genial.
Também guarda o IV ATM diário dos ativos dos EUA em data/iv/<TICKER>.csv para montar o IV percentil real.
"""
from __future__ import annotations

import math
from datetime import date, datetime
from pathlib import Path
from statistics import NormalDist

import pandas as pd

N = NormalDist().cdf
RISCO = {"eua": 400.0, "br": 2000.0}
MEIO = {"eua": 200.0, "br": 1000.0}
JUROS = {"eua": 0.04, "br": 0.11}


def _d1(S, K, T, r, v):
    return (math.log(S / K) + (r + 0.5 * v * v) * T) / (v * math.sqrt(T))


def delta_call(S, K, T, r, v):
    if T <= 0 or v <= 0:
        return 1.0 if S > K else 0.0
    return N(_d1(S, K, T, r, v))


def preco_call(S, K, T, r, v):
    if T <= 0:
        return max(S - K, 0.0)
    a = _d1(S, K, T, r, v)
    return S * N(a) - K * math.exp(-r * T) * N(a - v * math.sqrt(T))


def preco_put(S, K, T, r, v):
    return preco_call(S, K, T, r, v) - S + K * math.exp(-r * T)


def pop_put_credito(S, be, T, r, v):
    """Probabilidade (neutra a risco) de o ativo terminar acima do breakeven."""
    if T <= 0 or v <= 0:
        return float(S > be)
    a = _d1(S, be, T, r, v)
    return N(a - v * math.sqrt(T))


def _mid(row):
    b, a = row.get("bid", 0) or 0, row.get("ask", 0) or 0
    if b > 0 and a > 0:
        return (b + a) / 2, (a - b) / ((a + b) / 2)
    lp = row.get("lastPrice", 0) or 0
    return lp, None


def _escolher_venc(datas: list[str], alvo_dias=60, minimo=45) -> str | None:
    hoje = date.today()
    cand = [(abs((datetime.strptime(d, "%Y-%m-%d").date() - hoje).days - alvo_dias), d) for d in datas
            if (datetime.strptime(d, "%Y-%m-%d").date() - hoje).days >= minimo]
    return min(cand)[1] if cand else None


def estrutura_eua(tk, S: float, veiculo: str) -> dict:
    """tk = yfinance.Ticker. Devolve detalhes da estrutura com dados reais da cadeia."""
    venc = _escolher_venc(list(tk.options or []))
    if not venc:
        return {"erro": "sem vencimento >= 45 dias"}
    dias = (datetime.strptime(venc, "%Y-%m-%d").date() - date.today()).days
    T = dias / 365
    cadeia = tk.option_chain(venc)
    r = JUROS["eua"]
    calls = cadeia.calls.copy()
    puts = cadeia.puts.copy()
    for df_ in (calls, puts):
        df_["iv"] = df_["impliedVolatility"].clip(lower=0.05)
        df_["delta_call"] = [delta_call(S, k, T, r, v) for k, v in zip(df_["strike"], df_["iv"])]
    # IV ATM (média call/put do strike mais próximo)
    katm = calls.iloc[(calls["strike"] - S).abs().argsort().iloc[0]]
    iv_atm = float(katm["iv"])
    out = {"vencimento": venc, "dias": dias, "iv_atm": round(iv_atm, 4)}
    if veiculo == "call_atm":
        c = calls.iloc[(calls["delta_call"] - 0.50).abs().argsort().iloc[0]]
        mid, spr = _mid(c)
        if mid <= 0:
            return {**out, "erro": "sem preço para a call ATM"}
        out.update({
            "estrutura": "Compra de call ATM", "strike": float(c["strike"]), "delta": round(float(c["delta_call"]), 2),
            "premio_meio": round(mid, 2), "bid": float(c.get("bid", 0) or 0), "ask": float(c.get("ask", 0) or 0),
            "spread_pct": round(spr * 100, 1) if spr is not None else None,
            "open_interest": int(c.get("openInterest", 0) or 0),
            "contratos_cheio": int(RISCO["eua"] // (mid * 100)), "contratos_meio": int(MEIO["eua"] // (mid * 100)),
            "custo_por_contrato": round(mid * 100, 2),
            "viavel_cheio": bool(mid * 100 <= RISCO["eua"]), "viavel_meio": bool(mid * 100 <= MEIO["eua"]),
        })
    elif veiculo == "trava_put_credito":
        puts["delta_put"] = 1 - puts["delta_call"]
        vend = puts.iloc[(puts["delta_put"] - 0.30).abs().argsort().iloc[0]]
        comp = puts[puts["strike"] < vend["strike"]]
        if comp.empty:
            return {**out, "erro": "sem strike para a ponta comprada"}
        comp = comp.iloc[(comp["delta_put"] - 0.15).abs().argsort().iloc[0]]
        mv, sv = _mid(vend)
        mc, sc = _mid(comp)
        credito = mv - mc
        larg = float(vend["strike"] - comp["strike"])
        risco = larg - credito
        if credito <= 0 or risco <= 0:
            return {**out, "erro": "crédito inválido"}
        be = float(vend["strike"]) - credito
        pop = pop_put_credito(S, be, T, r, float(vend["iv"]))
        out.update({
            "estrutura": "Trava de alta com put (crédito)",
            "vende_put": float(vend["strike"]), "delta_vendida": round(float(vend["delta_put"]), 2),
            "compra_put": float(comp["strike"]), "delta_comprada": round(float(comp["delta_put"]), 2),
            "credito_meio": round(credito, 2), "largura": larg, "risco_por_trava": round(risco * 100, 2),
            "rr": round(credito / risco, 3), "pop": round(pop, 3), "breakeven": round(be, 2),
            "aprovada_regras": bool(credito / risco > 0.25 and pop > 0.60),
            "spread_pct_vendida": round(sv * 100, 1) if sv is not None else None,
            "open_interest_vendida": int(vend.get("openInterest", 0) or 0),
            "travas_cheio": int(RISCO["eua"] // (risco * 100)), "travas_meio": int(MEIO["eua"] // (risco * 100)),
            "realizar_quando_valer": round(credito * 0.5, 2),
            "viavel_cheio": bool(risco * 100 <= RISCO["eua"]), "viavel_meio": bool(risco * 100 <= MEIO["eua"]),
        })
    return out


def _passo_br(S):
    return 0.25 if S < 10 else (0.5 if S < 30 else 1.0)


def estrutura_br_teorica(S: float, hv: float, veiculo: str, dias: int = 35) -> dict:
    """Sugestão teórica para a B3 (conferir strikes e prêmios reais na Genial)."""
    v = max(0.15, min(2.5, (hv or 0.3) * 1.1))
    T, r, st = dias / 365, JUROS["br"], _passo_br(S)
    grade = [round(k * st, 2) for k in range(int(S * 0.5 / st), int(S * 1.6 / st) + 1)]
    out = {"vencimento_dias": dias, "vol_usada": round(v, 3), "obs": "teórico: confirmar strikes, prêmios e liquidez na Genial"}
    if veiculo == "call_atm":
        k = min(grade, key=lambda k: abs(delta_call(S, k, T, r, v) - 0.5))
        p = preco_call(S, k, T, r, v)
        out.update({"estrutura": "Compra de call ATM", "strike": k, "premio_teorico": round(p, 2),
                    "qtd_cheio": int(RISCO["br"] / p // 100 * 100), "qtd_meio": int(MEIO["br"] / p // 100 * 100)})
    elif veiculo == "trava_put_credito":
        kv = min(grade, key=lambda k: abs((1 - delta_call(S, k, T, r, v)) - 0.30))
        menores = [k for k in grade if k < kv]
        if not menores:
            return {**out, "erro": "sem strike"}
        kc = min(menores, key=lambda k: abs((1 - delta_call(S, k, T, r, v)) - 0.15))
        cred = preco_put(S, kv, T, r, v) - preco_put(S, kc, T, r, v)
        risco = (kv - kc) - cred
        if cred <= 0 or risco <= 0:
            return {**out, "erro": "crédito inválido"}
        pop = pop_put_credito(S, kv - cred, T, r, v)
        out.update({"estrutura": "Trava de alta com put (crédito)", "vende_put": kv, "compra_put": kc,
                    "credito_teorico": round(cred, 2), "rr": round(cred / risco, 3), "pop": round(pop, 3),
                    "aprovada_regras": bool(cred / risco > 0.25 and pop > 0.60),
                    "qtd_cheio": int(RISCO["br"] / risco // 100 * 100), "qtd_meio": int(MEIO["br"] / risco // 100 * 100)})
    return out


def registrar_iv(pasta: Path, ticker: str, dia: str, iv_atm: float) -> float | None:
    """Acrescenta o IV ATM do dia e devolve o IV percentil (precisa de >= 120 dias de histórico)."""
    pasta.mkdir(parents=True, exist_ok=True)
    f = pasta / f"{ticker}.csv"
    df = pd.read_csv(f) if f.exists() else pd.DataFrame(columns=["data", "iv_atm"])
    df = pd.concat([df[df["data"] != dia], pd.DataFrame([{"data": dia, "iv_atm": iv_atm}])]).sort_values("data").tail(400)
    df.to_csv(f, index=False)
    hist = df["iv_atm"].astype(float).tail(252)
    if len(hist) < 120:
        return None
    return float((hist < iv_atm).mean())
