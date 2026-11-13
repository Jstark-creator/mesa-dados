import sys, json, numpy as np, pandas as pd
sys.path.insert(0,"scripts")
import backtest_m3 as b
meta,dados=b.carregar()

def feats(df):
    f=pd.DataFrame(index=df.index)
    c,h,l,v=df.close,df.high,df.low,df.volume
    f["sma50"]=c.rolling(50).mean(); f["sma200"]=c.rolling(200).mean()
    tr=pd.concat([h-l,(h-c.shift()).abs(),(l-c.shift()).abs()],axis=1).max(axis=1)
    atr=tr.ewm(alpha=1/14,adjust=False).mean(); f["atr"]=atr
    up=h.diff(); dn=-l.diff()
    pdm=np.where((up>dn)&(up>0),up,0.0); mdm=np.where((dn>up)&(dn>0),dn,0.0)
    pdi=100*pd.Series(pdm,index=df.index).ewm(alpha=1/14,adjust=False).mean()/atr
    mdi=100*pd.Series(mdm,index=df.index).ewm(alpha=1/14,adjust=False).mean()/atr
    dx=100*(pdi-mdi).abs()/(pdi+mdi).replace(0,np.nan)
    f["adx"]=dx.ewm(alpha=1/14,adjust=False).mean(); f["pdi"]=pdi; f["mdi"]=mdi
    f["volr"]=v/v.rolling(20).mean()
    w=c.resample("W-FRI").last(); wma=w.rolling(20).mean(); wma10=w.rolling(10).mean()
    wk=pd.DataFrame({"wup":(w>wma)&(wma10>wma)}).shift(1)  # semana anterior completa
    f["wup"]=wk["wup"].reindex(df.index,method="ffill")
    f["ret63"]=c/c.shift(63)-1
    f["dist20"]=(c-df.mms20)/atr
    f["hi52"]=c/h.rolling(252).max()
    f["ifr"]=df.ifr14
    return f

F={t:feats(df) for t,df in dados.items()}
# força relativa e amplitude por mercado (cross-section)
for mk in ("eua","br"):
    ts=[t for t in F if meta[t][0]==mk]
    r=pd.DataFrame({t:F[t]["ret63"] for t in ts}); rk=r.rank(axis=1,pct=True)
    a=pd.DataFrame({t:(dados[t].close>F[t]["sma200"]).where(F[t]["sma200"].notna()) for t in ts}); br=a.mean(axis=1)
    for t in ts: F[t]["rs"]=rk[t]; F[t]["breadth"]=br.reindex(F[t].index)

def run(**kw):
    rows=[]
    for t,df in dados.items():
        idx={d:i for i,d in enumerate(df.index.strftime("%Y-%m-%d"))}
        for r in b.simular(t,df,*meta[t],**kw):
            if r["direcao"]!="compra": continue
            i3=idx[r["entrada_data"]]-1
            row=F[t].iloc[i3].to_dict(); row.update(r); row["close"]=df.close.iloc[i3]; rows.append(row)
    return pd.DataFrame(rows)

base=run()
def m(x):
    if len(x)<50: return None
    r=x.r; g=r[r>0]; p=r[r<=0]
    return dict(n=len(r),acerto=(r>0).mean(),exp=r.mean(),pf=g.sum()/-p.sum())
def show(nome,mask,df=base):
    out=[nome]
    for lab,sub in (("treino",df[mask&(df.ano<=2018)]),("valid",df[mask&(df.ano>=2019)])):
        k=m(sub); out.append(f"{lab}: n={k['n']} ac={k['acerto']:.1%} exp={k['exp']:+.3f} pf={k['pf']:.2f}" if k else f"{lab}: -")
    print(" | ".join(out))
T=pd.Series(True,index=base.index)
show("BASE compras",T)
show("MM200 (tendência primária)",base.close>base.sma200)
show("Semanal em alta (múltiplos tempos)",base.wup==True)
show("ADX>20",base.adx>20)
show("ADX>25",base.adx>25)
show("+DI>-DI",base.pdi>base.mdi)
show("Volume c3 > média",base.volr>1)
show("Força relativa top 50%",base.rs>0.5)
show("Força relativa top 30%",base.rs>0.7)
show("Amplitude >50% acima MM200",base.breadth>0.5)
show("Perto da máxima 52s (>90%)",base.hi52>0.9)
show("Não esticado (dist MM20 < 1,5 ATR)",base.dist20<1.5)
show("IFR 50-65",base.ifr<65)
show("IFR > 60",base.ifr>60)
base.to_pickle("data/backtest/base_compras.pkl")
