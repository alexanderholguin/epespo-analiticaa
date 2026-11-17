import numpy as np
import pandas as pd


def calcular_tasas_graduacion_provinciales(
    df: pd.DataFrame,
) -> pd.DataFrame:
    columnas = ["provincia", "registros", "graduados", "tasa_graduacion"]
    if df.empty:
        return pd.DataFrame(columns=columnas)

    resumen = (
        df.groupby("provincia", dropna=False)
        .agg(
            registros=("provincia", "size"),
            graduados=("es_graduado", "sum"),
        )
        .reset_index()
    )
    resumen["tasa_graduacion"] = (
        resumen["graduados"] / resumen["registros"] * 100
    )
    return resumen.sort_values(
        "tasa_graduacion",
        ascending=False,
    ).reset_index(drop=True)


def comparar_registros_provinciales(
    df: pd.DataFrame,
    anio_base: int,
    anio_comparacion: int,
) -> pd.DataFrame:
    columnas = [
        "provincia",
        "registros_base",
        "registros_comparacion",
        "cambio",
        "variacion_porcentual",
        "tendencia",
    ]
    if anio_base == anio_comparacion:
        raise ValueError("Selecciona dos años distintos para compararlos.")

    datos = df[df["anio"].isin([anio_base, anio_comparacion])]
    if datos.empty:
        return pd.DataFrame(columns=columnas)

    conteos = (
        datos.groupby(["provincia", "anio"], dropna=False)
        .size()
        .unstack(fill_value=0)
    )
    for anio in (anio_base, anio_comparacion):
        if anio not in conteos.columns:
            conteos[anio] = 0

    base = conteos[anio_base].astype(int)
    comparacion = conteos[anio_comparacion].astype(int)
    cambio = comparacion - base
    variacion = (cambio / base.where(base.ne(0)) * 100).round(1)
    tendencia = np.select(
        [
            base.eq(0) & comparacion.gt(0),
            cambio.gt(0),
            cambio.lt(0),
        ],
        ["Nuevo", "Aumentó", "Disminuyó"],
        default="Sin cambio",
    )

    return (
        pd.DataFrame(
            {
                "provincia": conteos.index,
                "registros_base": base.to_numpy(),
                "registros_comparacion": comparacion.to_numpy(),
                "cambio": cambio.to_numpy(),
                "variacion_porcentual": variacion.to_numpy(),
                "tendencia": tendencia,
            }
        )
        .sort_values("cambio", ascending=False)
        .reset_index(drop=True)
    )
