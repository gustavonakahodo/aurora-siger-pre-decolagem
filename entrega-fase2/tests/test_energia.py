"""Testes da análise de energia."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import energia


def test_exemplo_do_enunciado_consumo_maior_que_geracao():
    balanco = energia.analisar_balanco(40, 70)
    assert balanco.situacao == "DEFICIT"
    assert balanco.saldo_kw == -30
    assert balanco.mensagem == "ALERTA: consumo maior que geração"


def test_exemplo_do_enunciado_geracao_maior_que_consumo():
    balanco = energia.analisar_balanco(80, 30)
    assert balanco.situacao == "EXCEDENTE"
    assert balanco.saldo_kw == 50
    assert balanco.mensagem == "SUGESTÃO: armazenar energia excedente"


def test_equilibrio():
    balanco = energia.analisar_balanco(50, 50)
    assert balanco.situacao == "EQUILIBRIO"
    assert balanco.mensagem.startswith("OK")


def test_autonomia_da_reserva_em_deficit():
    balanco = energia.analisar_balanco(40, 70, reserva_pct=40, capacidade_kwh=400)
    assert balanco.autonomia_h == pytest.approx(160 / 30)


def test_sem_reserva_informada_nao_ha_autonomia():
    assert energia.analisar_balanco(40, 70).autonomia_h is None


def test_excedente_com_reserva_cheia_nao_manda_armazenar():
    balanco = energia.analisar_balanco(80, 30, reserva_pct=95, capacidade_kwh=400)
    assert "reserva cheia" in balanco.mensagem


def test_excedente_logo_abaixo_do_limite_ainda_armazena():
    balanco = energia.analisar_balanco(80, 30, reserva_pct=94.9, capacidade_kwh=400)
    assert balanco.mensagem == "SUGESTÃO: armazenar energia excedente"


def test_projecao_da_reserva_em_deficit():
    assert energia.projetar_reserva(40, -13, 6, 400) == pytest.approx(20.5)


def test_projecao_da_reserva_em_excedente():
    assert energia.projetar_reserva(78, 5, 6, 400) == pytest.approx(85.5)


def test_projecao_nao_passa_dos_limites():
    assert energia.projetar_reserva(10, -100, 6, 400) == 0.0
    assert energia.projetar_reserva(95, 100, 6, 400) == 100.0
