from collections.abc import Callable

import numpy as np
import pandas as pd


def mapear_valores_unicos(
    serie: pd.Series,
    transformar: Callable[[object], object],
) -> pd.Series:
    codigos, valores_unicos = pd.factorize(serie, sort=False)
    salida = np.empty(len(serie), dtype=object)
    validos = codigos >= 0
    transformados = np.asarray(
        [transformar(valor) for valor in valores_unicos],
        dtype=object,
    )
    salida[validos] = transformados[codigos[validos]]
    if (~validos).any():
        salida[~validos] = transformar(pd.NA)
    return pd.Series(salida, index=serie.index, name=serie.name)
