"""Testes da organização e navegação dos dados da colônia."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import dados


@pytest.fixture(scope="module")
def colonia():
    return dados.carregar_colonia()


def test_carrega_historico_em_listas_do_mesmo_tamanho(colonia):
    historico = colonia["historico"]
    assert len(historico["vento_ms"]) == len(historico["energia_eolica_kw"])
    assert len(historico["irradiancia_wm2"]) == len(historico["energia_solar_kw"])


def test_carrega_cenario_por_chave(colonia):
    assert dados.carregar_cenario(colonia, "economia")["reserva_pct"] == 40.0


def test_cenario_inexistente_levanta_erro_legivel(colonia):
    with pytest.raises(KeyError, match="inexistente"):
        dados.carregar_cenario(colonia, "marte")


def test_navega_ate_um_subsistema_pelo_caminho(colonia):
    eolico = dados.buscar_subsistema(colonia["sistemas"], "energia/geracao/eolico")
    assert eolico["rotulo"] == "Eólico"


def test_navega_ate_um_agrupamento(colonia):
    geracao = dados.buscar_subsistema(colonia["sistemas"], "energia/geracao")
    assert set(geracao["subsistemas"]) == {"solar", "eolico"}


def test_caminho_inexistente_levanta_erro(colonia):
    with pytest.raises(KeyError, match="não existe"):
        dados.buscar_subsistema(colonia["sistemas"], "energia/nuclear")


def test_lista_todas_as_folhas_com_caminho(colonia):
    caminhos = [c for c, _ in dados.listar_folhas(colonia["sistemas"])]
    assert "energia/geracao/solar" in caminhos
    assert "suporte_vida/oxigenio" in caminhos
    assert len(caminhos) == 11


def test_consumo_total_soma_so_o_que_esta_ligado(colonia):
    arvore = colonia["sistemas"]
    assert dados.consumo_total(arvore, ["suporte_vida/oxigenio", "habitat/lazer"]) == 20.0


def test_consumo_total_de_um_ramo(colonia):
    arvore = colonia["sistemas"]
    ligados = colonia["cenarios"]["nominal"]["ligados"]
    ramo = dados.buscar_subsistema(arvore, "suporte_vida")
    assert dados.consumo_total(ramo, ligados, "suporte_vida") == 30.0


def test_cenario_economia_consome_70_como_no_enunciado(colonia):
    ligados = colonia["cenarios"]["economia"]["ligados"]
    assert dados.consumo_total(colonia["sistemas"], ligados) == 70.0


def test_consumidores_ligados_trazem_prioridade(colonia):
    itens = dados.consumidores_ligados(colonia["sistemas"], ["habitat/lazer"])
    assert itens == [{"caminho": "habitat/lazer", "rotulo": "Lazer",
                      "consumo_kw": 8.0, "prioridade": 3}]


def test_gerador_nao_e_consumidor(colonia):
    with pytest.raises(KeyError, match="não é um consumidor"):
        dados.consumidores_ligados(colonia["sistemas"], ["energia/geracao/solar"])


def test_todo_cenario_so_liga_subsistemas_existentes(colonia):
    for cenario in colonia["cenarios"].values():
        dados.consumidores_ligados(colonia["sistemas"], cenario["ligados"])
