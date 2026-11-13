exec(open("opcoes3.py").read().split("for cen,(se,sb)")[0])
def cart(X,risco=2000,inicio=100000,max_pos=10,ano_ini=2021):
    X=X[X.r.notna()&(X.ent.dt.year>=ano_ini)].sort_values("ent")
    eq=inicio; ab=[]; log=[]
    for _,t in X.iterrows():
        for a in sorted([a for a in ab if a["sai"]<t.ent],key=lambda a:a["sai"]): eq+=a["pnl"]; log.append((a["sai"],a["pnl"])); ab.remove(a)
        if len(ab)>=max_pos or sum(a["cap"] for a in ab)+risco>eq: continue
        ab.append({"sai":t.sai,"pnl":risco*t.r,"cap":risco})
    for a in ab: eq+=a["pnl"]; log.append((a["sai"],a["pnl"]))
    L=pd.DataFrame(log,columns=["data","pnl"]); L["ano"]=L.data.dt.year
    e=inicio; out=[]; cur=inicio; pk=inicio; mdd=0
    for _,q in L.sort_values("data").iterrows(): cur+=q.pnl; pk=max(pk,cur); mdd=min(mdd,(cur-pk)/pk)
    for y,g in L.groupby("ano"): ini=e; e+=g.pnl.sum(); out.append(f"{y}:{e/ini-1:+.0%}")
    return " ".join(out)+f" | final R${e:,.0f} | pior queda {mdd:.0%} | ops {len(L)}"
res={}
for se,sb,lab in ((0.05,0.10,"normal"),(0.02,0.02,"boa")):
    X=pd.read_pickle(f"matriz_{se}.pkl")
    C=rodar(se,sb,modo="call")  # call ATM em todos os sinais
    C=C.merge(X[["ticker","ent","ivp"]].dropna(),on=["ticker","ent"],how="left",suffixes=("","_x"))
    def m2(x):
        r=x.r; g=r[r>0]; p=r[r<=0]; return f"n={len(r)} ac={(r>0).mean():.1%} exp={r.mean():+.3f} pf={g.sum()/-p.sum():.2f}"
    B=C[C.ivp<0.40]; Cc=C[C.ivp<0.60]
    print(f"[{lab}] call só IV<40%: {m2(B)} | treino {m2(B[B.ano<=2018])} | valid {m2(B[B.ano>=2019])}")
    print(f"[{lab}] call só IV<60%: {m2(Cc)} | treino {m2(Cc[Cc.ano<=2018])} | valid {m2(Cc[Cc.ano>=2019])}")
    print(f"[{lab}] call IV>=60% (para ver): {m2(C[C.ivp>=0.60])}")
    print(f"[{lab}] CARTEIRA matriz do Gustavo      ", cart(X))
    print(f"[{lab}] CARTEIRA call só IV<40%          ", cart(B))
    print(f"[{lab}] CARTEIRA call só IV<40%, risco R$1.000", cart(B,risco=1000))
