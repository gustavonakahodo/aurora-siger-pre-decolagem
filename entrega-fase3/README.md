# Colônia Aurora Siger — Sistema Integrado de Energia

**FIAP — Atividade Integradora, Fase 3: A Aurora Estabelece os Primeiros Sistemas da Colônia**

| | |
|---|---|
| **Nome completo** | Gustavo Hiroshi Fernandes Nakahodo |
| **RM** | 576337 |
| **Turma** | Ciência da Computação (On-Line) |

---

## O que o sistema faz

A colônia gera energia com sol e vento, guarda o que sobra em baterias e
gasta com suporte à vida, estufa, laboratório e o resto do habitat. O sistema
recebe as leituras de um momento e responde, em texto, **o que fazer agora**
e **o que esperar das próximas horas**. São quatro passos, um por módulo:

1. **Organiza os dados** (`src/dados.py`) — o histórico fica em listas, os
   cenários em tabelas chave-valor e os sistemas da colônia em uma árvore
   (`energia → geração → solar / eólico`). O consumo total não é digitado:
   é a soma dos equipamentos ligados, calculada percorrendo a árvore.
2. **Analisa a energia** (`src/energia.py`) — compara geração e consumo:
   se falta, alerta e diz por quantas horas a reserva aguenta; se sobra,
   sugere armazenar.
3. **Decide** (`src/decisoes.py`) — aplica regras do tipo "se reserva < 50 E
   consumo alto → modo economia" e escolhe o que desligar pela prioridade:
   primeiro lazer e laboratório, depois estufa e iluminação. Suporte à vida
   nunca é desligado.
4. **Prevê** (`src/previsao.py`) — ajusta uma reta ao histórico (vento ×
   energia eólica, irradiância × energia solar) e estima a geração da próxima
   janela a partir da previsão do clima. Com isso o sistema avisa **antes**
   de o problema chegar.

`src/colonia.py` junta os quatro e imprime o relatório.

O sistema também se protege de dados ruins: recusa leituras impossíveis
(reserva fora de 0–100 %, geração negativa) com uma mensagem clara, e avisa
quando o clima previsto está fora da faixa do histórico — nesse caso a reta
está extrapolando e a previsão merece desconfiança.

### Regras de decisão

| Condição | Saída |
|---|---|
| reserva < 20 % | `CRÍTICO: manter apenas sistemas essenciais` |
| reserva < 50 % **E** consumo > 60 kW | `ALERTA: reduzir consumo — modo economia ativado` |
| reserva < 50 % | `ALERTA: reduzir consumo` |
| consumo > geração, reserva ≥ 50 % | `ATENÇÃO: consumo acima da geração — usando a reserva` |
| nenhuma das anteriores | `NORMAL: operação normal` |

As regras são testadas nessa ordem e vale a primeira que se aplica. A mesma
tabela é aplicada duas vezes: às leituras de agora e à projeção da próxima
janela. Se a projeção for pior — nível mais grave, ou mesmo nível com a
reserva caindo —, a decisão ganha uma linha `PREVENTIVO`.

## Estrutura

```
entrega-fase3/
├── README.md
├── requirements.txt        # só pytest, para os testes
├── data/
│   └── colonia.json        # DADOS: hierarquia, histórico e cenários
├── src/
│   ├── dados.py            # carregar e navegar a hierarquia
│   ├── energia.py          # LÓGICA: balanço geração × consumo × reserva
│   ├── previsao.py         # LÓGICA: regressão linear
│   ├── decisoes.py         # DECISÕES: regras e prioridades
│   └── colonia.py          # integração, relatório e linha de comando
├── tests/                  # 101 testes automatizados
└── docs/
    ├── relatorio.md        # relatório da entrega
    └── relatorio.pdf       # o mesmo relatório, em PDF
```

## Como executar

Python 3.10 ou superior. Nenhuma biblioteca externa é necessária. Se o seu
sistema não tiver o comando `python`, use `python3`.

```bash
cd entrega-fase3
python src/colonia.py               # cenário nominal
python src/colonia.py economia      # reserva baixa e consumo alto
python src/colonia.py critico       # reserva quase esgotada
python src/colonia.py preventivo    # bem agora, mal na previsão
```

Para rodar os testes:

```bash
pip install pytest
pytest tests/ -v
```

