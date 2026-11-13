import sys, numpy as np, pandas as pd
sys.path.insert(0,"scripts")
import backtest_m3 as b
meta,dados=b.carregar()
base=pd.read_pickle("data/backtest/base_compras.pkl")
sel=base[(base.volr>1)&(base.ifr>60)&(base.close>base.sma200)]
def sim(t,ent_date,hold,alvo_mult=2.0,be=None,trail=False,atr_buf=0.0,atr=None):
    df=dados[t]; idx=df.index.get_loc(pd.Timestamp(ent_date)); c4=idx; c1,c2,c3=c4-3,c4-2,c4-1
    o,h,l,c,e9=(df[k].to_numpy() for k in ("open","high","low","close","mme9"))
    gat=o[c1]; entrada=o[c4] if (c[c3]>gat or o[c4]>=gat) else gat
    stop=l[c2]-atr_buf*atr; risco=entrada-stop
    lo,hi=min(l[c1:c4+1]),max(h[c1:c4+1]); alvo=lo+alvo_mult*(hi-lo)
    if risco<=0 or alvo<=entrada: return None
    if l[c4]<=stop: return -1.0
    s=stop; n=len(df)
    for j in range(c4+1,n):
        if l[j]<=s: return ((o[j] if o[j]<s else s)-entrada)/risco
        if h[j]>=alvo: return ((o[j] if o[j]>alvo else alvo)-entrada)/risco
        if j-c4>=hold: return (c[j]-entrada)/risco
        if be and h[j]>=entrada+be*risco: s=max(s,entrada)
        if trail and c[j]<e9[j] and j-c4>=3: return (c[j]-entrada)/risco
    return None
def run(**kw):
    rs=[]; anos=[]
    for _,r in sel.iterrows():
        hold=35 if r.mercado=="eua" else 14
        x=sim(r.ticker,r.entrada_data,hold,atr=r.atr,**kw)
        if x is not None: rs.append(x); anos.append(r.ano)
    s=pd.DataFrame({"r":rs,"ano":anos})
    def m(x):
        r=x.r; g=r[r>0]; p=r[r<=0]; return f"n={len(r)} ac={(r>0).mean():.1%} exp={r.mean():+.3f} pf={g.sum()/-p.sum():.2f}"
    return f"treino {m(s[s.ano<=2018])} | valid {m(s[s.ano>=2019])}"
print("Referência (alvo Fib 200%)        ", run())
print("Alvo Fib 161,8%                   ", run(alvo_mult=1.618))
print("Alvo Fib 261,8%                   ", run(alvo_mult=2.618))
print("Breakeven após +1R                ", run(be=1.0))
print("Breakeven após +1,5R              ", run(be=1.5))
print("Saída no fechamento abaixo da MME9", run(trail=True))
print("Stop 0,5 ATR abaixo do fundo      ", run(atr_buf=0.5))
print("Stop 0,5 ATR + alvo 161,8%        ", run(atr_buf=0.5,alvo_mult=1.618))
