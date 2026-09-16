"""Gera e executa o notebook de entrega a partir de células declaradas aqui.

Não faz parte da entrega: é ferramenta de build. Rodar da raiz do projeto:
    .venv/bin/python tools/gerar_notebook.py
"""

from pathlib import Path

import nbformat
from nbclient import NotebookClient

RAIZ = Path(__file__).resolve().parents[1]
DESTINO = RAIZ / "entrega-fase1" / "notebooks" / "analise_telemetria.ipynb"

MD = "markdown"
CODE = "code"

CELULAS: list[tuple[str, str]] = [
    (MD, """# Missão Aurora-1 — Verificação de Telemetria Pré-Lançamento

**Atividade Integradora — FIAP, Fase 1**

Este notebook executa o checklist de pré-lançamento do foguete Aurora-1: lê a
telemetria da janela T-10 min, aplica as faixas seguras de cada parâmetro,
decide entre `PRONTO PARA DECOLAR` e `DECOLAGEM ABORTADA`, e calcula a
autonomia energética da missão.

A lógica não é redefinida aqui: ela vive em `src/missao.py` e é coberta por
testes automatizados em `tests/test_missao.py`. O notebook importa esse módulo,
de modo que o que você executa abaixo é exatamente o código testado."""),

    (MD, """## 0. Preparação do ambiente

Se estiver no Google Colab, descomente e rode a célula de clone. Localmente,
basta executar a célula seguinte a partir do repositório."""),

    (CODE, """# No Google Colab, descomente as duas linhas abaixo:
# !git clone https://github.com/SEU_USUARIO/SEU_REPOSITORIO.git
# %cd SEU_REPOSITORIO/entrega-fase1/notebooks"""),

    (CODE, """import sys
from pathlib import Path

# Torna src/ importável a partir da pasta do notebook.
RAIZ = Path.cwd().parent if Path.cwd().name == "notebooks" else Path.cwd()
sys.path.insert(0, str(RAIZ / "src"))

import missao

print("Módulo carregado de:", missao.__file__)
print("Telemetria em:", missao.CAMINHO_PADRAO)"""),

    (MD, """## 1. Organização e descrição da telemetria

Os dados chegam em `data/telemetria.json` com três cenários: o nominal e dois
de falha, usados para demonstrar o comportamento do algoritmo. Cada parâmetro
tem uma faixa segura definida como premissa do projeto."""),

    (CODE, """dados = missao.carregar_telemetria(missao.CAMINHO_PADRAO, "nominal")

print(f"{'Parâmetro':<28} {'Leitura':>12}  {'Faixa segura':<22} Situação")
print("-" * 78)
for chave, (minimo, maximo) in missao.FAIXAS.items():
    valor = dados[chave]
    unidade = missao.UNIDADES[chave]
    situacao = "OK" if minimo <= valor <= maximo else "FORA DA FAIXA"
    print(f"{missao.ROTULOS[chave]:<28} {f'{valor} {unidade}':>12}  "
          f"{f'{minimo} a {maximo} {unidade}':<22} {situacao}")

print()
print(f"{'Integridade estrutural':<28} {dados['integridade_estrutural']:>12}  "
      f"{'= 1':<22} {'OK' if dados['integridade_estrutural'] == 1 else 'COMPROMETIDA'}")

valor_energia = f"{dados['nivel_energia_pct']} %"
situacao_energia = ("OK" if dados['nivel_energia_pct'] >= missao.ENERGIA_MINIMA_PCT
                     else "INSUFICIENTE")
print(f"{'Nível de energia':<28} {valor_energia:>12}  "
      f"{'>= 85.0 %':<22} {situacao_energia}")

print()
print("Módulos críticos:")
for nome in missao.MODULOS_CRITICOS:
    print(f"  - {missao.ROTULOS[nome]:<22} {dados['modulos_criticos'][nome]}")"""),

    (MD, """## 2. Algoritmo de verificação

O fluxograma está em [`docs/fluxograma.md`](../docs/fluxograma.md) e o
pseudocódigo em [`docs/pseudocodigo.md`](../docs/pseudocodigo.md).

Duas decisões governam o algoritmo:

1. **Limites inclusivos.** Uma leitura de exatamente 28,0 °C é aprovada.
2. **Nenhuma parada antecipada.** Todas as verificações são executadas mesmo
   depois da primeira reprovação, para que o operador receba a lista completa
   de problemas de uma só vez."""),

    (CODE, """resultado = missao.verificar_telemetria(dados)

print("Decisão:", resultado.decisao)
print("Aprovado:", resultado.aprovado)
print("Falhas:", resultado.falhas or "(nenhuma)")"""),

    (MD, """## 3. Script em Python — execução completa

A função `executar` percorre o fluxo inteiro: leitura dos dados, execução das
verificações e impressão do resultado final."""),

    (CODE, """print(missao.executar("nominal"))"""),

    (MD, """### 3.1 Cenários de falha

Para demonstrar que o algoritmo aborta corretamente — e reporta *todos* os
motivos, não apenas o primeiro."""),

    (CODE, """print(missao.executar("falha_termica"))"""),

    (CODE, """print(missao.executar("falha_multipla"))"""),

    (MD, r"""## 4. Análise energética

$$E_{disp} = C_{total} \times \frac{carga}{100} \times \left(1 - \frac{perdas}{100}\right)$$

$$E_{rest} = E_{disp} - E_{decolagem} \qquad
  t_{autonomia} = \frac{E_{rest}}{P_{voo}} \qquad
  margem = \frac{E_{rest}}{E_{decolagem}} \times 100$$"""),

    (CODE, """energia = missao.analisar_energia(dados["nivel_energia_pct"])

print(f"Capacidade total ......... {missao.CAPACIDADE_TOTAL_KWH:>8.2f} kWh")
print(f"Carga atual .............. {dados['nivel_energia_pct']:>8.2f} %")
print(f"Perdas energéticas ....... {missao.PERDAS_PCT:>8.2f} %")
print(f"Energia disponível ....... {energia.disponivel_kwh:>8.2f} kWh")
print(f"Consumo na decolagem ..... {missao.CONSUMO_DECOLAGEM_KWH:>8.2f} kWh")
print(f"Energia restante ......... {energia.restante_kwh:>8.2f} kWh")
print(f"Consumo em voo ........... {missao.CONSUMO_VOO_KW:>8.2f} kW")
print(f"Autonomia estimada ....... {energia.autonomia_h:>8.2f} h")
print(f"Margem sobre a decolagem . {energia.margem_pct:>8.2f} % "
      f"(mínimo {missao.MARGEM_MINIMA_PCT:.0f} %)")
print()
print("Parecer energético:", "ADEQUADO" if energia.aprovado else "INSUFICIENTE")"""),

    (MD, """### 4.1 Sensibilidade da autonomia ao nível de carga

Qual é a carga mínima que ainda permite decolar com a margem de 20 %?"""),

    (CODE, """print(f"{'Carga (%)':>10} {'Disponível (kWh)':>18} {'Autonomia (h)':>15} "
      f"{'Margem (%)':>12}  Parecer")
print("-" * 70)
for carga in range(50, 101, 5):
    e = missao.analisar_energia(float(carga))
    parecer = "adequado" if e.aprovado else "insuficiente"
    print(f"{carga:>10} {e.disponivel_kwh:>18.2f} {e.autonomia_h:>15.2f} "
          f"{e.margem_pct:>12.2f}  {parecer}")"""),

    (MD, """## 5. Análise assistida por IA

A telemetria e as faixas seguras foram submetidas a um modelo de linguagem
(Claude), com o prompt reproduzido abaixo. A resposta e o comentário crítico
sobre ela estão no relatório, em
[`docs/relatorio.md`](../docs/relatorio.md#5-análise-assistida-por-ia).

> **Prompt enviado:**
> "Você é um engenheiro de sistemas de lançamento. A seguir está a telemetria
> de um foguete na janela T-10 min e as faixas seguras adotadas pela equipe.
> (1) Classifique cada parâmetro como nominal, de atenção ou crítico.
> (2) Identifique possíveis anomalias, inclusive correlações entre parâmetros
> que isoladamente pareceriam aceitáveis. (3) Liste os riscos de missão que
> essas leituras sugerem, do mais provável ao menos provável. Seja explícito
> sobre o que não é possível concluir apenas com esses dados."

A resposta do modelo foi avaliada criticamente — não aceita como veredito.
O ponto principal: a IA levanta hipóteses úteis sobre *correlações* que o
checklist determinístico não captura, mas não pode substituir o checklist,
porque não tem garantia de reprodutibilidade nem rastreabilidade de decisão."""),

    (MD, """## 6. Reflexão crítica

O texto completo sobre ética e responsabilidade, impacto social da exploração
espacial e sustentabilidade tecnológica está em
[`docs/relatorio.md`](../docs/relatorio.md#6-reflexão-crítica)."""),

    (MD, """## 7. Testes automatizados

A lógica usada acima é coberta por testes. Para executá-los, a partir da raiz
do repositório:

```bash
pytest entrega-fase1/tests/ -v
```"""),
]


def construir() -> nbformat.NotebookNode:
    nb = nbformat.v4.new_notebook()
    nb.cells = [
        nbformat.v4.new_markdown_cell(fonte) if tipo == MD
        else nbformat.v4.new_code_cell(fonte)
        for tipo, fonte in CELULAS
    ]
    nb.metadata = {
        "kernelspec": {"display_name": "Python 3", "language": "python",
                       "name": "python3"},
        "language_info": {"name": "python", "version": "3"},
    }
    return nb


def main() -> None:
    nb = construir()
    DESTINO.parent.mkdir(parents=True, exist_ok=True)
    cliente = NotebookClient(nb, timeout=120, kernel_name="python3",
                             resources={"metadata": {"path": str(DESTINO.parent)}})
    cliente.execute()
    nbformat.write(nb, DESTINO)
    print(f"Notebook gerado e executado: {DESTINO}")


if __name__ == "__main__":
    main()
