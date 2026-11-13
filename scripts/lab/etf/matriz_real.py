"""Matriz de estruturas de opções com COTAÇÕES REAIS (bid/ask de fechamento da ThetaData), SPY e QQQ.

Diretrizes 1–3 do Gustavo: execução na última hora (cotação de fechamento), três modelos de execução:
  natural  = compra no ask, vende no bid (execução ruim, a mercado);
  meio_50  = metade do caminho entre o meio e o pior lado;
  meio     = no meio do spread (execução ótima).
Comissão: US$ 0,65 por contrato por lado. Decisão (sinal, IV percentil) no fechamento ANTERIOR; execução no dia.
Strikes escolhidos pelo delta calculado da IV implícita do próprio contrato. Vencimento mais próximo de 45 dias (30–60).
Saídas iguais às de matriz.py: alvo/stop da estrutura ou 21 dias restantes, avaliadas na cotação de fechamento.
Saída: data/lab/opcoes_reais/ (só agregados; dados brutos ficam fora do repositório).
"""
from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import brentq
from scipy.stats import norm

sys.path.insert(0, str(Path(__file__).parent))
import matriz as M  # noqa: E402

RAIZ = Path(__file__).resolve().parents[3]
COMISSAO = 0.65 / 100  # por ação (1 contrato = 100)
Q = {"SPY": 0.013, "QQQ": 0.006}
EXEC = {"natural": 1.0, "meio_50": 0.5, "meio": 0.0}


def bs(S, K, T, r, q, v, tipo):
    if T <= 0 or v <= 0:
        return max(S - K, 0) if tipo == "c" else max(K - S, 0)
    d1 = (math.log(S / K) + (r - q + v * v / 2) * T) / (v * math.sqrt(T)); d2 = d1 - v * math.sqrt(T)
    if tipo == "c":
        return S * math.exp(-q * T) * norm.cdf(d1) - K * math.exp(-r * T) * norm.cdf(d2)
    return K * math.exp(-r * T) * norm.cdf(-d2) - S * math.exp(-q * T) * norm.cdf(-d1)


def iv_delta(S, K, T, r, q, preco, tipo):
    intr = max(S - K, 0) if tipo == "c" else max(K - S, 0)
    if preco <= intr + 1e-4 or T <= 0:
        return None, None
    try:
        v = brentq(lambda x: bs(S, K, T, r, q, x, tipo) - preco, 1e-3, 5.0, maxiter=100)
    except ValueError:
        return None, None
    d1 = (math.log(S / K) + (r - q + v * v / 2) * T) / (v * math.sqrt(T))
    dl = math.exp(-q * T) * (norm.cdf(d1) if tipo == "c" else norm.cdf(d1) - 1)
    return v, abs(dl)


def carregar_cadeia(pasta: Path, sym: str) -> pd.DataFrame:
    arqs = sorted((pasta / sym).glob("*.csv.gz"))
    if not arqs:
        raise SystemExit(f"sem dados em {pasta/sym}")
    df = pd.concat([pd.read_csv(a) for a in arqs], ignore_index=True)
    df.columns = [c.lower() for c in df.columns]
    data_col = "created" if "created" in df else ("date" if "date" in df else None)
    df["dia"] = pd.to_datetime(df[data_col].astype(str).str[:10])
    df["exp"] = pd.to_datetime(df["expiration"].astype(str).str[:10].str.replace(r"^(\d{4})(\d{2})(\d{2})$", r"\1-\2-\3", regex=True))
    df["tipo"] = df["right"].astype(str).str.lower().str[0]  # c/p
    df["strike"] = df["strike"].astype(float)
    if df["strike"].median() > 5000:  # milésimos de dólar (formato antigo)
        df["strike"] = df["strike"] / 1000
    df = df[(df.bid > 0) & (df.ask > 0) & (df.ask >= df.bid)]
    return df[["dia", "exp", "tipo", "strike", "bid", "ask"]].drop_duplicates(["dia", "exp", "tipo", "strike"])


def preco_exec(bid, ask, lado, f):
    mid = (bid + ask) / 2
    return mid + f * (ask - mid) if lado > 0 else mid - f * (mid - bid)


