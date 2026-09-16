"""Testes do módulo de verificação da missão Aurora-1."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import missao


def test_carrega_cenario_nominal():
    dados = missao.carregar_telemetria(missao.CAMINHO_PADRAO, "nominal")
    assert dados["temperatura_interna_c"] == 23.4
    assert dados["integridade_estrutural"] == 1
    assert dados["modulos_criticos"]["propulsao"] == "OK"


def test_carrega_cenario_de_falha():
    dados = missao.carregar_telemetria(missao.CAMINHO_PADRAO, "falha_multipla")
    assert dados["nivel_energia_pct"] == 78.0
    assert dados["modulos_criticos"]["comunicacao"] == "FALHA"


def test_cenario_inexistente_levanta_erro_em_portugues():
    with pytest.raises(KeyError, match="inexistente"):
        missao.carregar_telemetria(missao.CAMINHO_PADRAO, "inexistente")


def test_faixas_seguras_conferem_com_o_spec():
    assert missao.FAIXAS["temperatura_interna_c"] == (18.0, 28.0)
    assert missao.FAIXAS["temperatura_externa_c"] == (-40.0, 50.0)
    assert missao.FAIXAS["pressao_lox_bar"] == (200.0, 250.0)
    assert missao.FAIXAS["pressao_rp1_bar"] == (190.0, 240.0)
    assert missao.ENERGIA_MINIMA_PCT == 85.0
    assert len(missao.MODULOS_CRITICOS) == 5
