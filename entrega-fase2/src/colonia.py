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
    x_min: float
    x_max: float


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
    extrapolacoes: tuple[str, ...]
    reserva_prevista_pct: float
    balanco_previsto: energia.Balanco
    decisao_prevista: decisoes.Decisao
    tendencia: str
    aviso_preventivo: str | None


def treinar(xs: list[float], ys: list[float]) -> Modelo:
    """Ajusta a reta a um par de listas do histórico."""
    a, b = previsao.ajustar_reta(xs, ys)
    return Modelo(a, b, previsao.r2(xs, ys, a, b), len(xs), min(xs), max(xs))


def estimar(modelo: Modelo, x: float) -> float:
    """Geração prevista, na resolução das medições do histórico (0,1 kW)."""
    return round(previsao.prever(modelo.a, modelo.b, x), 1)


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
    vento, irradiancia = clima["vento_ms"], clima["irradiancia_wm2"]
    prev_eolica = estimar(modelo_eolico, vento)
    prev_solar = estimar(modelo_solar, irradiancia)
    geracao_prevista = prev_solar + prev_eolica

    extrapolacoes = []
    if previsao.fora_da_faixa(historico["vento_ms"], vento):
        extrapolacoes.append(
            f"vento {vento} m/s fora do histórico "
            f"({modelo_eolico.x_min} a {modelo_eolico.x_max} m/s)")
    if previsao.fora_da_faixa(historico["irradiancia_wm2"], irradiancia):
        extrapolacoes.append(
            f"irradiância {irradiancia} W/m² fora do histórico "
            f"({modelo_solar.x_min} a {modelo_solar.x_max} W/m²)")

    # A projeção parte do consumo que sobra depois da decisão de agora.
    restantes = [c for c in consumidores if c["rotulo"] not in decisao.desligar]
    consumo_futuro = decisao.consumo_apos_kw
    reserva_prevista = energia.projetar_reserva(
        reserva, geracao_prevista - consumo_futuro, janela_h, capacidade)
    balanco_previsto = energia.analisar_balanco(
        geracao_prevista, consumo_futuro, reserva_prevista, capacidade)
    decisao_prevista = decisoes.decidir(
        reserva_prevista, consumo_futuro, geracao_prevista, restantes)
    tendencia = decisoes.comparar(decisao, decisao_prevista,
                                  reserva, reserva_prevista)

    # Se os cortes previstos forem feitos já, quanto de reserva se preserva?
    reserva_antecipando = energia.projetar_reserva(
        reserva, geracao_prevista - decisao_prevista.consumo_apos_kw,
        janela_h, capacidade)

    return Resultado(
        cenario=nome_cenario, reserva_pct=reserva, consumo_kw=consumo,
        geracao_solar_kw=solar, geracao_eolica_kw=eolica, balanco=balanco,
        decisao=decisao, modelo_eolico=modelo_eolico, modelo_solar=modelo_solar,
        previsao_solar_kw=prev_solar, previsao_eolica_kw=prev_eolica,
        extrapolacoes=tuple(extrapolacoes),
        reserva_prevista_pct=reserva_prevista, balanco_previsto=balanco_previsto,
        decisao_prevista=decisao_prevista, tendencia=tendencia,
        aviso_preventivo=aviso_preventivo(
            decisao_prevista, tendencia, janela_h, reserva,
            reserva_prevista, reserva_antecipando),
    )


def aviso_preventivo(prevista: decisoes.Decisao, tendencia: str, janela_h: float,
                     reserva_pct: float, reserva_prevista_pct: float,
                     reserva_antecipando_pct: float) -> str | None:
    """Se a previsão é pior que o presente, recomenda agir antes da hora."""
    if tendencia != "PIORA":
        return None
    aviso = (f"PREVENTIVO: em {janela_h} h a reserva vai de {reserva_pct:.1f} % "
             f"a {reserva_prevista_pct:.1f} % (situação {prevista.nivel})")
    if prevista.desligar:
        aviso += (f". Desligando já {', '.join(prevista.desligar)}, a "
                  f"reserva fica em {reserva_antecipando_pct:.1f} %")
    return aviso + "."


