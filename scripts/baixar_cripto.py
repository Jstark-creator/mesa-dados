"""Histórico cripto para o laboratório do J.Satoshi.

Saídas em data/cripto/:
  <SYM>.csv          OHLCV diário (yfinance, período máximo)
  fear_greed.csv     índice Fear & Greed (alternative.me, desde 2018)
  funding_<SYM>.csv  histórico de funding rate de perpétuos (tenta OKX, Bybit, Binance; o que responder)
"""
from __future__ import annotations

import json
import sys
import time
import urllib.request
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from atualizar_dados import RAIZ, baixar  # noqa: E402

UNIVERSO = {
    "BTC": "BTC-USD", "ETH": "ETH-USD", "SOL": "SOL-USD", "BNB": "BNB-USD", "XRP": "XRP-USD",
    "ADA": "ADA-USD", "DOGE": "DOGE-USD", "AVAX": "AVAX-USD", "LINK": "LINK-USD", "DOT": "DOT-USD",
    "LTC": "LTC-USD", "TRX": "TRX-USD", "NEAR": "NEAR-USD", "ATOM": "ATOM-USD", "UNI": "UNI7083-USD",
    "SUI": "SUI20947-USD", "TON": "TON11419-USD", "APT": "APT21794-USD", "BCH": "BCH-USD", "XLM": "XLM-USD",
}
DEST = RAIZ / "data" / "cripto"


def get_json(url: str):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())


def fear_greed() -> None:
    try:
        d = get_json("https://api.alternative.me/fng/?limit=0&format=json")["data"]
        df = pd.DataFrame(d)
        df["data"] = pd.to_datetime(df["timestamp"].astype(int), unit="s").dt.date
        df = df[["data", "value", "value_classification"]].rename(columns={"value": "fg", "value_classification": "classe"})
        df.sort_values("data").to_csv(DEST / "fear_greed.csv", index=False)
        print(f"fear&greed: {len(df)} dias")
    except Exception as e:
        print(f"fear&greed falhou: {e}")


def funding_okx(sym: str) -> pd.DataFrame | None:
    linhas, depois = [], ""
    for _ in range(40):  # ~100 por página, 8h cada
        url = f"https://www.okx.com/api/v5/public/funding-rate-history?instId={sym}-USDT-SWAP&limit=100" + (f"&after={depois}" if depois else "")
        d = get_json(url).get("data", [])
        if not d:
            break
        linhas += d
        depois = d[-1]["fundingTime"]
        time.sleep(0.2)
    if not linhas:
        return None
    df = pd.DataFrame(linhas)
    df["ts"] = pd.to_datetime(df["fundingTime"].astype("int64"), unit="ms")
    df["rate"] = df["realizedRate"].replace("", None).fillna(df["fundingRate"]).astype(float)
    return df[["ts", "rate"]]


def funding_bybit(sym: str) -> pd.DataFrame | None:
    linhas, fim = [], None
    for _ in range(30):
        url = f"https://api.bybit.com/v5/market/funding/history?category=linear&symbol={sym}USDT&limit=200" + (f"&endTime={fim}" if fim else "")
        d = get_json(url).get("result", {}).get("list", [])
        if not d:
            break
        linhas += d
        fim = int(d[-1]["fundingRateTimestamp"]) - 1
        time.sleep(0.2)
    if not linhas:
        return None
    df = pd.DataFrame(linhas)
    df["ts"] = pd.to_datetime(df["fundingRateTimestamp"].astype("int64"), unit="ms")
    df["rate"] = df["fundingRate"].astype(float)
    return df[["ts", "rate"]]


def funding_binance(sym: str) -> pd.DataFrame | None:
    linhas, ini = [], 1567900800000
    for _ in range(20):
        d = get_json(f"https://fapi.binance.com/fapi/v1/fundingRate?symbol={sym}USDT&limit=1000&startTime={ini}")
        if not d:
            break
        linhas += d
        ini = int(d[-1]["fundingTime"]) + 1
        if len(d) < 1000:
            break
        time.sleep(0.2)
    if not linhas:
        return None
    df = pd.DataFrame(linhas)
    df["ts"] = pd.to_datetime(df["fundingTime"].astype("int64"), unit="ms")
    df["rate"] = df["fundingRate"].astype(float)
    return df[["ts", "rate"]]


def funding(sym: str) -> None:
    for nome, f in (("binance", funding_binance), ("bybit", funding_bybit), ("okx", funding_okx)):
        try:
            df = f(sym)
            if df is not None and len(df):
                df = df.drop_duplicates("ts").sort_values("ts")
                df["fonte"] = nome
                df.to_csv(DEST / f"funding_{sym}.csv", index=False)
                print(f"funding {sym}: {len(df)} registros via {nome} desde {df.ts.min()}")
                return
        except Exception as e:
            print(f"funding {sym} {nome}: {e}")
    print(f"funding {sym}: nenhuma fonte respondeu")


def main() -> None:
    DEST.mkdir(parents=True, exist_ok=True)
    dados = baixar(list(UNIVERSO.values()), "max")
    for sym, yfs in UNIVERSO.items():
        df = dados.get(yfs)
        if df is None or df.empty:
            print(f"{sym}: sem dados")
            continue
        df.round(8).to_csv(DEST / f"{sym}.csv", index_label="data")
        print(f"{sym}: {len(df)} dias desde {df.index.min().date()}")
    fear_greed()
    for sym in ("BTC", "ETH", "SOL"):
        funding(sym)


if __name__ == "__main__":
    main()
