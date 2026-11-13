import sys, numpy as np, pandas as pd
sys.path.insert(0,"/home/claude/mesa-dados/scripts")
import backtest_m3 as b
meta,dados=b.carregar()
base=pd.read_pickle("base.pkl")
v2=base[(base.volr>1)&(base.ifr>60)&(base.close>base.sma200)].copy()
H="/home/claude/mesa-dados/data/historico/"
def idx(f):
    d=pd.read_csv(H+f,parse_dates=["data"],index_col="data"); d["sma200"]=d.close.rolling(200).mean(); d["sma50"]=d.close.rolling(50).mean(); return d
IX={"eua":idx("IDX_GSPC.csv"),"br":idx("IDX_BVSP.csv")}
# features bollinger + regime por trade (no c3)
def bb(df):
    mid=df.close.rolling(20).mean(); sd=df.close.rolling(20).std(ddof=0)
    up,lo=mid+2*sd,mid-2*sd; bw=(up-lo)/mid
    return pd.DataFrame({"mid":mid,"up":up,"lo":lo,"pctb":(df.close-lo)/(up-lo),"bwr":bw.rolling(120).rank(pct=True)})
BB={t:bb(df) for t,df in dados.items()}
rows=[]
for k,r in v2.iterrows():
    df=dados[r.ticker]; i4=df.index.get_loc(pd.Timestamp(r.entrada_data)); i3,i2,i1=i4-1,i4-2,i4-3
    d3=df.index[i3]; ix=IX[r.mercado]; ixr=ix.loc[:d3].iloc[-1]
    B=BB[r.ticker]
    rows.append(dict(k=k,reg=ixr.close>ixr.sma200, reg50=ixr.close>ixr.sma50,
        pctb=B.pctb.iloc[i3], squeeze=min(B.bwr.iloc[i1],B.bwr.iloc[i3])<0.25,
        toca_mid=df.low.iloc[i2]<=B.mid.iloc[i2], acima_sup=df.close.iloc[i3]>B.up.iloc[i3]))
v2=v2.join(pd.DataFrame(rows).set_index("k"))
v2.to_pickle("v2.pkl")
exec(open("saidas.py").read().split("sel=base")[0].split("base=pd.read_pickle")[0])
