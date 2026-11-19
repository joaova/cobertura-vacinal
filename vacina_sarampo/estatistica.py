"""Estatística descritiva usada na página de relação cobertura × incidência."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy import stats


@dataclass
class ResultadoSpearman:
    n: int
    rho: float | None
    p_valor: float | None
    ic95: tuple[float, float] | None  # intervalo aproximado (transformação de Fisher)

    @property
    def interpretavel(self) -> bool:
        return self.n >= 10 and self.rho is not None


def spearman(x: pd.Series, y: pd.Series) -> ResultadoSpearman:
    """Correlação de postos de Spearman com p-valor e IC95% aproximado (Fisher)."""
    d = pd.concat([x, y], axis=1).dropna()
    n = len(d)
    if n < 3 or d.iloc[:, 0].nunique() < 2 or d.iloc[:, 1].nunique() < 2:
        return ResultadoSpearman(n, None, None, None)
    rho, p = stats.spearmanr(d.iloc[:, 0], d.iloc[:, 1])
    ic = None
    if n > 3 and abs(rho) < 1:
        z, se = np.arctanh(rho), 1.06 / np.sqrt(n - 3)  # 1,06 = correção para Spearman
        ic = (float(np.tanh(z - 1.96 * se)), float(np.tanh(z + 1.96 * se)))
    return ResultadoSpearman(n, float(rho), float(p), ic)


def descreve_forca(rho: float | None) -> str:
    if rho is None:
        return "indeterminada"
    a = abs(rho)
    forca = "desprezível" if a < 0.1 else "fraca" if a < 0.3 else "moderada" if a < 0.5 else "forte"
    sentido = "negativa" if rho < 0 else "positiva"
    return f"{forca} {sentido}" if a >= 0.1 else forca
