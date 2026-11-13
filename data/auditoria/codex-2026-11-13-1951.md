# Auditoria Codex — 2026-11-13T19:51Z — commit 7eeed31

Auditoria feita apenas com dados locais, sem alterar o repositório. Reproduzi **E1 +0,451R/op, 37,4R, 83 operações** e **E2 +0,940R/op, 79,0R, 84 operações**, com custo 2× e slippage. Consultei o histórico anterior.

### Achados

1. **CRÍTICO — E2 escolhe ordens usando os rompimentos que aconteceram no dia.**  
   [c3_ordens_stop.py:93](/home/runner/work/mesa-dados/mesa-dados/scripts/lab/cripto/c3_ordens_stop.py:93), com [c2_alts.py:20](/home/runner/work/mesa-dados/mesa-dados/scripts/lab/cripto/c2_alts.py:20).  
   A carteira ordena por momentum **somente os ativos que efetivamente tocaram a entrada naquele dia**. Essa lista não existe quando as ordens são programadas em t−1. Identifiquei 12 datas nos cinco anos com mais entradas candidatas que vagas disponíveis. Seria necessário reservar vagas antes dos toques ou modelar sua sequência intradiária. Além disso, operações rejeitadas continuam bloqueando novos sinais no simulador individual até sua saída hipotética. Portanto, filtrar operações depois não reproduz fielmente uma carteira. A direção do efeito é incerta.

2. **CRÍTICO — ETFs decidem com o fechamento completo e executam nesse mesmo fechamento.**  
   [matriz.py:54](/home/runner/work/mesa-dados/mesa-dados/scripts/lab/etf/matriz.py:54), linhas 63–79 e 92–101.  
   Sinais, strikes, IV e gatilhos de saída usam dados finais do próprio dia. “Última hora” não fornece antecipadamente esses valores. É antecipação operacional, embora os indicadores não consultem dias futuros. Em uma variante causal em `/tmp`, selecionei sinal/strikes no fechamento anterior, entrei no fechamento seguinte e executei saídas um fechamento após o gatilho:

   | Validação 2019+, slippage 2% | Original → variante |
   |---|---:|
   | Débito 0,50/0,25; tendência, IV baixa | +0,166 → +0,172R |
   | Crédito put 0,30/0,15; tendência, IV baixa | +0,049 → +0,056R |
   | Condor; IV alta | +0,068 → +0,063R |

   A correção não destruiu essas médias; tampouco comprova preenchimento real.

3. **MÉDIO — Aquecimento duplicado no E2 stop.**  
   [c3_ordens_stop.py:25](/home/runner/work/mesa-dados/mesa-dados/scripts/lab/cripto/c3_ordens_stop.py:25), linha 91.  
   São retirados 200 candles e depois ignorados outros 201, apesar de os indicadores já estarem calculados. A comparação com fechamento usa históricos distintos. Corrigindo apenas isso: **+0,940→+0,887R/op; 79,0→75,4R; 84→85 operações**.

4. **MÉDIO — A comparação cripto muda mais que a execução.**  
   [c3_ordens_stop.py:34](/home/runner/work/mesa-dados/mesa-dados/scripts/lab/cripto/c3_ordens_stop.py:34), linhas 54 e 67; [c1_sistemas.py:10](/home/runner/work/mesa-dados/mesa-dados/scripts/lab/cripto/c1_sistemas.py:10).  
   Stop programado ancora o risco no preenchimento; fechamento ancora o stop no fechamento do sinal. Além disso, stop exclui posições abertas, enquanto o motor de fechamento liquida artificialmente no último candle. As saídas por fechamento também usam o próprio close, enquanto [cripto.py:85](/home/runner/work/mesa-dados/mesa-dados/scripts/cripto.py:85) registra abertura seguinte. Assim, os resultados não isolam o benefício de trocar o tipo de ordem.

5. **MÉDIO — “IV real” não significa preço real de opções.**  
   [matriz.py:24](/home/runner/work/mesa-dados/mesa-dados/scripts/lab/etf/matriz.py:24), linhas 35 e 50.  
   Black-Scholes europeu sem dividendos usa um índice de volatilidade de 30 dias como superfície plana para todos os strikes e vencimentos. Não há skew, exercício americano ou cotações negociáveis. O arredondamento por 0,5% do spot também cria strikes potencialmente inexistentes. Vantagens de poucos centésimos de R permanecem dependentes dessas aproximações.

6. **MÉDIO — Sobreposição e seleção limitam a evidência dos ETFs.**  
   [matriz.py:104](/home/runner/work/mesa-dados/mesa-dados/scripts/lab/etf/matriz.py:104), linhas 112–121.  
   Entradas a cada cinco pregões permitem várias posições simultâneas: na trava débito em tendência, houve pico de **quatro por ETF**; 240 de 261 entradas do SPY ocorreram com posição anterior ainda aberta. Isso não invalida a média por operação, mas impede tratar operações como independentes ou somar R como retorno de carteira. Escolher vencedores entre sinais, estruturas e faixas olhando 2019+ reutiliza a validação.

7. **BAIXO — Percentil e limite de perda precisam de ajustes.**  
   [matriz.py:57](/home/runner/work/mesa-dados/mesa-dados/scripts/lab/etf/matriz.py:57): compara o valor atual com **251**, não 252 observações anteriores; não usa a amostra inteira.  
   [matriz.py:101](/home/runner/work/mesa-dados/mesa-dados/scripts/lab/etf/matriz.py:101): limita artificialmente perdas de crédito a −1R, desconsiderando eventual custo adicional de recompra. **Remover esse teto não mudou esta amostra.**

### O que está correto

- Cripto: canais deslocados; ATR, MM200, regime BTC e momentum usam t−1. Gaps recebem preenchimento adverso. Entrada e stop no mesmo candle são tratados conservadoramente. Ativar também o canal no dia da entrada não mudou os resultados.
- ETFs: fórmulas BS e inversão de delta estão corretas sob suas hipóteses. Risco de débito e largura menos crédito estão corretos antes dos custos adicionais de saída. Slippage incide **nos dois lados**, sobre o preço líquido. Não há `bfill`.
- Cripto cobra custos nos dois lados e impõe piso de risco de 0,3%. Funding realizado dos shorts permanece ausente; o universo fixo de alts mantém o risco de sobrevivência já registrado.

## Veredito

As médias cripto alegadas são reproduzíveis, mas a carteira E2 exige correção causal antes de ser validada.  
Os ETFs preservam médias positivas pequenas após a variante de execução causal; continuam dependentes da precificação sintética.  
A 10% ainda existem células positivas: “quase nada sobrevive” descreve fragilidade econômica, não ausência de médias positivas.  
Os dois estudos sustentam investigação adicional, ainda sem evidência suficiente para virar playbook.