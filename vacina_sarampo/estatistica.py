"""Estatística descritiva usada na página de relação cobertura × incidência."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy import stats


def resumo_por_meta(dados: pd.DataFrame, meta: float) -> pd.DataFrame:
    """Resume um registro por localidade em um único ano, ponderando pela população.

    Registros sem cobertura, casos ou população válida não entram na comparação.
    Grupos sem localidades têm incidência ausente, em vez de zero.
    """
    validos = dados.dropna(subset=["cobertura", "casos", "populacao_ibge"])
    validos = validos[validos.populacao_ibge > 0]
    grupos = [f"Abaixo de {meta:g}%", f"{meta:g}% ou mais"]
    situacao = pd.Categorical(
        np.where(validos.cobertura < meta, grupos[0], grupos[1]),
        categories=grupos, ordered=True,
    )
    resumo = (validos.assign(situacao=situacao).groupby("situacao", observed=True)
              .agg(localidades=("cod_ibge", "size"), populacao=("populacao_ibge", "sum"),
                   casos=("casos", "sum"), localidades_com_casos=("casos", lambda s: int((s > 0).sum())))
              .reindex(grupos, fill_value=0).reset_index())
    resumo["incidencia_100k"] = 100_000 * resumo.casos / resumo.populacao.where(resumo.populacao > 0)
    return resumo


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
