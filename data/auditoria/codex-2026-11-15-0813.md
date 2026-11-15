# Auditoria Codex — 2026-11-15T08:13Z — commit ea46aef

A reprovação permanece sustentada, mas **a vantagem no “meio” está contaminada por risco minúsculo, spreads e amostras diferentes entre cenários**. Recalculei os agregados de `operacoes.csv` com [script em `/tmp`](/tmp/auditar_m7.py), sem alterar o repositório.

**Limitação:** faltam as cadeias brutas usadas na rodada (`/tmp/td`), e o CSV não contém strikes, bid/ask ou horários. Portanto, não é possível comprovar cotações velhas nem recalcular exatamente um filtro por perna. O pré-registro referenciado pelo código também não está disponível.

### O que está correto

- **Percentil:** [m7.py:199](/home/runner/work/mesa-dados/mesa-dados/scripts/lab/m7/m7.py:199) exclui NaN, compara o valor atual apenas com observações anteriores e mascara dias sem IV. Usa até **252 observações válidas**, com mínimo de 126 anteriores; isso não equivale necessariamente a 252 pregões consecutivos.
- **Causalidade dos sinais:** [m7.py:116](/home/runner/work/mesa-dados/mesa-dados/scripts/lab/m7/m7.py:116) consulta o sinal anterior. HV e tendência podem incluir aquele fechamento, pois a entrada acontece depois. Não encontrei percentil calculado sobre a amostra inteira nem `bfill`.
- **HV:** [m7.py:196](/home/runner/work/mesa-dados/mesa-dados/scripts/lab/m7/m7.py:196) usa retornos logarítmicos do histórico ajustado, coerentemente com o gerador desses dados. Isso evita saltos artificiais de splits.
- **Custos e R:** comissão de US$ 0,65 por contrato em cada ponta está incluída; débito usa prêmio pago como risco, crédito usa largura menos crédito líquido. As perdas efetivas podem ultrapassar o stop: o código não garante artificialmente execução no limiar.

### Achados

**1. CRÍTICO — R minúsculo infla o condor no “meio”.**  
[m7.py:132](/home/runner/work/mesa-dados/mesa-dados/scripts/lab/m7/m7.py:132) aceita qualquer risco positivo, sem verificar consistência econômica das cotações. XLF, entrada **25/08/2025**, registra risco **US$ 1,60**, lucro US$ 32,80 e **+20,50R**.

Retirando apenas essa observação:

| Condor, meio | Original | Sem operação |
|---|---:|---:|
| Média total | +0,261R | +0,111R |
| Validação | +0,357R | +0,037R |
| XLF | +0,792R | +0,112R |

Exigir retrospectivamente risco ≥US$ 50 reduz a média total a **+0,071R**, mas é apenas sensibilidade; esse piso não constitui filtro validado.

**2. CRÍTICO — Cotações sem controle de qualidade distorcem também as perdas.**  
[matriz_real.py:68](/home/runner/work/mesa-dados/mesa-dados/scripts/lab/etf/matriz_real.py:68) exige somente bid positivo e ask ≥ bid; [m7.py:143](/home/runner/work/mesa-dados/mesa-dados/scripts/lab/m7/m7.py:143) liquida pernas independentemente, sem limites econômicos do pacote.

Existem **23 operações abaixo de −1R**, chegando a **−3,47R** no crédito. Pagar spreads excessivos pode produzir essas perdas simuladas, mas não representa o risco máximo do payoff contratado; comissões de saída tampouco explicam tamanha diferença. Isso pode **prejudicar** as estruturas. Como sensibilidade, limitar perdas a −1R elevaria o `meio_50` de −0,193 para **−0,178R** no condor e de −0,186 para **−0,144R** no crédito: continuam negativos. Esse truncamento não substitui reprecificação.

**3. MÉDIO — A diferença entre cenários mistura spread e seleção.**  
[m7.py:110](/home/runner/work/mesa-dados/mesa-dados/scripts/lab/m7/m7.py:110) simula cada cenário separadamente: custos alteram entradas aceitas, saídas e oportunidades posteriores. Há **136 contra 119** condors em meio/meio_50.

Nas **88 entradas coincidentes**, as médias são **+0,121R/−0,187R**. O arrasto mediano de entrada, dividido pelo risco no meio, é **13,2% em XLF**, **14,5% em XLE**, contra **0,2% em SPY**. Isso sustenta forte sensibilidade à liquidez; não prova envelhecimento das cotações.

**Filtro proposto:** exigir por perna `(ask−bid)/mid ≤20%`, bid positivo, horário recente e sincronizado, além de consistência dos preços do pacote com seus limites econômicos. Aplicar na entrada; na saída, prever execução conservadora quando falhar, sem descartar a operação.

O CSV permite apenas uma aproximação: nas entradas pareadas, exigir  
`(risco_meio50−risco_meio)/risco_meio ≤10%`.

| Validação filtrada | N | Meio | Meio_50 |
|---|---:|---:|---:|
| Condor | 26 | +0,041R | −0,048R |
| Crédito | 58 | −0,010R | −0,095R |

São subconjuntos retrospectivos, sem reconstrução da carteira. **Não mudam a reprovação.**

**4. MÉDIO — Saída decidida e executada pela mesma cotação.**  
[m7.py:143](/home/runner/work/mesa-dados/mesa-dados/scripts/lab/m7/m7.py:143) observa o fechamento, verifica alvo/stop e presume execução naquele preço. Falta testar execução posterior à decisão. Sem dados intradiários, não quantifico o efeito.

**5. MÉDIO — Paridade resolve a escala, mas permanece aproximação.**  
[m7.py:25](/home/runner/work/mesa-dados/mesa-dados/scripts/lab/m7/m7.py:25) implementa corretamente a fórmula europeia. ETFs têm opções americanas e dividendos discretos; yields fixos e mids ruins afetam spot, IV e deltas. A correção de splits é coerente, mas não transforma o spot inferido em preço observado.

**6. MÉDIO — Descarte e carteira podem selecionar resultados.**  
[m7.py:153](/home/runner/work/mesa-dados/mesa-dados/scripts/lab/m7/m7.py:153) apaga operações sem saída cotada. [m7.py:227](/home/runner/work/mesa-dados/mesa-dados/scripts/lab/m7/m7.py:227) limita o grupo depois da simulação: operações rejeitadas já bloquearam oportunidades posteriores do ETF. O desempate alfabético também é arbitrário.

## Veredito

As conclusões de **não aprovação** se mantêm nas sensibilidades calculáveis.  
O ganho no “meio”, especialmente em XLF, não demonstra vantagem executável.  
As correções de percentil e HV estão corretas; a paridade melhora a escala, com limitações.  
O efeito exato de um filtro por perna exige as cadeias brutas e nova simulação causal.