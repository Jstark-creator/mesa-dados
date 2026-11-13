exec(open("opcoes3.py").read().split("for cen,(se,sb)")[0])
# dados por sinal: ivp, r da call ATM, r da ação, capital por unidade de risco da ação
rows=[]
for _,s in sel.iterrows():
    df=dados[s.ticker]; i4=df.index.get_loc(pd.Timestamp(s.entrada_data)); c1,c2,c3=i4-3,i4-2,i4-1
    o,l=df.open.to_numpy(),df.low.to_numpy(); c=df.close.to_numpy()
    gat=o[c1]; S0=o[i4] if (c[c3]>gat or o[i4]>=gat) else gat; stop=l[c2]-0.5*s.atr
    rows.append(dict(ticker=s.ticker,ent=pd.Timestamp(s.entrada_data),ivp=HV[s.ticker][1].iloc[c3],cap=S0/(S0-stop) if S0>stop else np.nan))
I=pd.DataFrame(rows)
A=pd.read_pickle("opc.pkl")[["ticker","ent","r_acao","sai"]].rename(columns={"sai":"sai_acao"})
res={}
for se,sb,lab in ((0.05,0.10,"normal"),(0.02,0.02,"boa")):
    C=rodar(se,sb,modo="call")[["ticker","ent","r","sai","mercado","ano"]].rename(columns={"r":"r_call","sai":"sai_call"})
    J=I.merge(A,on=["ticker","ent"]).merge(C,on=["ticker","ent"]).dropna(subset=["ivp","r_acao","r_call","cap"])
    res[lab]=J
J=res["normal"]
def m(r): g=r[r>0]; p=r[r<=0]; return f"n={len(r)} ac={(r>0).mean():.1%} exp={r.mean():+.3f} pf={g.sum()/-p.sum():.2f}"
alto=J[J.ivp>=0.40]
print("IV>=40%  AÇÃO :",m(alto.r_acao),"| treino",m(alto[alto.ano<=2018].r_acao),"| valid",m(alto[alto.ano>=2019].r_acao))
print("IV>=40%  CALL :",m(alto.r_call))
for faixa,s in (("40-60%",J[(J.ivp>=0.4)&(J.ivp<=0.6)]),(">60%",J[J.ivp>0.6])): print(f"  ação IV {faixa}:",m(s.r_acao),"| treino",m(s[s.ano<=2018].r_acao),"| valid",m(s[s.ano>=2019].r_acao))
def cart(J,regra,risco=2000,inicio=100000,max_pos=10,custo_acao=0.03,ano_ini=2021):
    X=J[J.ent.dt.year>=ano_ini].sort_values("ent"); eq=inicio; ab=[]; log=[]
    for _,t in X.iterrows():
        for a in sorted([a for a in ab if a["sai"]<t.ent],key=lambda a:a["sai"]): eq+=a["pnl"]; log.append((a["sai"],a["pnl"],a["tipo"])); ab.remove(a)
        tipo=regra(t)
        if tipo is None or len(ab)>=max_pos: continue
        if tipo=="call": cap,pnl,sai=risco,risco*t.r_call,t.sai_call
        else: cap,pnl,sai=risco*t.cap,risco*(t.r_acao-custo_acao),t.sai_acao
        if sum(a["cap"] for a in ab)+cap>eq: continue
        ab.append({"sai":sai,"pnl":pnl,"cap":cap,"tipo":tipo})
    for a in ab: eq+=a["pnl"]; log.append((a["sai"],a["pnl"],a["tipo"]))
    L=pd.DataFrame(log,columns=["data","pnl","tipo"]); L["ano"]=L.data.dt.year
    e=inicio; out=[]; cur=inicio; pk=inicio; mdd=0
    for _,q in L.sort_values("data").iterrows(): cur+=q.pnl; pk=max(pk,cur); mdd=min(mdd,(cur-pk)/pk)
    for y,g in L.groupby("ano"): ini=e; e+=g.pnl.sum(); out.append(f"{y}:{e/ini-1:+.0%}")
    mix=L.tipo.value_counts().to_dict()
    return " ".join(out)+f" | final R${e:,.0f} | pior queda {mdd:.0%} | ops {mix}"
regras={"Só call (IV<40%)":lambda t:"call" if t.ivp<0.4 else None,
        "HÍBRIDO: call IV<40% + ação IV≥40%":lambda t:"call" if t.ivp<0.4 else "acao",
        "Híbrido: call IV<40% + ação IV 40–60%":lambda t:"call" if t.ivp<0.4 else ("acao" if t.ivp<=0.6 else None),
        "Só ação (todos os sinais)":lambda t:"acao"}
for lab in ("normal","boa"):
    print(f"\n=== execução {lab} | risco R$2.000 ===")
    for n,f in regras.items(): print(f"{n:42s}", cart(res[lab],f))
print("\n=== execução normal | risco R$1.000 ===")
for n,f in regras.items(): print(f"{n:42s}", cart(res["normal"],f,risco=1000))
