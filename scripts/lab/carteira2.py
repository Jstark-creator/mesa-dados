import sys, numpy as np, pandas as pd
exec(open("carteira.py").read().split("tr=[]")[0].replace('sel=base[(base.volr>1)&(base.ifr>60)&(base.close>base.sma200)&(base.ano>=2021)]','sel=pd.read_pickle("v2r.pkl")'))
tr=[]
for _,r in sel.iterrows():
    x=sim(r.ticker,r.entrada_data,35 if r.mercado=="eua" else 14,r.atr)
    if x: tr.append(dict(ticker=r.ticker,tier=r.tier,ent=pd.Timestamp(r.entrada_data),sai=x[1],r=x[0],sq=bool(r["squeeze"])))
TR=pd.DataFrame(tr).sort_values(["ent","tier"]).reset_index(drop=True)
def carteira(tr,inicio=100000,risco=2000,max_pos=10,custo=0.05,cb=None,cb_n=20,cb_fator=0.5,ano_ini=2021):
    tr=tr[tr.ent.dt.year>=ano_ini]
    eq=inicio; ab=[]; log=[]; hist=[]
    for _,t in tr.iterrows():
        for a in sorted([a for a in ab if a["sai"]<t.ent],key=lambda a:a["sai"]):
            eq+=a["pnl"]; log.append((a["sai"],a["pnl"])); hist.append(a["r"]); ab.remove(a)
        if len(ab)>=max_pos: continue
        f=1.0
        if cb and len(hist)>=cb_n and sum(hist[-cb_n:])<0: f=cb_fator
        ab.append({"sai":t.sai,"pnl":risco*f*(t.r-custo),"r":t.r})
    for a in sorted(ab,key=lambda a:a["sai"]): eq+=a["pnl"]; log.append((a["sai"],a["pnl"]))
    L=pd.DataFrame(log,columns=["data","pnl"]); L["ano"]=L.data.dt.year
    e=inicio; out={}
    peak=inicio; mdd=0; cur=inicio
    for _,row in L.sort_values("data").iterrows():
        cur+=row.pnl; peak=max(peak,cur); mdd=min(mdd,(cur-peak)/peak)
    for y,g in L.groupby("ano"):
        ini=e; e+=g.pnl.sum(); out[y]=e/ini-1
    return out,e,mdd
def show(nome,**kw):
    out,fim,mdd=carteira(**kw)
    print(f"{nome:44s} "+" ".join(f"{y}:{v:+.0%}" for y,v in out.items())+f" | final R${fim:,.0f} | pior queda {mdd:.0%}")
show("M3 v2",tr=TR)
show("M3 v2 sem squeeze",tr=TR[~TR.sq])
show("v2 + disjuntor (últ.20 <0 → meio risco)",tr=TR,cb=True)
show("v2 + disjuntor (últ.20 <0 → pausa)",tr=TR,cb=True,cb_fator=0.0)
show("v2 + disjuntor 10 trades → meio",tr=TR,cb=True,cb_n=10)
show("v2 sem squeeze + disjuntor 20 meio",tr=TR[~TR.sq],cb=True)
print("--- período longo (2007+), R$100k ---")
for nome,kw in [("M3 v2",dict(tr=TR)),("v2 sem squeeze + disjuntor",dict(tr=TR[~TR.sq],cb=True))]:
    out,fim,mdd=carteira(ano_ini=2007,**kw); neg=sum(v<0 for v in out.values())
    print(f"{nome:30s} final R${fim:,.0f} | anos negativos {neg}/{len(out)} | pior queda {mdd:.0%} | piores: "+", ".join(f"{y}:{v:+.0%}" for y,v in sorted(out.items(),key=lambda x:x[1])[:3]))
