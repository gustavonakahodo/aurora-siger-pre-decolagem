"""Testes de propriedade: milhares de entradas aleatórias, regras que valem sempre.

Os outros arquivos testam casos escolhidos a dedo. Este sorteia entradas
(com semente fixa, para o resultado ser reproduzível) e verifica o que deve
ser verdade para QUALQUER entrada válida.
"""
import copy
import random
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import colonia
import dados
import decisoes
import energia
import previsao

COLONIA = dados.carregar_colonia()
ARVORE = COLONIA["sistemas"]
CONSUMIDORES = [caminho for caminho, folha in dados.listar_folhas(ARVORE)
                if "consumo_kw" in folha]
RODADAS = 3000


def _ligados_aleatorios(sorteio):
    return [c for c in CONSUMIDORES if sorteio.random() < 0.7]


def _consumidores_aleatorios(sorteio):
    """Lista inventada, com prioridades de 1 a 5 e consumos quebrados."""
    return [{"caminho": f"x/{i}", "rotulo": f"Equip{i}",
             "consumo_kw": round(sorteio.uniform(0.5, 25), 1),
             "prioridade": sorteio.randint(1, 5)}
            for i in range(sorteio.randint(0, 12))]


def test_consumo_da_arvore_bate_com_a_soma_dos_ligados():
    sorteio = random.Random(1)
    for _ in range(RODADAS):
        ligados = _ligados_aleatorios(sorteio)
        itens = dados.consumidores_ligados(ARVORE, ligados)
        assert dados.consumo_total(ARVORE, ligados) == pytest.approx(
            sum(item["consumo_kw"] for item in itens))


def test_consumo_dos_ramos_soma_o_consumo_total():
    sorteio = random.Random(2)
    for _ in range(RODADAS):
        ligados = _ligados_aleatorios(sorteio)
        por_ramo = sum(
            dados.consumo_total(ramo, ligados, nome)
            for nome, ramo in ARVORE["subsistemas"].items())
        assert por_ramo == pytest.approx(dados.consumo_total(ARVORE, ligados))


def test_decisao_nunca_desliga_essencial_e_fecha_a_conta():
    sorteio = random.Random(3)
    for _ in range(RODADAS):
        itens = _consumidores_aleatorios(sorteio)
        consumo = sum(i["consumo_kw"] for i in itens)
        essencial = sum(i["consumo_kw"] for i in itens if i["prioridade"] == 1)
        reserva = sorteio.uniform(0, 100)
        geracao = sorteio.uniform(0, 150)
        d = decisoes.decidir(reserva, consumo, geracao, itens)

        por_rotulo = {i["rotulo"]: i for i in itens}
        cortados = [por_rotulo[r] for r in d.desligar]
        assert all(i["prioridade"] != 1 for i in cortados)
        assert len(set(d.desligar)) == len(d.desligar)          # sem repetição
        assert d.consumo_apos_kw == pytest.approx(
            consumo - sum(i["consumo_kw"] for i in cortados))
        assert d.consumo_apos_kw >= essencial - 1e-9
        assert d.regras                                         # sempre explica


def test_nivel_da_decisao_segue_os_limites():
    sorteio = random.Random(4)
    for _ in range(RODADAS):
        itens = _consumidores_aleatorios(sorteio)
        consumo = sum(i["consumo_kw"] for i in itens)
        reserva = sorteio.uniform(0, 100)
        geracao = sorteio.uniform(0, 150)
        d = decisoes.decidir(reserva, consumo, geracao, itens)
        if reserva < 20:
            assert d.nivel == "CRÍTICO"
            # crítico: não sobra nenhum não essencial
            assert d.consumo_apos_kw == pytest.approx(
                sum(i["consumo_kw"] for i in itens if i["prioridade"] == 1))
        elif reserva < 50:
            assert d.nivel == "ALERTA"
            assert ("modo economia" in d.acao) == (consumo > 60)
        elif consumo > geracao:
            assert d.nivel == "ATENÇÃO" and d.desligar == ()
        else:
            assert d.nivel == "NORMAL" and d.desligar == ()


