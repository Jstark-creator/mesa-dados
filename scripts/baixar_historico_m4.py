"""Histórico de 20 anos do universo M4 (config/universo_m4.json) -> data/historico/<TICKER>.csv."""
from __future__ import annotations
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from atualizar_dados import RAIZ, baixar  # noqa: E402

def main():
    u = json.loads((RAIZ / "config" / "universo_m4.json").read_text())
    pares = [(t, t) for t in u["eua"]] + [(t, f"{t}.SA") for t in u["br"]]
    dest = RAIZ / "data" / "historico"; dest.mkdir(parents=True, exist_ok=True)
    dados = baixar([y for _, y in pares], "20y")
    for t, y in pares:
        df = dados.get(y)
        if df is None or df.empty:
            print(f"{t}: sem dados"); continue
        df.round(4).to_csv(dest / f"{t}.csv", index_label="data")
        print(f"{t}: {len(df)} dias desde {df.index.min().date()}")

if __name__ == "__main__":
    main()
