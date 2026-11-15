# Auditoria Codex — 2026-11-15T02:57Z — commit b501c22

**A reprovação do M7 continua sustentada, mas os retornos ainda não constituem um backtest plenamente auditável.** Examinei código e agregados locais, sem internet e sem alterar o repositório. Sem as cadeias ThetaData, não é possível recalcular integralmente as estratégias.

### Achados

1. **CRÍTICO — Operações desaparecem conforme a disponibilidade futura de saída.**  
   [m7.py:119](scripts/lab/m7/m7.py#L119), especialmente linhas 123–137: quando falta cotação de alguma perna, o código adia a avaliação, inclusive depois do prazo de saída com ≤21 dias. Se não encontrar saída antes do vencimento/fim da amostra, apaga a operação inteira; ela também deixa de ocupar a vaga do ETF. Isso condiciona a inclusão à informação futura. Em teste sintético da cópia em `/tmp`, uma entrada executável sem saída disponível produziu **zero operações registradas**. É necessário preservar posições abertas e explicitar sua liquidação ou marcação.

2. **MÉDIO — Execução condicionada ao fechamento que fornece o próprio preço.**  
   [m7.py:101](scripts/lab/m7/m7.py#L101) e [m7.py:126](scripts/lab/m7/m7.py#L126): strikes são escolhidos usando spot e cotações finais de t; alvo/stop são detectados e executados nessa mesma fotografia. Para gestão “na última hora”, o fechamento definitivo ainda não existe. Os bid/ask de fechamento não demonstram que seria possível reconhecer o gatilho e executar simultaneamente todas as pernas nesses preços. Comparar com execução na próxima cotação seria a correção causal; faltam dados para quantificá-la.

3. **CRÍTICO — XLK apresenta indícios fortes de incompatibilidade entre spot e opções.**  
   [.github/workflows/m7.yml:43](.github/workflows/m7.yml#L43), [m7.py:25](scripts/lab/m7/m7.py#L25), [matriz_real.py:42](scripts/lab/etf/matriz_real.py#L42): o spot vem de `Close` com `auto_adjust=False`, o que não assegura preços históricos nominais anteriores a splits. Strikes/prêmios históricos podem estar em outra base. Não há verificação de paridade, distância relativa do strike ou concordância call/put.

   Além disso, `iv45` aceita **apenas um lado válido**: se a put falhar, a call sozinha determina a IV. Num exemplo sintético, spot dividido por dois com opções na escala original elevou a razão de aproximadamente 1× para **18×**. É um mecanismo compatível com o observado, não prova do split específico.

   **14,41× é o terceiro quartil, não o máximo** do relatório. Apenas 341 observações têm razão válida; o agregado não informa separadamente quantas falharam por IV ou HV.

4. **MÉDIO — NaNs distorcem o percentil para baixo.**  
   [m7.py:178](scripts/lab/m7/m7.py#L178): comparações com IV ausente retornam `False`, mas permanecem no denominador. A janela contém até 252 **linhas**, não necessariamente 252 IVs válidas. Isso pode suprimir sinais de volatilidade cara e favorecer barata, especialmente no XLK. Em teste sintético com 125 lacunas, um percentil correto de **100% tornou-se 50,4%**. Deve-se remover NaNs da referência e exigir histórico válido anterior suficiente.

5. **MÉDIO — Limite do grupo aplicado depois da simulação individual.**  
   [m7.py:97](scripts/lab/m7/m7.py#L97), [m7.py:143](scripts/lab/m7/m7.py#L143) e [m7.py:197](scripts/lab/m7/m7.py#L197): uma operação posteriormente rejeitada pelo limite de duas posições já bloqueou novas entradas daquele ETF durante a simulação. Assim, oportunidades que uma carteira executável poderia aceitar desaparecem. O desempate é alfabético por ETF, sem justificativa econômica documentada. O limite precisa integrar uma simulação cronológica conjunta.

6. **MÉDIO — Separação treino/validação vulnerável, sem impacto observado nesta amostra.**  
   [m7.py:198](scripts/lab/m7/m7.py#L198): a classificação usa somente a entrada; uma operação iniciada até 31/03/2025 poderia incorporar preços posteriores na escolha P1/P2. **Nenhuma das operações publicadas atravessa essa fronteira**, portanto purgá-las não altera os números atuais. O pré-registro citado no cabeçalho não está no repositório; não consegui confirmar sua anterioridade nem os critérios originais.

### Impacto observável do XLK

Recalculei os agregados em `/tmp`, excluindo somente suas operações publicadas:

| Validação, straddle P2 | Publicado | Sem XLK |
|---|---:|---:|
| `meio_50` | −0,188R; 13 ops | **−0,285R; 10 ops** |
| `natural` | −0,241R; 14 ops | **−0,294R; 10 ops** |

Condor e crédito publicados não contêm XLK e permanecem iguais. Isso é uma **sensibilidade**, não uma carteira corrigida: excluir XLK antes da simulação poderia liberar vagas.

### O que está correto

- HV20 é retrospectiva; sinais usam t−1; não encontrei `bfill` nem percentil calculado sobre toda a amostra futura.
- Vencimento próximo de 45 dias, deltas em módulo e regras numéricas de alvo/stop correspondem ao descrito.
- Comissão de US$0,65 por contrato/lado e cenários de spread estão corretamente aplicados.
- R usa débito ou largura máxima menos crédito líquido; menor risco publicado: **US$150,80**, sem denominadores minúsculos.
- Stops usam o prejuízo efetivamente cotado, sem truncá-lo artificialmente no limite.
- Não identifiquei implementação produtiva de M7 para comparar.

## Veredito
A conclusão operacional **“nada aprovado” se mantém** nos resultados disponíveis e na exclusão simples do XLK.  
O XLK contamina diretamente os straddles e provavelmente seus sinais; a causa exata permanece sem confirmação.  
Os retornos corrigidos exigem cadeias brutas, tratamento das posições sem saída e simulação conjunta causal.  
A reprovação atual não demonstra que o conceito seja inviável; demonstra ausência de evidência suficiente para operá-lo.