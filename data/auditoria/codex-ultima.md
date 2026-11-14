# Auditoria Codex — 2026-11-14T15:32Z — commit 18336d8

**A reprovação se mantém. Não encontrei erro CRÍTICO que explique uma rejeição injusta do regime.** Reproduzi os 5.528 registros e seus desfechos, usando apenas dados locais. Os testes ficaram em [/tmp/audit_m5.py](/tmp/audit_m5.py); não alterei arquivos do repositório nem acessei a internet.

Os números reproduzidos foram:

| Direção | P treino | Lift treino | N validação | P validação | Lift validação |
|---|---:|---:|---:|---:|---:|
| Compra | 30,18% | 1,090 | 743 | 34,05% | 1,077 |
| Venda | 27,90% | 1,018 | 277 | 24,91% | 1,042 |

**Achados, em ordem de prioridade**

1. **MÉDIO — Treino contém informação de desfechos de 2019.**  
   [fase_a.py:44](/home/runner/work/mesa-dados/mesa-dados/scripts/lab/m5/fase_a.py:44) separa períodos pela data do evento; a janela seguinte de 50 pregões pode atravessar a fronteira. Isso contamina a separação treino/validação, embora os indicadores do sinal sejam causais. Excluindo do treino eventos cuja janela alcança 2019: compras, **P 30,18% → 30,32%, lift 1,090 → 1,086**; vendas, **P 27,90% → 26,60%, lift 1,018 → 0,995**. O vazamento favorece ligeiramente a leitura original das vendas.

2. **MÉDIO — Fechamento da decisão também é referência de entrada.**  
   [fase_a.py:20](/home/runner/work/mesa-dados/mesa-dados/scripts/lab/m5/fase_a.py:20) ancora barreiras em `close[i]`, enquanto [linha 45](/home/runner/work/mesa-dados/mesa-dados/scripts/lab/m5/fase_a.py:45) depende desse fechamento para confirmar o regime. **Isso é válido como estudo de eventos observado após o fechamento**, mas não demonstra execução naquele preço. Como sensibilidade operacional, usando abertura seguinte como referência e somente janelas completas, compras na validação passam de **34,29% para 35,53%, lift 1,078 → 1,095**; vendas, **25,09% → 25,45%, lift 1,053 → 1,080**. A convenção original não está criando a reprovação.

3. **BAIXO — Janelas incompletas são selecionadas pelo próprio desfecho.**  
   [fase_a.py:21](/home/runner/work/mesa-dados/mesa-dados/scripts/lab/m5/fase_a.py:21) aceita eventos recentes já resolvidos e descarta os ainda abertos. Eventos com toque rápido ficam sobre-representados; o efeito sobre o regime não tem direção garantida. Exigindo 50 pregões completos, na validação:

   | Direção | N antes → depois | P antes → depois | Lift antes → depois |
   |---|---:|---:|---:|
   | Compra | 743 → 729 | 34,05% → 34,29% | 1,077 → 1,078 |
   | Venda | 277 → 275 | 24,91% → 25,09% | 1,042 → 1,053 |

4. **BAIXO — A composição por ETF explica parte do pequeno lift.**  
   [fase_a.py:57](/home/runner/work/mesa-dados/mesa-dados/scripts/lab/m5/fase_a.py:57) agrega a base por número de eventos, mas o regime tem outra distribuição entre ETFs. Reponderando a probabilidade-base de cada ETF pela quantidade de eventos daquele ETF no regime, o lift de validação cai de **1,077 para 1,050 nas compras** e de **1,042 para 1,001 nas vendas**.  
   **A base original é justa para a pergunta pré-especificada:** regime versus todos os meses, mesma direção. Incluir os próprios eventos na base é correto nessa definição, embora comprima o lift. Comparar apenas com meses sem regime seria outra pergunta e exigiria outro critério.

5. **MÉDIO — Pré-registro e independência da validação não são verificáveis.**  
   [fase_a.py:1](/home/runner/work/mesa-dados/mesa-dados/scripts/lab/m5/fase_a.py:1) referencia `estrategias/m5-preregistro.md`, ausente no repositório. O cabeçalho é datado de novembro de 2026, após quase toda a validação histórica. Não há evidência suficiente para certificar que universo, parâmetros e limites foram definidos sem consultar 2019+. Também não encontrei evidência de ajuste deliberado; a limitação é documental.

6. **BAIXO — N não mede observações independentes; aprovação usa arredondamento.**  
   A frequência mensal com horizonte de 50 pregões ([linha 37](/home/runner/work/mesa-dados/mesa-dados/scripts/lab/m5/fase_a.py:37)) produz janelas sobrepostas e ETFs correlacionados. Isso limita o significado estatístico de `N≥100`, sem invalidar a frequência descritiva. Nas [linhas 58–65](/home/runner/work/mesa-dados/mesa-dados/scripts/lab/m5/fase_a.py:58), o critério usa valores já arredondados, podendo aprovar resultados marginais abaixo dos limites. Aqui estão longe deles.

**O que está correto**

- MM200, retorno126 e volatilidade usam somente informação disponível no fechamento do evento; não há percentil global nem `bfill`.
- O acompanhamento começa no pregão seguinte e contém exatamente 50 pregões nas janelas completas; timeout vale fracasso.
- Stop recebe prioridade conservadora. Encontrei **zero primeiros toques ambíguos**; priorizar a abertura nos gaps não mudou os resultados.
- Nos 12 ETFs carregados, não encontrei datas duplicadas nem OHLC incompatíveis com abertura/fechamento.
- Fase A mede probabilidade de toque, não R ou rentabilidade: ausência de custos e precificação de opções não é erro desse desfecho. Não encontrei produção M5 para confrontar.

## Veredito
**As conclusões de reprovação se mantêm nas correções e sensibilidades executadas.**  
Nenhuma direção alcança conjuntamente P≥40% e lift≥1,3 nos dois períodos.  
A base é adequada à pergunta declarada; ajustar sua composição enfraquece o pequeno lift observado.  
O resultado não prova ausência universal de vantagem nem permite concluir rentabilidade de calls ou puts.