# M7 — Preço da volatilidade (gerado automaticamente; cotações reais ThetaData)

ETFs incluídos (cadeia completa): ['SPY', 'QQQ', 'IWM', 'DIA', 'XLK', 'XLF', 'XLE', 'SMH', 'GLD', 'TLT', 'EEM', 'XBI']

## Decisão pré-registrada

| estrutura          |   n_treino |   media_treino_meio50 |   n_val |   media_val_meio50 |   media_val_natural | aprovado   |
|:-------------------|-----------:|----------------------:|--------:|-------------------:|--------------------:|:-----------|
| 1 straddle P1      |         62 |                -0.276 |      28 |             -0.32  |              -0.428 | False      |
| 2a iron condor     |         60 |                -0.196 |      59 |             -0.19  |              -0.263 | False      |
| 2b crédito a favor |        108 |                -0.217 |     102 |             -0.154 |              -0.244 | False      |

Perfil do Módulo 1 escolhido no treino: 1 straddle P1

## Resumo por estrutura, execução e período

| estrutura          | execucao   | periodo   |   n |   media |   acerto |   total |
|:-------------------|:-----------|:----------|----:|--------:|---------:|--------:|
| 1 straddle P1      | meio       | treino    |  58 |   0.008 |    0.345 |   0.466 |
| 1 straddle P1      | meio       | validacao |  25 |  -0.048 |    0.24  |  -1.212 |
| 1 straddle P1      | meio_50    | treino    |  62 |  -0.276 |    0.129 | -17.115 |
| 1 straddle P1      | meio_50    | validacao |  28 |  -0.32  |    0.036 |  -8.966 |
| 1 straddle P1      | natural    | treino    |  64 |  -0.433 |    0.078 | -27.742 |
| 1 straddle P1      | natural    | validacao |  28 |  -0.428 |    0.036 | -11.994 |
| 1 straddle P2      | meio       | treino    |  54 |  -0.052 |    0.259 |  -2.811 |
| 1 straddle P2      | meio       | validacao |  24 |  -0.15  |    0.167 |  -3.603 |
| 1 straddle P2      | meio_50    | treino    |  62 |  -0.301 |    0.113 | -18.676 |
| 1 straddle P2      | meio_50    | validacao |  28 |  -0.32  |    0.036 |  -8.966 |
| 1 straddle P2      | natural    | treino    |  64 |  -0.437 |    0.078 | -27.957 |
| 1 straddle P2      | natural    | validacao |  28 |  -0.428 |    0.036 | -11.994 |
| 2a iron condor     | meio       | treino    |  72 |   0.175 |    0.694 |  12.633 |
| 2a iron condor     | meio       | validacao |  64 |   0.357 |    0.641 |  22.816 |
| 2a iron condor     | meio_50    | treino    |  60 |  -0.196 |    0.35  | -11.769 |
| 2a iron condor     | meio_50    | validacao |  59 |  -0.19  |    0.203 | -11.223 |
| 2a iron condor     | natural    | treino    |  46 |  -0.25  |    0.261 | -11.522 |
| 2a iron condor     | natural    | validacao |  70 |  -0.263 |    0.157 | -18.431 |
| 2b crédito a favor | meio       | treino    | 115 |   0.036 |    0.617 |   4.116 |
| 2b crédito a favor | meio       | validacao | 110 |   0.085 |    0.673 |   9.321 |
| 2b crédito a favor | meio_50    | treino    | 108 |  -0.217 |    0.435 | -23.468 |
| 2b crédito a favor | meio_50    | validacao | 102 |  -0.154 |    0.382 | -15.689 |
| 2b crédito a favor | natural    | treino    |  79 |  -0.225 |    0.342 | -17.803 |
| 2b crédito a favor | natural    | validacao | 105 |  -0.244 |    0.267 | -25.599 |

## Dias de sinal por ETF

| etf   |   barata |   cara |
|:------|---------:|-------:|
| DIA   |       18 |     82 |
| EEM   |       35 |    116 |
| GLD   |        8 |     75 |
| IWM   |       21 |     63 |
| QQQ   |       15 |     77 |
| SMH   |        5 |     43 |
| SPY   |       12 |     96 |
| TLT   |       54 |     64 |
| XBI   |       23 |     81 |
| XLE   |       27 |    116 |
| XLF   |       23 |    145 |
| XLK   |       19 |     62 |

## Razão IV/HV (mediana por ETF)

| etf   |   count |   25% |   50% |   75% |
|:------|--------:|------:|------:|------:|
| DIA   |     868 |  0.99 |  1.18 |  1.33 |
| EEM   |     841 |  0.98 |  1.1  |  1.31 |
| GLD   |     868 |  0.87 |  1.03 |  1.18 |
| IWM   |     868 |  0.96 |  1.13 |  1.29 |
| QQQ   |     868 |  0.95 |  1.13 |  1.33 |
| SMH   |     858 |  0.92 |  1.06 |  1.21 |
| SPY   |     868 |  0.99 |  1.2  |  1.41 |
| TLT   |     868 |  0.96 |  1.13 |  1.27 |
| XBI   |     868 |  0.98 |  1.14 |  1.29 |
| XLE   |     854 |  1.04 |  1.16 |  1.33 |
| XLF   |     850 |  1.07 |  1.25 |  1.44 |
| XLK   |     868 |  0.92 |  1.06 |  1.27 |