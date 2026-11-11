# Aurora Siger — Atividades Integradoras FIAP

| | |
|---|---|
| **Nome completo** | Gustavo Hiroshi Fernandes Nakahodo |
| **RM** | 576337 |
| **Turma** | Ciência da Computação (On-Line) |

Este repositório reúne as entregas das atividades integradoras. Cada fase
fica em sua própria pasta, com código, testes, README e relatório.

| Fase | Pasta | O que é |
|---|---|---|
| 1 | [`entrega-fase1/`](entrega-fase1/) | Verificador de telemetria pré-lançamento da missão Aurora-1 |
| 2 | [`entrega-fase2/`](entrega-fase2/) | Sistema integrado de energia da colônia |

## Fase 2 — Sistema integrado de energia da colônia

Um sistema em Python que organiza os dados da colônia (listas, chave-valor e
uma hierarquia de sistemas), analisa o balanço entre geração, consumo e
reserva, decide por regras o que fazer — desligando primeiro o que não é
essencial e nunca o suporte à vida — e prevê por regressão linear a geração
solar e eólica das próximas horas, para avisar antes de o problema chegar.
Exemplo: reserva = 40 e consumo = 70 → `ALERTA: reduzir consumo`.

```bash
cd entrega-fase2
python src/colonia.py economia
```

- **[`entrega-fase2/README.md`](entrega-fase2/README.md)** — funcionamento,
  instruções e exemplo de entrada e saída. **Comece por aqui.**
- **[`entrega-fase2/docs/relatorio.pdf`](entrega-fase2/docs/relatorio.pdf)** —
  relatório (4 páginas), também em [Markdown](entrega-fase2/docs/relatorio.md).

## Fase 1 — Verificação de telemetria pré-lançamento

Um verificador de telemetria
pré-lançamento do foguete fictício Aurora-1. O programa lê a telemetria de um
cenário, aplica sete verificações de segurança — temperaturas interna e
externa, pressão dos dois tanques de propelente, integridade estrutural, nível
de energia e estado dos módulos críticos —, decide entre `PRONTO PARA DECOLAR`
e `DECOLAGEM ABORTADA` e, em caso de aborto, lista **todos** os motivos de uma
só vez, em vez de parar no primeiro. Uma análise energética complementar
calcula a energia disponível, a autonomia de voo e a margem sobre o consumo da
decolagem. Tudo roda offline, apenas com a biblioteca padrão do Python, e está
coberto por testes automatizados.

Toda a entrega está em [`entrega-fase1/`](entrega-fase1/).

- **[`entrega-fase1/README.md`](entrega-fase1/README.md)** — documentação
  completa: estrutura, instruções de execução do script, dos testes e do
  notebook, e exemplos de saída. **Comece por aqui.**
- **[`entrega-fase1/docs/relatorio.pdf`](entrega-fase1/docs/relatorio.pdf)** —
  relatório técnico (27 páginas), também em [Markdown](entrega-fase1/docs/relatorio.md).
