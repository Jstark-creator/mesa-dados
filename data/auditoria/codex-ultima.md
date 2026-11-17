# Auditoria Codex — 2026-11-17T18:08Z — commit fde3237

Auditei o commit `fde3237`, concentrado em `scripts/cripto.py`, e comparei a camada L com o laboratório. Usei exclusivamente dados locais; simulações e saídas ficaram em `/tmp`. O repositório permaneceu intacto.

**Não encontrei lookahead nas alterações do commit.** Os problemas abaixo são herdados pelo novo uso de `estado()` ou são limitações da extrapolação para ETH.

### 1. Stop ignora gaps — MÉDIO

**Arquivo:** [scripts/cripto.py:74](/home/runner/work/mesa-dados/mesa-dados/scripts/cripto.py:74), especialmente linha 77.

Quando o candle atravessa o stop, `preco_saida` recebe sempre o nível do stop. Se a abertura já estiver além dele, esse preço não é executável. Para long, a referência deveria ser `min(abertura, stop)`; para short, `max(abertura, stop)`, antes de slippage.

**Teste controlado:** entrada 100, stop 94 e abertura seguinte em 90:

- Atual: saída 94, resultado bruto **−1,00R**.
- Corrigido: saída 90, resultado bruto **−1,67R**.

Nos históricos locais de BTC/ETH, não encontrei ocorrências que alterassem os resultados das camadas M/L examinadas: impacto observado **0R**. O defeito permanece relevante para eventos extremos.

### 2. Piso e direção do risco continuam sem validação — MÉDIO

**Arquivo:** [scripts/cripto.py:70](/home/runner/work/mesa-dados/mesa-dados/scripts/cripto.py:70), [linha 91](/home/runner/work/mesa-dados/mesa-dados/scripts/cripto.py:91) e [linha 123](/home/runner/work/mesa-dados/mesa-dados/scripts/cripto.py:123).

O laboratório rejeita operações cujo risco direcional seja ≤0,3% da entrada. `estado()` não faz isso, e o cálculo de R usa `abs(entrada − stop)`, que esconde um stop situado do lado errado após gap. `dimensionar()` também aceita distância arbitrariamente pequena ou zero.

Consequências: posições incompatíveis com o laboratório, quantidades excessivas e possível divisão por zero. O parâmetro novo `k_stop=3.0` é aplicado corretamente, mas não resolve essa validação.

**Impacto local:** nenhuma entrada histórica de BTC/ETH examinada violou o piso. Portanto, não houve mudança quantitativa nessa amostra. É uma pendência já registrada no histórico, ainda presente.

### 3. Laboratório sai no fechamento; produção, na abertura seguinte — MÉDIO

**Arquivo:** [scripts/cripto.py:79](/home/runner/work/mesa-dados/mesa-dados/scripts/cripto.py:79), especialmente linha 84; comparação com `scripts/lab/cripto/c1_sistemas.py:19`.

A produção espera confirmar o fechamento fora do canal e usa a abertura seguinte. Isso é causalmente correto. O laboratório atribui a saída ao próprio fechamento que confirmou o sinal, uma aproximação de execução otimista. A nova camada L herda essa divergência.

Substituí apenas o preço de saída por canal no laboratório, preservando os demais critérios e custos. Camada L long, entradas desde 2022, operações encerradas antes do último candle local:

| Ativo | Operações | Média original | Média corrigida |
|---|---:|---:|---:|
| BTC | 8 | +0,674R | +0,671R |
| ETH | 6 | +0,325R | +0,325R |

Total combinado: **+7,346R → +7,319R**. O efeito observado é pequeno e não inverte o sinal, mas são apenas 14 operações.

### 4. `resultado_R` é bruto, sem identificação explícita — BAIXO

**Arquivo:** [scripts/cripto.py:91](/home/runner/work/mesa-dados/mesa-dados/scripts/cripto.py:91), agora também acessível pela camada L na linha 230.

O resultado marcado a mercado desconta somente a entrada. Não incorpora taxas, slippage ou funding acumulado. Consultar o funding atual não recupera o custo histórico da posição.

Isso é aceitável como indicador **bruto**, mas o nome permite comparação indevida com o R líquido do laboratório. Para a camada L spot, permanecem taxas e slippage; funding só se aplica caso se use perpétuo. Nos dados locais, ambas as posições L estavam `FORA`, sem R aberto para recalcular.

### O que está correto

- Candles do dia UTC são excluídos; canais 20/50/100 usam `shift()`.
- MM200, ATR e momentum incluem o fechamento do sinal, informação disponível antes da entrada seguinte: isso **não constitui lookahead**.
- Acrescentar dados futuros não alterou os indicadores anteriores nos testes de prefixo de BTC/ETH.
- A camada L implementa corretamente long 100/50, filtro MM200 e stop inicial de 3 ATR; está explicitamente restrita a papel.
- O Mayer de ETH é causal. Contudo, aplicar a ele a régua de BTC não demonstra que esses multiplicadores tragam vantagem econômica.

## Veredito
As alterações não introduzem lookahead identificado; acompanhar a camada L em papel continua justificável.
A correção de execução testada preserva os resultados positivos, com amostra pequena.
Stops com gaps e validação do risco ainda exigem correção antes de maior confiança operacional.
Esta auditoria não valida capital real na camada L nem a eficácia da régua de aportes para ETH.