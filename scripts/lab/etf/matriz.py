"""Matriz de estruturas por IV percentil em ETFs com IV REAL (índices da CBOE). Diretrizes 1, 2 e 3.

- Pares: SPY/VIX, QQQ/VXN, GLD/GVZ. IV = índice/100 (30 dias), usada plana para todos os strikes/prazos
  (limitações: sem skew e sem estrutura a termo; por isso calendário/diagonal NÃO é testado aqui).
- IV percentil: posição do índice nos 252 pregões anteriores (só passado).
- Decisão e execução no FECHAMENTO (última hora): entrada no close do dia do sinal; gestão avaliada só em closes.
- Vencimento: 45 dias corridos. Saídas: alvo/stop da estrutura (regras fixas, não otimizadas) ou 21 dias restantes.
- Slippage por lado sobre o preço líquido da estrutura: 2%, 5%, 10%. Critério do Gustavo: positivo com 10%.
- R = resultado ÷ risco máximo da estrutura. Treino: até 2018. Validação: 2019+.
"""
import sys, math
from pathlib import Path
import numpy as np, pandas as pd
from scipy.stats import norm

DIR = Path(__file__).resolve().parents[3] / "data" / "etf"
PARES = {"SPY": "VIX", "QQQ": "VXN", "GLD": "GVZ"}
DTE, DTE_SAIDA = 45, 21

def ler(n):
    df = pd.read_csv(DIR / f"{n}.csv", index_col="data", parse_dates=True)
    return df[df.index < pd.Timestamp.now(tz="UTC").normalize().tz_localize(None)]

def bs(S, K, T, r, v, tipo):
    if T <= 0: return max(S-K, 0.0) if tipo == "c" else max(K-S, 0.0)
    d1 = (math.log(S/K) + (r + v*v/2)*T) / (v*math.sqrt(T)); d2 = d1 - v*math.sqrt(T)
    if tipo == "c": return S*norm.cdf(d1) - K*math.exp(-r*T)*norm.cdf(d2)
    return K*math.exp(-r*T)*norm.cdf(-d2) - S*norm.cdf(-d1)

def strike(S, T, r, v, delta, tipo):
    """Strike com o delta pedido (delta > 0 em módulo), arredondado para 0,5% do spot."""
    alvo = delta if tipo == "c" else 1 - delta
    d1 = norm.ppf(alvo)
    K = S * math.exp(-(d1 * v * math.sqrt(T)) + (r + v*v/2)*T)
    passo = max(round(S*0.005, 2), 0.01)
    return round(K / passo) * passo

# estrutura: lista de pernas (qtd, tipo, delta); regras de saída em múltiplos do risco/prêmio
ESTR = {
    "call 0,50":            dict(pernas=[(1,"c",.50)], alvo=1.0, stop=-0.5),
    "call 0,70":            dict(pernas=[(1,"c",.70)], alvo=1.0, stop=-0.5),
    "trava débito 0,50/0,25": dict(pernas=[(1,"c",.50),(-1,"c",.25)], alvo_pct_max=0.6, stop=-0.5),
    "trava débito 0,65/0,35": dict(pernas=[(1,"c",.65),(-1,"c",.35)], alvo_pct_max=0.6, stop=-0.5),
    "trava crédito put 0,30/0,15": dict(pernas=[(-1,"p",.30),(1,"p",.15)], cap=0.5, stop_cred=2.0),
    "trava crédito put 0,20/0,10": dict(pernas=[(-1,"p",.20),(1,"p",.10)], cap=0.5, stop_cred=2.0),
    "iron condor 0,20/0,10": dict(pernas=[(-1,"p",.20),(1,"p",.10),(-1,"c",.20),(1,"c",.10)], cap=0.5, stop_cred=2.0),
}

def preparar(etf, ivn):
    d = ler(etf); iv = ler(ivn).close / 100
    irx = ler("IRX").close / 100
    d = d.assign(iv=iv.reindex(d.index).ffill(limit=3), r=irx.reindex(d.index).ffill().fillna(0.02)).dropna(subset=["iv"])
    c = d.close
    d["mm200"] = c.rolling(200).mean(); d["mms20"] = c.rolling(20).mean(); d["mme9"] = c.ewm(span=9, adjust=False).mean()
    dl = c.diff(); up = dl.clip(lower=0).ewm(alpha=1/14, adjust=False).mean(); dn = (-dl.clip(upper=0)).ewm(alpha=1/14, adjust=False).mean()
    d["ifr"] = 100 - 100/(1+up/dn)
    d["ivp"] = d.iv.rolling(252).apply(lambda x: (x[:-1] < x[-1]).mean(), raw=True)
    d["hi20"] = d.high.rolling(20).max().shift()
    return d.dropna(subset=["mm200", "ivp"])

