# Auditoria Codex — 2026-11-17T18:01Z — commit 419ad40

Reproduzi **exatamente as 178 operações do CSV**, usando apenas dados locais. Os testes ficaram em [cópia de auditoria](/tmp/audit_c4.py); nenhum arquivo do repositório foi alterado.

### O que está correto

- **Canais sem look-ahead:** `hi100`, `lo100`, `hi50` e `lo50` usam `rolling(...).shift()` em [c4_camadas.py:10](/home/runner/work/mesa-dados/mesa-dados/scripts/lab/cripto/c4_camadas.py:10).
- **Entrada causal:** sinal no fechamento de *t*, execução na abertura de *t+1* ([base.py:81](/home/runner/work/mesa-dados/mesa-dados/scripts/lab/cripto/base.py:81)). MM200 e ATR podem incluir *t*, pois já estão disponíveis nessa decisão. Não encontrei `bfill` nem percentis globais nesse caminho.
- **Stop e R corretos:** stop inicial fixo em fechamento do sinal ±3 ATR14; denominador usa a distância entre **entrada efetiva** e stop. Conferência numérica sem diferenças. Há piso de risco de 0,3%; o menor risco observado foi 1,62%.
- **Custos 2x aplicados nas duas pontas:** 0,30% por lado no long spot e 0,16% no short, sobre os respectivos preços de entrada e saída ([base.py:104](/home/runner/work/mesa-dados/mesa-dados/scripts/lab/cripto/base.py:104)). Stops posteriores à entrada respeitam gaps adversos; não há alvo concorrente resolvido favoravelmente.

### Achados

**1. MÉDIO — Operações abertas não são excluídas corretamente.**  
[base.py:100](/home/runner/work/mesa-dados/mesa-dados/scripts/lab/cripto/base.py:100) transforma posições sem saída em operações encerradas no último fechamento. Depois, [c4_camadas.py:31](/home/runner/work/mesa-dados/mesa-dados/scripts/lab/cripto/c4_camadas.py:31) compara essa data com o relógio, não com o estado da posição.

Os dados terminam em **13/11/2026**, mas a execução ocorre em 17/11. Dois shorts M ainda abertos entram como realizados: BTC **+0,501R**, ETH **+0,931R**. Excluindo-os explicitamente:

| Validação, custo 2x | Publicado | Corrigido |
|---|---:|---:|
| M short | 34 operações; +11,99R | 32; +10,55R |
| M+L | +49,35R | +47,91R |
| L long | 14; +6,89R | **inalterado** |

A correção exige um campo explícito de motivo/estado da saída.

**2. MÉDIO — Encerramento oculto após 400 candles.**  
[base.py:67](/home/runner/work/mesa-dados/mesa-dados/scripts/lab/cripto/base.py:67) limita a duração; [base.py:101](/home/runner/work/mesa-dados/mesa-dados/scripts/lab/cripto/base.py:101) liquida no fechamento. Essa regra não consta do playbook fornecido.

O long ETH iniciado em 23/07/2020 realiza artificialmente **+122,29R** em 26/08/2021. Sem o limite, termina por regra em 06/01/2022, com **+136,01R**, eliminando também reentradas intermediárias. Treino L long: **17 operações, média +15,34R → 15, média +18,44R**. A validação L permanece igual. A versão corrigida exige cuidado adicional com operações que atravessam a fronteira treino/validação.

**3. MÉDIO — Saída executada no fechamento que gera o sinal.**  
[c1_sistemas.py:19](/home/runner/work/mesa-dados/mesa-dados/scripts/lab/cripto/c1_sistemas.py:19) observa o fechamento abaixo do canal e vende nesse mesmo preço. Esse preço só é confirmado quando o candle termina. A produção usa abertura seguinte ([cripto.py:83](/home/runner/work/mesa-dados/mesa-dados/scripts/cripto.py:83)).

Simulando abertura seguinte e excluindo abertas, L long passa de **+0,4923R para +0,4904R/operação**, total **+6,89R → +6,87R**. A inconsistência existe, mas seu impacto local é pequeno.

**4. MÉDIO — Drawdown e “diversificação” superinterpretados.**  
[base.py:57](/home/runner/work/mesa-dados/mesa-dados/scripts/lab/cripto/base.py:57) acumula operações na ordem recebida, agrupada por ativo. Ordenando cronologicamente e incluindo capital inicial zero, DD realizado da L long muda de **−3,9R para −4,5R**.

A função de carteira ordena corretamente ([c4_camadas.py:24](/home/runner/work/mesa-dados/mesa-dados/scripts/lab/cripto/c4_camadas.py:24)), mas considera apenas resultados realizados. Marcando posições diariamente pelo fechamento, com risco inicial unitário por operação:

| Carteira | DD realizado | DD marcado a mercado |
|---|---:|---:|
| M | −7,0R | **−19,1R** |
| L | −6,4R | **−17,1R** |
| M+L | −10,3R | **−33,0R** |

Comparar −10,3 com a **soma** −13,4 não demonstra melhoria frente a M. Há até quatro posições simultâneas; é necessário comparar sob orçamento de risco comum. Além disso, essa carteira inclui **L short reprovada**.

**5. MÉDIO — Aprovação estatística da L long não demonstrada.**  
A concentração foi confirmada: top-3 **+15,78R**, demais **−8,89R**. Bootstrap IID, 300 mil reamostragens, semente fixa: **IC95% da média aproximadamente [−0,77R; +2,11R]**; cerca de **27%** das médias reamostradas são não positivas. Isso não é probabilidade posterior de prejuízo. Reamostragem por ano, preservando agrupamento BTC/ETH, também inclui zero; há somente cinco blocos anuais.

**6. MÉDIO — Pré-registro indisponível e produção ainda v1.**  
O arquivo citado em [c4_camadas.py:1](/home/runner/work/mesa-dados/mesa-dados/scripts/lab/cripto/c4_camadas.py:1) não existe neste checkout: não pude verificar critérios nem anterioridade das escolhas. A produção mantém 20/20, 20/10 e 2 ATR; L não está implementada. Long sem funding corresponde a **spot**; perpétuos exigem outro teste.

## Veredito
L long mantém +6,9R na validação; L short continua reprovada.  
Aprovação por eventual regra mecânica não equivale a evidência estatística convincente.  
Eu manteria L long apenas em papel ou tamanho reduzido, aguardando dados novos.  
A alegação de diversificação precisa ser refeita com marcação diária e risco comparável.