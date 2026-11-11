"""Testes da regressão linear."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import dados
import previsao


def test_exemplo_do_enunciado_vento_11_preve_cerca_de_27():
    a, b = previsao.ajustar_reta([8, 10, 12], [20, 25, 30])
    assert a == pytest.approx(2.5)
    assert b == pytest.approx(0.0)
    assert previsao.prever(a, b, 11) == pytest.approx(27.5)


def test_reta_com_intercepto():
    a, b = previsao.ajustar_reta([0, 1, 2], [1, 3, 5])
    assert (a, b) == (pytest.approx(2.0), pytest.approx(1.0))


def test_dados_com_ruido_ficam_proximos_da_tendencia():
    a, b = previsao.ajustar_reta([1, 2, 3, 4], [2.1, 3.9, 6.2, 7.8])
    assert a == pytest.approx(1.94)
    assert b == pytest.approx(0.15)


def test_previsao_nunca_e_negativa():
    assert previsao.prever(2.0, -10.0, 1) == 0.0


def test_r2_de_ajuste_perfeito_e_um():
    a, b = previsao.ajustar_reta([8, 10, 12], [20, 25, 30])
    assert previsao.r2([8, 10, 12], [20, 25, 30], a, b) == pytest.approx(1.0)


def test_r2_cai_quando_ha_ruido():
    xs, ys = [1, 2, 3, 4], [2, 9, 1, 8]
    a, b = previsao.ajustar_reta(xs, ys)
    assert 0.0 <= previsao.r2(xs, ys, a, b) < 0.5


def test_listas_de_tamanhos_diferentes_sao_recusadas():
    with pytest.raises(ValueError, match="mesmo tamanho"):
        previsao.ajustar_reta([1, 2, 3], [1, 2])


def test_uma_medicao_so_e_recusada():
    with pytest.raises(ValueError, match="pelo menos duas"):
        previsao.ajustar_reta([1], [1])


def test_x_constante_e_recusado():
    with pytest.raises(ValueError, match="todos iguais"):
        previsao.ajustar_reta([5, 5, 5], [1, 2, 3])


def test_historico_da_colonia_e_bem_explicado_por_uma_reta():
    historico = dados.carregar_colonia()["historico"]
    for xs, ys in ((historico["vento_ms"], historico["energia_eolica_kw"]),
                   (historico["irradiancia_wm2"], historico["energia_solar_kw"])):
        a, b = previsao.ajustar_reta(xs, ys)
        assert a > 0
        assert previsao.r2(xs, ys, a, b) > 0.99
