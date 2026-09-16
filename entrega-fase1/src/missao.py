"""Verificação de telemetria pré-lançamento da missão Aurora-1.

Módulo sem estado: todas as funções são puras e recebem os dados de que
precisam. Usa apenas a biblioteca padrão do Python.
"""

from __future__ import annotations

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
