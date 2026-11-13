exec(open("opcoes.py").read().split("R=rodar()")[0])
import warnings; warnings.filterwarnings("ignore")
def trade2(t,ent_date,atr,mercado,tipo="trava",slip=None,itm=0.10,segura=False):
    df=dados[t]; p=dict(P[mercado]); 
    if slip is not None: p["slip"]=slip
    i4=df.index.get_loc(pd.Timestamp(ent_date)); c1,c2,c3=i4-3,i4-2,i4-1
    o,h,l,c=(df[k].to_numpy() for k in ("open","high","low","close"))
    gat=o[c1]; S0=o[i4] if (c[c3]>gat or o[i4]>=gat) else gat
    stop=l[c2]-0.5*atr; lo,hi=min(l[c1:i4+1]),max(h[c1:i4+1]); alvo=lo+2*(hi-lo)
    if S0<=stop or alvo<=S0: return None
    st=passo(S0,mercado); v0=vol(df,c3); T0=p["dte"]/365
    if tipo=="trava":
        K1=round(S0/st)*st; K2=max(K1+st,round(alvo/st)*st)
        f=lambda S,T,v: bs_call(S,K1,T,p["r"],v)-bs_call(S,K2,T,p["r"],v)
    elif tipo=="call_atm":
        K1=round(S0/st)*st; f=lambda S,T,v: bs_call(S,K1,T,p["r"],v)
    else: # call ITM
        K1=round(S0*(1-itm)/st)*st; f=lambda S,T,v: bs_call(S,K1,T,p["r"],v)
    deb=f(S0,T0,v0)*(1+p["slip"])
    if deb<=0: return None
    Sx=jx=None; alvo_batido=False
    if l[i4]<=stop: Sx,jx=stop,i4
    j=i4+1
    while Sx is None and j<len(df):
        if l[j]<=stop: Sx,jx=(o[j] if o[j]<stop else stop),j; break
        if h[j]>=alvo and not segura: Sx,jx=(o[j] if o[j]>alvo else alvo),j; break
        if h[j]>=alvo and segura and not alvo_batido: alvo_batido=True; stop=max(stop,S0)  # protege no zero a zero e segura
        if j-i4>=p["hold"]: Sx,jx=c[j],j; break
        j+=1
    if Sx is None: return None
    dias=(df.index[jx]-df.index[i4]).days; T=max(0,(p["dte"]-dias)/365)
    val=max(f(Sx,T,vol(df,jx)),0)*(1-p["slip"])
    return dict(r=val/deb-1,ano=df.index[i4].year,mercado=mercado,ent=df.index[i4],sai=df.index[jx],ticker=t,
                capital_acao=S0/(S0-stop))  # capital por 1 unidade de risco
def rodar2(**kw):
    rs=[trade2(r.ticker,r.entrada_data,r.atr,r.mercado,**kw) for _,r in sel.iterrows()]
    return pd.DataFrame([x for x in rs if x])
def m(x):
    r=x.r; g=r[r>0]; p=r[r<=0]
    return f"acerto={(r>0).mean():.1%} ganho={g.mean():+.2f} perda={p.mean():+.2f} exp={r.mean():+.3f} pf={g.sum()/-p.sum():.2f}"
for nome,kw in [("Trava (referência)",{}),("Trava, spread menor (2%)",dict(slip=0.02)),
                ("Trava, segura após alvo (stop no zero a zero)",dict(segura=True)),
                ("Call ATM seca",dict(tipo="call_atm")),("Call ITM 10% (delta ~0,75)",dict(tipo="call_itm")),
                ("Call ITM 10%, spread 2%",dict(tipo="call_itm",slip=0.02))]:
    X=rodar2(**kw); print(f"{nome:46s} TOTAL {m(X)} | EUA {m(X[X.mercado=='eua'])} | BR {m(X[X.mercado=='br'])}")
    if nome.startswith("Trava (ref"): cap=X.capital_acao.median(); print("   capital p/ operar a AÇÃO com risco 1 = %.0f× o risco (mediana)"%cap)
