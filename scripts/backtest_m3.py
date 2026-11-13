"""Backtest da estratégia M3 (Playbook v1.0) no ativo-objeto, em múltiplos de R.

Simulação (sem olhar o futuro):
- O padrão de 3 candles e os filtros (médias 9/20 e IFR 50) são avaliados no FECHAMENTO de c3.
- Entrada no dia seguinte (c4):
  * se c3 já fechou além da abertura de c1, entra na abertura de c4;
  * senão, ordem de rompimento na abertura de c1, válida só em c4 (se abrir além, entra na abertura).
- Stop: mínima de c2 (compra) / máxima de c2 (venda). Gap além do stop sai na abertura.
- Alvo: Fibonacci 200% sobre os 4 candles (c1..c4), ativo a partir de c5.
- Se stop e alvo forem tocados no mesmo dia, assume o stop (conservador).
- Stop temporal: máximo de N pregões (EUA 35 ≈ opção de 60 dias menos 10 dias; BR 14 ≈ 30 dias menos 10).
- 1 operação por ativo por vez.

Resultado em R = ganho / risco inicial (entrada→stop). Não inclui custos nem efeito das opções
(theta, volatilidade, teto da trava): mede se o SINAL tem vantagem no preço do ativo.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
import m3  # noqa: E402

RAIZ = Path(__file__).resolve().parents[1]


def carregar():
    wl = json.loads((RAIZ / "config" / "watchlist.json").read_text())
    meta = {}
    for tier, ts in wl["eua"].items():
        for t in ts:
            meta[t] = ("eua", tier)
    for tier, ts in wl["br"].items():
        for t in ts:
            meta[t] = ("br", tier)
    dados = {}
    for t in meta:
        f = RAIZ / "data" / "historico" / f"{t}.csv"
        if f.exists():
            df = pd.read_csv(f, parse_dates=["data"], index_col="data")
            df = df[(df["high"] >= df["low"]) & (df["close"] > 0)]
            if len(df) > 100:
                dados[t] = m3.indicadores(df)
    return meta, dados


def simular(t, df, mercado, tier, filtros=True, gestao="fib", max_hold=None):
    """gestao: 'fib' = alvo Fibonacci 200%;
               'curta' = metade sai a 50% do caminho até o alvo e o resto a 80% (proxy da realização em +50% / +90-100%)."""
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    mme, mms, ifr = (df[k].to_numpy() for k in ("mme9", "mms20", "ifr14"))
    datas = df.index
    n = len(df)
    hold = max_hold or (35 if mercado == "eua" else 14)
    trades = []
    i = 22
    while i < n - 2:
        c1, c2, c3 = i - 2, i - 1, i
        for direcao in ("compra", "venda"):
            if direcao == "compra":
                pad = l[c2] < l[c1] and l[c3] > l[c2]
                filt = mme[c3] > mms[c3] and c[c3] > mms[c3] and ifr[c3] > 50
            else:
                pad = h[c2] > h[c1] and h[c3] < h[c2]
                filt = mme[c3] < mms[c3] and c[c3] < mms[c3] and ifr[c3] < 50
            if not pad or (filtros and not filt) or np.isnan(mms[c3]):
                continue
            c4 = c3 + 1
            gat = o[c1]
            s = 1 if direcao == "compra" else -1
            # entrada em c4
            if s * (c[c3] - gat) > 0:
                entrada = o[c4]
            elif s * (o[c4] - gat) >= 0:
                entrada = o[c4]
            elif (s == 1 and h[c4] >= gat) or (s == -1 and l[c4] <= gat):
                entrada = gat
            else:
                continue
            stop = l[c2] if s == 1 else h[c2]
            risco = s * (entrada - stop)
            if risco <= 0 or risco / entrada < 0.002:
                continue
            lo4, hi4 = min(l[c1:c4 + 1]), max(h[c1:c4 + 1])
            amp = hi4 - lo4
            alvo = lo4 + 2 * amp if s == 1 else hi4 - 2 * amp
            if s * (alvo - entrada) <= 0:
                continue
            # dia c4: só stop (o alvo depende do fechamento de c4)
            saida, motivo, j = None, None, c4
            if (s == 1 and l[c4] <= stop) or (s == -1 and h[c4] >= stop):
                saida, motivo = stop, "stop"
            parcial = None  # para gestão curta
            alvo1 = entrada + s * 0.5 * s * (alvo - entrada) if gestao == "curta" else None
            alvo2 = entrada + s * 0.8 * s * (alvo - entrada) if gestao == "curta" else None
            j = c4 + 1
            while saida is None and j < n:
                bate_stop = (s == 1 and l[j] <= stop) or (s == -1 and h[j] >= stop)
                if bate_stop:
                    px = o[j] if s * (o[j] - stop) < 0 else stop
                    saida, motivo = px, "stop"
                    break
                if gestao == "fib":
                    if (s == 1 and h[j] >= alvo) or (s == -1 and l[j] <= alvo):
                        px = o[j] if s * (o[j] - alvo) > 0 else alvo
                        saida, motivo = px, "alvo"
                        break
                else:
                    if parcial is None and ((s == 1 and h[j] >= alvo1) or (s == -1 and l[j] <= alvo1)):
                        parcial = alvo1
                    if parcial is not None and ((s == 1 and h[j] >= alvo2) or (s == -1 and l[j] <= alvo2)):
                        saida, motivo = alvo2, "alvo"
                        break
                if j - c4 >= hold:
                    saida, motivo = c[j], "tempo"
                    break
                j += 1
            if saida is None:
                break
            r_final = s * (saida - entrada) / risco
            if gestao == "curta" and parcial is not None:
                r = 0.5 * s * (parcial - entrada) / risco + 0.5 * r_final
            else:
                r = r_final
            trades.append({"ticker": t, "mercado": mercado, "tier": tier, "direcao": direcao,
                           "entrada_data": str(datas[c4].date()), "saida_data": str(datas[min(j, n - 1)].date()),
                           "dias": int(min(j, n - 1) - c4), "r": float(r), "motivo": motivo,
                           "risco_pct": float(risco / entrada * 100),
                           "alvo_r": float(s * (alvo - entrada) / risco), "ano": datas[c4].year})
            i = j  # uma operação por vez
            break
        i += 1
    return trades


def metricas(tr: pd.DataFrame) -> dict:
    if tr.empty:
        return {"n": 0}
    r = tr["r"]
    g, p = r[r > 0], r[r <= 0]
    eq = r.cumsum()
    dd = (eq - eq.cummax()).min()
    return {"n": int(len(r)), "acerto": float((r > 0).mean()), "ganho_med_r": float(g.mean()) if len(g) else 0.0,
            "perda_med_r": float(p.mean()) if len(p) else 0.0, "expectativa_r": float(r.mean()),
            "profit_factor": float(g.sum() / -p.sum()) if p.sum() < 0 else float("inf"),
            "total_r": float(r.sum()), "max_dd_r": float(dd), "dias_med": float(tr["dias"].mean()),
            "alvo_r_med": float(tr["alvo_r"].median()),
            "saidas": tr["motivo"].value_counts(normalize=True).round(3).to_dict()}


def rodar():
    meta, dados = carregar()
    cenarios = {
        "M3 v1.0 · alvo Fibonacci": dict(filtros=True, gestao="fib"),
        "M3 v1.0 · realização curta": dict(filtros=True, gestao="curta"),
        "Sem filtros · alvo Fibonacci": dict(filtros=False, gestao="fib"),
    }
    out = {}
    base = None
    for nome, kw in cenarios.items():
        tr = []
        for t, df in dados.items():
            tr += simular(t, df, *meta[t], **kw)
        tr = pd.DataFrame(tr)
        out[nome] = {"geral": metricas(tr),
                     "desde_2021": metricas(tr[tr["ano"] >= 2021])}
        if base is None:
            base = tr
    q = {}
    for col in ("mercado", "tier", "direcao"):
        q[col] = {k: metricas(g) for k, g in base.groupby(col)}
    q["ano"] = {int(k): metricas(g) for k, g in base.groupby("ano")}
    q["ticker"] = {k: metricas(g) for k, g in base.groupby("ticker")}
    return out, q, base, len(dados)


if __name__ == "__main__":
    out, q, base, nat = rodar()
    dest = RAIZ / "data" / "backtest"
    dest.mkdir(parents=True, exist_ok=True)
    (dest / "m3_v1_resumo.json").write_text(json.dumps({"ativos": nat, "cenarios": out, "quebras": q}, ensure_ascii=False, indent=1, default=float))
    base.to_csv(dest / "m3_v1_trades.csv", index=False)
    for k, v in out.items():
        print(k, json.dumps(v["geral"], default=float))
