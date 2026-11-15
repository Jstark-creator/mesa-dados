# Auditoria Codex — 2026-11-15T02:50Z — commit a8f6ea1

Auditei `scripts/lab/m7/m7.py`, incluindo suas dependências de precificação e o histórico anterior. **Há problemas que impedem validar uma eventual aprovação do M7.** O filtro acrescentado no último commit também não comprova que as cadeias estejam completas.

Não alterei o repositório nem acessei a internet. As cadeias ThetaData, `/tmp/td/spot.csv`, resultados do M7 e o pré-registro citado não estão disponíveis neste checkout. Os números abaixo são de **testes sintéticos**, executados com cópias em `/tmp`; não representam o desempenho histórico da estratégia.

### 1. Saída decidida e executada na mesma cotação de fechamento — CRÍTICO

**Arquivo:** `scripts/lab/m7/m7.py:123–135`.

O código calcula o resultado usando bid/ask do fechamento e, se essa própria cotação acionar alvo ou stop, registra a execução nela. A informação que determina a ordem só fica conhecida junto com o preço atribuído à execução. Não há cotação posterior nem modelo de ordem condicional que sustente esse preenchimento.

O problema envolve os gatilhos de preço; a saída por prazo pode ser programada antecipadamente.

**Teste:** numa operação sintética, executar no fechamento que revelou o alvo produziu **+0,583R**; executar na cotação seguinte produziu **−0,410R**. Isso demonstra a fragilidade, sem estimar a direção ou magnitude do efeito histórico.

### 2. Operações sem saída desaparecem — CRÍTICO

**Arquivo:** `scripts/lab/m7/m7.py:119–139`.

Se faltarem cotações das pernas, chegar o vencimento ou terminar a amostra sem saída reconhecida, `resultado` permanece `None` e a operação é descartada. Ela não aparece sequer como posição aberta; o bloqueio `livre` também não é atualizado.

Assim, a inclusão de uma entrada depende de conseguir observar uma saída futura. Lacunas podem eliminar perdas ou ganhos, e o relatório não permite distinguir ausência de operações de posições pendentes.

**Teste:** uma posição aberta com resultado marcado de **−0,212R** virou **zero operações** no original. O correto seria preservar a posição e reportar sua situação; vencimentos e falhas de cotação precisam de tratamento explícito.

### 3. Treino recebe resultados conhecidos apenas na validação — MÉDIO

**Arquivo:** `scripts/lab/m7/m7.py:198,207–208`.

O período depende somente da entrada. Uma operação aberta até 31/03/2025 e encerrada depois contribui para escolher P1/P2 “no treino”, embora seu resultado ainda não estivesse disponível no corte.

Isso contamina a escolha do perfil com informação posterior. A correção é exigir saída até o corte para seleção e aplicar uma separação temporal compatível com o horizonte das operações. Não foi possível quantificar sem as cadeias.

### 4. Limite de posições aplicado depois da simulação individual — MÉDIO

**Arquivo:** `scripts/lab/m7/m7.py:97–98,139,143–154,197`.

Cada ETF primeiro bloqueia novas entradas durante suas operações simuladas. Depois, o filtro de grupo rejeita algumas dessas operações, mas não recupera sinais que elas bloquearam.

Exemplo reproduzido: SPY e QQQ ocupam duas vagas; uma entrada de DIA é rejeitada. QQQ sai, abrindo vaga, mas um novo sinal de DIA continua ausente por causa da posição hipotética rejeitada anteriormente.

É necessário simular a carteira cronologicamente. O desempate alfabético da linha 146 também influencia quais ETFs entram e precisa de justificativa prévia.

### 5. “41 arquivos” não equivale a cadeia completa — MÉDIO

**Arquivo:** `scripts/lab/m7/m7.py:164–166,217` — **introduzido no último commit**.

O filtro conta arquivos `*.csv.gz`; não verifica meses distintos esperados, continuidade, cobertura diária ou disponibilidade das pernas. Quarenta e um arquivos incompletos passam.

Além disso, o universo passa a depender da disponibilidade observada no cache da rodada inteira. Isso exige documentar exclusões e congelar o universo antes de interpretar a validação. **Não encontrei evidência de seleção por rentabilidade**, mas o critério atual não sustenta o rótulo “cadeia completa”.

### O que está correto

- Sinais e direção usam o dia anterior; HV/IV do fechamento do sinal não constituem lookahead nessa entrada.
- O percentil compara a IV atual apenas com observações anteriores, limitadas às últimas 252; não usa a amostra inteira nem `bfill`.
- Há bid/ask, cenários de execução e comissão nas duas pontas.
- O R usa débito no straddle e largura menos crédito líquido nas estruturas de crédito.
- Stops contabilizam o preço observado, inclusive ultrapassagens; não limitam artificialmente a perda ao gatilho.
- P1/P2 são escolhidos pelo campo de treino, embora falte corrigir sua fronteira temporal.

## Veredito

Uma eventual conclusão positiva do M7 **ainda não está demonstrada**.  
Descarte de posições e execução pelo fechamento precisam ser corrigidos antes de interpretar o R.  
O último commit não resolve esses problemas e acrescenta um filtro insuficiente de cobertura.  
Sem cadeias e resultados locais, não é possível afirmar se a aprovação ou reprovação numérica se mantém.