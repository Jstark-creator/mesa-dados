"""Sinais diários das estratégias cripto do J.Satoshi (rodar após 00:00 UTC, candle diário fechado).

E1 "Cripto Tendência" (BTC, ETH): long spot/futuros e short futuros, seguidor de tendência.
E2 "Cripto Rompimento Alts" (Top 20): long spot, máx. 3 posições, só com BTC acima da MM200.
Acúmulo BTC: multiplicador do aporte pelo múltiplo de Mayer.

Saída: data/cripto/sinais.json
"""
from __future__ import annotations

import json
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from atualizar_dados import RAIZ, baixar  # noqa: E402

E1 = {"BTC": "BTC-USD", "ETH": "ETH-USD"}
ALTS = {"SOL": "SOL-USD", "BNB": "BNB-USD", "XRP": "XRP-USD", "ADA": "ADA-USD", "DOGE": "DOGE-USD",
        "AVAX": "AVAX-USD", "LINK": "LINK-USD", "DOT": "DOT-USD", "LTC": "LTC-USD", "TRX": "TRX-USD",
        "NEAR": "NEAR-USD", "ATOM": "ATOM-USD", "UNI": "UNI7083-USD", "SUI": "SUI20947-USD",
        "BCH": "BCH-USD", "XLM": "XLM-USD"}
RISCO = {"cheio": 400.0, "meio": 200.0}
ALAV_MAX = 3
MAX_ALTS = 3
K_STOP = 2.0
DEST = RAIZ / "data" / "cripto"


def preparar(df: pd.DataFrame) -> pd.DataFrame:
    d = df.copy()
    hoje = datetime.now(timezone.utc).date()
    d = d[d.index.date < hoje]  # só candles fechados (UTC)
    c = d.close
    d["mm200"] = c.rolling(200).mean()
    pc = c.shift()
    tr = pd.concat([d.high - d.low, (d.high - pc).abs(), (d.low - pc).abs()], axis=1).max(axis=1)
    d["atr"] = tr.ewm(alpha=1 / 14, adjust=False).mean()
    for n in (10, 20):
        d[f"hi{n}"] = d.high.rolling(n).max().shift()
        d[f"lo{n}"] = d.low.rolling(n).min().shift()
    d["mom28"] = c / c.shift(28) - 1
    return d


def estado(d: pd.DataFrame, lado: int, sinal: pd.Series, n_saida: int, regime_extra: pd.Series | None = None):
    """Percorre o histórico com as regras e devolve a posição do sistema no último candle fechado."""
    o, h, l, c = d.open.values, d.high.values, d.low.values, d.close.values
    s = sinal.fillna(False).values
    if regime_extra is not None:
        s = s & regime_extra.reindex(d.index).fillna(False).values
    sai = (d[f"lo{n_saida}"] if lado == 1 else d[f"hi{n_saida}"]).values
    atr = d.atr.values
    n = len(d)
    pos = None
    ultimo = None
    i = 0
    while i < n:
        if pos is None:
            if s[i] and i == n - 1:
                return {"acao": "ENTRAR", "sinal_em": str(d.index[i].date()), "fechamento": float(c[i]),
                        "stop": float(c[i] - lado * K_STOP * atr[i]), "nivel_saida": float(sai[i]) if np.isfinite(sai[i]) else None}, ultimo
            if s[i]:
                pos = {"i": i + 1, "entrada": float(o[i + 1]), "stop": float(c[i] - lado * K_STOP * atr[i])}
            i += 1
            continue
        j = i
        bateu = (l[j] <= pos["stop"]) if lado == 1 else (h[j] >= pos["stop"])
        fecha_fora = (c[j] < sai[j]) if lado == 1 else (c[j] > sai[j])
        if bateu:
            ultimo = {"saida": str(d.index[j].date()), "motivo": "stop", "entrada": pos["entrada"], "preco_saida": pos["stop"]}
            pos = None
        elif fecha_fora:
            if j == n - 1:
                return {"acao": "SAIR", "motivo": "fechou além do canal", "entrada_data": str(d.index[pos["i"]].date()),
                        "entrada": pos["entrada"], "stop": pos["stop"], "fechamento": float(c[j]),
                        "nivel_saida": float(sai[j])}, ultimo
            ultimo = {"saida": str(d.index[j + 1].date()), "motivo": "canal", "entrada": pos["entrada"], "preco_saida": float(o[j + 1])}
            pos = None
        i += 1
    if pos is not None:
        ent, st = pos["entrada"], pos["stop"]
        return {"acao": "MANTER", "entrada_data": str(d.index[pos["i"]].date()), "entrada": ent, "stop": st,
                "fechamento": float(c[-1]), "nivel_saida": float(sai[-1]),
                "resultado_R": round((c[-1] - ent) * lado / abs(ent - st), 2)}, ultimo
    return {"acao": "FORA"}, ultimo


def trades_sistema(d, sinal, n_saida=20, regime_extra=None):
    """Lista de operações do sistema (sem limite de vagas) para montar a carteira limitada da E2."""
    o, l, c = d.open.values, d.low.values, d.close.values
    s = sinal.fillna(False).values
    if regime_extra is not None:
        s = s & regime_extra.reindex(d.index).fillna(False).values
    sai = d[f"lo{n_saida}"].values
    atr = d.atr.values
    m28 = d.mom28.values
    out, i, n = [], 0, len(d)
    while i < n - 1:
        if not s[i]:
            i += 1
            continue
        e = i + 1
        stop = c[i] - K_STOP * atr[i]
        if o[e] - stop <= o[e] * 0.003:
            i += 1
            continue
        js = next((j for j in range(e, n) if l[j] <= stop or c[j] < sai[j]), None)
        out.append({"entrada": d.index[e], "saida": None if js is None else d.index[js], "m28": float(m28[i])})
        if js is None:
            break
        i = js + 1
    return out


