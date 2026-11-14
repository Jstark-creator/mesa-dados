# Auditoria Codex — 2026-11-14T15:59Z — commit e6611dc

Reproduzi **exatamente o CSV agregado original**: nenhum perfil oficial passa no treino. Executei cinco versões em `/tmp`, sem internet e sem alterar o repositório. **Não identifiquei erro CRÍTICO que reverta a reprovação.**

As referências abaixo são de [scripts/lab/m6/fase_a.py](/home/runner/work/mesa-dados/mesa-dados/scripts/lab/m6/fase_a.py), salvo indicação.

### Achados

1. **MÉDIO — Desfechos do treino invadem a validação — linhas 119–130.**  
   O período é definido pela data do sinal, mas os 30 pregões seguintes podem alcançar 2019. Assim, a seleção do perfil pode incorporar resultados posteriores ao corte do treino.  
   **Correção conservadora:** removi do treino eventos cujo horizonte completo ultrapassa 2018. C2 compra, perfil atual: **N 356 → 353; P 24,72% → 24,93%; lift 0,878 → 0,879**. Nenhum perfil passa. A validação permanece igual.

2. **MÉDIO — Fechamento de referência não equivale a entrada executável — linhas 102–122 e 56.**  
   Volume total, fechamento, médias e confirmação do rompimento só ficam conhecidos ao terminar o candle; as barreiras são ancoradas nesse mesmo fechamento. Isso é aceitável para um estudo de eventos, mas não demonstra execução naquele preço.  
   **Sensibilidade:** mantive os sinais e σ, ancorando as barreiras na abertura seguinte. Na validação, perfil atual: C2 compra **P 25,00% → 24,03%**; C1 compra **17,71% → 16,67%**. Nenhum aprovado.

3. **MÉDIO — Base incondicional limita a interpretação do lift — linhas 127–137.**  
   A base reúne todos os dias elegíveis por preço e horizonte, sem os filtros oficiais, deduplicação ou pareamento por distribuição de ativos/datas. Portanto, o lift compara o **pacote completo** contra dias genéricos; não isola a contribuição de C1/C2 dentro dos filtros. Os muitos horizontes sobrepostos também não são observações independentes.  
   **Sensibilidade:** exigindo os mesmos filtros oficiais e espaço na base, C2 compra/atual na validação: **P_base 28,20% → 29,72%; lift 0,887 → 0,841**. Nenhum perfil passa. Essa alternativa ainda não constitui pareamento completo.

4. **MÉDIO — Universo retrospectivo e filtro nominal sobre preços ajustados — linhas 79–94 e 113.**  
   [config/universo_m6.json:2](/home/runner/work/mesa-dados/mesa-dados/config/universo_m6.json:2) declara expressamente uma lista atual, com sobrevivência. Isso afeta tanto a amostra quanto o ranking histórico: não representa as ações elegíveis em cada época. Dos **157 nomes configurados, entram 155**: MMC está ausente e ROKU tem somente dois registros.  
   Além disso, o carregamento usa `auto_adjust=True` em [atualizar_dados.py:60](/home/runner/work/mesa-dados/mesa-dados/scripts/atualizar_dados.py:60). Aplicar `close > 20` nessa série não reproduz o preço nominal histórico: ajustes posteriores podem mudar a elegibilidade passada. Não há dados locais suficientes para corrigir integralmente esses efeitos.

5. **MÉDIO — “Empate” não é equilíbrio financeiro demonstrado — linhas 50–64 e 138.**  
   O resultado é binário: alvo antes do stop vale 1; stop, empate intradiário e expiração sem alvo valem 0. Não existe cálculo de R realizado, saída por tempo, custos, spread ou execução dos gaps. Além disso, `b/(a+b)` corresponde às distâncias em log, não exatamente às perdas/ganhos monetários das barreiras exponenciais.  
   Isso não invalida a métrica pré-definida, mas impede interpretar `P ≥ 1,2×empate` como rentabilidade líquida, especialmente em opções. A abertura também poderia esclarecer alguns casos em que alvo e stop aparecem no mesmo candle; o código classifica todos como fracasso, conservadoramente.

### O que está correto

- **Pivôs, linhas 28–47:** apesar do cálculo retrospectivo dos candidatos, cada pivô só é disponibilizado em `t ≥ índice+3`. Testei todos os prefixos de uma série sintética: adicionar futuro não alterou os valores já disponíveis.
- **Ranking, linhas 90–94:** cross-sectional por data, usando `t−126 → t−21`; não há percentil calculado sobre toda a história nem `bfill`. Empates recebem posto médio, sem prioridade arbitrária por ticker.
- **ATR, volume médio e rompimentos:** referências anteriores corretamente deslocadas. Desfechos começam em `t+1`; os últimos 30 pregões sem horizonte completo ficam excluídos.
- **Dedup, linhas 68–75:** causal, por ativo/setup/lado/perfil/versão; aceita índices 0, 10, 20. Não elimina sobreposição com H=30, o que exige cautela estatística.
- **σ atual, linha 103:** disponível após o fechamento, portanto não é lookahead nessa convenção. Com σ até ontem, C1 compra/atual na validação melhora **17,71% → 30,93%**, mas continua reprovado. Nenhum perfil oficial passa nessa variante.
- A escolha consulta somente candidatos aprovados no treino. Não encontrei produção M6 para comparar. O pré-registro externo citado no cabeçalho está ausente; a fidelidade foi confrontada com o resumo fornecido.

## Veredito
A conclusão **“nada aprovado” se mantém** na reprodução e em todas as sensibilidades executadas.  
Os pivôs e o ranking não apresentam o lookahead suspeitado; σ atual afeta bastante C1, mas sua defasagem não produz aprovação.  
A separação treino/validação precisa de purga, e os resultados continuam sendo evidência de eventos, sem comprovação de rentabilidade executável.  
A reprovação sustenta não avançar; não demonstra que toda reformulação futura desses setups seja inútil.