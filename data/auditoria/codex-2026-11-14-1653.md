# Auditoria Codex — 2026-11-14T16:53Z — commit 66ea586

Auditei o arquivo novo do commit `66ea586` e consultei o histórico anterior. **Não é possível confirmar a rentabilidade do M7 nesta cópia:** faltam as cadeias ThetaData, o `spot.csv` e os resultados desse laboratório. Não acessei a internet nem alterei o repositório.

Os números abaixo são **testes sintéticos dos mecanismos**, executados em `/tmp/auditar_m7.py`, com funções extraídas do código. Não representam desempenho histórico.

## Achados

1. **CRÍTICO — Saída usa a própria cotação que dispara a decisão.**  
   [m7.py:123–135](/home/runner/work/mesa-dados/mesa-dados/scripts/lab/m7/m7.py:123)  
   O programa calcula o resultado pela cotação de fechamento, verifica alvo/stop e registra execução nessa mesma cotação. Falta demonstrar que seria possível observar o disparo e executar todas as pernas nesses preços. O cenário “natural” inclui spread, mas não resolve essa dependência temporal.  
   **Teste:** straddle com alvo atingido no fechamento: **+0,583R** no original; executando na cotação disponível seguinte: **−0,510R**. É uma sensibilidade ilustrativa, não uma estimativa do impacto histórico. Corrigir exige execução posterior à decisão ou dados intradiários que sustentem o preenchimento.

2. **CRÍTICO — Operações sem saída desaparecem, e a posição deixa de bloquear novas entradas.**  
   [m7.py:119–139](/home/runner/work/mesa-dados/mesa-dados/scripts/lab/m7/m7.py:119)  
   Se não encontrar saída antes do vencimento/fim dos dados, `resultado` permanece vazio e a operação é descartada. Isso ocorre também quando faltam cotações das pernas. Como `livre` só é atualizado para operações concluídas, o simulador pode aceitar outra entrada enquanto aquela posição continuaria aberta. A inclusão da operação depende, portanto, da disponibilidade futura de saída.  
   **Teste:** uma posição termina a amostra sem disparar alvo/stop. Original: **zero operações**; reconhecendo a posição e sua marcação final: **uma posição aberta, −0,311R**. A marcação deve ser identificada separadamente de uma saída executada.

3. **MÉDIO — Treino incorpora resultados posteriores ao corte e pode contaminar a escolha P1/P2.**  
   [m7.py:196–206](/home/runner/work/mesa-dados/mesa-dados/scripts/lab/m7/m7.py:196)  
   O período depende exclusivamente da entrada. Uma operação aberta até **31/03/2025**, mas encerrada em abril, contribui integralmente para a média de treino usada para selecionar P1/P2. Assim, a escolha pode utilizar preços da janela de validação.  
   A seleção deve considerar apenas resultados conhecidos no corte e explicitar o tratamento das posições abertas. A recomendação de purga já constava no histórico de auditoria.

4. **MÉDIO — Limite de carteira aplicado depois da simulação cria bloqueios por operações rejeitadas.**  
   [m7.py:97–98](/home/runner/work/mesa-dados/mesa-dados/scripts/lab/m7/m7.py:97), [143–154](/home/runner/work/mesa-dados/mesa-dados/scripts/lab/m7/m7.py:143) e [195](/home/runner/work/mesa-dados/mesa-dados/scripts/lab/m7/m7.py:195)  
   Cada ETF é simulado isoladamente; depois são descartadas operações que excedem duas vagas no grupo. Uma operação posteriormente rejeitada já impediu novas entradas naquele ETF durante sua duração simulada.  
   **Teste:** DIA e QQQ ocupam as vagas; SPY é rejeitado. Quando as vagas abrem, um novo candidato SPY permanece suprimido. A filtragem original aceita **duas operações**; incluindo esse candidato, aceita **três**. A carteira precisa decidir as admissões durante a simulação cronológica. O efeito na rentabilidade pode ter qualquer sinal.

5. **MÉDIO — HV calculada sobre preço não ajustado pode interpretar desdobramentos como volatilidade.**  
   [m7.py:160–177](/home/runner/work/mesa-dados/mesa-dados/scripts/lab/m7/m7.py:160)  
   O fluxo associado fornece fechamentos não ajustados, necessários para precificar as opções. Porém, esse mesmo preço alimenta os retornos da HV20. Desdobramentos produzem retornos artificiais; dividendos também afetam a comparação IV/HV. Isso pode mudar os sinais “barata” e “cara”.  
   Convém separar spot nominal para precificação de uma série de retornos com tratamento explícito desses eventos. Sem o `spot.csv`, não quantifiquei ocorrências.

## O que está correto

- O sinal de entrada e a tendência vêm da observação anterior disponível.
- O percentil usa somente observações anteriores como referência; não há percentil sobre a amostra inteira nem `bfill`.
- Comissão de **US$ 0,65 por contrato por lado** e spread entram nos dois lados da operação.
- O risco do straddle é o débito; para os créditos válidos, largura menos crédito líquido é a base apropriada.
- Os stops registram o prejuízo observado, sem truncá-lo artificialmente no limite.
- P1/P2 são comparados nominalmente no treino, embora o corte precise da correção acima.

O pré-registro citado, `estrategias/m7-preregistro.md`, não existe nesta cópia. Logo, não consegui verificar a anterioridade dos parâmetros, universo e desempate alfabético. Também não há base para afirmar equivalência deste laboratório com produção.

## Veredito
A causalidade dos sinais está, em grande parte, correta.  
Execução no fechamento e desaparecimento de posições comprometem a interpretação dos resultados.  
Seleção temporal e simulação da carteira precisam ser corrigidas antes da validação.  
**Uma eventual conclusão de rentabilidade do M7 permanece não demonstrada.**