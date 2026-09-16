# Missão Aurora-1 — Verificação de Telemetria Pré-Lançamento

**FIAP — Atividade Integradora, Fase 1**

| | |
|---|---|
| **Nome completo** | Gustavo Hiroshi Fernandes Nakahodo |
| **RM** | `<!-- PREENCHER -->` |
| **Turma** | `<!-- PREENCHER -->` |

Este repositório contém a entrega da Fase 1: um verificador de telemetria
pré-lançamento do foguete fictício Aurora-1. O programa lê a telemetria de um
cenário, aplica sete verificações de segurança — temperaturas interna e
externa, pressão dos dois tanques de propelente, integridade estrutural, nível
de energia e estado dos módulos críticos —, decide entre `PRONTO PARA DECOLAR`
e `DECOLAGEM ABORTADA` e, em caso de aborto, lista **todos** os motivos de uma
só vez, em vez de parar no primeiro. Uma análise energética complementar
calcula a energia disponível, a autonomia de voo e a margem sobre o consumo da
decolagem. Tudo roda offline, apenas com a biblioteca padrão do Python, e está
coberto por testes automatizados.

## Onde está o quê

Toda a entrega está em [`entrega-fase1/`](entrega-fase1/).

- **[`entrega-fase1/README.md`](entrega-fase1/README.md)** — documentação
  completa: estrutura, instruções de execução do script, dos testes e do
  notebook, e exemplos de saída. **Comece por aqui.**
- **[`entrega-fase1/docs/relatorio.pdf`](entrega-fase1/docs/relatorio.pdf)** —
  relatório técnico (27 páginas), também em [Markdown](entrega-fase1/docs/relatorio.md).
