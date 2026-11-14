# Auditoria Codex — 2026-11-14T18:25Z — commit 2ded619

Auditei o commit `2ded619`, com foco em `scripts/lab/etf/thetadata_baixar.py` e consulta ao histórico anterior. Não acessei a internet nem alterei o repositório. Os testes abaixo usaram uma cópia em `/tmp`, relógio virtual e respostas sintéticas.

Não encontrei novo viés de futuro diretamente no arquivo: ele coleta dados, sem calcular indicadores ou operações. Os problemas estão na integridade e na cobertura da amostra entregue ao backtest.

### Achados

1. **MÉDIO — Parada por tempo permite publicar resultados de uma coleta incompleta.**  
   **Arquivo:** [thetadata_baixar.py:81](/home/runner/work/mesa-dados/mesa-dados/scripts/lab/etf/thetadata_baixar.py:81), linhas 81–82. Integração: `.github/workflows/opcoes_reais.yml:69` e `:92–94`.

   O novo `return` encerra o processo com sucesso, mesmo deixando meses ou símbolos pendentes. O workflow pode então executar o backtest e publicar agregados sem exigir cobertura completa. Como a coleta percorre todos os meses de SPY antes de QQQ, a amostra parcial depende da ordem dos símbolos e da velocidade das respostas.

   **Reprodução:** solicitei janeiro a março para SPY e QQQ, com limite virtual de um minuto. Após uma resposta de 61 segundos, o script terminou normalmente com **1 dos 6 arquivos mensais previstos**. Isso reproduz e amplia o problema de cobertura já registrado na auditoria anterior.

   **Correção sugerida:** salvar um manifesto com cobertura e pendências; permitir a retomada, mas impedir a publicação de conclusões enquanto a cobertura exigida estiver incompleta. Não basta registrar a interrupção no log.

2. **MÉDIO — Cache pode reutilizar uma amostra incompatível com o pedido atual.**  
   **Arquivo:** [thetadata_baixar.py:77](/home/runner/work/mesa-dados/mesa-dados/scripts/lab/etf/thetadata_baixar.py:77), linhas 77–84. **Preexistente, relevante para a retomada introduzida pelo commit.**

   A identidade do cache contém apenas símbolo e mês. Não registra `max_dte`, `strike_range` nem o intervalo efetivamente solicitado. Por exemplo, uma coleta iniciada em **15 de janeiro** grava `2026-01.csv.gz`; outra iniciada em **1º de janeiro** considera esse mês completo. Ampliar a faixa de strikes ou DTE também não atualiza meses fechados.

   **Reprodução:** com janeiro já presente no cache, solicitei janeiro inteiro com DTE 120 e faixa de strikes 80: **nenhuma requisição para janeiro**, apenas fevereiro e março.

   Isso pode excluir contratos e datas silenciosamente, prejudicando comparações entre rodadas. A correção exige metadados ou uma chave de cache que represente a consulta, além de verificar cobertura.

3. **BAIXO — O limite de tempo não interrompe uma requisição em andamento.**  
   **Arquivo:** [thetadata_baixar.py:34](/home/runner/work/mesa-dados/mesa-dados/scripts/lab/etf/thetadata_baixar.py:34), linhas 34–48; nova checagem em `:81`.

   O prazo só é verificado antes de `pedir()`. Essa função pode consumir várias tentativas e pausas sem consultar o tempo restante.

   **Reprodução:** seis timeouts simulados de 300 segundos, com as pausas previstas, consumiram **31,5 minutos** antes de devolver o controle. Não é um teto absoluto: a leitura da resposta também pode prolongar a chamada.

   A folga atual do workflow reduz o risco, mas o argumento não garante um encerramento dentro do prazo. Usar um prazo baseado em `time.monotonic()` dentro das tentativas tornaria o comportamento mais previsível.

### O que está correto

- O arquivo não calcula percentis, não usa `bfill` e não escolhe entradas ou saídas; não identifiquei nele novo lookahead de estratégia.
- Meses anteriores já existentes são preservados, enquanto o mês corrente é solicitado novamente — comportamento adequado para atualizar dados ainda em formação.
- A checagem ocorre entre arquivos mensais, evitando interromper deliberadamente uma gravação no meio.
- O commit não altera cálculo de R, custos, stops, alvos ou regras de produção. Não há nova divergência demonstrada nesses pontos.

Não há cadeias ThetaData locais identificadas para medir impacto histórico em R. Os números apresentados demonstram falhas operacionais sintéticas, sem estimar rentabilidade.

## Veredito
O commit melhora a retomada, mas ainda permite tratar uma coleta parcial como pronta para análise.  
Mantém-se a conclusão anterior: falta evidência validada para transformar a matriz com cotações reais em playbook.  
Nenhum resultado de rentabilidade foi confirmado ou refutado nesta auditoria.  
Exija cobertura verificável e cache compatível antes de interpretar novos agregados.