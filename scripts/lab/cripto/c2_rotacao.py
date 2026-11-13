import sys; sys.path.insert(0, __file__.rsplit('/',1)[0])
from base import *
ALTS=["SOL","BNB","XRP","ADA","DOGE","AVAX","LINK","DOT","LTC","TRX","NEAR","ATOM","UNI","SUI","BCH","XLM"]
C=pd.DataFrame({s:carregar(s).close for s in ALTS+["BTC","ETH"]})
C=C[C.index>="2017-11-09"]
btc=C.BTC; reg=btc>btc.rolling(200).mean()
MOM={l:C/C.shift(l)-1 for l in (14,28,56)}
MM={f:C.rolling(f).mean() for f in (50,100)}
CNT=C.notna().cumsum()
def rot(look=28,top=3,filt=50,regime=True,custo=0.0015,dia=6):
    sem=C.index[(C.index.dayofweek==dia)&(C.index>="2018-07-01")]
    eq=[1.0]; datas=[sem[0]]; cart={}
    for a,b in zip(sem[:-1],sem[1:]):
        mom=MOM[look].loc[a][ALTS]
        ok=(C.loc[a][ALTS]>MM[filt].loc[a][ALTS])&(CNT.loc[a][ALTS]>200)
        cand=mom[ok].dropna()
        novo={}
        if (not regime or reg.loc[a]) and len(cand):
            esc=cand.sort_values(ascending=False).head(top)
            esc=esc[esc>0]
            novo={s:1/top for s in esc.index}
        giro=sum(abs(novo.get(s,0)-cart.get(s,0)) for s in set(novo)|set(cart))
        ret=sum(w*(C.loc[b,s]/C.loc[a,s]-1) for s,w in novo.items())
        eq.append(eq[-1]*(1+ret-giro*custo)); datas.append(b); cart=novo
    return pd.Series(eq,index=datas)
def met(e,ini,fim):
    e=e[(e.index>=ini)&(e.index<=fim)]; e=e/e.iloc[0]
    anos=(e.index[-1]-e.index[0]).days/365.25
    return f"CAGR {((e.iloc[-1])**(1/anos)-1)*100:6.1f}%  DD {((e/e.cummax()-1).min())*100:6.1f}%  x{e.iloc[-1]:.2f}"
bh=C.BTC.resample("W-SUN").last()
print("BTC buy&hold   treino",met(bh,"2018-07-01","2021-12-31"),"| valid",met(bh,"2022-01-01","2026-12-31"))
for look in (14,28,56):
  for top in (1,3,5):
    for filt in (50,100):
      e=rot(look,top,filt)
      print(f"look{look} top{top} mm{filt}: treino {met(e,'2018-07-01','2021-12-31')} | valid {met(e,'2022-01-01','2026-12-31')}")
e=rot(28,3,50,regime=False); print("sem regime BTC:", met(e,'2018-07-01','2021-12-31'),"|",met(e,'2022-01-01','2026-12-31'))
e=rot(28,3,50); e.to_csv("/tmp/rot.csv")
print(e.resample("YE").last().pct_change().round(2))