def test_em_alerta_o_corte_cobre_o_deficit_ou_esgota_o_que_pode_cortar():
    sorteio = random.Random(5)
    for _ in range(RODADAS):
        itens = _consumidores_aleatorios(sorteio)
        consumo = sum(i["consumo_kw"] for i in itens)
        essencial = sum(i["consumo_kw"] for i in itens if i["prioridade"] == 1)
        reserva = sorteio.uniform(20, 49.9)
        geracao = sorteio.uniform(0, 150)
        d = decisoes.decidir(reserva, consumo, geracao, itens)
        coube = d.consumo_apos_kw <= geracao + 1e-9
        esgotou = d.consumo_apos_kw == pytest.approx(essencial)
        assert coube or esgotou


def test_cortes_respeitam_a_ordem_de_prioridade_e_nao_exageram():
    sorteio = random.Random(6)
    for _ in range(RODADAS):
        itens = _consumidores_aleatorios(sorteio)
        reducao = sorteio.uniform(0, 80)
        cortes = decisoes.planejar_cortes(itens, reducao)
        prioridades = [c["prioridade"] for c in cortes]
        assert prioridades == sorted(prioridades, reverse=True)
        assert 1 not in prioridades
        # só avança para uma prioridade mais importante depois de esgotar a anterior
        for p in set(prioridades) - {min(prioridades, default=0)}:
            assert (sum(1 for c in cortes if c["prioridade"] == p)
                    == sum(1 for i in itens if i["prioridade"] == p))
        # não exagera: sem o último corte, a redução não seria atingida
        if cortes:
            assert sum(c["consumo_kw"] for c in cortes[:-1]) < reducao


def test_regressao_recupera_qualquer_reta_exata():
    sorteio = random.Random(7)
    for _ in range(RODADAS):
        a, b = sorteio.uniform(-50, 50), sorteio.uniform(-100, 100)
        xs = sorteio.sample(range(-200, 200), sorteio.randint(2, 30))
        ys = [a * x + b for x in xs]
        a2, b2 = previsao.ajustar_reta(xs, ys)
        assert a2 == pytest.approx(a, abs=1e-6)
        assert b2 == pytest.approx(b, abs=1e-6)
        assert previsao.r2(xs, ys, a2, b2) == pytest.approx(1.0, abs=1e-6)


def test_reta_ajustada_passa_pelo_ponto_medio_e_r2_fica_entre_0_e_1():
    sorteio = random.Random(8)
    for _ in range(RODADAS):
        n = sorteio.randint(2, 30)
        xs = sorteio.sample(range(0, 500), n)
        ys = [sorteio.uniform(0, 100) for _ in range(n)]
        a, b = previsao.ajustar_reta(xs, ys)
        assert a * sum(xs) / n + b == pytest.approx(sum(ys) / n)
        assert -1e-9 <= previsao.r2(xs, ys, a, b) <= 1 + 1e-9
        assert previsao.prever(a, b, sorteio.uniform(-100, 600)) >= 0


def test_reta_ajustada_tem_o_menor_erro_quadratico():
    sorteio = random.Random(9)

    def erro(xs, ys, a, b):
        return sum((y - (a * x + b)) ** 2 for x, y in zip(xs, ys))

    for _ in range(500):
        n = sorteio.randint(3, 15)
        xs = sorteio.sample(range(0, 100), n)
        ys = [sorteio.uniform(0, 100) for _ in range(n)]
        a, b = previsao.ajustar_reta(xs, ys)
        melhor = erro(xs, ys, a, b)
        for _ in range(10):   # qualquer outra reta próxima erra mais
            outra = erro(xs, ys, a + sorteio.uniform(-1, 1), b + sorteio.uniform(-5, 5))
            assert outra >= melhor - 1e-6


