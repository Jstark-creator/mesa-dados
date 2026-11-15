# M7 — Preço da volatilidade (gerado automaticamente; cotações reais ThetaData)

ETFs incluídos (cadeia completa): ['SPY', 'QQQ', 'IWM', 'DIA', 'XLK', 'GLD', 'TLT']

## Decisão pré-registrada

| estrutura          |   n_treino |   media_treino_meio50 |   n_val |   media_val_meio50 |   media_val_natural | aprovado   |
|:-------------------|-----------:|----------------------:|--------:|-------------------:|--------------------:|:-----------|
| 1 straddle P2      |         17 |                -0.111 |      13 |             -0.188 |              -0.241 | False      |
| 2a iron condor     |         21 |                 0.039 |      23 |              0.018 |              -0.044 | False      |
| 2b crédito a favor |         33 |                -0.041 |      38 |             -0.006 |              -0.02  | False      |

Perfil do Módulo 1 escolhido no treino: 1 straddle P2

## Resumo por estrutura, execução e período

| estrutura          | execucao   | periodo   |   n |   media |   acerto |   total |
|:-------------------|:-----------|:----------|----:|--------:|---------:|--------:|
| 1 straddle P1      | meio       | treino    |  17 |  -0.107 |    0.176 |  -1.824 |
| 1 straddle P1      | meio       | validacao |  14 |  -0.136 |    0.286 |  -1.908 |
| 1 straddle P1      | meio_50    | treino    |  17 |  -0.129 |    0.176 |  -2.188 |
| 1 straddle P1      | meio_50    | validacao |  13 |  -0.195 |    0.154 |  -2.538 |
| 1 straddle P1      | natural    | treino    |  17 |  -0.156 |    0.176 |  -2.659 |
| 1 straddle P1      | natural    | validacao |  14 |  -0.256 |    0.143 |  -3.586 |
| 1 straddle P2      | meio       | treino    |  17 |  -0.09  |    0.176 |  -1.522 |
| 1 straddle P2      | meio       | validacao |  13 |  -0.155 |    0.231 |  -2.014 |
| 1 straddle P2      | meio_50    | treino    |  17 |  -0.111 |    0.176 |  -1.895 |
| 1 straddle P2      | meio_50    | validacao |  13 |  -0.188 |    0.154 |  -2.439 |
| 1 straddle P2      | natural    | treino    |  17 |  -0.14  |    0.176 |  -2.375 |
| 1 straddle P2      | natural    | validacao |  14 |  -0.241 |    0.143 |  -3.379 |
| 2a iron condor     | meio       | treino    |  24 |   0.091 |    0.75  |   2.195 |
| 2a iron condor     | meio       | validacao |  23 |   0.043 |    0.783 |   0.982 |
| 2a iron condor     | meio_50    | treino    |  21 |   0.039 |    0.714 |   0.809 |
| 2a iron condor     | meio_50    | validacao |  23 |   0.018 |    0.739 |   0.415 |
| 2a iron condor     | natural    | treino    |  22 |  -0.035 |    0.545 |  -0.763 |
| 2a iron condor     | natural    | validacao |  26 |  -0.044 |    0.538 |  -1.138 |
| 2b crédito a favor | meio       | treino    |  33 |  -0.017 |    0.606 |  -0.565 |
| 2b crédito a favor | meio       | validacao |  40 |  -0.006 |    0.675 |  -0.229 |
| 2b crédito a favor | meio_50    | treino    |  33 |  -0.041 |    0.576 |  -1.364 |
| 2b crédito a favor | meio_50    | validacao |  38 |  -0.006 |    0.684 |  -0.23  |
| 2b crédito a favor | natural    | treino    |  33 |  -0.059 |    0.545 |  -1.943 |
| 2b crédito a favor | natural    | validacao |  38 |  -0.02  |    0.632 |  -0.778 |

## Dias de sinal por ETF

| etf   |   barata |   cara |
|:------|---------:|-------:|
| DIA   |       18 |     82 |
| GLD   |        8 |     76 |
| IWM   |       25 |     67 |
| QQQ   |       17 |     78 |
| SPY   |       13 |     96 |
| TLT   |       54 |     63 |
| XLK   |       15 |      0 |

## Razão IV/HV (mediana por ETF)

| etf   |   count |   25% |   50% |   75% |
|:------|--------:|------:|------:|------:|
| DIA   |     868 |  1    |  1.18 |  1.33 |
| GLD   |     868 |  0.87 |  1.03 |  1.18 |
| IWM   |     868 |  0.96 |  1.13 |  1.29 |
| QQQ   |     868 |  0.96 |  1.13 |  1.33 |
| SPY   |     868 |  0.99 |  1.19 |  1.41 |
| TLT   |     868 |  0.96 |  1.13 |  1.26 |
| XLK   |     341 |  1    |  1.28 | 14.41 |