def montar(cad_dia, S, dia, r, q, est):
    exps = sorted(cad_dia.exp.unique())
    alvo = dia + pd.Timedelta(days=M.DTE)
    validas = [e for e in exps if 30 <= (e - dia).days <= 60]
    if not validas:
        return None
    exp = min(validas, key=lambda e: abs((e - alvo).days))
    T = (exp - dia).days / 365
    ch = cad_dia[cad_dia.exp == exp]
    pernas = []
    for qtd, tipo, dl_alvo in est["pernas"]:
        sub = ch[ch.tipo == tipo]
        melhor = None
        for row in sub.itertuples():
            _, dl = iv_delta(S, row.strike, T, r, q, (row.bid + row.ask) / 2, tipo)
            if dl is None:
                continue
            err = abs(dl - dl_alvo)
            if melhor is None or err < melhor[0]:
                melhor = (err, row.strike)
        if melhor is None or melhor[0] > 0.08:
            return None
        pernas.append((qtd, tipo, melhor[1]))
    if len({(t, k) for _, t, k in pernas}) < len(pernas):
        return None
    return exp, pernas


def cotar(cad_dia, exp, pernas):
    out = []
    for qtd, tipo, k in pernas:
        x = cad_dia[(cad_dia.exp == exp) & (cad_dia.tipo == tipo) & (cad_dia.strike == k)]
        if x.empty:
            return None
        out.append((qtd, float(x.bid.iloc[0]), float(x.ask.iloc[0])))
    return out