def test_balanco_e_coerente_com_o_sinal_do_saldo():
    sorteio = random.Random(10)
    for _ in range(RODADAS):
        geracao, consumo = sorteio.uniform(0, 150), sorteio.uniform(0, 150)
        reserva = sorteio.uniform(0, 100)
        b = energia.analisar_balanco(geracao, consumo, reserva, 400)
        assert b.saldo_kw == pytest.approx(geracao - consumo)
        if consumo > geracao:
            assert b.situacao == "DEFICIT" and b.mensagem.startswith("ALERTA")
            assert b.autonomia_h >= 0
            # a autonomia é exatamente o tempo até a reserva zerar
            assert energia.projetar_reserva(
                reserva, b.saldo_kw, b.autonomia_h, 400) == pytest.approx(0, abs=1e-6)
        elif geracao > consumo:
            assert b.situacao == "EXCEDENTE" and b.mensagem.startswith("SUGESTÃO")
            assert b.autonomia_h is None


def test_reserva_projetada_fica_entre_0_e_100_e_segue_o_saldo():
    sorteio = random.Random(11)
    for _ in range(RODADAS):
        reserva, saldo = sorteio.uniform(0, 100), sorteio.uniform(-200, 200)
        horas = sorteio.uniform(0, 48)
        projetada = energia.projetar_reserva(reserva, saldo, horas, 400)
        assert 0 <= projetada <= 100
        if saldo > 0:
            assert projetada >= reserva
        if saldo < 0:
            assert projetada <= reserva


def _colonia_aleatoria(sorteio):
    alterada = copy.deepcopy(COLONIA)
    alterada["cenarios"]["sorteado"] = {
        "descricao": "Cenário sorteado.",
        "reserva_pct": round(sorteio.uniform(0, 100), 1),
        "geracao_solar_kw": round(sorteio.uniform(0, 70), 1),
        "geracao_eolica_kw": round(sorteio.uniform(0, 50), 1),
        "previsao_clima": {"vento_ms": sorteio.randint(0, 30),
                           "irradiancia_wm2": sorteio.randint(0, 1300)},
        "ligados": _ligados_aleatorios(sorteio),
    }
    return alterada


def test_sistema_completo_aguenta_qualquer_cenario_valido():
    sorteio = random.Random(12)
    niveis = set()
    for _ in range(RODADAS):
        alterada = _colonia_aleatoria(sorteio)
        r = colonia.avaliar(alterada, "sorteado")
        niveis.add(r.decisao.nivel)

        # aviso preventivo existe se, e só se, a tendência é de piora
        assert (r.aviso_preventivo is not None) == (r.tendencia == "PIORA")
        assert 0 <= r.reserva_prevista_pct <= 100
        assert r.previsao_solar_kw >= 0 and r.previsao_eolica_kw >= 0
        # essenciais ligados continuam ligados, agora e na previsão
        essenciais = sum(
            c["consumo_kw"] for c in dados.consumidores_ligados(
                ARVORE, alterada["cenarios"]["sorteado"]["ligados"])
            if c["prioridade"] == 1)
        assert r.decisao.consumo_apos_kw >= essenciais - 1e-9
        assert r.decisao_prevista.consumo_apos_kw >= essenciais - 1e-9
        # a previsão nunca religa nem desliga duas vezes a mesma coisa
        assert not set(r.decisao.desligar) & set(r.decisao_prevista.desligar)

        texto = colonia.formatar_relatorio(alterada, r)
        assert max(len(linha) for linha in texto.splitlines()) <= colonia.LARGURA
        assert f"DECISÃO: {r.decisao.acao}" in texto
    assert niveis == {"NORMAL", "ATENÇÃO", "ALERTA", "CRÍTICO"}   # cobriu todos


def test_antecipar_os_cortes_nunca_piora_a_reserva():
    sorteio = random.Random(13)
    vistos = 0
    for _ in range(RODADAS):
        alterada = _colonia_aleatoria(sorteio)
        r = colonia.avaliar(alterada, "sorteado")
        if not (r.aviso_preventivo and r.decisao_prevista.desligar):
            continue
        vistos += 1
        trecho = r.aviso_preventivo.split("a reserva fica em ")[1]
        antecipando = float(trecho.split(" %")[0])
        assert antecipando >= round(r.reserva_prevista_pct, 1) - 0.05
    assert vistos > 100
