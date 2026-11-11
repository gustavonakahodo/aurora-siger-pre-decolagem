"""Sistema integrado da colônia Aurora Siger.

Junta as quatro partes: organiza os dados (dados.py), analisa o uso de
energia (energia.py), decide por regras (decisoes.py) e prevê a geração da
próxima janela por regressão (previsao.py). Uso:

    python src/colonia.py [cenario]
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import textwrap

import dados
import decisoes
import energia
import previsao

LARGURA = 78


@dataclass(frozen=True)
class Modelo:
    """Reta ajustada ao histórico de uma fonte de energia."""

    a: float
    b: float
    r2: float
    medicoes: int


@dataclass(frozen=True)
class Resultado:
    """Tudo o que o sistema calculou para um cenário."""

    cenario: str
    reserva_pct: float
    consumo_kw: float
    geracao_solar_kw: float
    geracao_eolica_kw: float
    balanco: energia.Balanco
    decisao: decisoes.Decisao
    modelo_eolico: Modelo
    modelo_solar: Modelo
    previsao_solar_kw: float
    previsao_eolica_kw: float
    reserva_prevista_pct: float
    balanco_previsto: energia.Balanco
    decisao_prevista: decisoes.Decisao
    tendencia: str
    aviso_preventivo: str | None


def treinar(xs: list[float], ys: list[float]) -> Modelo:
    """Ajusta a reta a um par de listas do histórico."""
    a, b = previsao.ajustar_reta(xs, ys)
    return Modelo(a, b, previsao.r2(xs, ys, a, b), len(xs))


def avaliar(colonia: dict, nome_cenario: str) -> Resultado:
    """Executa o fluxo completo: dados → análise → decisão → previsão."""
    cenario = dados.carregar_cenario(colonia, nome_cenario)
    arvore = colonia["sistemas"]
    historico = colonia["historico"]
    janela_h = colonia["janela_previsao_h"]
    capacidade = dados.buscar_subsistema(
        arvore, "energia/armazenamento/baterias")["capacidade_kwh"]

    # 1. Situação atual (sistema reativo): leituras medidas.
    reserva = cenario["reserva_pct"]
    consumidores = dados.consumidores_ligados(arvore, cenario["ligados"])
    consumo = dados.consumo_total(arvore, cenario["ligados"])
    solar, eolica = cenario["geracao_solar_kw"], cenario["geracao_eolica_kw"]
    geracao = solar + eolica
    balanco = energia.analisar_balanco(geracao, consumo, reserva, capacidade)
    decisao = decisoes.decidir(reserva, consumo, geracao, consumidores)

    # 2. Próxima janela (sistema preditivo): geração estimada pelo clima.
    modelo_eolico = treinar(historico["vento_ms"], historico["energia_eolica_kw"])
    modelo_solar = treinar(historico["irradiancia_wm2"], historico["energia_solar_kw"])
    clima = cenario["previsao_clima"]
    prev_eolica = previsao.prever(modelo_eolico.a, modelo_eolico.b, clima["vento_ms"])
    prev_solar = previsao.prever(modelo_solar.a, modelo_solar.b, clima["irradiancia_wm2"])
    geracao_prevista = prev_solar + prev_eolica

    # A projeção parte do consumo que sobra depois da decisão de agora.
    restantes = [c for c in consumidores if c["rotulo"] not in decisao.desligar]
    consumo_futuro = decisao.consumo_apos_kw
    reserva_prevista = energia.projetar_reserva(
        reserva, geracao_prevista - consumo_futuro, janela_h, capacidade)
    balanco_previsto = energia.analisar_balanco(
        geracao_prevista, consumo_futuro, reserva_prevista, capacidade)
    decisao_prevista = decisoes.decidir(
        reserva_prevista, consumo_futuro, geracao_prevista, restantes)
    tendencia = decisoes.comparar(decisao, decisao_prevista)

    return Resultado(
        cenario=nome_cenario, reserva_pct=reserva, consumo_kw=consumo,
        geracao_solar_kw=solar, geracao_eolica_kw=eolica, balanco=balanco,
        decisao=decisao, modelo_eolico=modelo_eolico, modelo_solar=modelo_solar,
        previsao_solar_kw=prev_solar, previsao_eolica_kw=prev_eolica,
        reserva_prevista_pct=reserva_prevista, balanco_previsto=balanco_previsto,
        decisao_prevista=decisao_prevista, tendencia=tendencia,
        aviso_preventivo=aviso_preventivo(decisao_prevista, tendencia),
    )


def aviso_preventivo(prevista: decisoes.Decisao, tendencia: str) -> str | None:
    """Se a previsão é pior que o presente, recomenda agir antes da hora."""
    if tendencia != "PIORA":
        return None
    aviso = f"PREVENTIVO: situação prevista {prevista.nivel}"
    if prevista.desligar:
        aviso += f" — antecipar o desligamento de {', '.join(prevista.desligar)}"
    return aviso


def _quebrar(texto: str, recuo: str) -> list[str]:
    """Quebra um texto longo na largura do relatório, alinhando a sobra."""
    return textwrap.wrap(texto, LARGURA, subsequent_indent=recuo)


def _linhas_arvore(no: dict, ligados: list[str], caminho: str = "",
                   nivel: int = 0) -> list[str]:
    """Desenha a hierarquia com recuo, um nível por degrau."""
    recuo = "  " * (nivel + 1)
    if "subsistemas" in no:
        linhas = [f"{recuo}{no['rotulo']}"]
        for nome, filho in no["subsistemas"].items():
            sub = f"{caminho}/{nome}" if caminho else nome
            linhas.extend(_linhas_arvore(filho, ligados, sub, nivel + 1))
        return linhas
    rotulo = f"{recuo}{no['rotulo']}"
    if "consumo_kw" in no:
        estado = "LIGADO" if caminho in ligados else "desligado"
        return [f"{rotulo:<32}{no['consumo_kw']:>6.1f} kW   "
                f"prioridade {no['prioridade']}   {estado}"]
    if "capacidade_kwh" in no:
        return [f"{rotulo:<32}{no['capacidade_kwh']:>6.0f} kWh"]
    return [rotulo]


def _linha_modelo(nome: str, variavel: str, modelo: Modelo) -> str:
    sinal = "+" if modelo.b >= 0 else "-"
    return (f"  {nome}: energia = {modelo.a:.4f} × {variavel} {sinal} "
            f"{abs(modelo.b):.2f}   (R² = {modelo.r2:.4f}, "
            f"{modelo.medicoes} medições)")


def _linhas_decisao(decisao: decisoes.Decisao, balanco: energia.Balanco) -> list[str]:
    analise = balanco.mensagem
    if balanco.autonomia_h is not None:
        analise += f" (a reserva cobre {balanco.autonomia_h:.1f} h)"
    linhas = [*_quebrar(f"  Análise ........... {analise}", " " * 22),
              f"  Decisão ........... {decisao.acao}"]
    for regra in decisao.regras:
        linhas.extend(_quebrar(f"    regra: {regra}", " " * 11))
    if decisao.desligar:
        linhas.append(f"  Desligar .......... {', '.join(decisao.desligar)}")
        linhas.append(f"  Consumo após ...... {decisao.consumo_apos_kw:.1f} kW")
    return linhas


def formatar_relatorio(colonia: dict, r: Resultado) -> str:
    """Monta o relatório em texto puro."""
    cenario = colonia["cenarios"][r.cenario]
    clima = cenario["previsao_clima"]
    geracao = r.geracao_solar_kw + r.geracao_eolica_kw
    geracao_prevista = r.previsao_solar_kw + r.previsao_eolica_kw
    linhas = [
        "=" * LARGURA,
        f"COLÔNIA {colonia['colonia'].upper()} — SISTEMA INTEGRADO DE ENERGIA",
        *_quebrar(f"Cenário: {r.cenario} — {cenario['descricao']}", " " * 9),
        "=" * LARGURA,
        "",
        "1. SISTEMAS DA COLÔNIA",
    ]
    linhas.extend(_linhas_arvore(colonia["sistemas"], cenario["ligados"]))
    linhas += [
        "",
        "2. SITUAÇÃO ATUAL",
        f"  Reserva ........... {r.reserva_pct:.1f} %",
        f"  Geração ........... {geracao:.1f} kW "
        f"(solar {r.geracao_solar_kw:.1f} + eólica {r.geracao_eolica_kw:.1f})",
        f"  Consumo ........... {r.consumo_kw:.1f} kW (soma dos sistemas ligados)",
        f"  Saldo ............. {r.balanco.saldo_kw:+.1f} kW",
    ]
    linhas.extend(_linhas_decisao(r.decisao, r.balanco))
    linhas += [
        "",
        "3. MODELO DE PREVISÃO (regressão linear sobre o histórico)",
        _linha_modelo("Eólica", "vento", r.modelo_eolico),
        _linha_modelo("Solar ", "irradiância", r.modelo_solar),
        "",
        f"4. PRÓXIMA JANELA ({colonia['janela_previsao_h']} h)",
        f"  Clima previsto .... vento {clima['vento_ms']} m/s, "
        f"irradiância {clima['irradiancia_wm2']} W/m²",
        f"  Geração prevista .. {geracao_prevista:.1f} kW "
        f"(solar {r.previsao_solar_kw:.1f} + eólica {r.previsao_eolica_kw:.1f})",
        f"  Consumo ........... {r.decisao.consumo_apos_kw:.1f} kW",
        f"  Saldo previsto .... {r.balanco_previsto.saldo_kw:+.1f} kW",
        f"  Reserva projetada . {r.reserva_prevista_pct:.1f} %",
    ]
    linhas.extend(_linhas_decisao(r.decisao_prevista, r.balanco_previsto))
    linhas += [
        f"  Tendência ......... {r.tendencia}",
        "",
        "=" * LARGURA,
        f"DECISÃO: {r.decisao.acao}",
    ]
    if r.aviso_preventivo:
        linhas.extend(_quebrar(r.aviso_preventivo, " " * 12))
    linhas.append("=" * LARGURA)
    return "\n".join(linhas)


def executar(cenario: str = "nominal",
             caminho: str | Path = dados.CAMINHO_PADRAO) -> str:
    """Carrega os dados, avalia o cenário e devolve o relatório."""
    colonia = dados.carregar_colonia(caminho)
    return formatar_relatorio(colonia, avaliar(colonia, cenario))


if __name__ == "__main__":
    import sys

    escolhido = sys.argv[1] if len(sys.argv) > 1 else "nominal"
    try:
        print(executar(escolhido))
    except KeyError as erro:
        # Cenário inexistente é erro de uso: mensagem legível e código 1.
        print(f"Erro: {erro.args[0]}", file=sys.stderr)
        sys.exit(1)
