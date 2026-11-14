# Auditoria Codex — 2026-11-14T14:32Z — commit 12ca672

Reproduzi **exatamente as contagens e os acertos das 768 linhas por ativo**. Não alterei o repositório nem acessei a internet. Os testes ficaram em [/tmp](/tmp/audita_m4.py), com [resultados comparativos](/tmp/m4_audit_summary.csv).

**Não encontrei erro CRÍTICO que explique uma rejeição injusta dos setups.** Há problemas metodológicos e ambiguidades que merecem correção.

### Achados

1. **MÉDIO — Base de tendência não corresponde ao regime dos sinais.**  
   [fase_a.py:109](/home/runner/work/mesa-dados/mesa-dados/scripts/lab/m4/fase_a.py:109) usa `regime == lado`: compra é comparada sempre com dias acima da MM200. Entretanto, **610/863 compras S3 nos EUA** acontecem abaixo dela. Além disso, a agregação pondera a base por quantidade de dias, enquanto os setups têm outra distribuição por ativo. Pareando a expectativa da base por **ativo e regime efetivo de cada sinal**, o lift dessas compras passa de **1,02 para 1,08**; nas vendas S3 BR, de **1,00 para 0,91**. Pode prejudicar ou favorecer; nenhuma aprovação aparece.

2. **MÉDIO — S2 interpreta “toque” de maneira restritiva.**  
   [fase_a.py:47](/home/runner/work/mesa-dados/mesa-dados/scripts/lab/m4/fase_a.py:47) exige que a mínima da compra esteja a até 1 ATR da média. Um candle que atravessa toda essa faixa pode ser excluído mesmo tendo tocado nela. Interpretando toque como interseção do intervalo `[mínima, máxima]` com `MM ± ATR`, compras EUA passam de **3.206 para 4.048 sinais**, com P **27,45% → 28,19%**. Compras BR: **22,55% → 22,76%**. A diferença depende da intenção do pré-registro; não resgata S2.

3. **MÉDIO — σ20 tem uma convenção adicional não explicitada no material disponível.**  
   [fase_a.py:39](/home/runner/work/mesa-dados/mesa-dados/scripts/lab/m4/fase_a.py:39) calcula desvio dos retornos logarítmicos diários e multiplica por **√20**, inclusive no BR, cujo horizonte é 15. Isso representa volatilidade escalada para 20 pregões, não simplesmente volatilidade diária estimada em 20 observações. **Não é possível declarar a fórmula errada sem a definição original.** Como sensibilidade, retirando √20, compras S1 EUA passam de **35,10% para 42,50%**, mas o lift cai de **1,20 para 1,12**, ainda reprovando.

4. **MÉDIO — Treino usa alguns desfechos de 2019.**  
   [fase_a.py:96–99](/home/runner/work/mesa-dados/mesa-dados/scripts/lab/m4/fase_a.py:96) divide pela data do sinal, permitindo que eventos de dezembro de 2018 sejam resolvidos na validação. Purgando os últimos H pregões do treino, vendas S2 EUA passam de **22,36% para 21,51%**; lift **0,94 → 0,92**. É vazamento entre partições, embora não seja lookahead na geração do sinal.

5. **MÉDIO — Universo retrospectivo e pré-registro não verificável.**  
   [Cabeçalho:1](/home/runner/work/mesa-dados/mesa-dados/scripts/lab/m4/fase_a.py:1) referencia `estrategias/m4-preregistro.md`, ausente. [universo_m4.json:2](/home/runner/work/mesa-dados/mesa-dados/config/universo_m4.json:2) registra escolhas em novembro de 2026, depois de quase toda a “validação”. Portanto, 2019+ é uma separação cronológica, **não uma amostra comprovadamente intocada**. Há risco de sobrevivência/seleção retrospectiva; JBSS3 também está sem histórico. Não demonstrei ajuste deliberado de parâmetros.

6. **MÉDIO — Candles locais inconsistentes passam pelo filtro.**  
   [fase_a.py:20](/home/runner/work/mesa-dados/mesa-dados/scripts/lab/m4/fase_a.py:20) verifica apenas fechamento positivo e máxima ≥ mínima. Encontrei **60 candles BR inconsistentes**, todos anteriores a 2017, incluindo cinco aberturas zero. Exemplo: [CMIG4.csv:1514](/home/runner/work/mesa-dados/mesa-dados/data/historico/CMIG4.csv:1514), fechamento **1,8819**, abaixo da mínima **2,1472**. Isso pode distorcer indicadores e barreiras no treino. Sem fonte alternativa local, não inventei preços corrigidos.

7. **BAIXO — Seleção pelo desfecho nas janelas finais incompletas.**  
   [fase_a.py:71–80](/home/runner/work/mesa-dados/mesa-dados/scripts/lab/m4/fase_a.py:71) inclui eventos recentes já resolvidos e exclui os ainda abertos. Exigindo H pregões completos para todos, vendas S1 BR passam de **19,68% para 19,16%**; compras S1 EUA, **35,10% para 35,16%**.

8. **BAIXO — Dependência entre eventos e arredondamento.**  
   [fase_a.py:105](/home/runner/work/mesa-dados/mesa-dados/scripts/lab/m4/fase_a.py:105) aceita sinais sobrepostos: adequado para frequência de eventos, mas N não representa observações independentes. Como sensibilidade, impondo intervalo superior a H entre sinais do mesmo ativo/setup/direção, compras S1 EUA passam de **567 para 393 eventos**, P **35,10% → 32,82%**. [Linhas 123–132](/home/runner/work/mesa-dados/mesa-dados/scripts/lab/m4/fase_a.py:123) também aprovam usando valores arredondados; deveriam usar precisão integral.

### O que está correto

- Indicadores são causais no fechamento; máximas/mínimas de rompimento e volume médio excluem o candle atual. Percentis são móveis, sem amostra futura ou `bfill`.
- Desfechos começam no pregão seguinte; timeout conta como fracasso.
- Stop primeiro não favorece resultados. **Nenhum sinal da validação teve primeiro toque ambíguo**; priorizar a abertura nos gaps não alterou seus acertos.
- OHLC são baixados com ajuste conjunto; isso não prova erro de ajuste.
- Fase A não calcula R, custos ou rentabilidade de opções. Não há produção M4 para comparar.

## Veredito
**A conclusão de nenhum setup aprovado se mantém nas correções e sensibilidades executadas.**  
Não encontrei evidência de que execução pessimista esteja derrubando os setups.  
As probabilidades e lifts precisam das ressalvas acima; “sem aprovação” não demonstra ausência universal de vantagem.  
A validação histórica tampouco comprova desempenho futuro ou rentabilidade em opções.