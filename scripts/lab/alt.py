exec(open("hibrido.py").read().split("regras={")[0].replace('print("IV>=40%','pass #').replace('    print(f"  ação IV','    pass #'))
# call ITM delta 0,70 para a faixa 40-60%
src=open("opcoes3.py").read()
exec(src.split("def rodar(")[0].replace('''    if est=="call":
        K1=strike_delta(S0,T0,r,v0,0.50,st)''','''    if est in ("call","call70"):
        K1=strike_delta(S0,T0,r,v0,0.70 if est=="call70" else 0.50,st)'''))
for lab,(se,sb) in (("normal",(0.05,0.10)),("boa",(0.02,0.02))):
    out=[trade(r.ticker,r.entrada_data,r.atr,r.mercado,se if r.mercado=="eua" else sb,"call70") for _,r in sel.iterrows()]
    C7=pd.DataFrame([x for x in out if x and "r" in x])[["ticker","ent","r","sai"]].rename(columns={"r":"r_c70","sai":"sai_c70"})
    res[lab]=res[lab].merge(C7,on=["ticker","ent"],how="left")
J=res["normal"]; f=J[(J.ivp>=0.4)&(J.ivp<=0.6)]
print("faixa IV 40-60%  call delta 0,70:",m(f.r_c70.dropna()),"| treino",m(f[f.ano<=2018].r_c70.dropna()),"| valid",m(f[f.ano>=2019].r_c70.dropna()))
def cart2(J,regra,risco=2000,inicio=100000,max_pos=10,max_acoes=99,custo_acao=0.03,ano_ini=2021):
    X=J[J.ent.dt.year>=ano_ini].sort_values("ent"); eq=inicio; ab=[]; log=[]; capmax=0
    for _,t in X.iterrows():
        for a in sorted([a for a in ab if a["sai"]<t.ent],key=lambda a:a["sai"]): eq+=a["pnl"]; log.append((a["sai"],a["pnl"],a["tipo"])); ab.remove(a)
        tipo=regra(t)
        if tipo is None or len(ab)>=max_pos: continue
        if tipo=="call": cap,pnl,sai=risco,risco*t.r_call,t.sai_call
        elif tipo=="c70":
            if pd.isna(t.r_c70): continue
            cap,pnl,sai=risco,risco*t.r_c70,t.sai_c70
        else:
            if sum(1 for a in ab if a["tipo"]=="acao")>=max_acoes: continue
            cap,pnl,sai=risco*t.cap,risco*(t.r_acao-custo_acao),t.sai_acao
        if sum(a["cap"] for a in ab)+cap>eq: continue
        ab.append({"sai":sai,"pnl":pnl,"cap":cap,"tipo":tipo}); capmax=max(capmax,sum(a["cap"] for a in ab))
    for a in ab: eq+=a["pnl"]; log.append((a["sai"],a["pnl"],a["tipo"]))
    L=pd.DataFrame(log,columns=["data","pnl","tipo"]); L["ano"]=L.data.dt.year
    e=inicio; out=[]; cur=inicio; pk=inicio; mdd=0
    for _,q in L.sort_values("data").iterrows(): cur+=q.pnl; pk=max(pk,cur); mdd=min(mdd,(cur-pk)/pk)
    for y,g in L.groupby("ano"): ini=e; e+=g.pnl.sum(); out.append(f"{y}:{e/ini-1:+.0%}")
    return " ".join(out)+f" | final R${e:,.0f} | pior queda {mdd:.0%} | capital máx. preso R${capmax:,.0f}"
R={"Só calls (IV<40%)":(lambda t:"call" if t.ivp<0.4 else None,{}),
   "Híbrido (ação ilimitada na faixa 40-60%)":(lambda t:"call" if t.ivp<0.4 else ("acao" if t.ivp<=0.6 else None),{}),
   "Híbrido com no máx. 2 ações abertas":(lambda t:"call" if t.ivp<0.4 else ("acao" if t.ivp<=0.6 else None),{"max_acoes":2}),
   "Call ATM IV<40% + call delta 0,70 IV 40-60%":(lambda t:"call" if t.ivp<0.4 else ("c70" if t.ivp<=0.6 else None),{})}
for lab in ("normal","boa"):
    print(f"\n=== execução {lab} ===")
    for n,(f_,kw) in R.items(): print(f"{n:46s}",cart2(res[lab],f_,**kw))
