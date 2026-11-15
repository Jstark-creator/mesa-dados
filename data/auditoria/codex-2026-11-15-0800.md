# Auditoria Codex — 2026-11-15T08:00Z — commit bf9159a

Auditei `bf9159a`, com foco em `scripts/lab/etf/matriz_real.py` e leitura do histórico anterior. **A correção do commit está correta, mas não resolve limitações relevantes do simulador.**

Não há cadeias brutas da ThetaData nem resultados de `opcoes_reais` disponíveis neste ambiente. Portanto, não reproduzi médias históricas. Os números abaixo são **testes sintéticos de lógica**, executados sobre cópias em `/tmp`. Nenhum arquivo do repositório foi alterado; não acessei a internet.

### Achados

**1. CRÍTICO — A cotação de fechamento determina a saída e também seu preço de execução.**  
Arquivo: [matriz_real.py:160](/home/runner/work/mesa-dados/mesa-dados/scripts/lab/etf/matriz_real.py:160), condições nas linhas 165–170.

O simulador observa o valor final da estrutura, verifica alvo/stop e registra a liquidação nessa mesma cotação. Isso pressupõe conseguir negociar depois de conhecer a informação que dispara a decisão. Cotações diárias finais não demonstram essa possibilidade; seriam necessários dados anteriores ao encerramento ou execução posterior.

Em exemplo sintético, uma call entra por US$1,00, alcança US$2,20 no fechamento seguinte e depois cai para US$0,40. Com comissões:

- Código atual: **+1,179R**.
- Cópia com execução no fechamento seguinte à decisão: **−0,609R**.

Isso demonstra sensibilidade à sequência temporal, não estima o impacto histórico. A montagem por delta com o spot e a cadeia do próprio fechamento também pressupõe seleção e execução simultâneas, nas linhas 127–132.

**2. MÉDIO — Operações executadas podem desaparecer por falta de cotação de saída.**  
Arquivo: [matriz_real.py:155](/home/runner/work/mesa-dados/mesa-dados/scripts/lab/etf/matriz_real.py:155), linhas 157–172.

Sem cotação de alguma perna, o código pula o dia. Se não encontrar saída antes do vencimento ou do fim da amostra, descarta a operação inteira. Não registra posição aberta, pendência de dados ou liquidação no vencimento.

O filtro `bid > 0`, na linha 68, agrava o problema: uma opção comprada praticamente sem valor pode justamente perder sua cotação válida. A seleção da amostra passa a depender do que aconteceu depois da entrada; o sentido líquido do viés exige os dados brutos.

Teste sintético: **uma entrada executada, nenhuma saída cotada → zero operações reportadas**. Essa pendência já constava no histórico para M7 e também existe neste simulador.

**3. MÉDIO — Cinco pregões entre entradas não impedem posições sobrepostas.**  
Arquivo: [matriz_real.py:175](/home/runner/work/mesa-dados/mesa-dados/scripts/lab/etf/matriz_real.py:175).

`prox` depende da entrada anterior, sem considerar sua saída. Logo, o mesmo ativo e a mesma estratégia podem acumular posições enquanto as anteriores continuam abertas.

Em teste sintético com preços constantes: **seis operações encerradas, até quatro simultâneas**. Na cópia que também aguarda a saída anterior: **duas operações, máximo de uma simultânea**.

Sobreposição pode ser uma escolha válida, mas exige capital e limite de exposição explícitos. A soma de R reportada não representa retorno de uma carteira com capital fixo, e as operações não são observações independentes.

**4. MÉDIO — A comparação Black-Scholes não garante o “mesmo período”.**  
Arquivo: [matriz_real.py:215](/home/runner/work/mesa-dados/mesa-dados/scripts/lab/etf/matriz_real.py:215), linhas 216–219.

O comparador recebe toda a `base` e é filtrado apenas por `entrada >= inicio`. Não há corte no último dia disponível da cadeia real. Se o cache de opções terminar antes dos preços locais, o modelo inclui um período adicional.

Além disso, `M.simular` executa no dia do sinal, enquanto a matriz real usa o sinal anterior; os vencimentos também diferem: prazo sintético fixo versus vencimento listado. A diferença entre médias mistura execução, datas e contratos com o efeito do modelo de preços.

### O que está correto

- **O commit acerta ao identificar débito/crédito pela estrutura**, evitando tratar crédito líquido negativo após custos como uma compra.
- Sinais e faixa de IV usam a observação anterior à entrada. O percentil herdado é móvel e retrospectivo; não encontrei percentil calculado sobre toda a amostra nem `bfill`.
- Compra no ask/venda no bid e operações inversas na saída estão coerentes no cenário natural.
- Há comissão na entrada e na saída; o resultado desconta ambas.
- Stops são avaliados pelo preço observado, sem limitar artificialmente a perda ao gatilho. Não há desempate intradiário entre stop e alvo favorecendo o resultado.

## Veredito
A correção pontual do commit se mantém e melhora a classificação das estruturas.  
A matriz ainda não demonstra vantagem executável: temporalidade das saídas e descarte de posições comprometem essa interpretação.  
Não há dados brutos locais para quantificar quanto as médias históricas mudariam.  
A conclusão anterior de “vantagem não demonstrada” permanece; a alteração auditada não modifica o simulador próprio da M7.