exec(open("hibrido.py").read().split("regras={")[0].replace('print("IV>=40%','pass #').replace('    print(f"  ação IV','    pass #'))
RES=pd.read_pickle("credito_res.pkl")
def cart(T,risco=2000,inicio=100000,max_pos=10,ano_ini=2021):
    T=T[T.ent.dt.year>=ano_ini].sort_values("ent"); eq=inicio; ab=[]; log=[]
    for _,t in T.iterrows():
        for a in sorted([a for a in ab if a["sai"]<t.ent],key=lambda a:a["sai"]): eq+=a["pnl"]; log.append((a["sai"],a["pnl"],a["tipo"])); ab.remove(a)
        if len(ab)>=max_pos or sum(a["cap"] for a in ab)+risco>eq: continue
        ab.append({"sai":t.sai,"pnl":risco*t.r,"cap":risco,"tipo":t.tipo})
    for a in ab: eq+=a["pnl"]; log.append((a["sai"],a["pnl"],a["tipo"]))
    L=pd.DataFrame(log,columns=["data","pnl","tipo"]); L["ano"]=L.data.dt.year
    e=inicio; out=[]; cur=inicio; pk=inicio; mdd=0
    for _,q in L.sort_values("data").iterrows(): cur+=q.pnl; pk=max(pk,cur); mdd=min(mdd,(cur-pk)/pk)
    for y,g in L.groupby("ano"): ini=e; e+=g.pnl.sum(); out.append(f"{y}:{e/ini-1:+.0%}")
    return " ".join(out)+f" | final R${e:,.0f} | pior queda {mdd:.0%} | ops {L.tipo.value_counts().to_dict()}"
for lab in ("normal","boa"):
    J=res[lab]
    C=J[J.ivp<0.4][["ent","sai_call","r_call"]].rename(columns={"sai_call":"sai","r_call":"r"}); C["tipo"]="call"
    for nome in ("Put 0,30/0,15, realiza 50%","Put 0,30/0,15 (fora do dinheiro), saída M3","Call crédito 0,30/0,15 (trava de baixa), saída M3"):
        Pt=RES[(lab,nome)][["ent","sai","r"]].copy(); Pt["tipo"]="credito"
        print(f"[{lab}] calls IV<40% + {nome:48s}", cart(pd.concat([C,Pt])))
    print(f"[{lab}] só calls IV<40% {'':57s}", cart(C))
