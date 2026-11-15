# Auditoria Codex — 2026-11-15T02:59Z — commit b97c635

Auditei `b97c635`, com foco em `scripts/lab/m7/m7.py`, e consultei o histórico. **Não alterei o repositório nem acessei a internet.** As cadeias ThetaData e `/tmp/td/spot.csv` não estão disponíveis: conferi os agregados locais e executei funções do simulador com dados sintéticos em `/tmp`. Os números sintéticos abaixo demonstram mecanismos, não estimam o impacto histórico.

### Achados

1. **CRÍTICO — decisão e execução da saída na mesma cotação final.**  
   **Arquivo:** `scripts/lab/m7/m7.py:140–152`.  
   O código observa o bid/ask de fechamento, calcula se atingiu stop/alvo e executa exatamente nessa cotação. Isso pressupõe conseguir negociar depois de conhecer o fechamento definitivo. Também seleciona os strikes usando os preços finais da própria entrada (`:118–125`), sem representar a latência.  
   **Teste em `/tmp`:** um straddle entra com cada perna a US$5; ambas passam a US$8 e depois a US$2. O simulador registra **+0,597R**; uma cópia que executa na próxima cotação registra **−0,602R**, incluindo comissões. O impacto histórico pode ter qualquer direção. É necessário usar observações anteriores ao horário de execução ou executar posteriormente.

2. **CRÍTICO — operações sem saída observável desaparecem, liberando capital retroativamente.**  
   **Arquivo:** `scripts/lab/m7/m7.py:138–154`, com efeito em `:156`.  
   Sem cotação completa das pernas, o simulador pula o dia, inclusive quando já deveria encerrar por prazo. Se não encontra saída antes do vencimento/fim da amostra, elimina a operação inteira. Como `livre` só é atualizado nas operações concluídas, pode aceitar novas entradas enquanto a posição eliminada estaria aberta. A seleção depende da disponibilidade futura de dados.  
   **Teste sintético:** entrada válida seguida de ausência das pernas de saída produz **zero operações registradas**. Falta registrar posições pendentes, reservar capital e estabelecer tratamento explícito para vencimento/cotações ausentes. O histórico anterior já apontava o descarte; o problema permanece.

3. **MÉDIO — paridade é uma aproximação sem controle de qualidade.**  
   **Arquivo:** `scripts/lab/m7/m7.py:25–39` e `:194`.  
   A mudança corrige a incompatibilidade de escala dos desdobramentos, mas passa a substituir todo spot pela paridade europeia com dividend yield fixo. Para opções americanas de ETFs, exercício antecipado e dividendos discretos podem produzir diferenças. Além disso, escolhe o menor `|C−P|` sem limitar spreads ou validar a consistência entre strikes; `S_ref` é recebido e ignorado.  
   Uma cotação problemática pode contaminar simultaneamente spot, IV, percentil e escolha de strikes. Recomendo verificar dispersão da paridade entre pares líquidos e confrontar com spot nominal ajustado apenas pelos eventos societários pertinentes. **Impacto histórico não quantificável aqui.**

4. **MÉDIO — limite de grupo aplicado depois da simulação distorce a carteira.**  
   **Arquivo:** `scripts/lab/m7/m7.py:110–156`, `:160–171` e `:227`.  
   Primeiro cada ETF ocupa sua agenda individual; depois o filtro rejeita operações pelo limite de grupo. Uma operação rejeitada já impediu entradas posteriores daquele ETF durante a simulação, embora nunca tenha integrado a carteira final. Isso não equivale a simular as vagas cronologicamente.  
   Nos empates, a prioridade é alfabética (`etf`), sem justificativa econômica documentada no arquivo. O efeito pode ser positivo ou negativo; exige repetir a simulação com controle conjunto das posições.

5. **MÉDIO — universo condicionado à cobertura futura e resultados ainda anteriores à correção.**  
   **Arquivo:** `scripts/lab/m7/m7.py:181`; referência ao pré-registro em `:1`.  
   Exigir 41 arquivos mensais para incluir um ETF usa cobertura conhecida somente no fim da amostra; tampouco garante integridade diária. A ressalva é menor se o universo e esse filtro foram realmente fixados antes da análise, mas o pré-registro referenciado **não existe neste checkout**, impedindo essa confirmação.  
   Os resultados locais também não foram regenerados no último commit: ainda exibem XLK com quartil superior de IV/HV de **14,41**, compatível com o problema anterior. Portanto, não comprovam o desempenho da versão corrigida.

### O que está correto

- O percentil revisado exclui NaNs do denominador e compara a IV atual somente com observações anteriores; não usa a amostra inteira nem `bfill`.
- Sinal e tendência usados na entrada vêm da observação anterior. HV com fechamento do dia do sinal é causal nesse fluxo.
- A HV agora usa retornos ajustados, evitando saltos artificiais de desdobramento.
- Há spreads e comissões nos dois lados. As fórmulas básicas de débito, crédito e risco máximo são coerentes; o menor risco registrado é **US$150,80**, sem denominador quase zero nos CSVs.
- P1/P2 é escolhido pelo treino. Embora a separação use apenas a entrada, encontrei **zero operações cruzando o corte** nos resultados salvos.
- Não há sobreposição por ETF dentro de cada cenário salvo; os cenários são alternativas.

## Veredito
Mantém-se a conclusão prudente: **M7 ainda não demonstrou vantagem operacional**.  
Os agregados anteriores reprovam todas as estruturas, mas não validam a versão corrigida.  
Execução no mesmo fechamento e descarte de posições impedem confiar nas médias como desempenho negociável.  
A correção do percentil é adequada; a eficácia da nova base por paridade permanece sem confirmação histórica independente.