def dimensionar(preco: float, stop: float, futuro: bool) -> dict:
    dist = abs(preco - stop)
    out = {"distancia_stop_pct": round(dist / preco * 100, 2)}
    for k, r in RISCO.items():
        q = r / dist
        nocional = q * preco
        out[k] = {"quantidade": round(q, 6), "nocional_usd": round(nocional, 2)}
        if futuro:
            out[k]["margem_3x_usd"] = round(nocional / ALAV_MAX, 2)
    return out


def get_json(url: str):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode())


def funding_atual(sym: str):
    try:
        d = get_json(f"https://www.okx.com/api/v5/public/funding-rate?instId={sym}-USDT-SWAP")["data"][0]
        return round(float(d["fundingRate"]) * 100, 4)
    except Exception:
        return None


def main() -> None:
    DEST.mkdir(parents=True, exist_ok=True)
    dados = baixar(list(E1.values()) + list(ALTS.values()), "3y")
    D = {s: preparar(dados[y]) for s, y in {**E1, **ALTS}.items() if y in dados}
    btc = D["BTC"]
    btc_alta = btc.close > btc.mm200
    saida = {"gerado_em": datetime.now(timezone.utc).isoformat(timespec="minutes"),
             "candle": str(btc.index[-1].date()), "regras": "playbooks/cripto.md v1",
             "e1": [], "e2": {"regime_btc": "ligado" if bool(btc_alta.iloc[-1]) else "desligado (BTC abaixo da MM200)", "ativos": []}}

    for s in E1:
        d = D[s]
        c = d.close
        for lado, nome, sig, nsai in ((1, "long", (c > d.mm200) & (c > d.hi20), 20), (-1, "short", (c < d.mm200) & (c < d.lo20), 10)):
            st, ult = estado(d, lado, sig, nsai)
            item = {"ativo": s, "lado": nome, **st, "ultima_saida": ult,
                    "preco": round(float(c.iloc[-1]), 2), "mm200": round(float(d.mm200.iloc[-1]), 2)}
            if st["acao"] == "ENTRAR":
                item["veiculo"] = "spot ou perpétuo OKX (até 3x)" if lado == 1 else "perpétuo OKX (até 3x)"
                item["tamanho"] = dimensionar(st["fechamento"], st["stop"], True)
            if lado == 1 or st["acao"] != "FORA":
                item["funding_pct_8h"] = funding_atual(s)
            saida["e1"].append(item)

    candidatos = []
    for s in ALTS:
        d = D.get(s)
        if d is None or len(d) < 260:
            continue
        c = d.close
        st, ult = estado(d, 1, (c > d.mm200) & (c > d.hi20), 20, regime_extra=btc_alta)
        item = {"ativo": s, **st, "preco": float(c.iloc[-1]), "mom28_pct": round(float(d.mom28.iloc[-1]) * 100, 1),
                "acima_mm200": bool(c.iloc[-1] > d.mm200.iloc[-1])}
        if st["acao"] == "ENTRAR":
            item["tamanho"] = dimensionar(st["fechamento"], st["stop"], False)
            candidatos.append(item)
        elif st["acao"] != "FORA":
            saida["e2"]["ativos"].append(item)
    # carteira do sistema com limite de 3 vagas, igual ao laboratório (prioridade por alta em 28 dias)
    todos = []
    for s_ in ALTS:
        d = D.get(s_)
        if d is None or len(d) < 260:
            continue
        c = d.close
        todos += [{**t, "sym": s_} for t in trades_sistema(d, (c > d.mm200) & (c > d.hi20), 20, btc_alta)]
    todos.sort(key=lambda t: (t["entrada"], -t["m28"]))
    cart = []
    for t in todos:
        cart = [x for x in cart if x["saida"] is None or x["saida"] >= t["entrada"]]
        if len(cart) < MAX_ALTS:
            cart.append(t)
    abertas = sum(1 for x in cart if x["saida"] is None)
    saida["e2"]["carteira_sistema"] = [x["sym"] for x in cart if x["saida"] is None]
    vagas = max(0, MAX_ALTS - abertas)
    candidatos.sort(key=lambda x: -x["mom28_pct"])
    for k, x in enumerate(candidatos):
        x["prioridade"] = k + 1
        x["dentro_do_limite"] = k < vagas
        saida["e2"]["ativos"].append(x)
    saida["e2"]["nota"] = (f"Carteira do sistema: {abertas}/{MAX_ALTS} vagas ocupadas. As vagas REAIS vêm do Journal: "
                           "o agente usa as posições reais; dentro_do_limite considera só a carteira do sistema.")

    c = btc.close
    mayer = float(c.iloc[-1] / btc.mm200.iloc[-1])
    mult = 3 if mayer < 0.8 else 2 if mayer < 1.0 else 1 if mayer < 1.5 else 0.5 if mayer < 2.4 else 0
    fg = None
    try:
        fg = int(get_json("https://api.alternative.me/fng/?limit=1")["data"][0]["value"])
    except Exception:
        pass
    saida["acumulo_btc"] = {"mayer": round(mayer, 2), "multiplicador_aporte": mult, "fear_greed": fg,
                            "regra": "<0,8 → 3x · 0,8–1,0 → 2x · 1,0–1,5 → 1x · 1,5–2,4 → 0,5x · >2,4 → pausa (sobra vai pra reserva)"}
    (DEST / "sinais.json").write_text(json.dumps(saida, ensure_ascii=False, indent=1, default=float))
    print(json.dumps(saida, ensure_ascii=False, indent=1, default=float)[:3000])


if __name__ == "__main__":
    main()
