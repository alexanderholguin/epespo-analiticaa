import unicodedata

import pandas as pd


_COLUMNAS_AREA = [
    "area_operativa",
    "registros",
    "graduados",
    "graduados_pct",
    "no_culmino",
    "no_culmino_pct",
    "otros",
    "otros_pct",
]
_COLUMNAS_CURSO = [
    "curso",
    "registros",
    "graduados",
    "no_culmino",
    "tasa_no_culminacion",
]


def _normalizar_condicion(valor: object) -> str:
    texto = unicodedata.normalize("NFKD", str(valor))
    return "".join(
        caracter
        for caracter in texto
        if not unicodedata.combining(caracter)
    ).strip().casefold()


def _resumir_por_grupo(
    datos: pd.DataFrame,
    columna: str,
) -> pd.DataFrame:
    resumen = (
        datos.groupby(columna, dropna=False)
        .agg(
            registros=(columna, "size"),
            graduados=("es_graduado", "sum"),
            no_culmino=(
                "estado_resumen",
                lambda estados: estados.eq("No culminó").sum(),
            ),
            otros=(
                "estado_resumen",
                lambda estados: estados.eq("Otros / sin estado").sum(),
            ),
        )
        .reset_index()
    )
    resumen["otros"] = (
        resumen["registros"] - resumen["graduados"] - resumen["no_culmino"]
    )
    resumen["graduados_pct"] = (
        resumen["graduados"] / resumen["registros"] * 100
    )
    resumen["no_culmino_pct"] = (
        resumen["no_culmino"] / resumen["registros"] * 100
    )
    resumen["otros_pct"] = resumen["otros"] / resumen["registros"] * 100
    return resumen


def resumir_areas_especialidades(
    df: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    if df.empty:
        return (
            pd.DataFrame(columns=_COLUMNAS_AREA),
            pd.DataFrame(columns=_COLUMNAS_CURSO),
        )

    requeridas = {"area_operativa", "curso", "es_graduado", "condicion"}
    faltantes = requeridas - set(df.columns)
    if faltantes:
        raise ValueError(
            "Faltan columnas para resumir áreas y especialidades: "
            + ", ".join(sorted(faltantes))
        )

    datos = df.copy()
    datos["es_graduado"] = datos["es_graduado"].fillna(False).astype(bool)
    condicion = datos["condicion"].fillna("").map(_normalizar_condicion)
    datos["estado_resumen"] = "Otros / sin estado"
    datos.loc[condicion.eq("no culmino"), "estado_resumen"] = "No culminó"
    datos.loc[datos["es_graduado"], "estado_resumen"] = "Graduado"

    resumen_area = _resumir_por_grupo(datos, "area_operativa")
    resumen_area = resumen_area[_COLUMNAS_AREA]

    resumen_curso = _resumir_por_grupo(datos, "curso")
    resumen_curso["tasa_no_culminacion"] = (
        resumen_curso["no_culmino"] / resumen_curso["registros"] * 100
    )
    resumen_curso = resumen_curso[_COLUMNAS_CURSO]
    return resumen_area, resumen_curso
