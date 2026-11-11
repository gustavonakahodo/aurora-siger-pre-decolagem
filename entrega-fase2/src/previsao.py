"""Previsão por regressão linear simples (mínimos quadrados).

Ajusta a reta y = a·x + b que melhor acompanha um histórico de medições e a
usa para estimar valores ainda não observados. Só aritmética básica.
"""

from __future__ import annotations


def _media(valores: list[float]) -> float:
    return sum(valores) / len(valores)


def ajustar_reta(xs: list[float], ys: list[float]) -> tuple[float, float]:
    """Devolve (a, b) da reta y = a·x + b que minimiza o erro quadrático."""
    if len(xs) != len(ys):
        raise ValueError("As listas de x e y precisam ter o mesmo tamanho.")
    if len(xs) < 2:
        raise ValueError("São necessárias pelo menos duas medições.")
    media_x, media_y = _media(xs), _media(ys)
    variacao_x = sum((x - media_x) ** 2 for x in xs)
    if variacao_x == 0:
        raise ValueError("Os valores de x são todos iguais: não há reta.")
    covariacao = sum((x - media_x) * (y - media_y) for x, y in zip(xs, ys))
    a = covariacao / variacao_x
    b = media_y - a * media_x
    return a, b


def prever(a: float, b: float, x: float) -> float:
    """Estima y para um x novo. Geração de energia nunca é negativa."""
    return max(0.0, a * x + b)


def r2(xs: list[float], ys: list[float], a: float, b: float) -> float:
    """Fração da variação de y explicada pela reta (1.0 = ajuste perfeito)."""
    media_y = _media(ys)
    total = sum((y - media_y) ** 2 for y in ys)
    if total == 0:
        return 1.0
    residuo = sum((y - (a * x + b)) ** 2 for x, y in zip(xs, ys))
    return 1.0 - residuo / total
