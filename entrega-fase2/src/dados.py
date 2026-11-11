"""Dados da colônia: carga do arquivo e navegação na hierarquia de sistemas.

Os sistemas formam uma árvore de dicionários aninhados. Um nó com a chave
"subsistemas" é um agrupamento; um nó sem ela é uma folha (um equipamento).
Cada nó é endereçado por um caminho como "energia/geracao/eolico".
"""

from __future__ import annotations

import json
from pathlib import Path

CAMINHO_PADRAO = Path(__file__).resolve().parents[1] / "data" / "colonia.json"


def carregar_colonia(caminho: str | Path = CAMINHO_PADRAO) -> dict:
    """Lê o arquivo de dados da colônia."""
    with open(caminho, encoding="utf-8") as arquivo:
        return json.load(arquivo)


def carregar_cenario(colonia: dict, nome: str) -> dict:
    """Devolve as leituras de um cenário pelo nome (tabela chave-valor)."""
    cenarios = colonia["cenarios"]
    if nome not in cenarios:
        disponiveis = ", ".join(sorted(cenarios))
        raise KeyError(
            f"Cenário '{nome}' inexistente. Disponíveis: {disponiveis}."
        )
    validar_cenario(nome, cenarios[nome])
    return cenarios[nome]


def validar_cenario(nome: str, cenario: dict) -> None:
    """Recusa leituras impossíveis antes que virem uma decisão errada."""
    if not 0 <= cenario["reserva_pct"] <= 100:
        raise ValueError(f"Cenário '{nome}': a reserva deve estar entre 0 e 100 %.")
    clima = cenario["previsao_clima"]
    medidas = {
        "geração solar": cenario["geracao_solar_kw"],
        "geração eólica": cenario["geracao_eolica_kw"],
        "vento previsto": clima["vento_ms"],
        "irradiância prevista": clima["irradiancia_wm2"],
    }
    for rotulo, valor in medidas.items():
        if valor < 0:
            raise ValueError(f"Cenário '{nome}': {rotulo} não pode ser negativa.")
    ligados = cenario["ligados"]
    if len(set(ligados)) != len(ligados):
        raise ValueError(f"Cenário '{nome}': há subsistema repetido em 'ligados'.")


def buscar_subsistema(arvore: dict, caminho: str) -> dict:
    """Desce pela árvore seguindo o caminho, um nível por vez."""
    no = arvore
    for parte in caminho.split("/"):
        filhos = no.get("subsistemas", {})
        if parte not in filhos:
            raise KeyError(f"Subsistema '{caminho}' não existe na colônia.")
        no = filhos[parte]
    return no


def listar_folhas(no: dict, prefixo: str = "") -> list[tuple[str, dict]]:
    """Percorre a árvore em profundidade e devolve (caminho, folha)."""
    if "subsistemas" not in no:
        return [(prefixo, no)]
    folhas: list[tuple[str, dict]] = []
    for nome, filho in no["subsistemas"].items():
        caminho = f"{prefixo}/{nome}" if prefixo else nome
        folhas.extend(listar_folhas(filho, caminho))
    return folhas


def consumidores_ligados(arvore: dict, ligados: list[str]) -> list[dict]:
    """Lista os equipamentos ligados que consomem energia.

    Cada item traz caminho, rótulo, consumo e prioridade — o formato que as
    regras de decisão usam para escolher o que desligar.
    """
    itens = []
    for caminho in ligados:
        folha = buscar_subsistema(arvore, caminho)
        if "consumo_kw" not in folha:
            raise KeyError(f"Subsistema '{caminho}' não é um consumidor.")
        itens.append({
            "caminho": caminho,
            "rotulo": folha["rotulo"],
            "consumo_kw": folha["consumo_kw"],
            "prioridade": folha["prioridade"],
        })
    return itens


def consumo_total(no: dict, ligados: list[str], prefixo: str = "") -> float:
    """Soma, recursivamente, o consumo dos equipamentos ligados sob um nó.

    Serve para a colônia inteira ou para qualquer ramo dela.
    """
    if "subsistemas" not in no:
        return no.get("consumo_kw", 0.0) if prefixo in ligados else 0.0
    total = 0.0
    for nome, filho in no["subsistemas"].items():
        caminho = f"{prefixo}/{nome}" if prefixo else nome
        total += consumo_total(filho, ligados, caminho)
    return total
