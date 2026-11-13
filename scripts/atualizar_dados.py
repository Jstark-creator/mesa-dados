"""Coleta diária: baixa candles diários da watchlist via yfinance, calcula indicadores,
detecta sinais M3 e grava tudo em data/.

Saídas:
- data/precos/<TICKER>.csv        últimos ~2 anos de candles diários com indicadores
- data/resumo.json                foto de cada ativo (preço, variação, IFR, tendência)
- data/mercado.json               índices, moedas, juros e commodities monitorados
- data/sinais/hoje.json           sinais M3 do último pregão
- data/sinais/historico.csv       todos os sinais já detectados (acumulado)
- data/status.json                quando rodou, quantos ativos ok, falhas

Uso: python scripts/atualizar_dados.py [--periodo 2y]
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import yfinance as yf

sys.path.insert(0, str(Path(__file__).parent))
import m3  # noqa: E402

RAIZ = Path(__file__).resolve().parents[1]
DADOS = RAIZ / "data"


def carregar_watchlist() -> dict:
    return json.loads((RAIZ / "config" / "watchlist.json").read_text(encoding="utf-8"))


def lista_ativos(wl: dict) -> list[dict]:
    ativos = []
    for tier, tickers in wl["eua"].items():
        for t in tickers:
            ativos.append({"ticker": t, "yf": t, "mercado": "eua", "tier": tier})
    for tier, tickers in wl["br"].items():
        for t in tickers:
            ativos.append({"ticker": t, "yf": f"{t}.SA", "mercado": "br", "tier": tier})
    for t in wl.get("cripto", []):
        ativos.append({"ticker": t.replace("-USD", ""), "yf": t, "mercado": "cripto", "tier": "tier1"})
    return ativos


def baixar(simbolos: list[str], periodo: str) -> dict[str, pd.DataFrame]:
    """Baixa em lotes e devolve {simbolo: DataFrame OHLCV com colunas minúsculas}."""
    resultado: dict[str, pd.DataFrame] = {}
    lote = 25
    for i in range(0, len(simbolos), lote):
        parte = simbolos[i:i + lote]
        for tentativa in range(3):
            try:
                bruto = yf.download(parte, period=periodo, interval="1d", group_by="ticker",
                                    auto_adjust=True, progress=False, threads=True)
                break
            except Exception as e:  # rede instável: tenta de novo
                print(f"lote {i}: erro {e}, tentativa {tentativa + 1}")
                time.sleep(5)
        else:
            continue
        for s in parte:
            try:
                if isinstance(bruto.columns, pd.MultiIndex):
                    if s not in bruto.columns.get_level_values(0):
                        raise KeyError(s)
                    df = bruto[s]
                else:
                    df = bruto
                df = df.rename(columns=str.lower)[["open", "high", "low", "close", "volume"]].dropna()
                if len(df):
                    df.index = pd.to_datetime(df.index).tz_localize(None)
                    resultado[s] = df
            except Exception as e:
                print(f"{s}: sem dados ({e})")
        time.sleep(1)
    return resultado


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--periodo", default="2y")
    args = ap.parse_args()

    wl = carregar_watchlist()
    ativos = lista_ativos(wl)
    (DADOS / "precos").mkdir(parents=True, exist_ok=True)
    (DADOS / "sinais").mkdir(parents=True, exist_ok=True)

    dados = baixar([a["yf"] for a in ativos], args.periodo)

    resumos, sinais, falhas = [], [], []
    for a in ativos:
        df = dados.get(a["yf"])
        if df is None or len(df) < 30:
            falhas.append(a["ticker"])
            continue
        df = m3.indicadores(df)
        df.round(4).to_csv(DADOS / "precos" / f"{a['ticker']}.csv", index_label="data")
        r = m3.resumo(a["ticker"], df)
        r.update({"mercado": a["mercado"], "tier": a["tier"]})
        resumos.append(r)
        if a["mercado"] in ("eua", "br"):
            for s in m3.detectar(a["ticker"], df):
                d = m3.sinal_dict(s)
                d.update({"mercado": a["mercado"], "tier": a["tier"]})
                sinais.append(d)

    # mercado (índices, moedas, juros, commodities)
    mon = wl.get("monitorados", {})
    dm = baixar(list(mon.values()), "1mo")
    mercado = []
    for nome, sim in mon.items():
        df = dm.get(sim)
        if df is None or len(df) < 2:
            mercado.append({"nome": nome, "simbolo": sim, "ultimo": None, "var_dia_pct": None})
            continue
        u, ant = df.iloc[-1], df.iloc[-2]
        mercado.append({"nome": nome, "simbolo": sim, "data": str(df.index[-1].date()),
                        "ultimo": round(float(u["close"]), 4),
                        "var_dia_pct": round((float(u["close"]) / float(ant["close"]) - 1) * 100, 2)})

    agora = datetime.now(timezone.utc).isoformat(timespec="seconds")
    ordem = {"acionado": 0, "armado": 1}
    tiers = {"tier1": 0, "tier2": 1, "tier3": 2}
    sinais.sort(key=lambda s: (ordem.get(s["estado"], 9), tiers.get(s["tier"], 9), -s["rr"]))

    (DADOS / "resumo.json").write_text(json.dumps({"gerado_em": agora, "ativos": resumos}, ensure_ascii=False, indent=1), encoding="utf-8")
    (DADOS / "mercado.json").write_text(json.dumps({"gerado_em": agora, "itens": mercado}, ensure_ascii=False, indent=1), encoding="utf-8")
    (DADOS / "sinais" / "hoje.json").write_text(json.dumps({
        "gerado_em": agora, "playbook": "M3 v1.0",
        "obs": "armado = padrão de 3 candles fechou, entrada no rompimento da abertura de c1 no próximo pregão; acionado = rompimento já ocorreu no último candle",
        "sinais": sinais}, ensure_ascii=False, indent=1), encoding="utf-8")

    hist = DADOS / "sinais" / "historico.csv"
    if sinais:
        novo = pd.DataFrame(sinais)
        if hist.exists():
            antigo = pd.read_csv(hist)
            novo = pd.concat([antigo, novo]).drop_duplicates(subset=["ticker", "direcao", "estado", "data"], keep="last")
        novo.to_csv(hist, index=False)

    (DADOS / "status.json").write_text(json.dumps({
        "gerado_em": agora, "ativos_ok": len(resumos), "ativos_total": len(ativos),
        "falhas": falhas, "sinais": len(sinais)}, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"ok: {len(resumos)}/{len(ativos)} ativos, {len(sinais)} sinais, falhas: {falhas}")


if __name__ == "__main__":
    main()
