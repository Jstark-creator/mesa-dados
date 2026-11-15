"""M7 "Preço da volatilidade" — teste direto com cotações reais (pré-registro: estrategias/m7-preregistro.md).
Uso: python m7.py --dados /tmp/td --spot /tmp/td/spot.csv
"""
from __future__ import annotations
import argparse, math, sys
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "etf"))
from matriz_real import bs, iv_delta, carregar_cadeia, preco_exec, COMISSAO  # noqa: E402

RAIZ = Path(__file__).resolve().parents[3]
ETFS = ["SPY", "QQQ", "IWM", "DIA", "XLK", "XLF", "XLE", "SMH", "GLD", "TLT", "EEM", "XBI"]
GRUPO = {"SPY", "QQQ", "DIA", "IWM", "XLK", "SMH"}
Q = dict(SPY=.013, QQQ=.006, IWM=.012, DIA=.017, XLK=.007, XLF=.015, XLE=.033, SMH=.005, GLD=0, TLT=.038, EEM=.025, XBI=0)
EXEC = {"natural": 1.0, "meio_50": 0.5, "meio": 0.0}
TREINO_FIM = pd.Timestamp("2025-03-31")


def escolher_exp(ch, dia):
    exps = sorted(ch.exp.unique()); alvo = dia + pd.Timedelta(days=45)
    ok = [e for e in exps if 30 <= (e - dia).days <= 60]
    return min(ok, key=lambda e: abs((e - alvo).days)) if ok else None


def iv45(ch, S, dia, r, q):
    exp = escolher_exp(ch, dia)
    if exp is None:
        return np.nan
    T = (exp - dia).days / 365; c = ch[ch.exp == exp]
    if c.empty:
        return np.nan
    k = c.strike.iloc[(c.strike - S).abs().argsort().iloc[0]]
    ivs = []
    for tipo in ("c", "p"):
        x = c[(c.strike == k) & (c.tipo == tipo)]
        if len(x):
            v, _ = iv_delta(S, k, T, r, q, float((x.bid.iloc[0] + x.ask.iloc[0]) / 2), tipo)
            if v:
                ivs.append(v)
    return float(np.mean(ivs)) if ivs else np.nan


def strike_delta(ch, exp, S, T, r, q, tipo, alvo):
    sub = ch[(ch.exp == exp) & (ch.tipo == tipo)]; melhor = None
    for row in sub.itertuples():
        _, dl = iv_delta(S, row.strike, T, r, q, (row.bid + row.ask) / 2, tipo)
        if dl is None:
            continue
        e = abs(dl - alvo)
        if melhor is None or e < melhor[0]:
            melhor = (e, row.strike)
    return None if melhor is None or melhor[0] > 0.08 else melhor[1]


def montar(estr, ch, S, dia, r, q, tendencia_alta):
    exp = escolher_exp(ch, dia)
    if exp is None:
        return None
    T = (exp - dia).days / 365; c = ch[ch.exp == exp]
    if estr == "straddle":
        k = c.strike.iloc[(c.strike - S).abs().argsort().iloc[0]]
        pernas = [(1, "c", k), (1, "p", k)]
    elif estr == "condor":
        ks = [strike_delta(ch, exp, S, T, r, q, "p", .20), strike_delta(ch, exp, S, T, r, q, "p", .10),
              strike_delta(ch, exp, S, T, r, q, "c", .20), strike_delta(ch, exp, S, T, r, q, "c", .10)]
        if None in ks or ks[1] >= ks[0] or ks[3] <= ks[2]:
            return None
        pernas = [(-1, "p", ks[0]), (1, "p", ks[1]), (-1, "c", ks[2]), (1, "c", ks[3])]
    else:  # credito a favor da tendência
        tipo = "p" if tendencia_alta else "c"
        kv, kc = strike_delta(ch, exp, S, T, r, q, tipo, .30), strike_delta(ch, exp, S, T, r, q, tipo, .15)
        if None in (kv, kc) or kv == kc:
            return None
        pernas = [(-1, tipo, kv), (1, tipo, kc)]
    return exp, pernas


def cotar(ch, exp, pernas):
    out = []
    for q_, t, k in pernas:
        x = ch[(ch.exp == exp) & (ch.tipo == t) & (ch.strike == k)]
        if x.empty:
            return None
        out.append((q_, float(x.bid.iloc[0]), float(x.ask.iloc[0])))
    return out