São 101 testes. Além dos casos escolhidos a dedo (os exemplos do enunciado e
as fronteiras de cada limite), `tests/test_propriedades.py` sorteia milhares
de entradas e verifica o que tem de valer sempre — por exemplo, que nenhuma
decisão desliga um sistema essencial e que a reta ajustada é a de menor erro.

## Exemplo de entrada e saída

### Entrada

O cenário `economia` de `data/colonia.json` — o exemplo do enunciado, com
energia (reserva) em 40 e consumo em 70:

```json
"economia": {
  "reserva_pct": 40.0,
  "geracao_solar_kw": 21.0,
  "geracao_eolica_kw": 19.0,
  "previsao_clima": {"vento_ms": 6, "irradiancia_wm2": 200},
  "ligados": [
    "suporte_vida/oxigenio", "suporte_vida/agua", "suporte_vida/controle_termico",
    "habitat/comunicacao", "habitat/iluminacao", "habitat/estufa",
    "habitat/laboratorio", "habitat/lazer"
  ]
}
```

O consumo de 70 kW não aparece na entrada: sai da soma dos oito equipamentos
ligados. A previsão usa também o histórico do mesmo arquivo:

```json
"vento_ms":          [4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15],
"energia_eolica_kw": [10.2, 12.1, 15.3, 17.4, 20.1, 22.8, 24.7, 27.9, 30.2, 32.1, 35.4, 37.3]
```

### Saída — `python src/colonia.py economia`

```text
==============================================================================
COLÔNIA AURORA SIGER — SISTEMA INTEGRADO DE ENERGIA
Cenário: economia — Reserva baixa e consumo alto: o exemplo do enunciado
         (energia 40, consumo 70).
==============================================================================

1. SISTEMAS DA COLÔNIA
  Colônia
    Sistema energético
      Geração
        Solar                     21.0 kW   gerando
        Eólico                    19.0 kW   gerando
      Armazenamento
        Baterias                   400 kWh  reserva em 40.0 %
    Suporte à vida
      Oxigênio                    12.0 kW   prioridade 1   LIGADO
      Água                         8.0 kW   prioridade 1   LIGADO
      Controle térmico            10.0 kW   prioridade 1   LIGADO
    Habitat
      Comunicação                  4.0 kW   prioridade 1   LIGADO
      Iluminação                   6.0 kW   prioridade 2   LIGADO
      Estufa                      10.0 kW   prioridade 2   LIGADO
      Laboratório                 12.0 kW   prioridade 3   LIGADO
      Lazer                        8.0 kW   prioridade 3   LIGADO

2. SITUAÇÃO ATUAL
  Reserva ........... 40.0 %
  Geração ........... 40.0 kW (solar 21.0 + eólica 19.0)
  Consumo ........... 70.0 kW (soma dos sistemas ligados)
  Saldo ............. -30.0 kW
  Análise ........... ALERTA: consumo maior que geração (reserva cobre 5.3 h)
  Decisão ........... ALERTA: reduzir consumo — modo economia ativado
    regra: reserva 40.0 % < 50 % E consumo 70.0 kW > 60 kW → modo economia
  Desligar .......... Laboratório, Lazer, Estufa
  Consumo após ...... 40.0 kW

3. MODELO DE PREVISÃO (regressão linear sobre o histórico)
  Eólica: energia = 2.4990 × vento + 0.05   (R² = 0.9988, 12 medições)
  Solar : energia = 0.0598 × irradiância + 0.16   (R² = 0.9996, 10 medições)

4. PRÓXIMA JANELA (6 h)
  Clima previsto .... vento 6 m/s, irradiância 200 W/m²
  Geração prevista .. 27.1 kW (solar 12.1 + eólica 15.0)
  Consumo ........... 40.0 kW
  Saldo previsto .... -12.9 kW
  Reserva projetada . 20.7 %
  Análise ........... ALERTA: consumo maior que geração (reserva cobre 6.4 h)
  Decisão ........... ALERTA: reduzir consumo
    regra: reserva 20.7 % < 50 % → reduzir consumo
    regra: mesmo com os cortes possíveis o consumo supera a geração: o que
           ficou ligado é alimentado pela reserva
  Desligar .......... Iluminação
  Consumo após ...... 34.0 kW
  Tendência ......... PIORA

==============================================================================
DECISÃO: ALERTA: reduzir consumo — modo economia ativado
PREVENTIVO: em 6 h a reserva vai de 40.0 % a 20.7 % (situação ALERTA).
            Desligando já Iluminação, a reserva fica em 29.7 %.
==============================================================================
```

