# mesa-dados

Fábrica de dados da mesa de operações do Gustavo. Roda de graça no GitHub Actions e alimenta os agentes (J.Barsi, J.Buffet, J.Taleb, J.Master, J.James).

## O que acontece todo dia
Às 19h15 (Asunción/Brasília), de segunda a sexta, a Action **Coleta diária e sinais M3**:
1. Baixa os candles diários dos ativos da watchlist (EUA, B3 e BTC/ETH) pela biblioteca [yfinance](https://github.com/ranaroussi/yfinance).
2. Calcula a MME 9, a MMS 20 e o IFR 14.
3. Procura sinais da estratégia **M3 (Playbook v1.0)**: padrão de 3 candles, filtro de tendência pelas médias, filtro de IFR 50, stop no extremo do padrão e alvo na Fibonacci de 200%.
4. Salva tudo na pasta `data/`.

## Arquivos
| Arquivo | Conteúdo |
|---|---|
| `data/sinais/hoje.json` | Sinais M3 do último pregão ("armado" = entrada no próximo pregão; "acionado" = já rompeu) |
| `data/sinais/historico.csv` | Todos os sinais já detectados |
| `data/resumo.json` | Foto de cada ativo: preço, variação, IFR, tendência, máx./mín. de 52 semanas |
| `data/mercado.json` | Índices, VIX, dólar, juros, ouro e petróleo |
| `data/precos/<TICKER>.csv` | ~2 anos de candles com indicadores |
| `data/historico/<TICKER>.csv` | 20 anos de candles, para backtest |
| `data/status.json` | Quando rodou e quais ativos falharam |

## Rodar na mão
Aba **Actions** → escolha a Action → **Run workflow**.

## Como mudar a watchlist
Edite `config/watchlist.json`. Ativos da B3 sem o sufixo (o script adiciona `.SA`).

## Aviso
A yfinance não é oficial (usa dados públicos do Yahoo Finance). Se o Yahoo mudar algo, a coleta pode falhar por alguns dias até a biblioteca ser atualizada. O `data/status.json` mostra as falhas. Uso pessoal, sem recomendação de investimento.
