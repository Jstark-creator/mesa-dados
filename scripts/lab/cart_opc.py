exec(open("opcoes2.py").read().split("for nome,kw in")[0])
def cart(X, modo, risco=2000, inicio=100000, max_pos=10, custo_acao=0.03, ano_ini=2021):
    X=X[X.ent.dt.year>=ano_ini].sort_values("ent")
    eq=inicio; ab=[]; log=[]
    for _,t in X.iterrows():
        for a in sorted([a for a in ab if a["sai"]<t.ent],key=lambda a:a["sai"]):
            eq+=a["pnl"]; log.append((a["sai"],a["pnl"])); ab.remove(a)
        if len(ab)>=max_pos: continue
        if modo=="acao":
            notional=risco*t.capital_acao
            if sum(a["cap"] for a in ab)+notional>eq: continue   # sem alavancagem
            ab.append({"sai":t.sai,"pnl":risco*(t.r_acao-custo_acao),"cap":notional})
        else:
            if sum(a["cap"] for a in ab)+risco>eq: continue
            ab.append({"sai":t.sai,"pnl":risco*t.r,"cap":risco})
    for a in ab: eq+=a["pnl"]; log.append((a["sai"],a["pnl"]))
    L=pd.DataFrame(log,columns=["data","pnl"]); L["ano"]=L.data.dt.year
    e=inicio; out=[]; cur=inicio; pk=inicio; mdd=0
    for _,r_ in L.sort_values("data").iterrows(): cur+=r_.pnl; pk=max(pk,cur); mdd=min(mdd,(cur-pk)/pk)
    for y,g in L.groupby("ano"): ini=e; e+=g.pnl.sum(); out.append(f"{y}:{e/ini-1:+.0%}")
    return " ".join(out)+f" | final R${e:,.0f} | pior queda {mdd:.0%} | ops {len(L)}"
A=rodar2(); A["r_acao"]=[None]*len(A)
# r da ação para os mesmos trades
ra=pd.read_pickle("opc.pkl")[["ticker","ent","r_acao"]]
A=A.drop(columns="r_acao").merge(ra,on=["ticker","ent"],how="left").dropna(subset=["r_acao"])
T2=rodar2(slip=0.02).merge(ra,on=["ticker","ent"],how="left")
print("AÇÕES, risco R$1.000/op, sem alavancagem ", cart(A,"acao",risco=1000))
print("AÇÕES, risco R$2.000/op, sem alavancagem ", cart(A,"acao",risco=2000))
print("TRAVAS débito R$2.000, spread 5%/10%      ", cart(A,"opc"))
print("TRAVAS débito R$2.000, spread 2% (só líquidas/ordem no meio)", cart(T2,"opc"))
print("TRAVAS só EUA, spread 2%                  ", cart(T2[T2.mercado=="eua"],"opc"))