### Saída — `python src/colonia.py preventivo`

Aqui está a diferença entre reagir e prever: a situação atual é normal, mas
a previsão de pouco vento e pouco sol levaria a reserva de 65 % a 5,9 % em
seis horas. O sistema avisa antes e mostra o ganho de agir já: com os cortes
antecipados, a reserva termina a janela em 59,9 %.

```text
==============================================================================
COLÔNIA AURORA SIGER — SISTEMA INTEGRADO DE ENERGIA
Cenário: preventivo — Tudo bem agora, mas a previsão indica queda de vento e
         de sol.
==============================================================================

1. SISTEMAS DA COLÔNIA
  Colônia
    Sistema energético
      Geração
        Solar                     42.0 kW   gerando
        Eólico                    33.0 kW   gerando
      Armazenamento
        Baterias                   400 kWh  reserva em 65.0 %
    Suporte à vida
      Oxigênio                    12.0 kW   prioridade 1   LIGADO
      Água                         8.0 kW   prioridade 1   LIGADO
      Controle térmico            10.0 kW   prioridade 1   LIGADO
    Habitat
      Comunicação                  4.0 kW   prioridade 1   LIGADO
      Iluminação                   6.0 kW   prioridade 2   LIGADO
      Estufa                      10.0 kW   prioridade 2   LIGADO
      Laboratório                 12.0 kW   prioridade 3   LIGADO
      Lazer                        8.0 kW   prioridade 3   LIGADO

2. SITUAÇÃO ATUAL
  Reserva ........... 65.0 %
  Geração ........... 75.0 kW (solar 42.0 + eólica 33.0)
  Consumo ........... 70.0 kW (soma dos sistemas ligados)
  Saldo ............. +5.0 kW
  Análise ........... SUGESTÃO: armazenar energia excedente
  Decisão ........... NORMAL: operação normal
    regra: nenhuma condição de risco

3. MODELO DE PREVISÃO (regressão linear sobre o histórico)
  Eólica: energia = 2.4990 × vento + 0.05   (R² = 0.9988, 12 medições)
  Solar : energia = 0.0598 × irradiância + 0.16   (R² = 0.9996, 10 medições)

4. PRÓXIMA JANELA (6 h)
  Clima previsto .... vento 5 m/s, irradiância 300 W/m²
  Geração prevista .. 30.6 kW (solar 18.1 + eólica 12.5)
  Consumo ........... 70.0 kW
  Saldo previsto .... -39.4 kW
  Reserva projetada . 5.9 %
  Análise ........... ALERTA: consumo maior que geração (reserva cobre 0.6 h)
  Decisão ........... CRÍTICO: manter apenas sistemas essenciais
    regra: reserva 5.9 % < 20 % → desligar tudo que não é essencial
    regra: mesmo com os cortes possíveis o consumo supera a geração: o que
           ficou ligado é alimentado pela reserva
  Desligar .......... Laboratório, Lazer, Estufa, Iluminação
  Consumo após ...... 34.0 kW
  Tendência ......... PIORA

==============================================================================
DECISÃO: NORMAL: operação normal
PREVENTIVO: em 6 h a reserva vai de 65.0 % a 5.9 % (situação CRÍTICO).
            Desligando já Laboratório, Lazer, Estufa, Iluminação, a reserva
            fica em 59.9 %.
==============================================================================
```

### Os outros dois cenários, em resumo

| Cenário | Reserva | Geração | Consumo | Decisão |
|---|---|---|---|---|
| `nominal` | 78 % | 83 kW | 70 kW | `NORMAL: operação normal` + `SUGESTÃO: armazenar energia excedente` |
| `critico` | 15 % | 16 kW | 50 kW | `CRÍTICO: manter apenas sistemas essenciais` (desliga estufa e iluminação; previsão: melhora) |

## Documentação

- [Relatório (PDF)](docs/relatorio.pdf)
- [Relatório (Markdown)](docs/relatorio.md)

## Premissas

O enunciado não fornece dados. O histórico, os consumos, as prioridades, os
limites das regras (20 %, 50 %, 60 kW) e os quatro cenários foram definidos
por nós e são sintéticos; estão todos em `data/colonia.json` e no topo de
`src/decisoes.py`, e podem ser alterados sem tocar na lógica.
