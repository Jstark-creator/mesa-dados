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

## 13/11/2026 (noite) — c3_ordens_stop.py e etf/matriz.py — auditoria Claude + Codex (codex-2026-11-13-1951.md)
Cripto por ordens stop: números reproduzidos; sem lookahead nos níveis. Dependência extrema de poucas operações (sem as 5 maiores: E1 2,0R, E2 −9,4R); sobrevivência (SOL = 33R de 79R na E2); carteira E2 deve reservar vagas no fechamento anterior (simulação correta: +1,10R, 86,1R); aquecimento duplicado corrigido pelo Codex: E2 +0,887R, 75,4R.
ETFs: nada útil a 10% de slippage; com skew estilizado, crédito put e condor ≈ 0–0,02R; trava de débito em SPY/QQQ em tendência ~+0,05–0,10R (t≈2), efeito direcional e não de IV; execução causal não muda as médias. Precisa de cadeia real antes de playbook.

## 14/11/2026 — M4 Fase A (estudo de eventos pré-registrado) — auditoria Claude + Codex (codex-2026-11-14-1432.md)
Nenhum dos 12 setups (S1/S2/S3 × compra/venda, EUA e BR) aprovado: P(+1σ antes de −0,5σ) ≈ base aleatória; lift 0,8–1,3.
Auditor Claude: código fiel ao pré-registro; base bate com passeio aleatório simulado (EUA 26,7%, BR 22,6%); barras paradas na B3 favoreciam S1 venda BR (lift treino 1,32 → 1,21). Codex: sem erro crítico; ressalvas médias que não revertem a conclusão.
Único candidato informativo para v2: S1 compra em ETFs EUA (validação P=43%, lift 1,50, N=130; treino 1,09) — só testável ao vivo/papel.

## 14/11/2026 — M5 Fase A (tendência em ETFs) — auditoria Claude (+ Codex automático)
Reprovado e confirmado: calls lift 1,08–1,09 sobre a base (P_val 34%); puts ~1,03. Implementação fiel; base coerente com passeio aleatório (H=50: ~27%).
Informativo: contra meses FORA do regime, calls 1,31 (treino) / 1,26 (validação), IC90% 1,02–1,60; puts sem sinal. Efeito heterogêneo por ETF (SPY/SMH/XLF/QQQ fortes; XLE/IWM fracos). Qualquer exploração exige novo pré-registro (M6) sem reaproveitar estes dados para decidir.

## 14/11/2026 — M6 Fase A (catalisador + força relativa, 155 ações) — auditoria Claude + Codex (codex-2026-11-14-1559.md)
Nada aprovado; confirmado pelos dois auditores, sem lookahead em pivôs/ranking/filtros. Robusto a: σ até ontem, sem filtro de preço > US$20 (que usava preço AJUSTADO e cortava 31% do treino — corrigir em pré-registros futuros), e as duas mudanças juntas.
Ressalvas: C1 call com σ até ontem chegou perto no treino (P 0,37–0,39, lift 1,32–1,37) mas caiu na validação (lift 1,10–1,13); puts sem amostra (N 6–50) — não concluem nada. Codex: separação treino/validação deveria ter purga de H dias.
Padrões para próximos pré-registros: σ até ontem; filtros de preço com preço nominal; purga de H dias entre treino e validação.

## 15/11/2026 — M7 (preço da volatilidade), rodada preliminar com 7 ETFs — auditoria Claude (+ Codex automático)
Nada aprovado: straddle −0,11/−0,19R (treino/val., meio_50); condor +0,04/+0,02R (−0,04 a mercado); crédito ≈0. IC95% excluem +0,15R nos três; efeitos pequenos (0,03–0,05R) não detectáveis com N 13–40.
Bugs corrigidos antes da rodada oficial com 12 ETFs (regras inalteradas): (1) percentil contava dias sem IV como "não menor" (favorecia "barata"); (2) XLK com desdobramento: yfinance auto_adjust=False ajusta splits retroativamente, ThetaData não → agora o preço usado na precificação é o implícito pela paridade put-call na própria cadeia e a HV vem de retornos ajustados. XLK só afetava o straddle (para melhor). Pendências do auditor: delta ±0,08 não estava no pré-registro; operações sem cotação até o fim são descartadas sem registro; limite de grupo aplicado por cenário.

## 15/11/2026 — M7 rodada OFICIAL (12 ETFs) — auditoria Claude + Codex (codex-2026-11-15-0813.md)
NADA APROVADO. Validação meio_50: straddle −0,32R, condor −0,19R, crédito −0,15R (a mercado: −0,43 / −0,26 / −0,24).
O ganho no cenário "meio" (condor +0,26R; XLF +0,79R) é artefato: cotações de fechamento largas/velhas em XLF, XLE, XBI, EEM, SMH, XLK (spread de 25–100% do prêmio; condor XLF com crédito ~95% da largura, impossível). Só ETFs líquidos (SPY, QQQ, IWM, GLD, TLT, DIA): condor +0,06 meio / −0,01 meio_50 / −0,07 natural; crédito −0,02/−0,03/−0,03; straddle −0,18/−0,22/−0,31.
Correções (percentil sem NaN; spot por paridade; HV ajustada) confirmadas como corretas. Para próximos testes com cotações reais: filtro de qualidade (spread relativo por perna < 10% do meio), amostra pareada entre cenários, registrar operações sem cotação em vez de descartar.

## 17/11/2026 — Cripto v2, camada L (100/50, 3 ATR) — auditoria Claude + Codex (codex-2026-11-17-1801.md)
L long passa na letra do critério (valid. 14 ops, +0,49R, +6,9R), mas é concentrada (top-3 +15,8R, resto −8,9R; 2025–26 negativo); o bootstrap tem ~27% de médias ≤0. L short REPROVADA (treino −0,13R).
DECISÃO: L long só EM PAPEL (bloco camada_l_papel em sinais.json); reavaliar após 10 operações novas. A tendência (45%) opera só a camada M em BTC+ETH.
Achados Codex a corrigir em base.py: (1) operações abertas tratadas como fechadas (M short validação 34→32 ops, +12,0→+10,6R); (2) encerramento oculto após 400 candles; (3) saída no fechamento do sinal vs abertura seguinte na produção (impacto ~0); (4) drawdown deve ser marcado a mercado (camada M: −19R, não −7R).
Padrão novo: drawdown sempre marcado a mercado diariamente, e "diversificação" medida sob orçamento de risco comum.
