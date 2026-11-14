"""M4 — Fase A (pré-registrada em estrategias/m4-preregistro.md, 14/11/2026).

Para cada setup (S1, S2, S3 × compra/venda), mede a probabilidade de o ATIVO tocar +1,0·σ20 a favor
antes de −0,5·σ20 contra, em H pregões (EUA 20, BR 15). Compara com a base (todos os dias) e a base
de tendência (mesmo regime de MM200). Treino até 2018; validação 2019+. Sem parâmetros livres.
"""
from __future__ import annotations
import json
from pathlib import Path
import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parents[3]
H = {"eua": 20, "br": 15}
K_ALVO, K_STOP = 1.0, 0.5


def carregar(t):
    df = pd.read_csv(RAIZ / "data" / "historico" / f"{t}.csv", index_col="data", parse_dates=True)
    df = df[(df.close > 0) & (df.high >= df.low)]
    return df[df.index < pd.Timestamp.now().normalize()]


def ind(d):
    c = d.close
    d = d.copy()
    for n in (21, 50, 200):
        d[f"mm{n}"] = c.rolling(n).mean()
    pc = c.shift()
    tr = pd.concat([d.high - d.low, (d.high - pc).abs(), (d.low - pc).abs()], axis=1).max(axis=1)
    d["atr"] = tr.rolling(14).mean()
    dl = c.diff(); up = dl.clip(lower=0).ewm(alpha=1/14, adjust=False).mean(); dn = (-dl.clip(upper=0)).ewm(alpha=1/14, adjust=False).mean()
    d["ifr"] = 100 - 100 / (1 + up / dn)
    m20 = c.rolling(20).mean(); sd = c.rolling(20).std()
    d["bbw"] = 4 * sd / m20
    d["bbw_pct"] = d.bbw.rolling(120).apply(lambda x: (x[:-1] < x[-1]).mean(), raw=True)
    d["hi20"] = d.high.rolling(20).max().shift(); d["lo20"] = d.low.rolling(20).min().shift()
    d["vmed"] = d.volume.rolling(20).mean().shift()
    d["sig20"] = np.log(c).diff().rolling(20).std() * np.sqrt(20)
    return d


def setups(d):
    c, h, l = d.close, d.high, d.low
    comp = d.bbw_pct.rolling(5).min() <= 0.20
    vol = d.volume > 1.5 * d.vmed
    perto21 = (l - d.mm21).abs() <= d.atr; perto50 = (l - d.mm50).abs() <= d.atr
    perto21v = (h - d.mm21).abs() <= d.atr; perto50v = (h - d.mm50).abs() <= d.atr
    rng = (h - l).replace(0, np.nan)
    return {
        ("S1", 1): comp & (c > d.hi20) & vol & (c > d.mm50),
        ("S1", -1): comp & (c < d.lo20) & vol & (c < d.mm50),
        ("S2", 1): (c > d.mm200) & (d.mm50 > d.mm200) & (perto21 | perto50).rolling(3).max().astype(bool)
                   & (d.ifr.rolling(5).min() <= 45) & (c > h.shift()),
        ("S2", -1): (c < d.mm200) & (d.mm50 < d.mm200) & (perto21v | perto50v).rolling(3).max().astype(bool)
                    & (d.ifr.rolling(5).max() >= 55) & (c < l.shift()),
        ("S3", 1): (l < d.lo20) & (c > d.lo20) & ((c - l) / rng >= 2 / 3) & (d.ifr < 40),
        ("S3", -1): (h > d.hi20) & (c < d.hi20) & ((h - c) / rng >= 2 / 3) & (d.ifr > 60),
    }


def desfechos(d, lado, Hd):
    """1 = alvo primeiro, 0 = stop primeiro (ou mesmo dia), nan = nenhum em H (conta como não-alvo)."""
    c, h, l, s = d.close.values, d.high.values, d.low.values, d.sig20.values
    n = len(d); out = np.full(n, np.nan); tempo = np.full(n, np.nan)
    for i in range(n - 1):
        if not np.isfinite(s[i]) or s[i] <= 0:
            continue
        alvo = c[i] * np.exp(lado * K_ALVO * s[i]); stop = c[i] * np.exp(-lado * K_STOP * s[i])
        res = 0.0  # timeout conta como fracasso
        for j in range(i + 1, min(n, i + 1 + Hd)):
            ba = h[j] >= alvo if lado == 1 else l[j] <= alvo
            bs = l[j] <= stop if lado == 1 else h[j] >= stop
            if bs:
                res = 0.0; tempo[i] = j - i; break
            if ba:
                res = 1.0; tempo[i] = j - i; break
        else:
            if i + Hd >= n:
                continue  # janela incompleta no fim
        out[i] = res
    return out, tempo