def simular(sym, cad, spot, base, sinal, nome_e, f, espaco=5):
    est = M.ESTR[nome_e]
    dias = [d for d in base.index if d in spot.index and d in cad.groups]
    sg = sinal.reindex(base.index).fillna(False)
    res = []; prox = None; spreads = []
    for k in range(1, len(dias)):
        dia, ontem = dias[k], dias[k - 1]
        if prox is not None and dia < prox:
            continue
        if not sg.get(ontem, False):
            continue
        cd = cad.get_group(dia)
        S = float(spot[dia]); r = float(base.r.get(dia, 0.04))
        m = montar(cd, S, dia, r, Q[sym], est)
        if m is None:
            continue
        exp, pernas = m
        q0 = cotar(cd, exp, pernas)
        if q0 is None:
            continue
        nat = sum(q * ((a if q > 0 else b)) for q, b, a in q0)
        meio = sum(q * (b + a) / 2 for q, b, a in q0)
        if abs(meio) > 0:
            spreads.append(abs(nat - meio) / abs(meio))
        custo = sum(q * preco_exec(b, a, q, f) for q, b, a in q0) + COMISSAO * len(q0)
        debito = custo > 0
        if debito:
            risco = custo
            maxg = abs(pernas[0][2] - pernas[1][2]) - custo if len(pernas) == 2 else None
        else:
            cred = -custo
            larg = max(abs(pernas[0][2] - pernas[1][2]), abs(pernas[2][2] - pernas[3][2]) if len(pernas) == 4 else 0)
            risco = larg - cred
            if cred <= 0 or risco <= 0:
                continue
        resultado = None; saida = None
        for j in range(k + 1, len(dias)):
            dj = dias[j]
            if dj >= exp:
                break
            qj = cotar(cad.get_group(dj), exp, pernas)
            if qj is None:
                continue
            fechar = sum(q * preco_exec(b, a, -q, f) for q, b, a in qj) - COMISSAO * len(qj)  # valor líquido recebido ao fechar (negativo se paga)
            fim = (exp - dj).days <= M.DTE_SAIDA
            if debito:
                pnl = fechar - custo
                alvo = est["alvo_pct_max"] * maxg if "alvo_pct_max" in est else est["alvo"] * custo
                if pnl >= alvo or pnl <= est["stop"] * custo or fim:
                    resultado, saida = pnl, dj; break
            else:
                pnl = cred + fechar  # fechar é negativo (paga para recomprar)
                if pnl >= est["cap"] * cred or pnl <= -est["stop_cred"] * cred or fim:
                    resultado, saida = pnl, dj; break
        if resultado is None:
            continue
        res.append(dict(sym=sym, estrutura=nome_e, entrada=dia, saida=saida, ivp=float(base.ivp.get(ontem, np.nan)),
                        r=resultado / risco, risco=risco * 100))
        prox = dias[min(k + espaco, len(dias) - 1)]
    return pd.DataFrame(res), spreads


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dados", default="/tmp/td")
    ap.add_argument("--spot", default="/tmp/td/spot.csv", help="fechamentos NÃO ajustados (yfinance auto_adjust=False)")
    a = ap.parse_args()
    spot_all = pd.read_csv(a.spot, index_col=0, parse_dates=True)
    saida = RAIZ / "data" / "lab" / "opcoes_reais"; saida.mkdir(parents=True, exist_ok=True)
    linhas = []; slip_lin = []; bs_lin = []
    for sym, ivn in (("SPY", "VIX"), ("QQQ", "VXN")):
        cad = carregar_cadeia(Path(a.dados), sym)
        inicio = cad.dia.min()
        base = M.preparar(sym, ivn)
        base = base[base.index >= inicio - pd.Timedelta(days=10)]
        sinais = M.sinais(base)
        grupos = cad.groupby("dia")
        spot = spot_all[sym].dropna()
        for nome_s, sig in sinais.items():
            for nome_e in M.ESTR:
                if nome_s.startswith("sem direção") != nome_e.startswith("iron"):
                    continue
                if nome_s.startswith("M3-like"):
                    continue
                for ex, f in EXEC.items():
                    T, spr = simular(sym, grupos, spot, base, sig, nome_e, f)
                    if ex == "natural" and spr:
                        slip_lin.append(dict(sym=sym, sinal=nome_s, estrutura=nome_e, n=len(spr),
                                             slippage_mediano_pct=round(float(np.median(spr)) * 100, 1),
                                             slippage_p90_pct=round(float(np.percentile(spr, 90)) * 100, 1)))
                    if T.empty:
                        continue
                    T["faixa"] = T.ivp.map(M.faixa)
                    for fx, g in T.groupby("faixa"):
                        linhas.append(dict(sym=sym, sinal=nome_s, estrutura=nome_e, execucao=ex, faixa=fx, n=len(g),
                                           media_R=round(g.r.mean(), 3), acerto=round((g.r > 0).mean() * 100),
                                           total_R=round(g.r.sum(), 1), risco_medio_usd=round(g.risco.mean())))
                # comparação: modelo Black-Scholes (VIX plano) no mesmo período
                for slip in (0.02, 0.05, 0.10):
                    Tb = M.simular(base, sig, nome_e, slip)
                    Tb = Tb[Tb.entrada >= inicio]
                    if len(Tb):
                        bs_lin.append(dict(sym=sym, sinal=nome_s, estrutura=nome_e, slip=slip, n=len(Tb), media_R=round(Tb.r.mean(), 3)))
    R = pd.DataFrame(linhas); Sl = pd.DataFrame(slip_lin); B = pd.DataFrame(bs_lin)
    R.to_csv(saida / "resumo.csv", index=False); Sl.to_csv(saida / "slippage_real.csv", index=False); B.to_csv(saida / "modelo_bs_mesmo_periodo.csv", index=False)
    # agregado SPY+QQQ por estrutura × faixa × execução
    if not R.empty:
        R["soma"] = R.media_R * R.n
        agg = R.groupby(["sinal", "estrutura", "faixa", "execucao"]).agg(n=("n", "sum"), soma=("soma", "sum")).reset_index()
        agg["media_R"] = (agg.soma / agg.n).round(3)
        piv = agg.pivot_table(index=["sinal", "estrutura", "faixa"], columns="execucao", values="media_R").reset_index()
        nn = agg[agg.execucao == "natural"][["sinal", "estrutura", "faixa", "n"]]
        piv = piv.merge(nn, on=["sinal", "estrutura", "faixa"], how="left")
    else:
        piv = pd.DataFrame()
    with open(saida / "resultado.md", "w") as fh:
        fh.write(f"# Matriz de opções com cotações reais (ThetaData, SPY+QQQ)\n\nPeríodo: {inicio.date()} até o último dado. Gerado automaticamente.\n\n")
        fh.write("## Média em R por operação (natural = compra no ask/vende no bid; meio_50; meio)\n\n")
        fh.write(piv.to_markdown(index=False) if not piv.empty else "sem operações\n")
        fh.write("\n\n## Slippage real na entrada (custo a mercado vs. meio do spread, % do preço líquido da estrutura)\n\n")
        fh.write(Sl.to_markdown(index=False) if not Sl.empty else "n/d\n")
        fh.write("\n\n## Modelo Black-Scholes com VIX plano, mesmo período (para calibrar)\n\n")
        fh.write(B.to_markdown(index=False) if not B.empty else "n/d\n")
    print(open(saida / "resultado.md").read())


if __name__ == "__main__":
    main()
