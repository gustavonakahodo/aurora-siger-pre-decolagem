"""Análise do uso de energia: geração × consumo × reserva."""

from __future__ import annotations

from dataclasses import dataclass

RESERVA_CHEIA_PCT = 95.0

MSG_DEFICIT = "ALERTA: consumo maior que geração"
MSG_EXCEDENTE = "SUGESTÃO: armazenar energia excedente"
MSG_RESERVA_CHEIA = ("SUGESTÃO: reserva cheia — direcionar o excedente a "
                     "cargas não essenciais")
MSG_EQUILIBRIO = "OK: geração e consumo em equilíbrio"


@dataclass(frozen=True)
class Balanco:
    """Resultado da comparação entre geração e consumo."""

    saldo_kw: float
    situacao: str            # "DEFICIT", "EXCEDENTE" ou "EQUILIBRIO"
    mensagem: str
    autonomia_h: float | None  # horas de reserva; só existe em déficit


def analisar_balanco(geracao_kw: float, consumo_kw: float,
                     reserva_pct: float | None = None,
                     capacidade_kwh: float | None = None) -> Balanco:
    """Compara geração e consumo e devolve uma ação simples.

    Com reserva e capacidade informadas, calcula também por quantas horas a
    reserva cobre o déficit.
    """
    saldo = geracao_kw - consumo_kw
    if saldo < 0:
        autonomia = None
        if reserva_pct is not None and capacidade_kwh is not None:
            autonomia = capacidade_kwh * reserva_pct / 100.0 / -saldo
        return Balanco(saldo, "DEFICIT", MSG_DEFICIT, autonomia)
    if saldo > 0:
        cheia = reserva_pct is not None and reserva_pct >= RESERVA_CHEIA_PCT
        mensagem = MSG_RESERVA_CHEIA if cheia else MSG_EXCEDENTE
        return Balanco(saldo, "EXCEDENTE", mensagem, None)
    return Balanco(0.0, "EQUILIBRIO", MSG_EQUILIBRIO, None)


def projetar_reserva(reserva_pct: float, saldo_kw: float, horas: float,
                     capacidade_kwh: float) -> float:
    """Reserva esperada depois de `horas` com o saldo dado, entre 0 e 100 %."""
    variacao_pct = saldo_kw * horas / capacidade_kwh * 100.0
    return min(100.0, max(0.0, reserva_pct + variacao_pct))
