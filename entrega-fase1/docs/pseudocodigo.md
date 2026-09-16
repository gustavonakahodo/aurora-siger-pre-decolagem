# Pseudocódigo do algoritmo de verificação

```
ALGORITMO VerificacaoPreLancamento

CONSTANTES
    TEMP_INTERNA_MIN   <- 18.0     TEMP_INTERNA_MAX   <- 28.0     // °C
    TEMP_EXTERNA_MIN   <- -40.0    TEMP_EXTERNA_MAX   <- 50.0     // °C
    PRESSAO_LOX_MIN    <- 200.0    PRESSAO_LOX_MAX    <- 250.0    // bar
    PRESSAO_RP1_MIN    <- 190.0    PRESSAO_RP1_MAX    <- 240.0    // bar
    ENERGIA_MINIMA     <- 85.0                                    // %
    MODULOS_CRITICOS   <- [navegação, comunicação, propulsão,
                           controle térmico, suporte de vida]
    CAPACIDADE_TOTAL   <- 120.0    // kWh
    PERDAS             <- 8.0      // %
    CONSUMO_DECOLAGEM  <- 45.0     // kWh
    CONSUMO_VOO        <- 6.5      // kW
    MARGEM_MINIMA      <- 20.0     // %

INÍCIO
    LER telemetria DO cenário escolhido
    falhas <- lista vazia

    // 1. Parâmetros com faixa de mínimo e máximo (limites inclusivos)
    SE NÃO (TEMP_INTERNA_MIN <= telemetria.temperatura_interna <= TEMP_INTERNA_MAX) ENTÃO
        ADICIONAR "Temperatura interna fora da faixa segura" EM falhas
    FIM SE
    SE NÃO (TEMP_EXTERNA_MIN <= telemetria.temperatura_externa <= TEMP_EXTERNA_MAX) ENTÃO
        ADICIONAR "Temperatura externa fora da faixa segura" EM falhas
    FIM SE
    SE NÃO (PRESSAO_LOX_MIN <= telemetria.pressao_lox <= PRESSAO_LOX_MAX) ENTÃO
        ADICIONAR "Pressão do tanque de LOX fora da faixa segura" EM falhas
    FIM SE
    SE NÃO (PRESSAO_RP1_MIN <= telemetria.pressao_rp1 <= PRESSAO_RP1_MAX) ENTÃO
        ADICIONAR "Pressão do tanque de RP-1 fora da faixa segura" EM falhas
    FIM SE

    // 2. Parâmetro binário
    SE telemetria.integridade_estrutural <> 1 ENTÃO
        ADICIONAR "Integridade estrutural comprometida" EM falhas
    FIM SE

    // 3. Parâmetro com mínimo apenas
    SE telemetria.nivel_energia < ENERGIA_MINIMA ENTÃO
        ADICIONAR "Nível de energia abaixo do mínimo" EM falhas
    FIM SE

    // 4. Estado dos módulos críticos
    modulos_em_falha <- lista vazia
    PARA CADA modulo EM MODULOS_CRITICOS FAÇA
        SE telemetria.modulos_criticos[modulo] <> "OK" ENTÃO
            ADICIONAR modulo EM modulos_em_falha
        FIM SE
    FIM PARA
    SE modulos_em_falha NÃO ESTÁ VAZIA ENTÃO
        ADICIONAR "Módulos críticos em falha: " + modulos_em_falha EM falhas
    FIM SE

    // 5. Balanço energético (informativo, não bloqueia a decisão)
    disponivel <- CAPACIDADE_TOTAL * (telemetria.nivel_energia / 100)
                                   * (1 - PERDAS / 100)
    restante   <- disponivel - CONSUMO_DECOLAGEM
    SE restante > 0 ENTÃO
        autonomia <- restante / CONSUMO_VOO
    SENÃO
        autonomia <- 0
    FIM SE
    margem <- (restante / CONSUMO_DECOLAGEM) * 100

    // 6. Decisão
    SE falhas ESTÁ VAZIA ENTÃO
        decisao <- "PRONTO PARA DECOLAR"
    SENÃO
        decisao <- "DECOLAGEM ABORTADA"
    FIM SE

    ESCREVER telemetria, disponivel, restante, autonomia, margem
    ESCREVER decisao
    SE falhas NÃO ESTÁ VAZIA ENTÃO
        ESCREVER cada item de falhas
    FIM SE
FIM
```

## Decisões de projeto registradas no algoritmo

1. **Os limites são inclusivos.** Uma leitura de exatamente 28,0 °C é
   aprovada. A faixa segura é o intervalo fechado, não o aberto.
2. **A avaliação não interrompe na primeira falha.** Todas as verificações
   rodam sempre, e a saída traz a lista completa de motivos.
3. **A análise energética não bloqueia o lançamento.** Ela produz um parecer
   próprio (margem adequada ou insuficiente). O nível de carga em si já é
   verificado no item 3; a margem serve para o planejamento da missão depois
   da decolagem.
