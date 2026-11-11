"""Testes do sistema integrado, de ponta a ponta."""
import copy
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

import colonia
import dados

COLONIA = dados.carregar_colonia()


def _rodar(*argumentos, **ambiente):
    """Executa o programa como o usuário faria, lendo a saída como UTF-8."""
    return subprocess.run(
        [sys.executable, "src/colonia.py", *argumentos], cwd=RAIZ,
        capture_output=True, encoding="utf-8", env={**os.environ, **ambiente})


def test_cenario_nominal_sugere_armazenar_e_segue_normal():
    r = colonia.avaliar(COLONIA, "nominal")
    assert r.balanco.mensagem == "SUGESTÃO: armazenar energia excedente"
    assert r.decisao.nivel == "NORMAL"
    assert r.tendencia == "MELHORA"             # a reserva sobe
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
    assert r.reserva_prevista_pct < 10
    assert "59.9 %" in r.aviso_preventivo       # reserva se os cortes forem antecipados


def test_cenario_economia_avisa_que_a_reserva_continua_caindo():
    r = colonia.avaliar(COLONIA, "economia")
    assert r.decisao.nivel == r.decisao_prevista.nivel == "ALERTA"
    assert r.tendencia == "PIORA"               # mesmo nível, reserva em queda
    assert "Iluminação" in r.aviso_preventivo


def test_parcelas_da_previsao_somam_o_total_exibido():
    for nome in COLONIA["cenarios"]:
        r = colonia.avaliar(COLONIA, nome)
        total = r.previsao_solar_kw + r.previsao_eolica_kw
        assert f"{total:.1f}" == f"{round(r.previsao_solar_kw, 1) + round(r.previsao_eolica_kw, 1):.1f}"
        assert r.previsao_solar_kw == round(r.previsao_solar_kw, 1)


def test_clima_fora_do_historico_gera_aviso_de_extrapolacao():
    alterada = copy.deepcopy(COLONIA)
    alterada["cenarios"]["nominal"]["previsao_clima"] = {
        "vento_ms": 60, "irradiancia_wm2": 0}
    r = colonia.avaliar(alterada, "nominal")
    assert len(r.extrapolacoes) == 2
    texto = colonia.formatar_relatorio(alterada, r)
    assert texto.count("CUIDADO ........... extrapolação:") == 2
    assert max(len(linha) for linha in texto.splitlines()) <= colonia.LARGURA


def test_clima_dentro_do_historico_nao_gera_aviso():
    for nome in COLONIA["cenarios"]:
        assert colonia.avaliar(COLONIA, nome).extrapolacoes == ()


def test_arvore_do_relatorio_mostra_geracao_e_reserva():
    texto = colonia.executar("economia")
    assert "Solar                     21.0 kW   gerando" in texto
    assert "reserva em 40.0 %" in texto


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
    saida = _rodar("economia")
    assert saida.returncode == 0
    assert "DECISÃO: ALERTA: reduzir consumo" in saida.stdout


def test_linha_de_comando_sem_argumento_usa_o_cenario_nominal():
    saida = _rodar()
    assert saida.returncode == 0
    assert "Cenário: nominal" in saida.stdout


def test_linha_de_comando_recusa_cenario_inexistente():
    saida = _rodar("marte")
    assert saida.returncode == 1
    assert "inexistente" in saida.stderr
    assert "Traceback" not in saida.stderr


@pytest.mark.parametrize("cenario", sorted(COLONIA["cenarios"]))
def test_saida_nao_quebra_em_terminal_com_codificacao_do_windows(cenario):
    # cp1252 não tem "→" nem "≥": sem reconfigurar a saída, o print falharia.
    saida = _rodar(cenario, PYTHONIOENCODING="cp1252")
    assert saida.returncode == 0
    assert saida.stderr == ""
    assert "R² = " in saida.stdout


def test_executar_recusa_arquivo_com_leitura_invalida(tmp_path):
    alterada = copy.deepcopy(COLONIA)
    alterada["cenarios"]["nominal"]["reserva_pct"] = -20
    arquivo = tmp_path / "colonia.json"
    arquivo.write_text(json.dumps(alterada), encoding="utf-8")
    with pytest.raises(ValueError, match="entre 0 e 100"):
        colonia.executar("nominal", arquivo)
