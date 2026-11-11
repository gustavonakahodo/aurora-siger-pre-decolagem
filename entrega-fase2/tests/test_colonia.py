"""Testes do sistema integrado, de ponta a ponta."""
import subprocess
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

import colonia
import dados

COLONIA = dados.carregar_colonia()


def test_cenario_nominal_sugere_armazenar_e_segue_normal():
    r = colonia.avaliar(COLONIA, "nominal")
    assert r.balanco.mensagem == "SUGESTÃO: armazenar energia excedente"
    assert r.decisao.nivel == "NORMAL"
    assert r.aviso_preventivo is None


def test_cenario_economia_reproduz_o_exemplo_do_enunciado():
    r = colonia.avaliar(COLONIA, "economia")
    assert (r.reserva_pct, r.consumo_kw) == (40.0, 70.0)
    assert r.balanco.mensagem == "ALERTA: consumo maior que geração"
    assert r.decisao.acao.startswith("ALERTA: reduzir consumo")
    assert r.decisao.consumo_apos_kw == 40.0


def test_cenario_critico_preserva_os_essenciais_e_preve_melhora():
    r = colonia.avaliar(COLONIA, "critico")
    assert r.decisao.nivel == "CRÍTICO"
    assert r.decisao.consumo_apos_kw == 34.0
    assert r.tendencia == "MELHORA"


def test_cenario_preventivo_avisa_antes_do_problema():
    r = colonia.avaliar(COLONIA, "preventivo")
    assert r.decisao.nivel == "NORMAL"          # hoje está tudo bem
    assert r.tendencia == "PIORA"               # mas a previsão não
    assert r.aviso_preventivo.startswith("PREVENTIVO")
    assert "Laboratório" in r.aviso_preventivo


def test_previsao_usa_as_retas_do_historico():
    r = colonia.avaliar(COLONIA, "nominal")
    assert r.previsao_eolica_kw == pytest.approx(30.0, abs=0.5)   # vento 12
    assert r.previsao_solar_kw == pytest.approx(45.0, abs=0.5)    # irradiância 750


def test_projecao_parte_do_consumo_apos_os_cortes():
    r = colonia.avaliar(COLONIA, "economia")
    geracao_prevista = r.previsao_solar_kw + r.previsao_eolica_kw
    assert r.balanco_previsto.saldo_kw == pytest.approx(geracao_prevista - 40.0)


@pytest.mark.parametrize("cenario", sorted(COLONIA["cenarios"]))
def test_relatorio_tem_todas_as_secoes_e_cabe_na_largura(cenario):
    texto = colonia.executar(cenario)
    for secao in ("1. SISTEMAS DA COLÔNIA", "2. SITUAÇÃO ATUAL",
                  "3. MODELO DE PREVISÃO", "4. PRÓXIMA JANELA", "DECISÃO: "):
        assert secao in texto
    assert max(len(linha) for linha in texto.splitlines()) <= colonia.LARGURA


def test_linha_de_comando_roda_o_cenario_pedido():
    saida = subprocess.run([sys.executable, "src/colonia.py", "economia"],
                           cwd=RAIZ, capture_output=True, text=True)
    assert saida.returncode == 0
    assert "DECISÃO: ALERTA: reduzir consumo" in saida.stdout


def test_linha_de_comando_recusa_cenario_inexistente():
    saida = subprocess.run([sys.executable, "src/colonia.py", "marte"],
                           cwd=RAIZ, capture_output=True, text=True)
    assert saida.returncode == 1
    assert "inexistente" in saida.stderr
    assert "Traceback" not in saida.stderr
