import sys; sys.path.insert(0, __file__.rsplit('/',1)[0])
from base import *
from c1_sistemas import rodar, saida_trail_don
def gerar(custo_long=CUSTO_FUT, fund=True, nt_long=20, k=2.0, nt_short=10):
    ts=[]
    for s in ["BTC","ETH"]:
        d=ind(carregar(s)); c=d.close
        ts.append(rodar(d,s,"long",1,(c>d.mm200)&(c>d.hi20),k,saida_trail_don(nt_long),custo_long,fund))
        ts.append(rodar(d,s,"short",-1,(c<d.mm200)&(c<d.lo20),k,saida_trail_don(nt_short),CUSTO_FUT,False))
    return pd.concat(ts).sort_values("entrada")
if __name__=="__main__":
    for rot,args in (("long futuros",{}),("long spot",dict(custo_long=CUSTO_SPOT,fund=False))):
        T=gerar(**args)
        print("==",rot)
        for nome,g in [("long",T[T.sist=="long"]),("short",T[T.sist=="short"]),("TOTAL",T)]:
            print(nome, "treino",stats(g,nome,fim="2021-12-31"), "\n      valid",stats(g,nome,ini="2022-01-01"))
    T=gerar()
    T["ano"]=pd.to_datetime(T.entrada).dt.year
    print(T.groupby(["ano","sist"]).r.agg(["count","sum"]).round(1).unstack())
    T.to_csv("/tmp/c1_final.csv",index=False)
    # posições simultâneas
    ev=[]
    for _,t in T.iterrows(): ev+= [(t.entrada,1),(t.saida,-1)]
    ev.sort(); m=cur=0
    for _,x in ev: cur+=x; m=max(m,cur)
    print("max posições simultâneas",m, " maior perda seguida em R:", )
    r=T.r.values; seq=mx=0
    for x in r:
        seq = seq+1 if x<0 else 0; mx=max(mx,seq)
    print("maior sequência de perdas:",mx)
    print(T[T.entrada>="2025-06-01"][["sym","sist","entrada","saida","pe","ps","r"]].round(2).to_string(index=False))
