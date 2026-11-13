"""Fotografia rápida de preços (intradiário, com atraso de ~15 min do Yahoo) da watchlist,
cripto e indicadores de mercado. Arquivo pequeno, pensado para rodar a cada 30 minutos.

Saída: data/cotacoes.json
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from atualizar_dados import DADOS, baixar, carregar_watchlist, lista_ativos  # noqa: E402


def main() -> None:
    wl = carregar_watchlist()
    ativos = lista_ativos(wl)
    mon = wl.get("monitorados", {})
    simbolos = [a["yf"] for a in ativos] + list(mon.values())
    dados = baixar(simbolos, "5d")
    nomes = {a["yf"]: (a["ticker"], a["mercado"]) for a in ativos}
    nomes.update({v: (k, "mercado") for k, v in mon.items()})
    itens = []
    for sim, df in dados.items():
        if len(df) < 2:
            continue
        u, ant = df.iloc[-1], df.iloc[-2]
        tk, mercado = nomes.get(sim, (sim, "?"))
        itens.append({"ticker": tk, "mercado": mercado, "data": str(df.index[-1].date()),
                      "preco": round(float(u["close"]), 4),
                      "var_dia_pct": round((float(u["close"]) / float(ant["close"]) - 1) * 100, 2),
                      "max_dia": round(float(u["high"]), 4), "min_dia": round(float(u["low"]), 4)})
    DADOS.mkdir(exist_ok=True)
    (DADOS / "cotacoes.json").write_text(json.dumps({
        "gerado_em": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "obs": "preços do Yahoo Finance via yfinance, com atraso de até ~15 minutos",
        "itens": sorted(itens, key=lambda x: (x["mercado"], x["ticker"]))}, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"cotações: {len(itens)}")


if __name__ == "__main__":
    main()
