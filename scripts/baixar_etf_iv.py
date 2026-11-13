"""Histórico máximo de ETFs e dos índices de volatilidade implícita da CBOE (IV real e gratuita).

Saída: data/etf/<NOME>.csv (OHLCV diário). Usado pelo laboratório de opções em ETFs.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from atualizar_dados import RAIZ, baixar  # noqa: E402

SERIES = {
    "SPY": "SPY", "QQQ": "QQQ", "IWM": "IWM", "GLD": "GLD", "USO": "USO", "XLE": "XLE", "TLT": "TLT",
    "VIX": "^VIX", "VXN": "^VXN", "RVX": "^RVX", "GVZ": "^GVZ", "OVX": "^OVX",
    "VIX9D": "^VIX9D", "VIX3M": "^VIX3M", "IRX": "^IRX",
}


def main() -> None:
    dest = RAIZ / "data" / "etf"
    dest.mkdir(parents=True, exist_ok=True)
    dados = baixar(list(SERIES.values()), "max")
    for nome, sim in SERIES.items():
        df = dados.get(sim)
        if df is None or df.empty:
            print(f"{nome}: sem dados")
            continue
        df.round(4).to_csv(dest / f"{nome}.csv", index_label="data")
        print(f"{nome}: {len(df)} dias desde {df.index.min().date()}")


if __name__ == "__main__":
    main()
