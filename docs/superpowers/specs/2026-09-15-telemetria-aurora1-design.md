# Verificador de Telemetria Pré‑Lançamento — Missão Aurora‑1

**Data:** 2026-09-15
**Contexto:** Atividade Integradora FIAP, Fase 1. Entrega em `entrega-fase1/`.

## 1. Objetivo

Construir um sistema que leia a telemetria de um foguete na janela T‑10 min,
decida entre **PRONTO PARA DECOLAR** e **DECOLAGEM ABORTADA**, e calcule a
autonomia energética da missão. A entrega é avaliada em 5 critérios de 2 pontos:
organização da telemetria, algoritmo de verificação, script Python funcional,
análise energética e documentação (PDF + repositório GitHub público com README).

## 2. Premissas

O enunciado não fornece dados nem faixas seguras. Todos os valores abaixo foram
definidos por nós e estão documentados como premissas no relatório. Eles são
plausíveis para um veículo lançador de carga com propelentes LOX/RP‑1, mas não
representam um veículo real.

## 3. Modelo de dados

Telemetria em `entrega-fase1/data/telemetria.json`, com três cenários:
`nominal`, `falha_termica` e `falha_multipla`.

| Parâmetro | Chave | Unidade | Faixa segura | Nominal |
|---|---|---|---|---|
| Temperatura interna (aviônica) | `temperatura_interna_c` | °C | 18 – 28 | 23,4 |
| Temperatura externa (fuselagem) | `temperatura_externa_c` | °C | −40 – 50 | 12,8 |
| Integridade estrutural | `integridade_estrutural` | 0/1 | = 1 | 1 |
| Nível de energia | `nivel_energia_pct` | % | ≥ 85 | 92 |
| Pressão tanque LOX | `pressao_lox_bar` | bar | 200 – 250 | 228 |
| Pressão tanque RP‑1 | `pressao_rp1_bar` | bar | 190 – 240 | 214 |
| Módulos críticos | `modulos_criticos` | OK/FALHA | todos OK | todos OK |

Módulos críticos: navegação, comunicação, propulsão, controle térmico,
suporte de vida.

## 4. Algoritmo de verificação

Regra de decisão: a missão é liberada somente se **todas** as verificações
passarem. O algoritmo **não** para na primeira falha — avalia todos os
parâmetros e devolve a lista completa de motivos, porque um relatório de
aborto parcial esconderia problemas do operador.

Saída: um objeto de resultado com `aprovado: bool`, `decisao: str` e
`falhas: list[str]` (motivo legível por parâmetro reprovado).

Representações exigidas pelo enunciado:
- fluxograma em Mermaid — `entrega-fase1/docs/fluxograma.md`
- pseudocódigo em português estruturado — `entrega-fase1/docs/pseudocodigo.md`

Ambos devem descrever exatamente a lógica implementada em `src/missao.py`.

## 5. Análise energética

Constantes: capacidade 120 kWh, carga 92%, perdas 8%, consumo na decolagem
45 kWh, consumo em voo 6,5 kW, margem mínima exigida 20%.

```
disponivel_kwh   = capacidade × carga × (1 − perdas) = 120 × 0,92 × 0,92 = 101,57
restante_kwh     = disponivel − consumo_decolagem     = 101,57 − 45      =  56,57
autonomia_h      = restante ÷ consumo_voo             =  56,57 ÷ 6,5     ≈   8,70
margem_pct       = (disponivel − consumo) ÷ consumo   ≈ 125,7 %
```

A margem é comparada ao mínimo de 20%; o resultado entra no relatório como
parecer energético (aprovado/reprovado), separado da decisão de lançamento.

## 6. Arquitetura

```
entrega-fase1/
├── README.md                 explicação, instruções de execução, prints
├── requirements.txt
├── data/telemetria.json
├── src/missao.py             faixas, carregamento, verificações, energia
├── tests/test_missao.py      pytest
├── notebooks/analise_telemetria.ipynb
└── docs/
    ├── relatorio.md → relatorio.pdf
    ├── fluxograma.md
    ├── pseudocodigo.md
    └── prints/               screenshots preenchidos pelo usuário
```

`src/missao.py` é a única fonte da lógica. Módulo pequeno e sem estado, com
funções puras: `carregar_telemetria`, `verificar_telemetria`,
`analisar_energia`, `formatar_relatorio`. O notebook **importa** esse módulo
(com bootstrap de `sys.path` e uma célula opcional de `git clone` para Colab)
em vez de redefinir a lógica — assim os testes cobrem o mesmo código que o
avaliador executa.

## 7. Testes

pytest sobre `src/missao.py`:
- cada parâmetro numérico nos limites inferior e superior, dentro e fora;
- integridade estrutural 0 e 1;
- módulo crítico em FALHA;
- cenário nominal → aprovado;
- cenário multi‑falha → reprovado com todos os motivos presentes;
- cálculo energético contra valores calculados à mão.

## 8. Análise assistida por IA (item 1.5)

Seção do notebook e do relatório contendo: o prompt enviado à IA, a resposta
(classificação dos dados, anomalias identificadas, riscos sugeridos) e um
comentário crítico do autor sobre onde a IA acertou e onde seria imprudente
confiar nela. Sem chamada de API em tempo de execução — o notebook roda sem
chave.

## 9. Reflexão crítica (item 1.6)

Texto no relatório sobre ética e responsabilidade em decisões automatizadas de
lançamento, impacto social da exploração espacial e sustentabilidade
tecnológica.

## 10. Entrega

- Relatório: `docs/relatorio.md` convertido para `docs/relatorio.pdf`.
- Git: repositório inicializado na raiz do projeto, commits organizados.
- GitHub: publicação via `gh` somente após revisão e autorização explícita do
  usuário, que também define o nome do repositório.
- Prints de execução: o usuário captura e adiciona em `docs/prints/`; o README
  já traz os espaços marcados.

## 11. Fora de escopo

Interface gráfica, leitura de telemetria em tempo real, integração com hardware,
persistência em banco de dados, chamada de API de IA em runtime.
