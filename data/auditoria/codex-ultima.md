# Auditoria Codex — 2026-11-13T19:28Z — commit 4ddd57d

## Reprodução e limites

Auditoria exclusivamente local; testes em `/tmp`, sem alterar arquivos versionados. Comparei com o resumo de Claude em `data/auditoria/historico.md`; o relatório completo citado nele não está disponível.

De 13/11/2021 até o último candle fechado, 12/11/2026:

| Estratégia | Operações | Média líquida |
|---|---:|---:|
| E1: long spot + short futuros | 63 | **+0,728R** |
| E1: ambos em futuros, com funding do modelo | 63 | **+0,654R** |
| E2: spot, três vagas | 66 | **+1,149R** |

Portanto, reproduzi os números solicitados, mas **+0,73R corresponde à versão com long spot**.

## Achados

1. **CRÍTICO — informação futura na precificação da saída das opções.**  
   `scripts/lab/opcoes3.py:78` e `credito.py:35–36`: stops/alvos intradiários são precificados com HV que incorpora o **fechamento posterior daquele dia**. Na seleção reconstruída, calls IVP<40%, desde 2021, custos de 5% EUA/10% BR: substituir somente a HV de saída pela disponível no dia anterior reduz **+0,133R para +0,073R**, em 376 operações. É teste causal aproximado, não reconstrução da IV intradiária real. `credito.py:31` também decide realizar pelo fechamento e executa nesse mesmo fechamento.

2. **CRÍTICO — correção de “acionado” da M3 está incompleta.**  
   `scripts/m3.py:222–226,255–257`: o caso c3 agora usa fechamento como proxy da próxima abertura, corrigindo parte do problema; no caso c4, porém, ainda informa `max(gatilho, abertura_c4)` **depois de c4 terminar**, sem verificar se o stop já ocorreu. Exemplo reproduzido: **AAPL, 12/07/2011**, entrada 10,6000, stop 10,4224, mínima 10,4192; detector ainda devolve “acionado”. A sequência intradiária é indeterminada, mas o sinal não pode ser tratado como entrada nova executável naquele preço.

3. **MÉDIO — fechamento executável e divergência cripto.**  
   `scripts/lab/cripto/c1_sistemas.py:19–22` executa no fechamento que confirma a saída; `scripts/cripto.py:78–84` prevê abertura seguinte. Trocar apenas o preço pela abertura seguinte quase não altera esta amostra: E2 **1,148558→1,148594R**. Isso não valida toda a máquina de estados. `estado():68–69` também não aplica o piso de risco de 0,3% existente no laboratório e em `trades_sistema()`.

4. **MÉDIO — seleção herdada e sobreposição em opções.**  
   `scripts/lab/murphy.py:41–48` seleciona compras de uma simulação v1 que também operava vendas; filtros e saídas são modificados posteriormente. Assim, operações rejeitadas pela v2 continuam influenciando quais sinais existem. `opcoes3.py:84`, `opcoes4.py:5–8` e `cart_cred.py:5–8` não impedem posições simultâneas no mesmo ticker. Encontrei **17 entradas sobrepostas** nas 376 calls reconstruídas.

5. **MÉDIO — execução e dimensionamento otimistas em produção.**  
   `scripts/opcoes.py:54–59,88–99,107–129`: aceita último negócio sem bid/ask válido, seleciona delta sem exigir liquidez e dimensiona pelo meio do spread. Comprar no ask ou montar crédito nos lados executáveis aumenta o risco. Além disso, `scripts/atualizar_dados.py:150` passa a **entrada do sinal** como spot para calcular deltas da cadeia atual; deveria usar preço contemporâneo.

6. **MÉDIO — percentil real não equivale ao laboratório.**  
   `scripts/opcoes.py:171–176`: usa fração estritamente inferior; laboratório usa `rolling.rank(pct=True)`. Com 120 IVs iguais, produção retorna **0%**, laboratório **50,4%**: pode trocar “fora” por call. Reprocessar data antiga também inclui observações posteriores, pois falta filtrar `data <= dia`.

7. **MÉDIO — risco das carteiras e experimento auxiliar.**  
   `opcoes4.py:12` e `cart_cred.py:12` calculam drawdown apenas com resultados realizados, sem marcar posições abertas. `scripts/lab/cripto/c2_rotacao.py:18–24` escolhe carteira usando fechamento e compra nesse mesmo fechamento. Sobreajuste permanece explícito em `c1_grade.py`, que ordena parâmetros pelo resultado de validação.

## Sensibilidade das opções

Não existe `v2r.pkl`, exigido em `opcoes3.py:9`. Reconstruí 2.291 sinais pelo caminho v1→filtros v2.1; **não afirmo reprodução exata do artefato ausente**.

Média R desde 2021; slippage aplicado por lado, igual nos dois mercados:

| IV/HV | Call: 2% / 5% / 10% | Put 0,30/0,15, realiza 50%: 2% / 5% / 10% |
|---|---|---|
| 1,1 | +0,234 / +0,162 / +0,051 | +0,038 / +0,018 / −0,020 |
| 1,3 | +0,168 / +0,100 / −0,005 | +0,064 / +0,040 / −0,004 |
| 1,5 | +0,117 / +0,052 / −0,049 | +0,077 / +0,053 / +0,012 |

São 376 calls e 382 travas por cenário, ainda com as limitações acima.

**Correto:** canais cripto deslocados; entradas seguintes ao sinal; exclusão do candle UTC parcial; prioridade E2 por mom28 do sinal e limite histórico de três vagas. A prioridade final em produção perde precisão ao ordenar percentual arredondado. Black–Scholes, paridade, delta put e risco largura−crédito estão corretos no modelo europeu sem dividendos; stops precedem alvos e gaps posteriores são tratados nos motores principais.

## Veredito

E1/E2 mantêm expectativa histórica positiva na reprodução local.  
Discordo de considerar “acionado” integralmente corrigido e laboratório/produção plenamente equivalentes.  
Concordo com Claude sobre fragilidade de IV, slippage, sobrevivência e seleção pela validação.  
A vantagem das opções continua hipótese; os novos vieses impedem tratá-la como retorno executável demonstrado.