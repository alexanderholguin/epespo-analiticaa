import pandas as pd


COLUMNAS_RESUMEN_HISTORICO = [
    "periodo",
    "registros",
    "graduados",
    "brecha",
    "tasa_graduacion",
]


def resumir_evolucion(
    df: pd.DataFrame,
    columna_periodo: str,
) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=COLUMNAS_RESUMEN_HISTORICO)

    resumen = (
        df.groupby(columna_periodo, dropna=False)
        .agg(
            registros=(columna_periodo, "size"),
            graduados=("es_graduado", "sum"),
        )
        .reset_index()
        .rename(columns={columna_periodo: "periodo"})
    )
    resumen["brecha"] = resumen["registros"] - resumen["graduados"]
    resumen["tasa_graduacion"] = (
        resumen["graduados"] / resumen["registros"] * 100
    )
    return resumen


def calcular_crecimiento_interanual(
    df: pd.DataFrame,
    anio_actual: int,
    mes: int | None = None,
) -> tuple[int, int, float | None]:
    datos = df[df["anio"].isin([anio_actual - 1, anio_actual])]
    if mes is not None:
        datos = datos[datos["mes"] == mes]

    conteos = datos.groupby("anio").size()
    registros_actuales = int(conteos.get(anio_actual, 0))
    registros_anteriores = int(conteos.get(anio_actual - 1, 0))
    crecimiento = (
        (registros_actuales - registros_anteriores)
        / registros_anteriores
        * 100
        if registros_anteriores
        else None
    )
    return registros_actuales, registros_anteriores, crecimiento
