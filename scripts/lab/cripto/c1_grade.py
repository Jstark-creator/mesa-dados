import sys; sys.path.insert(0, __file__.rsplit('/',1)[0])
from base import *
from c1_sistemas import rodar, saida_trail_don
import itertools
res=[]
D={s: ind(carregar(s)) for s in ["BTC","ETH"]}
for s,d in D.items():
    for n in (30,40):
        d[f"hi{n}"]=d.high.rolling(n).max().shift(); d[f"lo{n}"]=d.low.rolling(n).min().shift()
    for n in (5,15):
        d[f"lo{n}"]=d.low.rolling(n).min().shift(); d[f"hi{n}"]=d.high.rolling(n).max().shift()
for lado in (1,-1):
  for nb,nt,k,filt in itertools.product((10,20,30,55),(5,10,20),(1.5,2,3),("mm200","mm100","nenhum")):
    if nt>=nb and nb!=10: pass
    ts=[]
    for s,d in D.items():
        c=d.close
        reg = (c>d[filt] if lado==1 else c<d[filt]) if filt!="nenhum" else pd.Series(True,index=d.index)
        sig = reg & ((c>d[f"hi{nb}"]) if lado==1 else (c<d[f"lo{nb}"]))
        ts.append(rodar(d,s,"x",lado,sig,k,saida_trail_don(nt),CUSTO_FUT,lado==1))
    T=pd.concat(ts)
    a=stats(T,"",fim="2021-12-31"); b=stats(T,"",ini="2022-01-01")
    res.append(dict(lado=lado,rompe=nb,trail=nt,stop=k,filtro=filt,tn=a["n"],tR=a.get("media_R"),vn=b["n"],vR=b.get("media_R"),vtot=b.get("total_R"),vdd=b.get("dd_R"),vac=b.get("acerto")))
R=pd.DataFrame(res)
for lado in (1,-1):
    x=R[R.lado==lado].sort_values("vtot",ascending=False)
    print("LADO",lado); print(x.head(12).to_string(index=False))
    print("mediana vR:",x.vR.median(),"  % combos com vR>0:",round((x.vR>0).mean()*100))
    print(x.groupby("filtro").vR.median(), x.groupby("trail").vR.median(), x.groupby("rompe").vR.median(), x.groupby("stop").vR.median())
