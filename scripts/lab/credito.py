exec(open("opcoes3.py").read().split("def trade(")[0])
def cred(t,ent_date,atr,mk,slip,tipo,dv=0.50,dc=0.25,saida="m3",pop_min=None,rr_min=None):
    df=dados[t]; p=P[mk]; i4=df.index.get_loc(pd.Timestamp(ent_date)); c1,c2,c3=i4-3,i4-2,i4-1
    o,h,l,c=(df[k].to_numpy() for k in ("open","high","low","close"))
    gat=o[c1]; S0=o[i4] if (c[c3]>gat or o[i4]>=gat) else gat
    stop=l[c2]-0.5*atr; lo,hi=min(l[c1:i4+1]),max(h[c1:i4+1]); alvo=lo+2*(hi-lo)
    if S0<=stop or alvo<=S0 or np.isnan(S0): return None
    st=passo(S0,mk); v0=iv(t,c3); T0=p["dte"]/365; r=p["r"]
    if np.isnan(v0): return None
    if tipo=="put":   # trava de alta com put (crédito)
        Ks=strike_delta(S0,T0,r,v0,dv,st,"put"); Kl=strike_delta(S0,T0,r,v0,dc,st,"put")
        if Ks is None or Kl is None: return None
        if Kl>=Ks: Kl=Ks-st
        f=lambda S,T,v: put(S,Ks,T,r,v)-put(S,Kl,T,r,v); be_dir=1
    else:             # trava de baixa com call (crédito), acima do preço
        Ks=strike_delta(S0,T0,r,v0,dv,st,"call"); Kl=strike_delta(S0,T0,r,v0,dc,st,"call")
        if Ks is None or Kl is None: return None
        if Kl<=Ks: Kl=Ks+st
        f=lambda S,T,v: call(S,Ks,T,r,v)-call(S,Kl,T,r,v); be_dir=-1
    larg=abs(Ks-Kl); credito=f(S0,T0,v0)*(1-slip); risco=larg-credito
    if credito<=0 or risco<=0: return None
    be=Ks-credito if tipo=="put" else Ks+credito
    a=d1(S0,be,T0,r,v0); pop=N(a-v0*sqrt(T0)) if tipo=="put" else 1-N(a-v0*sqrt(T0))
    if rr_min and credito/risco<rr_min: return {"pulou":1}
    if pop_min and pop<pop_min: return {"pulou":1}
    Sx=jx=None; j=i4
    while j<len(df):
        dias=(df.index[j]-df.index[i4]).days; T=max(0,(p["dte"]-dias)/365)
        if l[j]<=stop: Sx,jx=(o[j] if (j>i4 and o[j]<stop) else stop),j; break
        if saida=="m3" and j>i4 and h[j]>=alvo: Sx,jx=(o[j] if o[j]>alvo else alvo),j; break
        if saida=="50" and j>i4 and f(c[j],T,iv(t,j))*(1+slip)<=0.5*credito: Sx,jx=c[j],j; break
        if j>i4 and j-i4>=p["hold"]: Sx,jx=c[j],j; break
        j+=1
    if Sx is None: return None
    T=max(0,(p["dte"]-(df.index[jx]-df.index[i4]).days)/365)
    custo_saida=f(Sx,T,iv(t,jx))*(1+slip)
    custo_saida=min(max(custo_saida,0),larg)
    return dict(r=(credito-custo_saida)/risco,pop=pop,rr=credito/risco,ano=df.index[i4].year,ent=df.index[i4],sai=df.index[jx],ticker=t,mercado=mk)
alto=sel[[HV[s.ticker][1].iloc[dados[s.ticker].index.get_loc(pd.Timestamp(s.entrada_data))-1]>0.60 for _,s in sel.iterrows()]]
print("sinais com IV>60%:",len(alto))
def m(x):
    if len(x)<20: return f"n={len(x)}"
    r=x.r; g=r[r>0]; p_=r[r<=0]; return f"n={len(r)} acerto={(r>0).mean():.1%} ganho={g.mean():+.2f} perda={p_.mean():+.2f} exp={r.mean():+.3f} pf={g.sum()/-p_.sum():.2f} | treino {x[x.ano<=2018].r.mean():+.3f} valid {x[x.ano>=2019].r.mean():+.3f}"
cen={"Put 0,50/0,25 sem POP, R/R>25%, saída M3":dict(tipo="put",rr_min=0.25),
     "Put 0,50/0,25 sem POP, R/R>25%, realiza 50%":dict(tipo="put",rr_min=0.25,saida="50"),
     "Put 0,50/0,25 com POP>60% (regra original)":dict(tipo="put",rr_min=0.25,pop_min=0.60),
     "Put 0,30/0,15 (fora do dinheiro), saída M3":dict(tipo="put",dv=0.30,dc=0.15),
     "Put 0,30/0,15, realiza 50%":dict(tipo="put",dv=0.30,dc=0.15,saida="50"),
     "Call crédito 0,30/0,15 (trava de baixa), saída M3":dict(tipo="call",dv=0.30,dc=0.15),
     "Call crédito 0,30/0,15, realiza 50%":dict(tipo="call",dv=0.30,dc=0.15,saida="50")}
RES={}
for se,sb,lab in ((0.05,0.10,"normal"),(0.02,0.02,"boa")):
    print(f"\n=== execução {lab} ===")
    for n,kw in cen.items():
        out=[cred(s.ticker,s.entrada_data,s.atr,s.mercado,se if s.mercado=="eua" else sb,**kw) for _,s in alto.iterrows()]
        X=pd.DataFrame([x for x in out if x and "r" in x]); pul=sum(1 for x in out if x and "pulou" in x)
        RES[(lab,n)]=X; print(f"{n:50s} {m(X)} | pulados {pul}")
pd.to_pickle(RES,"credito_res.pkl")
