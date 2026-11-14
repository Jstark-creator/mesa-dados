# Auditoria Codex — 2026-11-14T14:03Z — commit e9fffa6

O commit `e9fffa6` adiciona coletores, sem mudar regras de entrada, saída ou cálculo de R. Encontrei problemas de cobertura e consistência dos dados que precisam ser resolvidos antes de validar o M4. Usei apenas arquivos locais e testes em `/tmp`, sem acesso à rede nem alterações no repositório.

### 1. Universo atual aplicado retrospectivamente — MÉDIO

**Arquivos:** `scripts/baixar_historico_m4.py:9–12`; `scripts/baixar_cotahist.py:35–37,52–55`.

Os dois coletores partem da lista atual de ativos e buscam seu passado. Isso permite estudar uma carteira fixa escolhida hoje, mas não demonstra o desempenho histórico de uma estratégia que selecionaria “opções líquidas” em cada época. Empresas excluídas, deslistadas e antigos integrantes não entram; a liquidez histórica também não é verificada.

A descrição “pré-registrada em 14/11/2026” protege testes prospectivos, mas não torna retrospectivos os critérios de seleção. Refinar o universo usando volume de todo o COTAHIST acrescentaria informação futura se essa seleção fosse aplicada aos primeiros anos.

**Correção:** definir integrantes e elegibilidade por data, com liquidez calculada apenas sobre pregões anteriores. Não há dados locais suficientes para quantificar o efeito em R.

### 2. Filtro por raiz perde códigos históricos e não identifica integralmente o objeto — MÉDIO

**Arquivo:** `scripts/baixar_cotahist.py:34–37,44–47`.

A seleção exige que as quatro primeiras letras do código pertençam ao universo atual. Mudanças de código não recebem tratamento: registros sob uma raiz antiga são descartados. Além disso, `ativo=raiz` não identifica a classe da ação subjacente; não é seguro associar automaticamente toda opção dessa raiz ao único ticker configurado.

Em teste sintético representando uma mudança de raiz, o parser reteve **1 de 2 registros**; incluindo explicitamente a raiz anterior, reteve **2 de 2**. Isso demonstra a perda pelo filtro, não mede a perda histórica efetiva.

**Correção:** cadastro temporal de códigos e identificação do subjacente por contrato. Guardar os campos de identificação disponíveis no registro ajuda a reconciliar séries.

### 3. Histórico ajustado e opções nominais exigem reconciliação — MÉDIO

**Arquivo:** `scripts/baixar_historico_m4.py:6,12,17`; dependência em `scripts/atualizar_dados.py:59–60`.

O histórico de ações usa `auto_adjust=True`, enquanto o COTAHIST fornece preços e strikes históricos nominais. Combinar diretamente esses arquivos para moneyness, IV, delta ou exercício mistura escalas, especialmente antes de dividendos e eventos societários.

**Não encontrei um consumidor M4 fazendo essa combinação**, portanto este é um risco concreto da interface dos dados, ainda não uma distorção de resultado demonstrada.

**Correção:** guardar OHLC sem ajuste para casar com contratos reais e, separadamente, séries ajustadas para indicadores, com tratamento explícito dos eventos. Sem COTAHIST local, não cabe apresentar impacto numérico.

### 4. Cache congela cobertura e pode deixar ações ausentes — MÉDIO

**Arquivo:** `scripts/baixar_cotahist.py:59–61`.

Basta existir `opcoes_<ano>.csv.gz` de um ano encerrado para pular todo o processamento. O código não verifica se o universo mudou nem se `acoes_<ano>.csv.gz` existe. Assim, ampliar o universo pode produzir cobertura diferente por período, silenciosamente.

**Teste isolado:** com opções de 2020 em cache e ações ausentes, o ano **não foi reprocessado** e o arquivo de ações **continuou ausente**.

**Correção:** validar ambos os arquivos e registrar versão do parser e universo usado; idealmente, preservar o arquivo bruto e refazer a extração quando o filtro mudar.

### 5. Falhas permitem uma base incompleta sem erro final — BAIXO

**Arquivos:** `scripts/baixar_cotahist.py:62–65`; `scripts/baixar_historico_m4.py:14–17`.

Falhas de download ou ausência de dados apenas imprimem mensagens e continuam. Arquivos antigos também permanecem no destino. Um consumidor pode confundir uma mistura de séries antigas, novas e ausentes com uma coleta completa.

No teste com download substituído por uma função que falha, o coletor COTAHIST encerrou normalmente apesar das falhas. Recomendo manifesto de cobertura e retorno de erro quando houver lacunas obrigatórias.

### O que está correto

- Não há indicadores, percentis globais, `bfill` ou decisões de trading nesses dois arquivos.
- Não há resolução favorável de stop/alvo, cálculo de R ou cobrança de custos a auditar aqui.
- O parser separa calls e puts pelo mercado e preserva datas de negociação e vencimento.
- O ano corrente é reprocessado, permitindo atualizar sua cobertura.
- Não há divergência nova entre laboratório e produção demonstrada por este commit.

## Veredito
As conclusões anteriores sobre E1/E2 não são alteradas por estes coletores.
O commit não demonstra vantagem econômica do M4 nem resolve as ressalvas anteriores sobre opções.
A base proposta precisa de universo temporal, identificação dos contratos e reconciliação de preços.
Sem COTAHIST local, não foi possível medir impacto real em R ou validar integralmente o layout.