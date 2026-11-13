"""The metrics (R-77): pure functions of (answer, prediction) pairs. `None` means the target can't be scored."""
from __future__ import annotations


def auc(pairs: list[tuple[float, float]]) -> float | None:
    """Rank-based AUC, ties at 0.5. A one-class target is unscorable, never 0."""
    pos = [p for g, p in pairs if g == 1]
    neg = [p for g, p in pairs if g == 0]
    if not pos or not neg:
        return None
    wins = sum((a > b) + 0.5 * (a == b) for a in pos for b in neg)
    return round(wins / (len(pos) * len(neg)), 4)


def qwk(pairs: list[tuple[float, float]]) -> float | None:
    """Quadratic weighted kappa over integer classes."""
    g = [int(a) for a, _ in pairs]
    p = [int(round(b)) for _, b in pairs]
    lo, hi = min(g + p), max(g + p)
    k = hi - lo + 1
    if k < 2:
        return None
    n = len(g)
    obs = [[0] * k for _ in range(k)]
    for a, b in zip(g, p):
        obs[a - lo][b - lo] += 1
    gh = [g.count(c + lo) for c in range(k)]
    ph = [p.count(c + lo) for c in range(k)]
    num = den = 0.0
    for i in range(k):
        for j in range(k):
            w = ((i - j) ** 2) / ((k - 1) ** 2)
            num += w * obs[i][j]
            den += w * gh[i] * ph[j] / n
    return None if den == 0 else round(1 - num / den, 4)


def mae(pairs: list[tuple[float, float]]) -> float | None:
    if not pairs:
        return None
    return round(sum(abs(a - b) for a, b in pairs) / len(pairs), 4)
