import sys, numpy as np, pandas as pd
sys.path.insert(0,"/home/claude/mesa-dados/scripts")
import backtest_m3 as b
meta,dados=b.carregar()
base=pd.read_pickle("base.pkl")
sel=base[(base.volr>1)&(base.ifr>60)&(base.close>base.sma200)&(base.ano>=2021)]
def sim(t,ent_date,hold,atr):
    df=dados[t]; idx=df.index.get_loc(pd.Timestamp(ent_date)); c4=idx; c1,c2,c3=c4-3,c4-2,c4-1
    o,h,l,c=(df[k].to_numpy() for k in ("open","high","low","close"))
    gat=o[c1]; entrada=o[c4] if (c[c3]>gat or o[c4]>=gat) else gat
    stop=l[c2]-0.5*atr; risco=entrada-stop
    lo,hi=min(l[c1:c4+1]),max(h[c1:c4+1]); alvo=lo+2*(hi-lo)
    if risco<=0 or alvo<=entrada: return None
    if l[c4]<=stop: return -1.0, df.index[c4]
    for j in range(c4+1,len(df)):
        if l[j]<=stop: return ((o[j] if o[j]<stop else stop)-entrada)/risco, df.index[j]
        if h[j]>=alvo: return ((o[j] if o[j]>alvo else alvo)-entrada)/risco, df.index[j]
        if j-c4>=hold: return (c[j]-entrada)/risco, df.index[j]
    return None
tr=[]
for _,r in sel.iterrows():
    x=sim(r.ticker,r.entrada_data,35 if r.mercado=="eua" else 14,r.atr)
    if x: tr.append(dict(ticker=r.ticker,mercado=r.mercado,tier=r.tier,ent=pd.Timestamp(r.entrada_data),sai=x[1],r=x[0]))
tr=pd.DataFrame(tr).sort_values(["ent","tier"]).reset_index(drop=True)
def carteira(modo, custo_r=0.05, max_pos=10, risco_pct=0.02, risco_fixo=2000, inicio=100000):
    eq=inicio; abertas=[]; log=[]
    for _,t in tr.iterrows():
        # fecha as que saíram antes desta entrada
        for a in sorted([a for a in abertas if a["sai"]<t.ent], key=lambda a:a["sai"]):
            eq+=a["pnl"]; log.append((a["sai"],a["pnl"])); abertas.remove(a)
        if len(abertas)>=max_pos: continue
        risco = eq*risco_pct if modo=="composto" else risco_fixo
        abertas.append({"sai":t.sai,"pnl":risco*(t.r-custo_r)})
    for a in sorted(abertas,key=lambda a:a["sai"]): eq+=a["pnl"]; log.append((a["sai"],a["pnl"]))
    L=pd.DataFrame(log,columns=["data","pnl"]); L["ano"]=L.data.dt.year
    out=[]; e=inicio
    for y,g in L.groupby("ano"):
        ini=e; e+=g.pnl.sum()
        # drawdown intra-ano
        curva=ini+g.sort_values("data").pnl.cumsum(); pico=np.maximum.accumulate(np.r_[ini,curva.values]); dd=((np.r_[ini,curva.values]-pico)/pico).min()
        out.append(dict(ano=y,operacoes=len(g),inicio=ini,fim=e,ret=e/ini-1,dd=dd,acerto=(g.pnl>0).mean()))
    return pd.DataFrame(out)
for modo in ("fixo","composto"):
    for custo in (0.05,):
        print(f"== risco {modo} | custo {custo}R/op | máx 10 posições")
        print(carteira(modo,custo).to_string(index=False,formatters={"inicio":"{:,.0f}".format,"fim":"{:,.0f}".format,"ret":"{:+.1%}".format,"dd":"{:.1%}".format,"acerto":"{:.0%}".format}))
print("sem custo, fixo:"); print(carteira("fixo",0.0)[["ano","fim","ret"]].to_string(index=False))
