import sys; sys.path.insert(0, __file__.rsplit('/',1)[0])
from base import *

def stop_atr(k):
    return lambda d, i, lado=1: None

def rodar(d, sym, nome, lado, sinal, kstop, saida, custo, fund):
    a = d.atr.values; lo = d.low.values; hi = d.high.values
    stopf = (lambda dd, i: dd.close.values[i] - kstop * a[i]) if lado == 1 else (lambda dd, i: dd.close.values[i] + kstop * a[i])
    t = simular(d, sinal.fillna(False), lado, stopf, saida, custo, fund, sym)
    t["sist"] = nome
    return t

def saida_trail_don(n):
    def f(d, e, j, est, lado):
        c = d.close.values[j]
        if lado == 1:
            nv = d[f"lo{n}"].values[j]
            if c < nv: return True, c
        else:
            nv = d[f"hi{n}"].values[j]
            if c > nv: return True, c
        return False, None
    return f

def saida_chand(k):
    def f(d, e, j, est, lado):
        a = d.atr.values[j]
        if lado == 1:
            est["stop"] = max(est["stop"], est["max"] - k * a)
        else:
            est["stop"] = min(est["stop"], est["min"] + k * a)
        return False, None
    return f

def saida_rsi2(lim, maxd):
    def f(d, e, j, est, lado):
        r = d.rsi2.values[j]; c = d.close.values[j]
        if (lado == 1 and r > lim) or (lado == -1 and r < lim) or j - e >= maxd: return True, c
        return False, None
    return f

def saida_mm(n):
    def f(d, e, j, est, lado):
        c = d.close.values[j]; m = d[n].values[j]
        if (lado == 1 and c < m) or (lado == -1 and c > m): return True, c
        return False, None
    return f

def sistemas(d):
    c = d.close
    alta = c > d.mm200
    baixa = c < d.mm200
    return {
        "L1 rompe 20d + trail 10d": (1, alta & (c > d.hi20), 2.0, saida_trail_don(10)),
        "L1b rompe 20d + chandelier 3ATR": (1, alta & (c > d.hi20), 2.0, saida_chand(3)),
        "L1c rompe 55d + trail 20d": (1, alta & (c > d.hi55), 2.5, saida_trail_don(20)),
        "L2 pullback RSI2<10": (1, alta & (d.rsi2 < 10), 2.5, saida_rsi2(70, 10)),
        "L4 cruz MME9>21 + sai < MME21": (1, alta & (d.mme9 > d.mme21) & (d.mme9.shift() <= d.mme21.shift()), 2.0, saida_mm("mme21")),
        "S1 perde 20d + trail 10d": (-1, baixa & (c < d.lo20), 2.0, saida_trail_don(10)),
        "S1b perde 20d + chandelier 3ATR": (-1, baixa & (c < d.lo20), 2.0, saida_chand(3)),
        "S2 repique RSI2>90": (-1, baixa & (d.rsi2 > 90), 2.5, saida_rsi2(30, 10)),
        "S4 cruz MME9<21 + sai > MME21": (-1, baixa & (d.mme9 < d.mme21) & (d.mme9.shift() >= d.mme21.shift()), 2.0, saida_mm("mme21")),
    }

if __name__ == "__main__":
    syms = sys.argv[1].split(",") if len(sys.argv) > 1 else ["BTC", "ETH"]
    todos = []
    for s in syms:
        d = ind(carregar(s))
        for nome, (lado, sig, k, sai) in sistemas(d).items():
            fut = lado == -1
            todos.append(rodar(d, s, nome, lado, sig, k, sai, CUSTO_FUT if fut else CUSTO_SPOT, False))
            # versão em futuros (long também), com funding
            if lado == 1:
                t = rodar(d, s, nome + " [fut]", lado, sig, k, sai, CUSTO_FUT, True); todos.append(t)
    T = pd.concat(todos)
    T.to_csv("/tmp/c1_trades.csv", index=False)
    linhas = []
    for nome, g in T.groupby("sist"):
        a = stats(g, nome, fim="2021-12-31"); b = stats(g, nome, ini="2022-01-01")
        linhas.append({"sistema": nome, "trein_n": a["n"], "trein_R": a.get("media_R"), "trein_ac": a.get("acerto"),
                       "val_n": b["n"], "val_R": b.get("media_R"), "val_ac": b.get("acerto"), "val_pf": b.get("pf"),
                       "val_totR": b.get("total_R"), "val_dd": b.get("dd_R"), "dias": b.get("dias")})
    print(pd.DataFrame(linhas).to_string(index=False))
