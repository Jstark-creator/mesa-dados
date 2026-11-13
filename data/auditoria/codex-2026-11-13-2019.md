# Auditoria Codex — 2026-11-13T20:19Z — commit 223506f

Auditei o commit `223506f`, com foco nos dois arquivos solicitados e consulta ao histórico anterior. **Não há cadeias ThetaData nem agregados de `opcoes_reais` disponíveis localmente.** Não acessei a internet nem alterei arquivos do repositório.

Os números abaixo são testes sintéticos em cópias em `/tmp`, não estimativas de impacto histórico. Como falta SciPy no ambiente, fixei as pernas das estruturas nesses testes, verificando apenas execução e contabilização.

### Achados

1. **CRÍTICO — Decide e executa usando o mesmo fechamento.**  
   **Arquivo:** `scripts/lab/etf/matriz_real.py:155–168`; seleção das pernas em `:127–128` e `:91`.  
   O código observa a cotação final, verifica alvo/stop e registra a saída nessa mesma cotação. Também escolhe strikes com spot e bid/ask finais e simula execução nesses preços. Esses valores só ficam definitivamente conhecidos depois do fechamento; faltam snapshots anteriores ou execução posterior à decisão.  
   **Teste sintético:** uma call comprada a US$ 10, com closes posteriores de US$ 21 e US$ 5, gera **+1,098R** no original; decidindo no primeiro fechamento e executando no seguinte, **−0,501R**, com comissões. Isso demonstra a sensibilidade, sem quantificar o viés histórico.

2. **CRÍTICO — Operações sem saída desaparecem da amostra.**  
   **Arquivo:** `scripts/lab/etf/matriz_real.py:68`, `:153–157`, `:169–170`.  
   Cotações com bid zero são eliminadas, inclusive quando uma opção comprada praticamente perdeu todo o valor. Sem todas as pernas cotadas, a gestão pula o dia; chegando ao vencimento ou ao fim dos dados sem saída, a operação inteira é descartada. Isso pode excluir perdas e condiciona a inclusão à disponibilidade futura de cotações.  
   **Teste sintético:** uma entrada válida sem cotação posterior da perna produz **zero operações registradas**. É necessário distinguir posições abertas no fim da amostra de falhas de dados e manter ambas contabilizadas com tratamento explícito.

3. **MÉDIO — Estrutura de crédito pode virar débito e interromper toda a execução.**  
   **Arquivo:** `scripts/lab/etf/matriz_real.py:139–143`, `:162`.  
   A classificação depende do custo depois do spread e das comissões. Uma trava de crédito com spreads largos pode exigir pagamento líquido; o código então procura `alvo` na configuração da trava de crédito, onde essa chave não existe.  
   **Teste sintético:** put vendida com bid/ask **1/3** e comprada com **0,9/2,9** resulta em desembolso natural de **US$ 1,913 por ação**, incluindo comissão, e termina em **`KeyError: 'alvo'`**. Deve rejeitar a montagem incompatível antes de simular.

4. **MÉDIO — Comparação Black-Scholes não controla período nem operações.**  
   **Arquivo:** `scripts/lab/etf/matriz_real.py:189`, `:212–217`.  
   O modelo BS recebe toda a base após o início, sem limitar ao último dia da cadeia real. Meses ausentes também continuam no BS. Além disso, usa entrada no fechamento do sinal e vencimento sintético de 45 dias; o teste real entra depois e escolhe vencimento listado. Portanto, diferenças de média não isolam erro de precificação ou slippage.

5. **MÉDIO — Sobreposição sem controle de capital.**  
   **Arquivo:** `scripts/lab/etf/matriz_real.py:173`.  
   Autoriza nova entrada após cinco datas disponíveis, mesmo com a anterior aberta. Isso pode ser uma política válida, mas faltam limite de posições, margem e capital reservado. A média por operação é descritiva; `total_R` não representa retorno de uma carteira executável, e operações simultâneas são dependentes.

6. **MÉDIO — Downloads incompletos podem gerar relatório sem alerta de cobertura.**  
   **Arquivo:** `scripts/lab/etf/thetadata_baixar.py:76–88`; consumo em `matriz_real.py:117–121`.  
   Falhas e respostas vazias apenas imprimem mensagem e seguem. O backtest aceita os meses restantes e chama de “ontem” a data anterior com dados de opções, mesmo que existam pregões intermediários. Isso altera o sinal efetivamente utilizado. Falta validar cobertura e usar o pregão anterior da base de mercado.

### O que está correto

- Sinal e faixa de IV usam uma data anterior à entrada; não encontrei `bfill` nem percentil calculado sobre toda a amostra nesse fluxo. O percentil herdado é móvel.
- Os lados de compra/venda estão corretos na entrada e na recompra/liquidação; há comissão nas duas pontas para as quantidades atuais, todas unitárias.
- Não há resolução intradiária favorável entre stop e alvo: a gestão usa apenas fechamentos e registra o preço observado, sem limitar artificialmente a perda ao stop.
- Não identifiquei nova divergência com produção: estes arquivos implementam um experimento separado, sem demonstrar equivalência operacional com `opcoes.py`.

## Veredito
Mantém-se a conclusão anterior: ainda falta evidência para transformar essa matriz em playbook.  
O uso de bid/ask reais melhora o modelo, mas não resolve execução causal nem descarte de operações sem saída.  
Sem as cadeias locais, nenhuma rentabilidade histórica nova pôde ser confirmada.  
Resultados positivos precisam ser reavaliados após essas correções e a validação da cobertura.