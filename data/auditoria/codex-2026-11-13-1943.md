# Auditoria Codex — 2026-11-13T19:43Z — commit def253d

Auditei `scripts/baixar_etf_iv.py`, adicionado no commit `def253d`, e a função de download que ele reutiliza. **Não encontrei viés de futuro confirmado nem erro de execução de trades nesse arquivo**, mas há duas falhas de integridade dos dados.

Não existe `data/etf/` neste checkout, nem encontrei consumidor dessas séries nos laboratórios atuais. Portanto, não foi possível medir impacto em retorno, R ou drawdown. As reproduções foram sintéticas, offline, com saída apenas em `/tmp`; nenhum arquivo do repositório foi alterado.

### 1. Candle parcial pode ser publicado como diário definitivo — MÉDIO

**Arquivo:** [scripts/baixar_etf_iv.py:23](/home/runner/work/mesa-dados/mesa-dados/scripts/baixar_etf_iv.py:23), gravação na linha 29.

O script grava todas as linhas recebidas, sem verificar se a última sessão já encerrou. A função importada `baixar()` também não filtra candles parciais. O workflow permite execução manual e por push, sem restrição de horário.

**Consequência:** uma coleta intradiária pode produzir indicadores e sinais que desaparecem após o fechamento. Isso não demonstra lookahead por si só; torna-se informação futura se o consumidor tratar o fechamento definitivo daquele dia como disponível antes do encerramento.

**Reprodução:** forneci uma série sintética com uma linha do dia corrente; **1/1 linha foi gravada**, sem marcação de parcial. Não estimei efeito financeiro.

**Correção sugerida:** excluir sessões ainda abertas ou registrar explicitamente seu estado, considerando o horário de encerramento de cada série.

### 2. Falha de coleta mantém arquivos antigos sem sinalização estruturada — MÉDIO

**Arquivo:** [scripts/baixar_etf_iv.py:25](/home/runner/work/mesa-dados/mesa-dados/scripts/baixar_etf_iv.py:25), especialmente linhas 26–29.

Quando uma série falta ou vem vazia, o script apenas imprime `sem dados` e continua. Um CSV anterior permanece no diretório, enquanto outros são atualizados. Não há manifesto com data de referência, falhas ou completude, nem exceção que indique coleta incompleta.

**Consequência:** o laboratório pode combinar preço atualizado com volatilidade antiga. O erro dependerá do alinhamento posterior: pode eliminar datas silenciosamente ou reutilizar uma observação defasada.

**Reprodução:** simulei sucesso em SPY e falha em VIX, com um CSV antigo de VIX já existente. **SPY foi atualizado; VIX permaneceu intacto; `main()` terminou normalmente.**

**Correção sugerida:** registrar sucesso e última data por série, sinalizar coleta incompleta e exigir que o consumidor valide a disponibilidade temporal antes de usar os dados.

### Limitação conceitual: índice de volatilidade não é cadeia histórica de opções

**Arquivo:** [scripts/baixar_etf_iv.py:1](/home/runner/work/mesa-dados/mesa-dados/scripts/baixar_etf_iv.py:1) e linhas 13–16.

A descrição “IV real” exige cuidado: os arquivos coletados são índices de volatilidade, não cotações históricas de cada opção por strike e vencimento. O script também não fornece uma série de volatilidade específica para todos os ETFs listados.

Isso **não constitui erro de precificação neste coletor**, pois ele não precifica opções. Entretanto, esses dados isolados não comprovam prêmios executáveis, spreads ou rentabilidade de uma estratégia de opções.

### O que está correto

- Não há `bfill`, percentil sobre a amostra inteira, otimização de parâmetros ou seleção de operações neste arquivo.
- Não há resolução favorável de stop/alvo, cálculo de R, funding ou custos para auditar: o código apenas coleta e grava dados.
- A função reutilizada remove linhas com campos ausentes; não inventa valores para preencher lacunas.
- A lista de símbolos é explícita. Isso facilita a reprodução, embora não demonstre seleção do universo antes de observar resultados.
- O commit não altera diretamente os motores de cripto, M3 ou opções; não identifiquei nova divergência operacional entre laboratório e produção.

## Veredito

As conclusões anteriores não são modificadas por este commit; seus problemas registrados continuam fora desta alteração.  
O coletor precisa controlar candles parciais e coletas incompletas antes de alimentar validações quantitativas.  
Sem os CSVs de ETFs e um consumidor implementado, não há resultado financeiro novo verificável.  
Baixar índices de volatilidade, por si só, não valida a vantagem da M3 em opções.