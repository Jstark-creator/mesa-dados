"""M6 — Fase A (pré-registro: estrategias/m6-preregistro.md, 14/11/2026). Implementação vetorizada.

Setups C1 (gap de catalisador) e C2 (líder relativo rompendo), call/put, com 4 filtros comuns
(macro SPY×MM200; médias MM50/MM200; topos e fundos de Dow com pivôs 3/3 confirmados; espaço até a
resistência/suporte de 252 pregões) e 3 perfis de alvo/stop em σ (σ = vol 20d × √30; H = 30 pregões).
Versões sem filtros: só informativas.
"""
from __future__ import annotations
import json
from pathlib import Path
import numpy as np
import pandas as pd
from numpy.lib.stride_tricks import sliding_window_view as swv

RAIZ = Path(__file__).resolve().parents[3]
H = 30
PERFIS = {"conservador": (0.5, 0.5), "atual": (1.0, 0.5), "folgado": (1.0, 1.0)}
TREINO_FIM = pd.Timestamp("2018-12-31")


def carregar(t):
    df = pd.read_csv(RAIZ / "data" / "historico" / f"{t}.csv", index_col="data", parse_dates=True)
    df = df[(df.close > 0) & (df.high >= df.low)]
    df = df[~((df.open == df.high) & (df.high == df.low) & (df.low == df.close))]
    return df[df.index < pd.Timestamp.now().normalize()]


def pivos(h, l, k=3):
    n = len(h)
    ph = np.zeros(n, bool); pl = np.zeros(n, bool)
    for i in range(k, n - k):
        if h[i] > h[i - k:i].max() and h[i] > h[i + 1:i + 1 + k].max():
            ph[i] = True
        if l[i] < l[i - k:i].min() and l[i] < l[i + 1:i + 1 + k].min():
            pl[i] = True
    # estrutura conhecida em t: pivôs com índice <= t-k
    def ultimos(flags, vals):
        u1 = np.full(n, np.nan); u2 = np.full(n, np.nan)
        a = b = np.nan
        idx = np.where(flags)[0]; p = 0
        for t in range(n):
            while p < len(idx) and idx[p] <= t - k:
                b, a = a, vals[idx[p]]; p += 1
            u1[t], u2[t] = a, b
        return u1, u2
    h1, h2 = ultimos(ph, h); l1, l2 = ultimos(pl, l)
    return h1, h2, l1, l2


def desfecho(c, h, l, sig, a, b, lado):
    n = len(c); out = np.full(n, np.nan)
    if n <= H + 1:
        return out
    HH = swv(h[1:], H); LL = swv(l[1:], H)  # linha i -> dias i+1..i+H
    m = HH.shape[0]
    alvo = c[:m] * np.exp(lado * a * sig[:m]); stop = c[:m] * np.exp(-lado * b * sig[:m])
    if lado == 1:
        A = HH >= alvo[:, None]; S = LL <= stop[:, None]
    else:
        A = LL <= alvo[:, None]; S = HH >= stop[:, None]
    fa = np.where(A.any(1), A.argmax(1), H); fs = np.where(S.any(1), S.argmax(1), H)
    res = ((fa < fs) & (fa < H)).astype(float)
    res[~np.isfinite(sig[:m])] = np.nan
    out[:m] = res
    return out


def dedup(sinal, gap=10):
    s = sinal.values.copy(); ult = -10**9
    for i in np.where(s)[0]:
        if i - ult < gap:
            s[i] = False
        else:
            ult = i
    return pd.Series(s, index=sinal.index)


