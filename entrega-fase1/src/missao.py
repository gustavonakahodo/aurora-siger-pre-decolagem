"""Verificação de telemetria pré-lançamento da missão Aurora-1.

Módulo sem estado: todas as funções são puras e recebem os dados de que
precisam. Usa apenas a biblioteca padrão do Python.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path

CAMINHO_PADRAO = Path(__file__).resolve().parents[1] / "data" / "telemetria.json"

# Faixas seguras (mínimo e máximo inclusivos) definidas como premissa do projeto.
FAIXAS: dict[str, tuple[float, float]] = {
    "temperatura_interna_c": (18.0, 28.0),
    "temperatura_externa_c": (-40.0, 50.0),
    "pressao_lox_bar": (200.0, 250.0),
    "pressao_rp1_bar": (190.0, 240.0),
}

ENERGIA_MINIMA_PCT = 85.0

MODULOS_CRITICOS: tuple[str, ...] = (
    "navegacao",
    "comunicacao",
    "propulsao",
    "controle_termico",
    "suporte_vida",
)

ROTULOS: dict[str, str] = {
    "temperatura_interna_c": "Temperatura interna",
    "temperatura_externa_c": "Temperatura externa",
    "integridade_estrutural": "Integridade estrutural",
    "nivel_energia_pct": "Nível de energia",
    "pressao_lox_bar": "Pressão do tanque de LOX",
    "pressao_rp1_bar": "Pressão do tanque de RP-1",
    "modulos_criticos": "Módulos críticos",
    "navegacao": "navegação",
    "comunicacao": "comunicação",
    "propulsao": "propulsão",
    "controle_termico": "controle térmico",
    "suporte_vida": "suporte de vida",
}

UNIDADES: dict[str, str] = {
    "temperatura_interna_c": "°C",
    "temperatura_externa_c": "°C",
    "nivel_energia_pct": "%",
    "pressao_lox_bar": "bar",
    "pressao_rp1_bar": "bar",
}


def carregar_telemetria(caminho: str | Path = CAMINHO_PADRAO,
                        cenario: str = "nominal") -> dict:
    """Lê o arquivo de telemetria e devolve as leituras de um cenário."""
    with open(caminho, encoding="utf-8") as arquivo:
        conteudo = json.load(arquivo)
    cenarios = conteudo["cenarios"]
    if cenario not in cenarios:
        disponiveis = ", ".join(sorted(cenarios))
        raise KeyError(
            f"Cenário '{cenario}' inexistente. Disponíveis: {disponiveis}."
        )
    return cenarios[cenario]


DECISAO_APROVADA = "PRONTO PARA DECOLAR"
DECISAO_ABORTADA = "DECOLAGEM ABORTADA"


@dataclass(frozen=True)
class ResultadoVerificacao:
    """Veredito do checklist pré-lançamento."""

    aprovado: bool
    decisao: str
    falhas: tuple[str, ...]


def verificar_telemetria(dados: dict) -> ResultadoVerificacao:
    """Aplica todas as verificações de segurança e decide sobre o lançamento.

    Avalia todos os parâmetros antes de decidir: um relatório de aborto que
    parasse na primeira falha esconderia problemas do operador.
    """
    falhas: list[str] = []

    for chave, (mínimo, máximo) in FAIXAS.items():
        valor = dados[chave]
        if not mínimo <= valor <= máximo:
            unidade = UNIDADES[chave]
            falhas.append(
                f"{ROTULOS[chave]}: {valor} {unidade} fora da faixa segura "
                f"({mínimo} a {máximo} {unidade})."
            )

    if dados["integridade_estrutural"] != 1:
        falhas.append(
            f"{ROTULOS['integridade_estrutural']}: comprometida "
            f"(leitura {dados['integridade_estrutural']}, esperado 1)."
        )

    energia = dados["nivel_energia_pct"]
    if energia < ENERGIA_MINIMA_PCT:
        falhas.append(
            f"{ROTULOS['nivel_energia_pct']}: {energia} % abaixo do mínimo de "
            f"{ENERGIA_MINIMA_PCT} %."
        )

    modulos = dados["modulos_criticos"]
    em_falha = [ROTULOS[nome] for nome in MODULOS_CRITICOS
                if modulos.get(nome) != "OK"]
    if em_falha:
        falhas.append(
            f"{ROTULOS['modulos_criticos']} em falha: {', '.join(em_falha)}."
        )

    aprovado = not falhas
    return ResultadoVerificacao(
        aprovado=aprovado,
        decisao=DECISAO_APROVADA if aprovado else DECISAO_ABORTADA,
        falhas=tuple(falhas),
    )


# Parâmetros energéticos do veículo (premissas do projeto).
CAPACIDADE_TOTAL_KWH = 120.0
PERDAS_PCT = 8.0
CONSUMO_DECOLAGEM_KWH = 45.0
CONSUMO_VOO_KW = 6.5
MARGEM_MINIMA_PCT = 20.0


@dataclass(frozen=True)
class ResultadoEnergia:
    """Balanço energético da missão."""

    disponivel_kwh: float
    restante_kwh: float
    autonomia_h: float
    margem_pct: float
    aprovado: bool


def analisar_energia(
    carga_pct: float,
    capacidade_kwh: float = CAPACIDADE_TOTAL_KWH,
    perdas_pct: float = PERDAS_PCT,
    consumo_decolagem_kwh: float = CONSUMO_DECOLAGEM_KWH,
    consumo_voo_kw: float = CONSUMO_VOO_KW,
) -> ResultadoEnergia:
    """Calcula energia disponível, autonomia de voo e margem de segurança.

    A autonomia é o tempo de voo sustentável com a energia que sobra depois
    da decolagem. Se não sobra energia, a autonomia é zero — nunca negativa.
    """
    disponivel = capacidade_kwh * (carga_pct / 100.0) * (1 - perdas_pct / 100.0)
    restante = disponivel - consumo_decolagem_kwh
    autonomia = restante / consumo_voo_kw if restante > 0 else 0.0
    margem = (restante / consumo_decolagem_kwh) * 100.0
    return ResultadoEnergia(
        disponivel_kwh=disponivel,
        restante_kwh=restante,
        autonomia_h=autonomia,
        margem_pct=margem,
        aprovado=margem >= MARGEM_MINIMA_PCT,
    )


def _linha_parametro(chave: str, valor, faixa: str, situacao: str) -> str:
    return f"  {ROTULOS[chave]:<28} {str(valor):>10}  {faixa:<20} {situacao}"


def formatar_relatorio(dados: dict, verificacao: ResultadoVerificacao,
                       energia: ResultadoEnergia, cenario: str) -> str:
    """Monta o relatório de pré-lançamento em texto puro."""
    linhas: list[str] = []
    linhas.append("=" * 78)
    linhas.append("RELATÓRIO DE PRÉ-LANÇAMENTO — MISSÃO Aurora-1")
    linhas.append(f"Cenário de telemetria: {cenario}")
    linhas.append("=" * 78)
    linhas.append("")
    linhas.append("1. TELEMETRIA")
    linhas.append(
        f"  {'Parâmetro':<28} {'Leitura':>10}  {'Faixa segura':<20} Situação"
    )
    linhas.append("  " + "-" * 74)

    for chave, (mínimo, máximo) in FAIXAS.items():
        valor = dados[chave]
        unidade = UNIDADES[chave]
        dentro = mínimo <= valor <= máximo
        linhas.append(_linha_parametro(
            chave, f"{valor} {unidade}", f"{mínimo} a {máximo} {unidade}",
            "OK" if dentro else "FORA DA FAIXA",
        ))

    integridade = dados["integridade_estrutural"]
    linhas.append(_linha_parametro(
        "integridade_estrutural", integridade, "= 1",
        "OK" if integridade == 1 else "COMPROMETIDA",
    ))

    energia_pct = dados["nivel_energia_pct"]
    linhas.append(_linha_parametro(
        "nivel_energia_pct", f"{energia_pct} %", f">= {ENERGIA_MINIMA_PCT} %",
        "OK" if energia_pct >= ENERGIA_MINIMA_PCT else "INSUFICIENTE",
    ))

    linhas.append("")
    linhas.append("  Módulos críticos:")
    for nome in MODULOS_CRITICOS:
        estado = dados["modulos_criticos"].get(nome, "DESCONHECIDO")
        linhas.append(f"    - {ROTULOS[nome]:<22} {estado}")

    linhas.append("")
    linhas.append("2. ANÁLISE ENERGÉTICA")
    linhas.append(f"  Capacidade total .................. {CAPACIDADE_TOTAL_KWH:.2f} kWh")
    linhas.append(f"  Carga atual ....................... {energia_pct:.2f} %")
    linhas.append(f"  Perdas energéticas ................ {PERDAS_PCT:.2f} %")
    linhas.append(f"  Energia disponível ................ {energia.disponivel_kwh:.2f} kWh")
    linhas.append(f"  Consumo na decolagem .............. {CONSUMO_DECOLAGEM_KWH:.2f} kWh")
    linhas.append(f"  Energia restante .................. {energia.restante_kwh:.2f} kWh")
    linhas.append(f"  Consumo em voo .................... {CONSUMO_VOO_KW:.2f} kW")
    linhas.append(f"  Autonomia estimada ................ {energia.autonomia_h:.2f} h")
    linhas.append(
        f"  Margem sobre a decolagem .......... {energia.margem_pct:.2f} % "
        f"(mínimo {MARGEM_MINIMA_PCT:.0f} %) — "
        f"{'ADEQUADA' if energia.aprovado else 'INSUFICIENTE'}"
    )

    linhas.append("")
    linhas.append("3. MOTIVOS DE ABORTO")
    if verificacao.falhas:
        linhas.extend(f"  - {falha}" for falha in verificacao.falhas)
    else:
        linhas.append("  Nenhuma inconformidade encontrada.")

    linhas.append("")
    linhas.append("=" * 78)
    linhas.append(f"DECISÃO: {verificacao.decisao}")
    linhas.append("=" * 78)
    return "\n".join(linhas)


def executar(cenario: str = "nominal",
             caminho: str | Path = CAMINHO_PADRAO) -> str:
    """Executa o fluxo completo e devolve o relatório de pré-lançamento."""
    dados = carregar_telemetria(caminho, cenario)
    verificacao = verificar_telemetria(dados)
    energia = analisar_energia(dados["nivel_energia_pct"])
    return formatar_relatorio(dados, verificacao, energia, cenario)


if __name__ == "__main__":
    import sys

    cenario_escolhido = sys.argv[1] if len(sys.argv) > 1 else "nominal"
    try:
        print(executar(cenario_escolhido))
    except KeyError as erro:
        # Cenário inexistente é erro de uso, não defeito: mensagem legível
        # em stderr e código de saída 1, sem traceback.
        print(f"Erro: {erro.args[0]}", file=sys.stderr)
        sys.exit(1)
