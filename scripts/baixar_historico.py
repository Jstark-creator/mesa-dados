"""Baixa o histórico longo (padrão: 20 anos) de todos os ativos da watchlist para backtest.

Saída: data/historico/<TICKER>.csv (OHLCV diário ajustado, sem indicadores).
Uso: python scripts/baixar_historico.py [--periodo 20y]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from atualizar_dados import RAIZ, baixar, carregar_watchlist, lista_ativos  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--periodo", default="20y")
    args = ap.parse_args()
    ativos = lista_ativos(carregar_watchlist())
    destino = RAIZ / "data" / "historico"
    destino.mkdir(parents=True, exist_ok=True)
    dados = baixar([a["yf"] for a in ativos], args.periodo)
    ok = 0
    for a in ativos:
        df = dados.get(a["yf"])
        if df is None or df.empty:
            print(f"{a['ticker']}: sem dados")
            continue
        df.round(4).to_csv(destino / f"{a['ticker']}.csv", index_label="data")
        ok += 1
    # índices e indicadores de mercado (para filtros de regime)
    wl = carregar_watchlist()
    mon = wl.get("monitorados", {})
    dm = baixar(list(mon.values()), args.periodo)
    for nome, sim in mon.items():
        df = dm.get(sim)
        if df is not None and not df.empty:
            nomearq = sim.replace("^", "IDX_").replace("=", "_").replace(".", "_")
            df.round(4).to_csv(destino / f"{nomearq}.csv", index_label="data")
            ok += 1
    print(f"histórico salvo: {ok} séries")


if __name__ == "__main__":
    main()