def largura(pernas):
    ps = [k for _, t, k in pernas if t == "p"]; cs = [k for _, t, k in pernas if t == "c"]
    return max(max(ps) - min(ps) if len(ps) == 2 else 0, max(cs) - min(cs) if len(cs) == 2 else 0)


def simular_etf(sym, grupos, dias, sinal, tend, r_ser, spot, estr, f, alvo_deb=None):
    res = []; livre = None
    for k in range(1, len(dias)):
        dia, ontem = dias[k], dias[k - 1]
        if livre is not None and dia <= livre:
            continue
        if not sinal.get(ontem, False):
            continue
        ch = grupos.get_group(dia); S = float(spot[dia]); r = float(r_ser.get(dia, .04))
        m = montar(estr, ch, S, dia, r, Q[sym], bool(tend.get(ontem, True)))
        if m is None:
            continue
        exp, pernas = m; q0 = cotar(ch, exp, pernas)
        if q0 is None:
            continue
        custo = sum(q * preco_exec(b, a, q, f) for q, b, a in q0) + COMISSAO * len(q0)
        debito = estr == "straddle"
        if debito:
            if custo <= 0:
                continue
            risco = custo
        else:
            cred = -custo; risco = largura(pernas) - cred
            if cred <= 0 or risco <= 0:
                continue
        resultado = None; saida = None
        for j in range(k + 1, len(dias)):
            dj = dias[j]
            if dj >= exp:
                break
            qj = cotar(grupos.get_group(dj), exp, pernas)
            if qj is None:
                continue
            fechar = sum(q * preco_exec(b, a, -q, f) for q, b, a in qj) - COMISSAO * len(qj)
            fim = (exp - dj).days <= 21
            if debito:
                pnl = fechar - custo
                if pnl >= alvo_deb * custo or pnl <= -0.40 * custo or fim:
                    resultado, saida = pnl, dj; break
            else:
                pnl = cred + fechar
                if pnl >= 0.5 * cred or pnl <= -0.25 * risco or fim:
                    resultado, saida = pnl, dj; break
        if resultado is None:
            continue
        res.append(dict(etf=sym, entrada=dia, saida=saida, r=resultado / risco, risco_usd=risco * 100))
        livre = saida
    return res


