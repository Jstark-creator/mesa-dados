"""Diretriz 4: E1/E2 executadas por ORDENS STOP programadas (sem esperar o fechamento).

Variante "stop":
- Uma vez por dia (após o fechamento do candle t-1) o Gustavo programa as ordens para o dia t.
- Entrada long: se close[t-1] > MM200[t-1], ordem stop de compra em hi20[t] (máxima dos 20 dias até t-1).
  Preenche em max(open[t], hi20[t]) quando high[t] >= hi20[t].
- Stop inicial: entrada − 2×ATR14[t-1]. Saída: ordem stop em max(stop inicial, lo20[t]) (atualizada 1x/dia);
  preenche em min(open, nível). No dia da entrada, se low[t] <= stop, assume stopado (conservador:
  a ordem intradiária é desconhecida).
- Short espelhado (close[t-1] < MM200; stop de venda em lo20[t]; saída em hi10[t]).
Compara com a regra atual (sinal no fechamento, entra na abertura seguinte), com custo 1x e 2x.
"""
import sys; sys.path.insert(0, __file__.rsplit('/',1)[0])
from base import *
from c1_sistemas import rodar, saida_trail_don
from c2_alts import ALTS, limitar

def sim_stop(d, lado, n_ent, n_sai, custo, sym, regime_extra=None, k=2.0, slip=0.0):
    o,h,l,c = d.open.values,d.high.values,d.low.values,d.close.values
    mm,atr_ = d.mm200.values,d.atr.values
    ent_nv = (d[f"hi{n_ent}"] if lado==1 else d[f"lo{n_ent}"]).values
    sai_nv = (d[f"lo{n_sai}"] if lado==1 else d[f"hi{n_sai}"]).values
    reg = None if regime_extra is None else regime_extra.reindex(d.index).fillna(False).values
    m28 = (d.close/d.close.shift(28)-1).values
    out=[]; n=len(d); t=201
    while t < n:
        ok = np.isfinite(mm[t-1]) and np.isfinite(ent_nv[t]) and np.isfinite(atr_[t-1])
        ok = ok and ((c[t-1]>mm[t-1]) if lado==1 else (c[t-1]<mm[t-1]))
        if reg is not None: ok = ok and reg[t-1]
        # ordem só é colocada se o preço ainda não passou do nível no fechamento anterior
        toca = ok and ((h[t]>=ent_nv[t]) if lado==1 else (l[t]<=ent_nv[t]))
        if not toca: t+=1; continue
        ent = max(o[t],ent_nv[t])*(1+slip) if lado==1 else min(o[t],ent_nv[t])*(1-slip)
        stop0 = ent - lado*k*atr_[t-1]; risco = abs(ent-stop0)
        if risco <= ent*0.003: t+=1; continue
        px=None; j=t
        while j < n:
            nivel = stop0
            if j>t and np.isfinite(sai_nv[j]):
                nivel = max(stop0,sai_nv[j]) if lado==1 else min(stop0,sai_nv[j])
            if lado==1 and l[j]<=nivel:
                px = (min(o[j],nivel) if j>t else nivel)*(1-slip); break
            if lado==-1 and h[j]>=nivel:
                px = (max(o[j],nivel) if j>t else nivel)*(1+slip); break
            j+=1
        aberta = px is None
        if aberta: j=n-1; px=c[j]
        r = ((px-ent)*lado - custo*(ent+px))/risco
        out.append(dict(sym=sym,lado=lado,entrada=d.index[t],saida=d.index[j],pe=ent,ps=px,dias=j-t,r=r,aberta=aberta,m28=m28[t-1]))
        t = j+1
    return pd.DataFrame(out)

def resumo(T, nome):
    T=T[~T.aberta] if "aberta" in T else T
    linhas=[]
    for rot,ini,fim in (("treino",None,"2021-12-31"),("valid 2022+","2022-01-01",None),("5 anos","2021-11-13",None),("2 anos","2024-11-13",None)):
        s=stats(T,nome,ini,fim)
        t=T[(T.entrada>=(ini or "1900"))&(T.entrada<=(fim or "2100"))]
        sem3 = round(t.r.sum()-t.r.nlargest(3).sum(),1) if len(t)>3 else None
        linhas.append(f"  {rot:12s} n={s['n']:3d} ac={s.get('acerto')} med={s.get('media_R')} tot={s.get('total_R')} dd={s.get('dd_R')} sem3={sem3}")
    print(nome); print("\n".join(linhas))

def e1_fech(mult):
    ts=[]
    for s in ["BTC","ETH"]:
        d=ind(carregar(s)); c=d.close
        ts.append(rodar(d,s,"long",1,(c>d.mm200)&(c>d.hi20),2.0,saida_trail_don(20),CUSTO_SPOT*mult,False))
        ts.append(rodar(d,s,"short",-1,(c<d.mm200)&(c<d.lo20),2.0,saida_trail_don(10),CUSTO_FUT*mult,False))
    return pd.concat(ts).sort_values("entrada")
def e1_stop(mult, slip=0.0):
    ts=[]
    for s in ["BTC","ETH"]:
        d=ind(carregar(s))
        ts.append(sim_stop(d,1,20,20,CUSTO_SPOT*mult,s,slip=slip).assign(sist="long"))
        ts.append(sim_stop(d,-1,20,10,CUSTO_FUT*mult,s,slip=slip).assign(sist="short"))
    return pd.concat(ts).sort_values("entrada")
def e2_fech(mult):
    btc=ind(carregar("BTC")); ts=[]
    for s in ALTS:
        d=ind(carregar(s)); d=d.iloc[200:] if len(d)>200 else d.iloc[0:0]; c=d.close
        b=(btc.close>btc.mm200).reindex(d.index).fillna(False)
        t=rodar(d,s,"alt",1,(c>d.mm200)&(c>d.hi20)&b,2.0,saida_trail_don(20),CUSTO_SPOT*mult,False)
        if len(t): t["m28"]=(c/c.shift(28)-1).shift(1).reindex(t.entrada).values
        ts.append(t)
    return limitar(pd.concat(ts).sort_values(["entrada","m28"],ascending=[True,False],kind="mergesort"),3)
def e2_stop(mult, slip=0.0):
    btc=ind(carregar("BTC")); reg=btc.close>btc.mm200; ts=[]
    for s in ALTS:
        d=ind(carregar(s))
        if len(d)<=200: continue
        d=d.iloc[200:]
        ts.append(sim_stop(d,1,20,20,CUSTO_SPOT*mult,s,regime_extra=reg,slip=slip))
    return limitar(pd.concat(ts).sort_values(["entrada","m28"],ascending=[True,False],kind="mergesort"),3)

if __name__=="__main__":
    for mult in (1,2):
        print(f"\n===== CUSTO {mult}x =====")
        resumo(e1_fech(mult),"E1 fechamento (regra atual)")
        resumo(e1_stop(mult),"E1 ordens stop")
        resumo(e1_stop(mult,slip=0.002),"E1 ordens stop + 0,2% de slippage em cada stop")
        resumo(e2_fech(mult),"E2 fechamento (regra atual)")
        resumo(e2_stop(mult),"E2 ordens stop")
        resumo(e2_stop(mult,slip=0.004),"E2 ordens stop + 0,4% de slippage em cada stop")
    T=e1_stop(2,0.002); T=T[~T.aberta]
    for s in ("long","short"):
        resumo(T[T.sist==s],f"E1 stop 2x custo — {s}")