def sinais(d):
    c = d.close
    alta = (c > d.mm200) & (d.mme9 > d.mms20)
    return {
        "tendência (MM200 + MME9>MMS20)": alta,
        "M3-like (tendência + IFR>60 + mínima ascendente)": alta & (d.ifr > 60) & (d.low.shift(1) < d.low.shift(2)) & (d.low > d.low.shift(1)),
        "rompimento 20d em tendência": alta & (c > d.hi20),
        "sem direção (sempre)": pd.Series(True, index=d.index),
    }

def simular(d, sinal, nome_e, slip, espaco=5):
    e = ESTR[nome_e]; idx = d.index; S = d.close.values; IV = d.iv.values; R = d.r.values; IVP = d.ivp.values
    sg = sinal.values; out = []; prox = 0
    for i in range(len(d) - 1):
        if i < prox or not sg[i]: continue
        T0 = DTE/365; v = IV[i]; r = R[i]
        Ks = [(q, t, strike(S[i], T0, r, v, dl, t)) for q, t, dl in e["pernas"]]
        if len({k for _, _, k in Ks}) < len(Ks): continue
        val0 = sum(q*bs(S[i], k, T0, r, v, t) for q, t, k in Ks)
        debito = val0 > 0
        if debito:
            custo = val0*(1+slip); risco = custo
            maxg = (abs(Ks[0][2]-Ks[1][2]) - custo) if len(Ks) == 2 else None
        else:
            cred = -val0*(1-slip)
            larg = max(abs(Ks[0][2]-Ks[1][2]), abs(Ks[2][2]-Ks[3][2]) if len(Ks) == 4 else 0)
            risco = larg - cred
            if cred <= 0 or risco <= 0: continue
        res = None
        for j in range(i+1, len(d)):
            dias = (idx[j]-idx[i]).days; T = (DTE-dias)/365
            val = sum(q*bs(S[j], k, max(T, 0), R[j], IV[j], t) for q, t, k in Ks)
            fim = dias >= DTE-DTE_SAIDA
            if debito:
                pnl = val*(1-slip) - custo
                alvo = e["alvo_pct_max"]*maxg if "alvo_pct_max" in e else e["alvo"]*custo
                if pnl >= alvo or pnl <= e["stop"]*custo or fim: res = pnl; break
            else:
                fechar = -val*(1+slip)  # custo para recomprar
                pnl = cred - fechar
                if pnl >= e["cap"]*cred or pnl <= -e["stop_cred"]*cred or fim: res = max(pnl, -risco); break
        if res is None: continue
        out.append(dict(entrada=idx[i], saida=idx[j], ivp=IVP[i], r=res/risco, dias=(idx[j]-idx[i]).days))
        prox = i + espaco
    return pd.DataFrame(out)

def faixa(x): return "baixo <30%" if x < .30 else ("médio 30–60%" if x < .60 else "alto >60%")

if __name__ == "__main__":
    D = {e: preparar(e, i) for e, i in PARES.items()}
    linhas = []
    for nome_s in list(sinais(D["SPY"]).keys()):
        for nome_e in ESTR:
            if nome_s.startswith("sem direção") != nome_e.startswith("iron"): continue
            for slip in (0.02, 0.05, 0.10):
                T = pd.concat([simular(d, sinais(d)[nome_s], nome_e, slip).assign(etf=e) for e, d in D.items()])
                T["faixa"] = T.ivp.map(faixa)
                for fx, g in T.groupby("faixa"):
                    tr = g[g.entrada <= "2018-12-31"].r; va = g[g.entrada >= "2019-01-01"].r
                    linhas.append(dict(sinal=nome_s, estrutura=nome_e, slip=slip, faixa=fx, n_tr=len(tr), R_tr=round(tr.mean(), 3),
                                       n_va=len(va), R_va=round(va.mean(), 3), ac_va=round((va > 0).mean()*100), tot_va=round(va.sum(), 1)))
    R = pd.DataFrame(linhas); R.to_csv("/tmp/matriz_etf.csv", index=False)
    pd.set_option("display.width", 250); pd.set_option("display.max_rows", 500)
    p = R.pivot_table(index=["sinal", "estrutura", "faixa"], columns="slip", values=["R_tr", "R_va"]).round(3)
    n = R[R.slip == 0.10].set_index(["sinal", "estrutura", "faixa"])[["n_tr", "n_va", "ac_va"]]
    print(p.join(n).to_string())