def limitar_grupo(T):
    if T.empty:
        return T
    T = T.sort_values(["entrada", "etf"]); abertas = []; ok = []
    for _, t in T.iterrows():
        abertas = [s for s in abertas if s >= t.entrada]
        if t.etf in GRUPO:
            if len(abertas) >= 2:
                ok.append(False); continue
            abertas.append(t.saida)
        ok.append(True)
    return T[ok]


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--dados", default="/tmp/td"); ap.add_argument("--spot", default="/tmp/td/spot.csv")
    a = ap.parse_args()
    spot_all = pd.read_csv(a.spot, index_col=0, parse_dates=True)
    irx = pd.read_csv(RAIZ / "data" / "etf" / "IRX.csv", index_col="data", parse_dates=True).close / 100
    out = RAIZ / "data" / "lab" / "m7"; out.mkdir(parents=True, exist_ok=True)
    medidas = []; ops = []
    completos = [s_ for s_ in ETFS if len(list((Path(a.dados) / s_).glob("*.csv.gz"))) >= 41]
    print(f"ETFs com cadeia completa (>= 41 meses): {completos}")
    for sym in completos:
        try:
            cad = carregar_cadeia(Path(a.dados), sym)
        except SystemExit:
            print(f"{sym}: sem cadeia"); continue
        if sym not in spot_all:
            continue
        spot = spot_all[sym].dropna(); grupos = cad.groupby("dia")
        dias = [d for d in sorted(grupos.groups) if d in spot.index]
        hv = (np.log(spot).diff().rolling(20).std() * math.sqrt(252))
        r_ser = irx.reindex(spot.index).ffill().fillna(.04)
        iv = pd.Series({d: iv45(grupos.get_group(d), float(spot[d]), d, float(r_ser[d]), Q[sym]) for d in dias})
        pct = iv.expanding(min_periods=127).apply(lambda x: (x[:-1][-252:] < x[-1]).mean(), raw=True)
        razao = iv / hv.reindex(iv.index)
        adj = pd.read_csv(RAIZ / "data" / "historico" / f"{sym}.csv", index_col="data", parse_dates=True).close
        tend = (adj > adj.rolling(200).mean()).reindex(iv.index).fillna(True)
        barata = ((razao < 0.9) & (pct <= 1 / 3)).fillna(False)
        cara = ((razao > 1.3) & (pct >= 2 / 3)).fillna(False)
        medidas.append(pd.DataFrame(dict(etf=sym, iv45=iv, hv20=hv.reindex(iv.index), razao=razao, pct=pct, barata=barata, cara=cara)))
        for ex, f in EXEC.items():
            for perfil, alvo in (("P1", .5), ("P2", 1.0)):
                for o in simular_etf(sym, grupos, dias, barata, tend, r_ser, spot, "straddle", f, alvo):
                    ops.append(dict(o, estrutura=f"1 straddle {perfil}", execucao=ex))
            for estr, nome in (("condor", "2a iron condor"), ("credito", "2b crédito a favor")):
                for o in simular_etf(sym, grupos, dias, cara, tend, r_ser, spot, estr, f):
                    ops.append(dict(o, estrutura=nome, execucao=ex))
        print(f"{sym}: dias {len(dias)}, sinais barata {int(barata.sum())}, cara {int(cara.sum())}")
    M = pd.concat(medidas) if medidas else pd.DataFrame()
    O = pd.DataFrame(ops)
    if O.empty:
        (out / "resultado.md").write_text("# M7\n\nSem operações.\n"); return
    O = pd.concat([limitar_grupo(g) for _, g in O.groupby(["estrutura", "execucao"])])
    O["periodo"] = np.where(O.entrada <= TREINO_FIM, "treino", "validacao")
    O.to_csv(out / "operacoes.csv", index=False)
    resumo = O.groupby(["estrutura", "execucao", "periodo"]).r.agg(n="count", media="mean", acerto=lambda x: (x > 0).mean(), total="sum").round(3).reset_index()
    resumo.to_csv(out / "resumo.csv", index=False)
    # decisão pré-registrada
    def met(est, ex, per):
        x = O[(O.estrutura == est) & (O.execucao == ex) & (O.periodo == per)].r
        return len(x), (x.mean() if len(x) else np.nan)
    dec = []
    p1, p2 = met("1 straddle P1", "meio_50", "treino")[1], met("1 straddle P2", "meio_50", "treino")[1]
    perfil = "1 straddle P1" if (np.nan_to_num(p1, nan=-9) >= np.nan_to_num(p2, nan=-9)) else "1 straddle P2"
    for est in (perfil, "2a iron condor", "2b crédito a favor"):
        ntr, mtr = met(est, "meio_50", "treino"); nva, mva = met(est, "meio_50", "validacao"); _, mnat = met(est, "natural", "validacao")
        ok = (ntr + nva >= 60) and (nva >= 25) and (mtr > 0) and (mva >= 0.15) and (mnat >= 0)
        dec.append(dict(estrutura=est, n_treino=ntr, media_treino_meio50=round(mtr, 3) if ntr else None, n_val=nva,
                        media_val_meio50=round(mva, 3) if nva else None, media_val_natural=round(mnat, 3) if nva else None, aprovado=bool(ok)))
    D = pd.DataFrame(dec)
    sinais = M.groupby("etf")[["barata", "cara"]].sum() if not M.empty else pd.DataFrame()
    with open(out / "resultado.md", "w") as fh:
        fh.write(f"# M7 — Preço da volatilidade (gerado automaticamente; cotações reais ThetaData)\n\nETFs incluídos (cadeia completa): {completos}\n\n## Decisão pré-registrada\n\n")
        fh.write(D.to_markdown(index=False) + f"\n\nPerfil do Módulo 1 escolhido no treino: {perfil}\n\n## Resumo por estrutura, execução e período\n\n")
        fh.write(resumo.to_markdown(index=False) + "\n\n## Dias de sinal por ETF\n\n" + sinais.to_markdown())
        if not M.empty:
            fh.write("\n\n## Razão IV/HV (mediana por ETF)\n\n" + M.groupby("etf").razao.describe()[["count", "25%", "50%", "75%"]].round(2).to_markdown())
    print(open(out / "resultado.md").read())


if __name__ == "__main__":
    main()
