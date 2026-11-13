import sys; sys.path.insert(0, __file__.rsplit('/',1)[0])
from base import *
from c1_sistemas import rodar, saida_trail_don
ALTS=["SOL","BNB","XRP","ADA","DOGE","AVAX","LINK","DOT","LTC","TRX","NEAR","ATOM","UNI","SUI","BCH","XLM"]
btc=ind(carregar("BTC"))
def gerar(nb=20,nt=20,k=2.0,filtro_btc=True,custo=CUSTO_SPOT,fund=False, idade=200):
    ts=[]
    for s in ALTS:
        d=ind(carregar(s)); c=d.close
        d=d.iloc[idade:] if len(d)>idade else d.iloc[0:0]
        c=d.close
        b=(btc.close>btc.mm200).reindex(d.index).fillna(False)
        sig=(c>d.mm200)&(c>d[f"hi{nb}"])
        if filtro_btc: sig=sig&b
        ts.append(rodar(d,s,"alt",1,sig,k,saida_trail_don(nt),custo,fund))
    return pd.concat(ts).sort_values("entrada")
def limitar(T,maxpos):
    abertas=[]; ok=[]
    for _,t in T.iterrows():
        abertas=[x for x in abertas if x>t.entrada]
        if len(abertas)<maxpos: ok.append(True); abertas.append(t.saida)
        else: ok.append(False)
    return T[ok]
if __name__=="__main__":
    for nb,nt in ((20,10),(20,20),(55,20)):
        for fb in (False,True):
            T=gerar(nb,nt,filtro_btc=fb)
            for mp in (99,5,3):
                L=limitar(T,mp)
                a=stats(L,"",fim="2021-12-31"); b=stats(L,"",ini="2022-01-01")
                print(f"rompe{nb} trail{nt} filtroBTC={fb} max{mp}: treino n={a['n']} R={a.get('media_R')} | valid n={b['n']} R={b.get('media_R')} ac={b.get('acerto')} tot={b.get('total_R')} dd={b.get('dd_R')} /ano={b.get('por_ano')}")
    T=limitar(gerar(20,20,filtro_btc=True),5); T["ano"]=pd.to_datetime(T.entrada).dt.year
    print(T.groupby("ano").r.agg(["count","sum","mean"]).round(2))
    print("mediana R",T.r.median()," top5 trades:",T.nlargest(5,"r")[["sym","entrada","r"]].values.tolist())
    print("sem os 5 maiores, média valid:", T[T.entrada>="2022"].r.drop(T[T.entrada>="2022"].r.nlargest(5).index).mean())
