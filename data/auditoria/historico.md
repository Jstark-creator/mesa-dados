# Histórico de auditorias

## 13/11/2026 — auditoria Claude (agente independente)
Achados corrigidos: entrada "acionado" da M3 (risco real 1,8× o informado); vagas da E2 em produção; desempate por mom28 no laboratório da E2; candle parcial no laboratório.
Achados registrados (sem correção possível no código): vantagem da M3 em call ATM depende do modelo de IV (HV×1,1), do slippage e dos vencedores ex-post; short da E1 escolhido pela validação; trava de put ~0R desde 2021; funding fixo; viés de sobrevivência.
Detalhes no Projeto: estrategias/auditoria-2026-11-13.md.

## 13/11/2026 — auditoria Codex (segunda opinião), relatório data/auditoria/codex-2026-11-13-1928.md
Reproduziu E1 (+0,728R, 63 ops; +0,654R com long em futuros) e E2 (+1,149R, 66 ops).
Novos achados, ainda NÃO corrigidos:
- CRÍTICO: laboratório de opções precifica saídas intradiárias com HV que inclui o fechamento do mesmo dia (call IVP<40% desde 2021: +0,133R → +0,073R corrigindo).
- CRÍTICO: m3.py caso B (rompimento em c4) ainda informa entrada sem checar se o stop já foi atingido em c4.
- MÉDIO: cripto.py estado() sem o piso de risco de 0,3%; saída no lab no fechamento vs. produção na abertura (impacto ~0).
- MÉDIO: sinais de opções herdados da v1 (seleção), posições sobrepostas no mesmo ticker (17 de 376).
- MÉDIO: opcoes.py aceita last sem bid/ask, dimensiona no meio do spread, usa preço de entrada do sinal como spot; percentil de IV real difere do laboratório (empates/filtro de data).
- MÉDIO: drawdown das carteiras de opções só com resultado realizado; c2_rotacao compra no fechamento da decisão; c1_grade ordena pela validação.
Sensibilidade (call, desde 2021): IV×1,1 com slippage 2/5/10% = +0,23/+0,16/+0,05R; IV×1,3 = +0,17/+0,10/−0,01R; IV×1,5 = +0,12/+0,05/−0,05R. Put 0,30/0,15: −0,02 a +0,08R.
Concordância com a auditoria Claude: E1/E2 positivas; vantagem da M3 em opções é hipótese, não demonstrada.
