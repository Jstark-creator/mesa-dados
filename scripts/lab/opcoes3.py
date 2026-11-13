import sys, numpy as np, pandas as pd, warnings
from math import log, sqrt, exp
from statistics import NormalDist
warnings.filterwarnings("ignore")
Nd=NormalDist(); N=Nd.cdf
sys.path.insert(0,"/home/claude/mesa-dados/scripts")
import backtest_m3 as b
meta,dados=b.carregar()
sel=pd.read_pickle("v2r.pkl"); sel=sel[sel["squeeze"]==False]
def d1(S,K,T,r,v): return (log(S/K)+(r+0.5*v*v)*T)/(v*sqrt(T))
def call(S,K,T,r,v): 
    if T<=1e-6: return max(S-K,0.0)
    a=d1(S,K,T,r,v); return S*N(a)-K*exp(-r*T)*N(a-v*sqrt(T))
def put(S,K,T,r,v):
    if T<=1e-6: return max(K-S,0.0)
    return call(S,K,T,r,v)-S+K*exp(-r*T)
def dcall(S,K,T,r,v): return N(d1(S,K,T,r,v))
def passo(S,mk):
    if mk=="br": return 0.25 if S<10 else (0.5 if S<30 else 1.0)
    return 0.5 if S<25 else (1.0 if S<100 else (2.5 if S<250 else 5.0))
HV={}
for t,df in dados.items():
    hv=np.log(df.close).diff().rolling(20).std()*sqrt(252)
    HV[t]=(hv, hv.rolling(252,min_periods=120).rank(pct=True))
def iv(t,i): return max(0.15,min(2.5,HV[t][0].iloc[i]*1.1))
P={"eua":dict(dte=60,hold=35,r=0.04),"br":dict(dte=30,hold=14,r=0.11)}
def strike_delta(S,T,r,v,alvo_delta,st,tipo="call"):
    # strike na grade cujo delta (call) ou |delta| (put) é mais próximo do alvo
    best=None
    for k in np.arange(max(st,round(S*0.5/st)*st), S*1.8, st):
        dc=dcall(S,k,T,r,v); dlt=dc if tipo=="call" else 1-dc
        e=abs(dlt-alvo_delta)
        if best is None or e<best[0]: best=(e,k)
    return best[1] if best else None
def trade(t,ent_date,atr,mk,slip,modo="matriz"):
    df=dados[t]; p=P[mk]; i4=df.index.get_loc(pd.Timestamp(ent_date)); c1,c2,c3=i4-3,i4-2,i4-1
    o,h,l,c=(df[k].to_numpy() for k in ("open","high","low","close"))
    gat=o[c1]; S0=o[i4] if (c[c3]>gat or o[i4]>=gat) else gat
    stop=l[c2]-0.5*atr; lo,hi=min(l[c1:i4+1]),max(h[c1:i4+1]); alvo=lo+2*(hi-lo)
    if S0<=stop or alvo<=S0: return None
    st=passo(S0,mk); v0=iv(t,c3); T0=p["dte"]/365; r=p["r"]; pct=HV[t][1].iloc[c3]
    if np.isnan(pct) or np.isnan(v0) or np.isnan(S0): return None
    if modo=="matriz":
        est="call" if pct<0.40 else ("trava_call" if pct<=0.60 else "trava_put")
    else: est=modo
    if est=="call":
        K1=strike_delta(S0,T0,r,v0,0.50,st)
        if K1 is None: return None
        f=lambda S,T,v: call(S,K1,T,r,v)
        prem=f(S0,T0,v0)*(1+slip); risco=prem; sinal=1
    elif est=="trava_call":
        K1=strike_delta(S0,T0,r,v0,0.50,st); K2=strike_delta(S0,T0,r,v0,0.20,st)
        if K1 is None or K2 is None: return None
        if K2<=K1: K2=K1+st
        f=lambda S,T,v: call(S,K1,T,r,v)-call(S,K2,T,r,v)
        prem=f(S0,T0,v0)*(1+slip); risco=prem; sinal=1
        if (K2-K1-prem)/prem<2: return dict(pulou="R/R<2",est=est)
    else: # trava de alta com put (crédito)
        Ks=strike_delta(S0,T0,r,v0,0.50,st,"put"); Kl=strike_delta(S0,T0,r,v0,0.25,st,"put")
        if Ks is None or Kl is None: return None
        if Kl>=Ks: Kl=Ks-st
        f=lambda S,T,v: put(S,Ks,T,r,v)-put(S,Kl,T,r,v)   # valor da posição vendida
        cred=f(S0,T0,v0)*(1-slip); larg=Ks-Kl; risco=larg-cred
        if risco<=0: return None
        be=Ks-cred; a=d1(S0,be,T0,r,v0); pop=N(a-v0*sqrt(T0))
        if cred/risco<0.25 or pop<0.60: return dict(pulou="R/R ou POP",est=est,pop=pop,rr=cred/risco)
        sinal=-1; prem=cred
    # caminho do ativo
    Sx=jx=None
    if l[i4]<=stop: Sx,jx=stop,i4
    j=i4+1
    while Sx is None and j<len(df):
        if l[j]<=stop: Sx,jx=(o[j] if o[j]<stop else stop),j; break
        if h[j]>=alvo: Sx,jx=(o[j] if o[j]>alvo else alvo),j; break
        if j-i4>=p["hold"]: Sx,jx=c[j],j; break
        j+=1
    if Sx is None: return None
    T=max(0,(p["dte"]-(df.index[jx]-df.index[i4]).days)/365); vx=iv(t,jx)
    val=f(Sx,T,vx)
    if sinal==1: pnl=val*(1-slip)-prem
    else: pnl=prem-val*(1+slip)
    return dict(r=pnl/risco,est=est,mercado=mk,ano=df.index[i4].year,ent=df.index[i4],sai=df.index[jx],ticker=t,ivp=pct)
def rodar(slip_eua,slip_br,modo="matriz"):
    out=[trade(r.ticker,r.entrada_data,r.atr,r.mercado,slip_eua if r.mercado=="eua" else slip_br,modo) for _,r in sel.iterrows()]
    return pd.DataFrame([x for x in out if x])
def m(x):
    if len(x)<20: return f"n={len(x)}"
    r=x.r; g=r[r>0]; p=r[r<=0]
    return f"n={len(r):4d} acerto={(r>0).mean():.1%} ganho={g.mean():+.2f} perda={p.mean():+.2f} exp={r.mean():+.3f} pf={g.sum()/-p.sum():.2f}"
for cen,(se,sb) in {"execução normal (5% EUA / 10% BR)":(0.05,0.10),"execução boa (2%)":(0.02,0.02)}.items():
    X=rodar(se,sb); X.to_pickle(f"matriz_{se}.pkl")
    feitos=X[X.r.notna()] if "r" in X else X; pul=X[X.get("pulou").notna()] if "pulou" in X else X.iloc[0:0]
    print(f"\n=== {cen} ===  sinais {len(X)} | operados {len(feitos)} | pulados {len(pul)}: {pul.pulou.value_counts().to_dict() if len(pul) else {}}")
    print("MATRIZ total        ", m(feitos))
    for e,g in feitos.groupby("est"): print(f"  {e:12s}", m(g), "| EUA", m(g[g.mercado=='eua']), "| BR", m(g[g.mercado=='br']))
    for mk,g in feitos.groupby("mercado"): print("  mercado",mk, m(g))
    print("  treino",m(feitos[feitos.ano<=2018]),"| valid",m(feitos[feitos.ano>=2019]))
