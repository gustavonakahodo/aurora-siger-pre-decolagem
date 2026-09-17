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
# !git clone https://github.com/gustavonakahodo/aurora-siger-pre-decolagem.git
# %cd aurora-siger-pre-decolagem/entrega-fase1/notebooks"""),

    (CODE, """import sys
from pathlib import Path

# Localiza a raiz de entrega-fase1/ (quem tem src/missao.py) sem depender
# do nome da pasta atual, para funcionar a partir da raiz do notebook, de
# entrega-fase1/ ou da raiz do repositório.
cwd = Path.cwd()
candidatos = [cwd, cwd.parent, cwd / "entrega-fase1"]
RAIZ = next((c for c in candidatos if (c / "src" / "missao.py").exists()), None)
if RAIZ is None:
    raise RuntimeError(
        f"Não encontrei src/missao.py a partir de {cwd}. Rode o notebook "
        "de dentro do repositório (raiz, entrega-fase1/ ou "
        "entrega-fase1/notebooks/)."
    )
sys.path.insert(0, str(RAIZ / "src"))

import missao


def caminho_relativo(caminho) -> str:
    \"\"\"Caminho relativo à raiz do projeto, sem expor o disco local.\"\"\"
    return f"{RAIZ.name}/{Path(caminho).resolve().relative_to(RAIZ)}"


print("Módulo carregado de:", caminho_relativo(missao.__file__))
print("Telemetria em:", caminho_relativo(missao.CAMINHO_PADRAO))"""),

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
faixa_energia = f">= {missao.ENERGIA_MINIMA_PCT} %"
print(f"{'Nível de energia':<28} {valor_energia:>12}  "
      f"{faixa_energia:<22} {situacao_energia}")

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
print("Margem de segurança:", "ADEQUADA" if energia.aprovado else "INSUFICIENTE")"""),

    (MD, """### 4.1 Sensibilidade da autonomia ao nível de carga

Qual é a carga mínima que ainda permite decolar com a margem de 20 %? A varredura
começa em 40 % justamente para que o ponto de corte apareça na tabela: ele fica
entre a linha de 45 % (reprovada) e a de 50 % (aprovada), em 48,913 % de carga —
o valor exato está deduzido em
[`docs/relatorio.md` §4.3](../docs/relatorio.md#43-sensibilidade-ao-estado-de-carga)."""),

    (CODE, """print(f"{'Carga (%)':>10} {'Disponível (kWh)':>18} {'Autonomia (h)':>15} "
      f"{'Margem (%)':>12}  Parecer")
print("-" * 70)
for carga in range(40, 101, 5):
    e = missao.analisar_energia(float(carga))
    parecer = "ADEQUADA" if e.aprovado else "INSUFICIENTE"
    print(f"{carga:>10} {e.disponivel_kwh:>18.2f} {e.autonomia_h:>15.2f} "
          f"{e.margem_pct:>12.2f}  {parecer}")"""),

    (MD, """## 5. Análise assistida por IA

A telemetria e as faixas seguras foram submetidas a um modelo de linguagem
(Claude, da Anthropic). O prompt exato, a resposta transcrita e o comentário
crítico sobre ela estão no relatório — o prompt em
[`docs/relatorio.md` §5.2](../docs/relatorio.md#52-prompt-enviado), a resposta
e a crítica nas seções 5.3 e 5.4. O texto não é reproduzido aqui de propósito:
o relatório é a única versão dele, e duas cópias acabariam divergindo.

**Síntese para quem lê só o notebook.** O que se pediu ao modelo foi
classificar cada parâmetro de dois cenários, apontar correlações entre
parâmetros e ordenar os riscos por gravidade. O que ele agregou é exatamente o
que o checklist determinístico não produz: causalidade — a temperatura interna
alta lida como sintoma da falha do controle térmico, e não como um item
independente da lista —, hierarquia entre motivos de aborto que o algoritmo
devolve achatados, e riscos de segunda ordem, como a perda de comunicação
eliminar a terminação de voo. Onde não se pode confiar nele: a resposta não é
reprodutível — mesmo prompt, mesma telemetria, outra resposta amanhã —, não é
auditável até o requisito de engenharia que fixou cada limite, e afirma com o
mesmo tom seguro o que é quase certo e o que é apenas plausível. Por isso a
autorização de voo continua com o algoritmo determinístico, e o papel da IA é
gerar hipóteses *depois* do aborto.

O escopo do uso de IA no trabalho como um todo está declarado em
[§5.5](../docs/relatorio.md#55-escopo-do-uso-de-ia-neste-trabalho)."""),

    (MD, """## 6. Reflexão crítica

O texto completo sobre ética e responsabilidade, impacto social da exploração
espacial e sustentabilidade tecnológica está em
[`docs/relatorio.md`](../docs/relatorio.md#6-reflexão-crítica). Uma tese por
subseção, para quem lê só o notebook:

**6.1 — Ética e responsabilidade.** Os dois erros possíveis de um verificador
não são simétricos: um aborto indevido custa dinheiro e janela de lançamento,
um lançamento indevido pode custar vidas — daí o algoritmo conjuntivo e
conservador. Mas a responsabilidade nunca é do programa: quem decide é quem
fixa o limite, e por isso cada faixa tem a origem registrada. O risco que
sobra é o viés de automação, que o software só mitiga em parte, imprimindo
sempre todos os parâmetros em vez de um sinal único.

**6.2 — Impacto social.** O retorno tecnológico dos programas espaciais é
real, mas não encerra a discussão: a pergunta relevante não é se há retorno, e
sim quem o recebe. O acesso à órbita é concentrado, faixas orbitais e espectro
são recursos finitos alocados por ocupação, o lixo orbital é uma externalidade
paga por quem vier depois, e a tecnologia de lançamento é de uso dual por
natureza — nada disso é neutro.

**6.3 — Sustentabilidade.** A combustão de LOX/RP-1 emite dióxido de carbono e
fuligem diretamente na estratosfera, onde o efeito é desproporcional ao
volume; o número de lançamentos ainda é pequeno, a trajetória não é. O
reaproveitamento de estágios é o ganho estrutural mais relevante e é material
antes de ser energético, mas depende de quantas vezes o mesmo estágio voa de
fato. Vale aqui a ressalva que fazemos ao nosso próprio modelo energético: um
número favorável só significa o que suas premissas permitem."""),

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