def main():
    u = json.loads((RAIZ / "config" / "universo_m4.json").read_text())
    linhas = []; detalhes = []
    for mercado in ("eua", "br"):
        for t in u[mercado]:
            arq = RAIZ / "data" / "historico" / f"{t}.csv"
            if not arq.exists():
                print(f"sem histórico: {t}"); continue
            d = ind(carregar(t)).dropna(subset=["mm200", "sig20", "bbw_pct", "atr"])
            if len(d) < 300:
                continue
            per = np.where(d.index <= "2018-12-31", "treino", "validacao")
            regime = np.sign(d.close - d.mm200).values
            for lado in (1, -1):
                res, tempo = desfechos(d, lado, H[mercado])
                base = pd.DataFrame({"res": res, "per": per, "regime": regime})
                S = setups(d)
                for (nome, l2), sig in S.items():
                    if l2 != lado:
                        continue
                    m = sig.fillna(False).values & np.isfinite(res)
                    for p in ("treino", "validacao"):
                        sel = m & (per == p)
                        bsel = np.isfinite(res) & (per == p)
                        bt = bsel & (regime == lado)
                        linhas.append(dict(mercado=mercado, ativo=t, setup=nome, lado=lado, periodo=p,
                                           n=int(sel.sum()), acertos=float(np.nansum(res[sel])),
                                           base_n=int(bsel.sum()), base_ac=float(np.nansum(res[bsel])),
                                           baset_n=int(bt.sum()), baset_ac=float(np.nansum(res[bt]))))
                    idx = np.where(m)[0]
                    for i in idx:
                        detalhes.append(dict(mercado=mercado, ativo=t, setup=nome, lado=lado, data=d.index[i].date(),
                                             periodo=per[i], res=res[i], dias=tempo[i]))
    L = pd.DataFrame(linhas)
    out = RAIZ / "data" / "lab" / "m4"; out.mkdir(parents=True, exist_ok=True)
    L.to_csv(out / "fase_a_por_ativo.csv", index=False)
    pd.DataFrame(detalhes).to_csv(out / "fase_a_sinais.csv.gz", index=False, compression="gzip")
    g = L.groupby(["mercado", "setup", "lado", "periodo"]).sum(numeric_only=True).reset_index()
    g["P_setup"] = (g.acertos / g.n).round(3); g["P_base"] = (g.base_ac / g.base_n).round(3)
    g["P_base_tend"] = (g.baset_ac / g.baset_n).round(3); g["lift_tend"] = (g.P_setup / g.P_base_tend).round(2)
    g["n_ativos"] = L[L.n > 0].groupby(["mercado", "setup", "lado", "periodo"]).ativo.nunique().reindex(
        pd.MultiIndex.from_frame(g[["mercado", "setup", "lado", "periodo"]])).values
    tab = g[["mercado", "setup", "lado", "periodo", "n", "n_ativos", "P_setup", "P_base", "P_base_tend", "lift_tend"]]
    # critério pré-registrado
    v = tab[tab.periodo == "validacao"].set_index(["mercado", "setup", "lado"])
    tr = tab[tab.periodo == "treino"].set_index(["mercado", "setup", "lado"])
    ap = pd.DataFrame({"n_val": v.n, "P_val": v.P_setup, "lift_val": v.lift_tend, "lift_treino": tr.lift_tend})
    ap["aprovado"] = (ap.n_val >= 100) & (ap.P_val >= 0.40) & (ap.lift_val >= 1.3) & (ap.lift_treino >= 1.3)
    with open(out / "fase_a_resultado.md", "w") as fh:
        fh.write("# M4 — Fase A (gerado automaticamente)\n\n## Probabilidade de +1σ antes de −0,5σ\n\n")
        fh.write(tab.to_markdown(index=False))
        fh.write("\n\n## Critério pré-registrado (N_val ≥ 100, P_val ≥ 40%, lift ≥ 1,3 no treino e na validação)\n\n")
        fh.write(ap.reset_index().to_markdown(index=False))
    print(open(out / "fase_a_resultado.md").read())


if __name__ == "__main__":
    main()