def main():
    u = json.loads((RAIZ / "config" / "universo_m6.json").read_text())
    spy = carregar("SPY"); spy_alta = spy.close > spy.close.rolling(200).mean()
    D = {}
    for t in u["acoes"]:
        f = RAIZ / "data" / "historico" / f"{t}.csv"
        if f.exists():
            d = carregar(t)
            if len(d) > 400:
                D[t] = d
    print(f"ações com dados: {len(D)} de {len(u['acoes'])}")
    # força relativa (painel)
    C = pd.DataFrame({t: d.close for t, d in D.items()})
    mom = C.shift(21) / C.shift(126) - 1
    cnt = mom.notna().sum(1)
    rk = mom.rank(axis=1, pct=True)
    rk[cnt < 30] = np.nan
    linhas = []
    for t, d in D.items():
        c, h, l, o, v = d.close, d.high, d.low, d.open, d.volume
        pc = c.shift()
        tr = pd.concat([h - l, (h - pc).abs(), (l - pc).abs()], axis=1).max(axis=1)
        atr = tr.rolling(14).mean().shift()
        vmed = v.rolling(20).mean().shift()
        mm50, mm200 = c.rolling(50).mean(), c.rolling(200).mean()
        sig = (np.log(c).diff().rolling(20).std() * np.sqrt(H))
        h1, h2, l1, l2 = pivos(h.values, l.values)
        dow_alta = pd.Series((l1 > l2) & (h1 > h2), index=d.index)
        dow_baixa = pd.Series((l1 < l2) & (h1 < h2), index=d.index)
        hi252 = h.rolling(252).max().shift(); lo252 = l.rolling(252).min().shift()
        hi60, lo60 = h.rolling(60).max().shift(), l.rolling(60).min().shift()
        hi50, lo50 = h.rolling(50).max().shift(), l.rolling(50).min().shift()
        rng = (h - l).replace(0, np.nan); pos = (c - l) / rng
        mac = spy_alta.reindex(d.index).ffill().fillna(False)
        r = rk[t].reindex(d.index) if t in rk else pd.Series(np.nan, index=d.index)
        preco_ok = c > 20
        base_c1 = {1: (((o - pc) >= 2 * atr) | ((c - pc) >= 2 * atr)) & (v >= 3 * vmed) & (pos >= 0.5) & (c > hi60),
                   -1: (((pc - o) >= 2 * atr) | ((pc - c) >= 2 * atr)) & (v >= 3 * vmed) & (pos <= 0.5) & (c < lo60)}
        base_c2 = {1: (r >= 0.9) & (c > hi50), -1: (r <= 0.1) & (c < lo50)}
        filt = {1: mac & (c > mm50) & (mm50 > mm200) & dow_alta,
                -1: (~mac) & (c < mm50) & (mm50 < mm200) & dow_baixa}
        per = np.where(d.index <= TREINO_FIM, "treino", "validacao")
        for perfil, (a, b) in PERFIS.items():
            for lado in (1, -1):
                res = desfecho(c.values, h.values, l.values, sig.values, a, b, lado)
                ok = np.isfinite(res)
                espaco = ((hi252 <= c) | (hi252 >= c * np.exp(a * sig))) if lado == 1 else ((lo252 >= c) | (lo252 <= c * np.exp(-a * sig)))
                for setup, base in (("C1", base_c1[lado]), ("C2", base_c2[lado])):
                    for versao, s in (("oficial", base & filt[lado] & espaco), ("sem_filtros", base)):
                        s = dedup((s & preco_ok).fillna(False))
                        for p in ("treino", "validacao"):
                            m = s.values & ok & (per == p)
                            bm = ok & (per == p) & preco_ok.values
                            linhas.append(dict(ativo=t, setup=setup, lado=lado, perfil=perfil, versao=versao, periodo=p,
                                               n=int(m.sum()), ac=float(res[m].sum()), bn=int(bm.sum()), bac=float(res[bm].sum())))
    L = pd.DataFrame(linhas)
    out = RAIZ / "data" / "lab" / "m6"; out.mkdir(parents=True, exist_ok=True)
    L.to_csv(out / "fase_a_por_ativo.csv.gz", index=False, compression="gzip")
    g = L.groupby(["versao", "setup", "lado", "perfil", "periodo"])[["n", "ac", "bn", "bac"]].sum().reset_index()
    g["P"] = g.ac / g.n; g["P_base"] = g.bac / g.bn; g["lift"] = g.P / g.P_base
    g["empate"] = g.perfil.map({k: b / (a + b) for k, (a, b) in PERFIS.items()})
    g["passa"] = (g.n >= 100) & (g.P >= 1.2 * g.empate) & (g.lift >= 1.3)
    tab = g.round(3)
    # decisão pré-registrada (só versão oficial)
    dec = []
    for (setup, lado), gg in tab[tab.versao == "oficial"].groupby(["setup", "lado"]):
        tr = gg[gg.periodo == "treino"].set_index("perfil"); va = gg[gg.periodo == "validacao"].set_index("perfil")
        cand = tr[tr.passa]
        if cand.empty:
            dec.append(dict(setup=setup, lado=lado, perfil_escolhido="nenhum passa no treino", aprovado=False)); continue
        pf = (cand.P - cand.empate).idxmax()
        dec.append(dict(setup=setup, lado=lado, perfil_escolhido=pf, P_treino=cand.loc[pf, "P"], lift_treino=cand.loc[pf, "lift"],
                        n_val=va.loc[pf, "n"], P_val=va.loc[pf, "P"], lift_val=va.loc[pf, "lift"], aprovado=bool(va.loc[pf, "passa"])))
    Dd = pd.DataFrame(dec)
    cols = ["versao", "setup", "lado", "perfil", "periodo", "n", "P", "P_base", "lift", "empate", "passa"]
    with open(out / "fase_a_resultado.md", "w") as fh:
        fh.write(f"# M6 — Fase A (gerado automaticamente)\n\nAções com dados: {len(D)}\n\n## Decisão pré-registrada (versão oficial)\n\n")
        fh.write(Dd.to_markdown(index=False))
        fh.write("\n\n## Tabela completa (sem_filtros = só informativo)\n\n")
        fh.write(tab[cols].sort_values(["versao", "setup", "lado", "perfil", "periodo"]).to_markdown(index=False))
    print(open(out / "fase_a_resultado.md").read())


if __name__ == "__main__":
    main()
