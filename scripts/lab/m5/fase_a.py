"""M5 — Fase A (pré-registro: estrategias/m5-preregistro.md, 14/11/2026).
Eventos = 1º pregão de cada mês com regime ligado (alta: close>MM200 e ret126>0; baixa: close<MM200 e ret126<0).
Desfecho: tocar +1,0·σ50 a favor antes de −0,5·σ50 contra em 50 pregões (σ50 = vol diária 20d × √50).
Base = 1º pregão de todos os meses, mesma direção. Treino ≤2018, validação 2019+.
"""
from pathlib import Path
import numpy as np, pandas as pd

RAIZ = Path(__file__).resolve().parents[3]
ETFS = ["SPY", "QQQ", "IWM", "DIA", "XLK", "XLF", "XLE", "SMH", "GLD", "TLT", "EEM", "XBI"]
H, KA, KS = 50, 1.0, 0.5

def carregar(t):
    df = pd.read_csv(RAIZ / "data" / "historico" / f"{t}.csv", index_col="data", parse_dates=True)
    df = df[(df.close > 0) & (df.high >= df.low)]
    df = df[~((df.open == df.high) & (df.high == df.low) & (df.low == df.close))]  # barras paradas
    return df[df.index < pd.Timestamp.now().normalize()]

def desfecho(c, h, l, s, i, lado):
    alvo = c[i] * np.exp(lado * KA * s); stop = c[i] * np.exp(-lado * KS * s)
    if i + H >= len(c):
        # janela incompleta: só conta se já tocou algo
        pass
    for j in range(i + 1, min(len(c), i + 1 + H)):
        if (l[j] <= stop) if lado == 1 else (h[j] >= stop):
            return 0.0
        if (h[j] >= alvo) if lado == 1 else (l[j] <= alvo):
            return 1.0
    return 0.0 if i + H < len(c) else np.nan

def main():
    linhas = []
    for t in ETFS:
        d = carregar(t); c = d.close
        mm = c.rolling(200).mean(); r126 = c / c.shift(126) - 1
        s50 = np.log(c).diff().rolling(20).std() * np.sqrt(H)
        prim = d.index.to_series().groupby(d.index.to_period("M")).min().values
        C, Hh, L, S = c.values, d.high.values, d.low.values, s50.values
        pos = {dt: k for k, dt in enumerate(d.index)}
        for dt in prim:
            i = pos[pd.Timestamp(dt)]
            if not (np.isfinite(mm.iloc[i]) and np.isfinite(r126.iloc[i]) and np.isfinite(S[i])):
                continue
            per = "treino" if dt <= np.datetime64("2018-12-31") else "validacao"
            alta = (C[i] > mm.iloc[i]) and (r126.iloc[i] > 0)
            baixa = (C[i] < mm.iloc[i]) and (r126.iloc[i] < 0)
            for lado, lig in ((1, alta), (-1, baixa)):
                res = desfecho(C, Hh, L, S[i], i, lado)
                if np.isnan(res):
                    continue
                linhas.append(dict(etf=t, data=pd.Timestamp(dt).date(), periodo=per, lado=lado, regime=bool(lig), res=res))
    D = pd.DataFrame(linhas)
    out = RAIZ / "data" / "lab" / "m5"; out.mkdir(parents=True, exist_ok=True)
    D.to_csv(out / "fase_a_eventos.csv", index=False)
    rows = []
    for (lado, per), g in D.groupby(["lado", "periodo"]):
        s = g[g.regime]; b = g
        rows.append(dict(lado="compra (call)" if lado == 1 else "venda (put)", periodo=per, n=len(s), P_regime=round(s.res.mean(), 3),
                         n_base=len(b), P_base=round(b.res.mean(), 3), lift=round(s.res.mean() / b.res.mean(), 2)))
    T = pd.DataFrame(rows)
    ap = []
    for lado, g in T.groupby("lado"):
        v = g[g.periodo == "validacao"].iloc[0]; tr = g[g.periodo == "treino"].iloc[0]
        ap.append(dict(lado=lado, n_val=v.n, P_val=v.P_regime, lift_val=v.lift, lift_treino=tr.lift,
                       aprovado=bool(v.n >= 100 and v.P_regime >= 0.40 and v.lift >= 1.3 and tr.lift >= 1.3)))
    A = pd.DataFrame(ap)
    por_etf = D[D.regime].groupby(["etf", "lado", "periodo"]).res.agg(["count", "mean"]).round(3).unstack("periodo")
    with open(out / "fase_a_resultado.md", "w") as fh:
        fh.write("# M5 — Fase A (gerado automaticamente)\n\n")
        fh.write(T.to_markdown(index=False) + "\n\n## Critério pré-registrado\n\n" + A.to_markdown(index=False))
        fh.write("\n\n## Por ETF (só informativo)\n\n" + por_etf.to_markdown())
    print(open(out / "fase_a_resultado.md").read())

if __name__ == "__main__":
    main()
