"""Baixa o histórico OFICIAL e gratuito da B3 (COTAHIST) e extrai as opções (calls/puts) do universo BR do M4.

Fonte: https://bvmf.bmfbovespa.com.br/InstDados/SerHist/COTAHIST_A<ANO>.ZIP (layout posicional da B3).
Saída: data/b3/opcoes_<ANO>.csv.gz e data/b3/acoes_<ANO>.csv.gz (dados públicos da B3).
Campos: data, codigo, tipo (C/P), ativo (4 letras), strike, vencimento, abertura, maxima, minima, fechamento (último),
        melhor_compra, melhor_venda, negocios, volume_financeiro.
"""
from __future__ import annotations
import io, json, sys, urllib.request, zipfile
from datetime import date
from pathlib import Path
import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
URL = "https://bvmf.bmfbovespa.com.br/InstDados/SerHist/COTAHIST_A{ano}.ZIP"

def baixar(ano, tentativas=4):
    import time
    for k in range(tentativas):
        try:
            req = urllib.request.Request(URL.format(ano=ano), headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=600) as r:
                return r.read()
        except Exception as e:
            if k == tentativas - 1:
                raise
            print(f"{ano}: tentativa {k+1} falhou ({e}); repetindo")
            time.sleep(30 * (k + 1))

def p(x):  # preço com 2 casas implícitas
    return int(x) / 100

def parse(zbytes, raizes):
    zf = zipfile.ZipFile(io.BytesIO(zbytes))
    nome = zf.namelist()[0]
    op, ac = [], []
    with zf.open(nome) as fh:
        for raw in io.TextIOWrapper(fh, encoding="latin-1"):
            if not raw.startswith("01"):
                continue
            tpmerc = raw[24:27]
            cod = raw[12:24].strip()
            raiz = cod[:4]
            if raiz not in raizes:
                continue
            fatcot = int(raw[210:217]) or 1
            base = dict(data=raw[2:10], codigo=cod, abertura=p(raw[56:69]) / fatcot, maxima=p(raw[69:82]) / fatcot,
                        minima=p(raw[82:95]) / fatcot, fechamento=p(raw[108:121]) / fatcot,
                        melhor_compra=p(raw[121:134]) / fatcot, melhor_venda=p(raw[134:147]) / fatcot,
                        negocios=int(raw[147:152]), volume_financeiro=p(raw[170:188]))
            if tpmerc in ("070", "080"):
                base.update(tipo="C" if tpmerc == "070" else "P", ativo=raiz, strike=p(raw[188:201]) / fatcot,
                            vencimento=raw[202:210])
                op.append(base)
            elif tpmerc == "010" and cod in raizes.get(raiz, ()):
                ac.append(base)
    return pd.DataFrame(op), pd.DataFrame(ac)

def main():
    u = json.loads((RAIZ / "config" / "universo_m4.json").read_text())
    raizes = {}
    for t in u["br"]:
        raizes.setdefault(t[:4], set()).add(t)
    dest = RAIZ / "data" / "b3"; dest.mkdir(parents=True, exist_ok=True)
    ini = int(sys.argv[1]) if len(sys.argv) > 1 else 2012
    for ano in range(ini, date.today().year + 1):
        arq = dest / f"opcoes_{ano}.csv.gz"
        if arq.exists() and ano < date.today().year:
            continue
        try:
            z = baixar(ano)
        except Exception as e:
            print(f"{ano}: falhou ({e})"); continue
        op, ac = parse(z, raizes)
        op.to_csv(arq, index=False, compression="gzip")
        ac.to_csv(dest / f"acoes_{ano}.csv.gz", index=False, compression="gzip")
        print(f"{ano}: {len(op)} linhas de opções, {len(ac)} de ações")

if __name__ == "__main__":
    main()
