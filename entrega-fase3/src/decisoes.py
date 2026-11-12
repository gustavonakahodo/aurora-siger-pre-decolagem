"""Regras de decisão da colônia.

Transforma três números (reserva, consumo e geração) em uma ação clara e,
quando é preciso economizar, escolhe o que desligar respeitando a prioridade
de cada equipamento. Suporte à vida (prioridade 1) nunca é desligado.
"""

from __future__ import annotations

from dataclasses import dataclass

# Limites das regras (premissas do projeto).
RESERVA_BAIXA_PCT = 50.0
RESERVA_CRITICA_PCT = 20.0
CONSUMO_ALTO_KW = 60.0
MARGEM_ESTAVEL_PCT = 1.0   # variação de reserva tratada como "estável"

PRIORIDADE_ESSENCIAL = 1
PRIORIDADE_IMPORTANTE = 2

NORMAL, ATENCAO, ALERTA, CRITICO = "NORMAL", "ATENÇÃO", "ALERTA", "CRÍTICO"
GRAVIDADE = {NORMAL: 0, ATENCAO: 1, ALERTA: 2, CRITICO: 3}

ACAO_NORMAL = "NORMAL: operação normal"
ACAO_ATENCAO = "ATENÇÃO: consumo acima da geração — usando a reserva"
ACAO_ALERTA = "ALERTA: reduzir consumo"
ACAO_ECONOMIA = "ALERTA: reduzir consumo — modo economia ativado"
ACAO_CRITICO = "CRÍTICO: manter apenas sistemas essenciais"


@dataclass(frozen=True)
class Decisao:
    """Saída das regras: o que fazer e por quê."""

    nivel: str
    acao: str
    regras: tuple[str, ...]      # regras que dispararam, em texto
    desligar: tuple[str, ...]    # rótulos, na ordem em que devem ser desligados
    consumo_apos_kw: float       # consumo depois dos cortes


def planejar_cortes(consumidores: list[dict], reducao_kw: float,
                    prioridades: tuple[int, ...] | None = None) -> list[dict]:
    """Escolhe o que desligar para reduzir o consumo em `reducao_kw`.

    Percorre as prioridades da menos importante (número maior) para a mais
    importante e, dentro de cada uma, do maior consumo para o menor. Para
    assim que a redução é atingida. Equipamentos essenciais nunca entram na
    lista. `prioridades` restringe o corte a alguns níveis.
    """
    if prioridades is None:
        prioridades = tuple(sorted({c["prioridade"] for c in consumidores},
                                   reverse=True))
    cortes: list[dict] = []
    cortado = 0.0
    for prioridade in prioridades:
        if prioridade == PRIORIDADE_ESSENCIAL:
            continue
        grupo = [c for c in consumidores if c["prioridade"] == prioridade]
        for item in sorted(grupo, key=lambda c: -c["consumo_kw"]):
            if cortado >= reducao_kw:
                return cortes
            cortes.append(item)
            cortado += item["consumo_kw"]
    return cortes


def _nao_essenciais(consumidores: list[dict]) -> list[dict]:
    return planejar_cortes(consumidores, float("inf"))


def decidir(reserva_pct: float, consumo_kw: float, geracao_kw: float,
            consumidores: list[dict]) -> Decisao:
    """Aplica as regras, da mais grave para a mais leve, e devolve a decisão."""
    deficit = max(0.0, consumo_kw - geracao_kw)
    regras: list[str] = []
    cortes: list[dict] = []

    if reserva_pct < RESERVA_CRITICA_PCT:
        nivel, acao = CRITICO, ACAO_CRITICO
        regras.append(f"reserva {reserva_pct:.1f} % < {RESERVA_CRITICA_PCT:.0f} %"
                      " → desligar tudo que não é essencial")
        cortes = _nao_essenciais(consumidores)
    elif reserva_pct < RESERVA_BAIXA_PCT and consumo_kw > CONSUMO_ALTO_KW:
        nivel, acao = ALERTA, ACAO_ECONOMIA
        regras.append(f"reserva {reserva_pct:.1f} % < {RESERVA_BAIXA_PCT:.0f} % E "
                      f"consumo {consumo_kw:.1f} kW > {CONSUMO_ALTO_KW:.0f} kW"
                      " → modo economia")
        # Modo economia: sai tudo que é dispensável (prioridade 3 em
        # diante); se ainda faltar energia, a prioridade 2 cobre o resto.
        dispensaveis = tuple(sorted(
            {c["prioridade"] for c in consumidores
             if c["prioridade"] > PRIORIDADE_IMPORTANTE}, reverse=True))
        cortes = planejar_cortes(consumidores, float("inf"), dispensaveis)
        falta = deficit - sum(c["consumo_kw"] for c in cortes)
        if falta > 0:
            cortes += planejar_cortes(consumidores, falta,
                                      (PRIORIDADE_IMPORTANTE,))
    elif reserva_pct < RESERVA_BAIXA_PCT:
        nivel, acao = ALERTA, ACAO_ALERTA
        regras.append(f"reserva {reserva_pct:.1f} % < {RESERVA_BAIXA_PCT:.0f} %"
                      " → reduzir consumo")
        cortes = planejar_cortes(consumidores, deficit)
    elif deficit > 0:
        nivel, acao = ATENCAO, ACAO_ATENCAO
        regras.append(f"consumo {consumo_kw:.1f} kW > geração {geracao_kw:.1f} kW,"
                      f" com reserva ≥ {RESERVA_BAIXA_PCT:.0f} % → usar a reserva")
    else:
        nivel, acao = NORMAL, ACAO_NORMAL
        regras.append("nenhuma condição de risco")

    consumo_apos = consumo_kw - sum(c["consumo_kw"] for c in cortes)
    em_economia = nivel in (ALERTA, CRITICO)
    if em_economia and consumo_apos > geracao_kw:
        regras.append("mesmo com os cortes possíveis o consumo supera a"
                      " geração: o que ficou ligado é alimentado pela reserva")
    elif em_economia and not cortes:
        regras.append("sem déficit, nada a desligar agora: não ligar novas"
                      " cargas até a reserva se recuperar")
    return Decisao(nivel, acao, tuple(regras),
                   tuple(c["rotulo"] for c in cortes), consumo_apos)


def comparar(atual: Decisao, prevista: Decisao,
             reserva_atual_pct: float, reserva_prevista_pct: float) -> str:
    """Diz se a situação prevista é pior, igual ou melhor que a atual.

    Vale primeiro o nível da decisão; se o nível é o mesmo, desempata o
    rumo da reserva (uma reserva caindo é piora, mesmo sem mudar de nível).
    """
    diferenca = GRAVIDADE[prevista.nivel] - GRAVIDADE[atual.nivel]
    if diferenca == 0:
        variacao = reserva_prevista_pct - reserva_atual_pct
        diferenca = 0 if abs(variacao) < MARGEM_ESTAVEL_PCT else -variacao
    if diferenca > 0:
        return "PIORA"
    if diferenca < 0:
        return "MELHORA"
    return "ESTÁVEL"
