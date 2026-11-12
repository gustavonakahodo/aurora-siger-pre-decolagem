"""Testes das regras de decisão."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import dados
import decisoes

COLONIA = dados.carregar_colonia()
TODOS = dados.consumidores_ligados(
    COLONIA["sistemas"], COLONIA["cenarios"]["economia"]["ligados"])  # 70 kW


def test_exemplo_do_enunciado_energia_40_consumo_70():
    decisao = decisoes.decidir(40, 70, 40, TODOS)
    assert decisao.nivel == "ALERTA"
    assert decisao.acao.startswith("ALERTA: reduzir consumo")


def test_condicoes_combinadas_ativam_modo_economia():
    decisao = decisoes.decidir(40, 70, 40, TODOS)
    assert "modo economia" in decisao.acao
    assert " E " in decisao.regras[0]


def test_modo_economia_desliga_por_prioridade_ate_caber_na_geracao():
    decisao = decisoes.decidir(40, 70, 40, TODOS)
    # prioridade 3 inteira (maior consumo primeiro), depois prioridade 2
    assert decisao.desligar == ("Laboratório", "Lazer", "Estufa")
    assert decisao.consumo_apos_kw == 40


def test_modo_economia_sem_deficit_corta_so_prioridade_3():
    decisao = decisoes.decidir(40, 70, 90, TODOS)
    assert decisao.desligar == ("Laboratório", "Lazer")


def test_reserva_baixa_sem_consumo_alto_e_alerta_simples():
    ligados = [c for c in TODOS if c["rotulo"] != "Laboratório"]  # 58 kW
    decisao = decisoes.decidir(40, 58, 50, ligados)
    assert decisao.acao == "ALERTA: reduzir consumo"
    assert decisao.desligar == ("Lazer",)
    assert decisao.consumo_apos_kw == 50


def test_alerta_simples_sem_deficit_nao_desliga_nada():
    ligados = [c for c in TODOS if c["rotulo"] != "Laboratório"]
    decisao = decisoes.decidir(40, 58, 60, ligados)
    assert decisao.nivel == "ALERTA"
    assert decisao.desligar == ()


def test_reserva_critica_mantem_apenas_essenciais():
    decisao = decisoes.decidir(15, 70, 16, TODOS)
    assert decisao.nivel == "CRÍTICO"
    assert set(decisao.desligar) == {"Laboratório", "Lazer", "Estufa", "Iluminação"}
    assert decisao.consumo_apos_kw == 34
    assert "alimentado pela reserva" in decisao.regras[-1]


def test_suporte_a_vida_nunca_e_desligado():
    essenciais = {c["rotulo"] for c in TODOS if c["prioridade"] == 1}
    for reserva in (0, 10, 19.9, 30, 49.9, 60, 100):
        for geracao in (0, 20, 40, 100):
            decisao = decisoes.decidir(reserva, 70, geracao, TODOS)
            assert not essenciais & set(decisao.desligar)
            assert decisao.consumo_apos_kw >= 34


def test_deficit_com_reserva_boa_usa_a_reserva_sem_cortes():
    decisao = decisoes.decidir(80, 70, 50, TODOS)
    assert decisao.nivel == "ATENÇÃO"
    assert decisao.desligar == ()
    assert decisao.consumo_apos_kw == 70


def test_situacao_normal():
    decisao = decisoes.decidir(80, 70, 83, TODOS)
    assert decisao.nivel == "NORMAL"
    assert decisao.desligar == ()


def test_fronteiras_dos_limites():
    assert decisoes.decidir(50, 70, 80, TODOS).nivel == "NORMAL"      # 50 não é < 50
    assert decisoes.decidir(49.9, 70, 80, TODOS).nivel == "ALERTA"
    assert decisoes.decidir(20, 70, 80, TODOS).nivel == "ALERTA"      # 20 não é < 20
    assert decisoes.decidir(19.9, 70, 80, TODOS).nivel == "CRÍTICO"
    # consumo exatamente 60 não é "alto"
    assert decisoes.decidir(40, 60, 80, TODOS).acao == "ALERTA: reduzir consumo"


def test_planejar_cortes_para_assim_que_cobre_a_reducao():
    cortes = decisoes.planejar_cortes(TODOS, 10)
    assert [c["rotulo"] for c in cortes] == ["Laboratório"]


def test_planejar_cortes_sem_reducao_nao_corta():
    assert decisoes.planejar_cortes(TODOS, 0) == []


def test_comparar_decisoes():
    normal = decisoes.decidir(80, 70, 83, TODOS)
    critico = decisoes.decidir(5, 70, 30, TODOS)
    assert decisoes.comparar(normal, critico, 80, 5) == "PIORA"
    assert decisoes.comparar(critico, normal, 5, 80) == "MELHORA"
    assert decisoes.comparar(normal, normal, 80, 80) == "ESTÁVEL"


def test_mesmo_nivel_desempata_pelo_rumo_da_reserva():
    alerta = decisoes.decidir(40, 50, 40, TODOS)
    assert decisoes.comparar(alerta, alerta, 40, 21) == "PIORA"
    assert decisoes.comparar(alerta, alerta, 40, 48) == "MELHORA"
    assert decisoes.comparar(alerta, alerta, 40, 40.5) == "ESTÁVEL"


def test_nivel_pesa_mais_que_a_reserva():
    normal = decisoes.decidir(80, 70, 83, TODOS)
    alerta = decisoes.decidir(40, 50, 40, TODOS)
    # reserva subindo não compensa uma decisão mais grave
    assert decisoes.comparar(normal, alerta, 30, 45) == "PIORA"


PISCINA = {"caminho": "habitat/piscina", "rotulo": "Piscina",
           "consumo_kw": 5.0, "prioridade": 4}


def test_prioridade_acima_de_3_e_cortada_primeiro():
    cortes = decisoes.planejar_cortes(TODOS + [PISCINA], 4)
    assert [c["rotulo"] for c in cortes] == ["Piscina"]


def test_reserva_critica_desliga_qualquer_prioridade_nao_essencial():
    decisao = decisoes.decidir(15, 75, 16, TODOS + [PISCINA])
    assert "Piscina" in decisao.desligar
    assert decisao.consumo_apos_kw == 34


def test_modo_economia_desliga_tudo_acima_da_prioridade_2():
    decisao = decisoes.decidir(40, 75, 90, TODOS + [PISCINA])
    assert decisao.desligar == ("Piscina", "Laboratório", "Lazer")


def test_alerta_sem_nada_a_cortar_explica_o_que_fazer():
    essenciais = [c for c in TODOS if c["prioridade"] == 1]
    decisao = decisoes.decidir(43, 34, 52, essenciais)
    assert decisao.desligar == ()
    assert "não ligar novas cargas" in decisao.regras[-1]


def test_so_essenciais_em_deficit_explica_que_a_reserva_cobre():
    essenciais = [c for c in TODOS if c["prioridade"] == 1]
    decisao = decisoes.decidir(15, 34, 16, essenciais)
    assert decisao.desligar == ()
    assert "alimentado pela reserva" in decisao.regras[-1]
