import sys, math, numpy as np, pandas as pd
from math import log, sqrt, exp
from statistics import NormalDist
N=NormalDist().cdf
sys.path.insert(0,"/home/claude/mesa-dados/scripts")
import backtest_m3 as b
meta,dados=b.carregar()
sel=pd.read_pickle("v2r.pkl"); sel=sel[sel["squeeze"]==False]   # M3 v2.1
def bs_call(S,K,T,r,v):
    if T<=0: return max(S-K,0.0)
    d1=(log(S/K)+(r+0.5*v*v)*T)/(v*sqrt(T)); d2=d1-v*sqrt(T)
    return S*N(d1)-K*exp(-r*T)*N(d2)
def passo(S,mercado):
    if mercado=="br": return 0.25 if S<10 else (0.5 if S<30 else 1.0)
    return 0.5 if S<25 else (1.0 if S<100 else (2.5 if S<250 else 5.0))
def vol(df,i):
    r=np.log(df.close.iloc[i-20:i+1]).diff().dropna(); v=r.std()*sqrt(252)
    return max(0.15,min(2.5,v*1.1))
P={"eua":dict(dte=60,hold=35,r=0.04,slip=0.05),"br":dict(dte=30,hold=14,r=0.11,slip=0.10)}
def trade(t,ent_date,atr,mercado,alvo_mult=2.0,short_at="alvo"):
    df=dados[t]; p=P[mercado]; i4=df.index.get_loc(pd.Timestamp(ent_date)); c1,c2,c3=i4-3,i4-2,i4-1
    o,h,l,c=(df[k].to_numpy() for k in ("open","high","low","close"))
    gat=o[c1]; S0=o[i4] if (c[c3]>gat or o[i4]>=gat) else gat
    stop=l[c2]-0.5*atr; lo,hi=min(l[c1:i4+1]),max(h[c1:i4+1]); alvo=lo+alvo_mult*(hi-lo)
    if S0<=stop or alvo<=S0: return None
    st=passo(S0,mercado); K1=round(S0/st)*st
    tgt=alvo if short_at=="alvo" else S0+(alvo-S0)*0.5
    K2=max(K1+st, round(tgt/st)*st)
    v0=vol(df,c3); T0=p["dte"]/365
    deb=(bs_call(S0,K1,T0,p["r"],v0)-bs_call(S0,K2,T0,p["r"],v0))*(1+p["slip"])
    if deb<=0.02*(K2-K1): return None
    # percurso do ativo
    Sx=None; jx=None
    if l[i4]<=stop: Sx,jx=stop,i4
    j=i4+1
    while Sx is None and j<len(df):
        if l[j]<=stop: Sx,jx=(o[j] if o[j]<stop else stop),j; break
        if h[j]>=alvo: Sx,jx=(o[j] if o[j]>alvo else alvo),j; break
        if j-i4>=p["hold"]: Sx,jx=c[j],j; break
        j+=1
    if Sx is None: return None
    dias=(df.index[jx]-df.index[i4]).days; T=max(0,(p["dte"]-dias)/365)
    vx=vol(df,jx)
    val=(bs_call(Sx,K1,T,p["r"],vx)-bs_call(Sx,K2,T,p["r"],vx))*(1-p["slip"])
    val=min(max(val,0),K2-K1)
    risco_acao=S0-stop
    return dict(r_opc=val/deb-1, r_acao=(Sx-S0)/risco_acao, deb_pct=deb/(K2-K1), larg=(K2-K1)/S0, ent=df.index[i4], sai=df.index[jx], mercado=mercado, ticker=t, ano=df.index[i4].year)
def rodar(**kw):
    rs=[trade(r.ticker,r.entrada_data,r.atr,r.mercado,**kw) for _,r in sel.iterrows()]
    return pd.DataFrame([x for x in rs if x])
R=rodar(); R.to_pickle("opc.pkl")
def m(x,col):
    r=x[col]; g=r[r>0]; p=r[r<=0]
    return f"n={len(r)} acerto={(r>0).mean():.1%} ganho_med={g.mean():+.2f} perda_med={p.mean():+.2f} exp={r.mean():+.3f} pf={g.sum()/-p.sum():.2f}"
print("AÇÃO (R do ativo)      ", m(R,"r_acao"))
print("TRAVA (múltiplo do débito)", m(R,"r_opc"))
for mk,g in R.groupby("mercado"): print(" ",mk,"ação",m(g,"r_acao")," | trava",m(g,"r_opc"))
print("débito médio = %.0f%% da largura; largura média %.1f%% do preço" % (R.deb_pct.mean()*100, R.larg.mean()*100))
for lab,s in (("treino",R[R.ano<=2018]),("valid",R[R.ano>=2019])): print(lab,m(s,"r_opc"))
R2=rodar(short_at="meio"); print("Vendida no meio do caminho:",m(R2,"r_opc"))
