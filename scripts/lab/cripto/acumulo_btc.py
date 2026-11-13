import sys; sys.path.insert(0, __file__.rsplit('/',1)[0])
from base import *
b=carregar("BTC"); c=b.close; mayer=c/c.rolling(200).mean()
fg=pd.read_csv(DIR/"fear_greed.csv",parse_dates=["data"]).set_index("data").fg.reindex(c.index).ffill()
def sim(regra,ini,aporte=100.0,custo=0.002):
    dias=c.index[(c.index>=ini)&(c.index.dayofweek==0)]
    btc=0.0; caixa=0.0; total=0.0
    for d in dias:
        caixa+=aporte; total+=aporte
        m=regra(d)
        quero=min(caixa, aporte*m)
        btc+=quero*(1-custo)/c[d]; caixa-=quero
    px=c.iloc[-1]
    return dict(investido=round(total), btc=round(btc,4), preco_medio=round((total-caixa)/btc), caixa=round(caixa), valor=round(btc*px+caixa), mult=round((btc*px+caixa)/total,2))
def m_mayer(d):
    x=mayer[d]
    return 3 if x<0.8 else 2 if x<1.0 else 1 if x<1.5 else 0.5 if x<2.4 else 0
def m_fg(d):
    x=fg[d]
    if pd.isna(x): return 1
    return 2.5 if x<20 else 1.5 if x<40 else 1 if x<60 else 0.5 if x<80 else 0.25
def m_comb(d):
    return (m_mayer(d)+m_fg(d))/2
for ini in ("2018-03-01","2020-01-01","2022-01-01"):
    print("== início",ini)
    for nome,f in (("DCA fixo",lambda d:1),("Mayer",m_mayer),("Fear&Greed",m_fg),("Mayer+F&G",m_comb)):
        print(f"{nome:12s}",sim(f,ini))
print("hoje: mayer",round(mayer.iloc[-1],2),"F&G",fg.iloc[-1], "multiplicador combinado", m_comb(c.index[-1]))
