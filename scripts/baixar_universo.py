"""Baixa 20 anos de histórico para um universo em config (lista 'acoes' ou 'eua') -> data/historico/<T>.csv.
Uso: python scripts/baixar_universo.py config/universo_m6.json"""
from __future__ import annotations
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from atualizar_dados import RAIZ, baixar  # noqa: E402

def main():
    cfg = json.loads((RAIZ / sys.argv[1]).read_text())
    tick = cfg.get("acoes") or cfg.get("eua")
    if cfg.get("mercado"): tick = tick + [cfg["mercado"]]
    dest = RAIZ / "data" / "historico"; dest.mkdir(parents=True, exist_ok=True)
    dados = baixar(tick, "20y")
    for t in tick:
        df = dados.get(t)
        if df is None or df.empty:
            print(f"{t}: sem dados"); continue
        df.round(4).to_csv(dest / f"{t}.csv", index_label="data")
        print(f"{t}: {len(df)} dias desde {df.index.min().date()}")

if __name__ == "__main__":
    main()
