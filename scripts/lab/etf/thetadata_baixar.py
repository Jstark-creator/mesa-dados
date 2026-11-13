"""Baixa cadeias de opções (fechamento, bid/ask reais) da ThetaData pelo Theta Terminal v3 local.

Plano gratuito: dados de fechamento desde 2023-06-01, ~20 requisições/minuto.
Os dados brutos NÃO vão para o repositório (repo público; dados licenciados): ficam em cache do Actions.

Uso: python thetadata_baixar.py --simbolos SPY,QQQ --inicio 2023-06-01 --destino /tmp/td
"""
from __future__ import annotations

import argparse
import io
import time
import urllib.error
import urllib.request
from datetime import date
from pathlib import Path

import pandas as pd

BASE = "http://127.0.0.1:25503/v3"


def esperar_terminal(timeout=240):
    t0 = time.time()
    while time.time() - t0 < timeout:
        try:
            urllib.request.urlopen(f"{BASE}/option/list/expirations?symbol=SPY", timeout=10).read(100)
            return True
        except Exception:
            time.sleep(5)
    return False


def pedir(url, tentativas=6):
    for k in range(tentativas):
        try:
            with urllib.request.urlopen(url, timeout=300) as r:
                return r.read().decode()
        except urllib.error.HTTPError as e:
            corpo = e.read().decode(errors="ignore")[:200]
            if e.code in (429, 503, 504) or "limit" in corpo.lower():
                time.sleep(20 * (k + 1)); continue
            if e.code in (472, 404) or "no data" in corpo.lower():
                return ""
            print(f"HTTP {e.code}: {corpo}"); time.sleep(10)
        except Exception as e:  # rede/timeout
            print(f"erro {type(e).__name__}: {e}"); time.sleep(15)
    return None


def meses(inicio: date, fim: date):
    d = date(inicio.year, inicio.month, 1)
    while d <= fim:
        prox = date(d.year + (d.month == 12), d.month % 12 + 1, 1)
        yield max(d, inicio), min(fim, prox - pd.Timedelta(days=1).to_pytimedelta())
        d = prox


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--simbolos", default="SPY,QQQ")
    ap.add_argument("--inicio", default="2023-06-01")
    ap.add_argument("--destino", default="/tmp/td")
    ap.add_argument("--max_dte", type=int, default=75)
    ap.add_argument("--strike_range", type=int, default=40)
    ap.add_argument("--pausa", type=float, default=3.3)  # ~18 req/min
    a = ap.parse_args()
    if not esperar_terminal():
        raise SystemExit("Theta Terminal não respondeu na porta 25503")
    hoje = date.today()
    for sym in a.simbolos.split(","):
        pasta = Path(a.destino) / sym
        pasta.mkdir(parents=True, exist_ok=True)
        for ini, fim in meses(date.fromisoformat(a.inicio), hoje):
            arq = pasta / f"{ini:%Y-%m}.csv.gz"
            mes_fechado = (fim.year, fim.month) < (hoje.year, hoje.month)
            if arq.exists() and mes_fechado:
                continue  # cache
            url = (f"{BASE}/option/history/eod?symbol={sym}&expiration=*&start_date={ini:%Y%m%d}&end_date={fim:%Y%m%d}"
                   f"&max_dte={a.max_dte}&strike_range={a.strike_range}&format=csv")
            txt = pedir(url)
            time.sleep(a.pausa)
            if txt is None:
                print(f"{sym} {ini:%Y-%m}: falhou"); continue
            if not txt.strip():
                print(f"{sym} {ini:%Y-%m}: vazio"); continue
            df = pd.read_csv(io.StringIO(txt))
            df.to_csv(arq, index=False, compression="gzip")
            print(f"{sym} {ini:%Y-%m}: {len(df)} linhas")


if __name__ == "__main__":
    main()
