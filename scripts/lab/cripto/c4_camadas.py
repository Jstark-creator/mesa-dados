"""Cripto v2 (pré-registro estrategias/cripto-v2-preregistro.md, 17/11/2026):
camada M (20/20 long, 20/10 short, stop 2 ATR) e camada L (100/50, stop 3 ATR) em BTC e ETH, custo 1x e 2x."""
import sys; sys.path.insert(0, __file__.rsplit('/', 1)[0])
from base import *
from c1_sistemas import rodar, saida_trail_don

def preparar(s):
    d = ind(carregar(s))
    for n in (50, 100):
        d[f"hi{n}"] = d.high.rolling(n).max().shift(); d[f"lo{n}"] = d.low.rolling(n).min().shift()
    return d

def camada(d, s, nome, mult):
    c = d.close
    if nome == "M":
        L = rodar(d, s, "M long", 1, (c > d.mm200) & (c > d.hi20), 2.0, saida_trail_don(20), CUSTO_SPOT * mult, False)
        S = rodar(d, s, "M short", -1, (c < d.mm200) & (c < d.lo20), 2.0, saida_trail_don(10), CUSTO_FUT * mult, False)
    else:
        L = rodar(d, s, "L long", 1, (c > d.mm200) & (c > d.hi100), 3.0, saida_trail_don(50), CUSTO_SPOT * mult, False)
        S = rodar(d, s, "L short", -1, (c < d.mm200) & (c < d.lo100), 3.0, saida_trail_don(50), CUSTO_FUT * mult, False)
    return pd.concat([L, S])

def dd(t):
    eq = t.sort_values("saida").r.cumsum(); return round((eq - eq.cummax()).min(), 1)

if __name__ == "__main__":
    hoje = pd.Timestamp.now().normalize()
    D = {s: preparar(s) for s in ("BTC", "ETH")}
    for mult in (1, 2):
        T = pd.concat([camada(D[s], s, n, mult) for s in D for n in ("M", "L")])
        T = T[pd.to_datetime(T.saida) < hoje - pd.Timedelta(days=1)]  # exclui operações ainda abertas
        T["ano"] = pd.to_datetime(T.entrada).dt.year
        print(f"\n===== custo {mult}x =====")
        for sist, g in T.groupby("sist"):
            a = stats(g, sist, fim="2021-12-31"); b = stats(g, sist, ini="2022-01-01")
            print(f"{sist:8s} treino n={a['n']:3d} med={a.get('media_R')} | valid n={b['n']:3d} med={b.get('media_R')} ac={b.get('acerto')} tot={b.get('total_R')} dd={b.get('dd_R')} dias={b.get('dias')}")
        v = T[T.entrada >= "2022-01-01"]
        for cam in ("M", "L"):
            print(f"camada {cam} valid: tot={round(v[v.sist.str.startswith(cam)].r.sum(),1)} dd={dd(v[v.sist.str.startswith(cam)])}")
        print(f"M+L valid: tot={round(v.r.sum(),1)} dd={dd(v)}  (soma dos dd isolados = {dd(v[v.sist.str.startswith('M')]) + dd(v[v.sist.str.startswith('L')])})")
        if mult == 2:
            print(v.groupby(["ano", "sist"]).r.sum().round(1).unstack())
            T.to_csv("/tmp/c4_trades.csv", index=False)
