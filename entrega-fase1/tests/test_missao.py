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


def _telemetria(**alteracoes):
    """Telemetria nominal com os campos indicados sobrescritos."""
    dados = missao.carregar_telemetria(missao.CAMINHO_PADRAO, "nominal")
    modulos = alteracoes.pop("modulos_criticos", None)
    dados.update(alteracoes)
    if modulos:
        dados["modulos_criticos"] = {**dados["modulos_criticos"], **modulos}
    return dados


def test_cenario_nominal_libera_o_lancamento():
    resultado = missao.verificar_telemetria(_telemetria())
    assert resultado.aprovado is True
    assert resultado.decisao == "PRONTO PARA DECOLAR"
    assert resultado.falhas == ()


@pytest.mark.parametrize("valor", [18.0, 28.0])
def test_limites_da_faixa_sao_inclusivos(valor):
    resultado = missao.verificar_telemetria(_telemetria(temperatura_interna_c=valor))
    assert resultado.aprovado is True


@pytest.mark.parametrize("valor", [17.9, 28.1])
def test_temperatura_interna_fora_da_faixa_aborta(valor):
    resultado = missao.verificar_telemetria(_telemetria(temperatura_interna_c=valor))
    assert resultado.aprovado is False
    assert resultado.decisao == "DECOLAGEM ABORTADA"
    assert any("Temperatura interna" in f for f in resultado.falhas)


@pytest.mark.parametrize("chave,valor", [
    ("temperatura_externa_c", 50.1),
    ("temperatura_externa_c", -40.1),
    ("pressao_lox_bar", 199.9),
    ("pressao_lox_bar", 250.1),
    ("pressao_rp1_bar", 189.9),
    ("pressao_rp1_bar", 240.1),
])
def test_cada_parametro_numerico_fora_da_faixa_aborta(chave, valor):
    resultado = missao.verificar_telemetria(_telemetria(**{chave: valor}))
    assert resultado.aprovado is False
    assert any(missao.ROTULOS[chave] in f for f in resultado.falhas)


def test_integridade_estrutural_comprometida_aborta():
    resultado = missao.verificar_telemetria(_telemetria(integridade_estrutural=0))
    assert resultado.aprovado is False
    assert any("Integridade estrutural" in f for f in resultado.falhas)


@pytest.mark.parametrize("valor,aprovado", [(85.0, True), (84.9, False)])
def test_nivel_minimo_de_energia(valor, aprovado):
    resultado = missao.verificar_telemetria(_telemetria(nivel_energia_pct=valor))
    assert resultado.aprovado is aprovado


def test_modulo_critico_em_falha_aborta():
    resultado = missao.verificar_telemetria(
        _telemetria(modulos_criticos={"propulsao": "FALHA"})
    )
    assert resultado.aprovado is False
    assert any("propulsão" in f for f in resultado.falhas)


def test_todas_as_falhas_sao_reportadas_e_nao_apenas_a_primeira():
    dados = missao.carregar_telemetria(missao.CAMINHO_PADRAO, "falha_multipla")
    resultado = missao.verificar_telemetria(dados)
    assert resultado.aprovado is False
    assert len(resultado.falhas) == 5
    esperados = ["Temperatura interna", "Integridade estrutural",
                 "Nível de energia", "Pressão do tanque de LOX",
                 "comunicação", "controle térmico"]
    texto = " | ".join(resultado.falhas)
    for esperado in esperados:
        assert esperado in texto


def test_analise_energetica_do_cenario_nominal():
    resultado = missao.analisar_energia(carga_pct=92.0)
    assert resultado.disponivel_kwh == pytest.approx(101.568, abs=1e-3)
    assert resultado.restante_kwh == pytest.approx(56.568, abs=1e-3)
    assert resultado.autonomia_h == pytest.approx(8.7028, abs=1e-3)
    assert resultado.margem_pct == pytest.approx(125.707, abs=1e-3)
    assert resultado.aprovado is True


def test_analise_energetica_sem_perdas_e_numeros_redondos():
    resultado = missao.analisar_energia(
        carga_pct=50.0, capacidade_kwh=100.0, perdas_pct=0.0,
        consumo_decolagem_kwh=25.0, consumo_voo_kw=5.0,
    )
    assert resultado.disponivel_kwh == pytest.approx(50.0)
    assert resultado.restante_kwh == pytest.approx(25.0)
    assert resultado.autonomia_h == pytest.approx(5.0)
    assert resultado.margem_pct == pytest.approx(100.0)
    assert resultado.aprovado is True


def test_margem_abaixo_do_minimo_reprova():
    # 100 kWh x 30% = 30 disponíveis, consumo 27 -> margem 11,1 % (< 20 %)
    resultado = missao.analisar_energia(
        carga_pct=30.0, capacidade_kwh=100.0, perdas_pct=0.0,
        consumo_decolagem_kwh=27.0, consumo_voo_kw=5.0,
    )
    assert resultado.margem_pct == pytest.approx(11.111, abs=1e-3)
    assert resultado.aprovado is False


def test_energia_insuficiente_para_decolar_zera_autonomia():
    resultado = missao.analisar_energia(
        carga_pct=10.0, capacidade_kwh=100.0, perdas_pct=0.0,
        consumo_decolagem_kwh=45.0, consumo_voo_kw=5.0,
    )
    assert resultado.restante_kwh == pytest.approx(-35.0)
    assert resultado.autonomia_h == 0.0
    assert resultado.aprovado is False


def test_relatorio_nominal_mostra_decisao_e_autonomia():
    texto = missao.executar("nominal")
    assert "PRONTO PARA DECOLAR" in texto
    assert "Aurora-1" in texto
    assert "8.70 h" in texto
    assert "Nenhuma" in texto


def test_relatorio_de_falha_lista_todos_os_motivos():
    texto = missao.executar("falha_multipla")
    assert "DECOLAGEM ABORTADA" in texto
    assert "Temperatura interna" in texto
    assert "comunicação" in texto

    # Isolar a seção "3. MOTIVOS DE ABORTO" e contar os motivos
    partes = texto.split("3. MOTIVOS DE ABORTO")
    assert len(partes) == 2, "Seção 3 deve existir no relatório"

    secao_motivos = partes[1].split("=")[0]  # Pega até a próxima linha de "="
    motivos = [linha for linha in secao_motivos.split("\n") if "- " in linha]
    assert len(motivos) == 5, f"Deve haver exatamente 5 motivos, encontrou {len(motivos)}"


def test_relatorio_mostra_cada_parametro_com_sua_faixa():
    texto = missao.executar("nominal")
    assert "23.4" in texto
    assert "18.0 a 28.0" in texto
    assert "OK" in texto


def test_execucao_por_linha_de_comando():
    import subprocess
    import sys as _sys
    caminho = Path(missao.__file__)
    saida = subprocess.run(
        [_sys.executable, str(caminho), "falha_termica"],
        capture_output=True, text=True, check=True,
    )
    assert "DECOLAGEM ABORTADA" in saida.stdout


def test_cenario_inexistente_na_linha_de_comando_falha_sem_traceback():
    import subprocess
    import sys as _sys
    caminho = Path(missao.__file__)
    saida = subprocess.run(
        [_sys.executable, str(caminho), "inexistente"],
        capture_output=True, text=True,
    )
    assert saida.returncode == 1
    assert "Traceback" not in saida.stderr
    assert "Cenário 'inexistente' inexistente" in saida.stderr
    assert "falha_multipla" in saida.stderr  # lista os cenários disponíveis