def _quebrar(texto: str, recuo: str) -> list[str]:
    """Quebra um texto longo na largura do relatório, alinhando a sobra."""
    return textwrap.wrap(texto, LARGURA, subsequent_indent=recuo)


def _linhas_arvore(no: dict, ligados: list[str], leituras: dict[str, str],
                   caminho: str = "", nivel: int = 0) -> list[str]:
    """Desenha a hierarquia com recuo, um nível por degrau."""
    recuo = "  " * (nivel + 1)
    if "subsistemas" in no:
        linhas = [f"{recuo}{no['rotulo']}"]
        for nome, filho in no["subsistemas"].items():
            sub = f"{caminho}/{nome}" if caminho else nome
            linhas.extend(_linhas_arvore(filho, ligados, leituras, sub, nivel + 1))
        return linhas
    rotulo = f"{recuo}{no['rotulo']}"
    if "consumo_kw" in no:
        estado = "LIGADO" if caminho in ligados else "desligado"
        return [f"{rotulo:<32}{no['consumo_kw']:>6.1f} kW   "
                f"prioridade {no['prioridade']}   {estado}"]
    return [f"{rotulo:<32}{leituras.get(caminho, '')}".rstrip()]


def _linha_modelo(nome: str, variavel: str, modelo: Modelo) -> str:
    sinal = "+" if modelo.b >= 0 else "-"
    return (f"  {nome}: energia = {modelo.a:.4f} × {variavel} {sinal} "
            f"{abs(modelo.b):.2f}   (R² = {modelo.r2:.4f}, "
            f"{modelo.medicoes} medições)")


def _linhas_decisao(decisao: decisoes.Decisao, balanco: energia.Balanco) -> list[str]:
    analise = balanco.mensagem
    if balanco.autonomia_h is not None:
        analise += f" (reserva cobre {balanco.autonomia_h:.1f} h)"
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
    capacidade = dados.buscar_subsistema(
        colonia["sistemas"], "energia/armazenamento/baterias")["capacidade_kwh"]
    leituras = {
        "energia/geracao/solar": f"{r.geracao_solar_kw:>6.1f} kW   gerando",
        "energia/geracao/eolico": f"{r.geracao_eolica_kw:>6.1f} kW   gerando",
        "energia/armazenamento/baterias":
            f"{capacidade:>6.0f} kWh  reserva em {r.reserva_pct:.1f} %",
    }
    linhas = [
        "=" * LARGURA,
        f"COLÔNIA {colonia['colonia'].upper()} — SISTEMA INTEGRADO DE ENERGIA",
        *_quebrar(f"Cenário: {r.cenario} — {cenario['descricao']}", " " * 9),
        "=" * LARGURA,
        "",
        "1. SISTEMAS DA COLÔNIA",
    ]
    linhas.extend(_linhas_arvore(colonia["sistemas"], cenario["ligados"], leituras))
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
    ]
    for extrapolacao in r.extrapolacoes:
        linhas.extend(_quebrar(
            f"  CUIDADO ........... extrapolação: {extrapolacao}",
            " " * 22))
    linhas += [
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

    # O relatório usa símbolos (→, ×, ²) que a codificação padrão do terminal
    # do Windows não tem; sem isto o print falharia ao redirecionar a saída.
    for fluxo in (sys.stdout, sys.stderr):
        fluxo.reconfigure(encoding="utf-8")

    escolhido = sys.argv[1] if len(sys.argv) > 1 else "nominal"
    try:
        print(executar(escolhido))
    except (KeyError, ValueError) as erro:
        # Cenário inexistente ou com leitura inválida é erro de uso:
        # mensagem legível e código 1, sem traceback.
        print(f"Erro: {erro.args[0]}", file=sys.stderr)
        sys.exit(1)
