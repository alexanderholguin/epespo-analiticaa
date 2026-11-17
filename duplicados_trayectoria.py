import pandas as pd


_ETIQUETAS_CODIGO = {
    0: "Estudiante normal",
    1: "Recién graduado",
    2: "Duplicado",
}
_ORDEN_CLASIFICACIONES = [
    "Estudiante normal",
    "Recién graduado",
    "Duplicado",
    "Sin código / no reconocido",
]


def _clasificar_codigo_impresion(valor) -> tuple[str, str]:
    if pd.isna(valor):
        return "—", "Sin código / no reconocido"
    try:
        numero = float(valor)
    except (TypeError, ValueError):
        return "—", "Sin código / no reconocido"
    if not numero.is_integer() or int(numero) not in _ETIQUETAS_CODIGO:
        return "—", "Sin código / no reconocido"
    codigo = int(numero)
    return str(codigo), _ETIQUETAS_CODIGO[codigo]


def resumir_codigos_impresion(
    df: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    columnas_resumen = [
        "codigo",
        "clasificacion",
        "registros",
        "personas_dni",
    ]
    columnas_curso = ["curso", "codigo", "clasificacion", "registros"]
    if df.empty or "impresion" not in df:
        return (
            pd.DataFrame(columns=columnas_resumen),
            pd.DataFrame(columns=columnas_curso),
        )

    datos = df.copy()
    clasificaciones = datos["impresion"].map(_clasificar_codigo_impresion)
    datos["codigo"] = clasificaciones.map(lambda resultado: resultado[0])
    datos["clasificacion"] = clasificaciones.map(
        lambda resultado: resultado[1]
    )

    filas_resumen = []
    for codigo, clasificacion in (
        ("0", "Estudiante normal"),
        ("1", "Recién graduado"),
        ("2", "Duplicado"),
        ("—", "Sin código / no reconocido"),
    ):
        registros = datos[datos["codigo"] == codigo]
        personas_dni = (
            registros.loc[
                registros["estado_dni"] == "Con DNI",
                "cedula_limpia",
            ].nunique()
            if {"estado_dni", "cedula_limpia"}.issubset(registros.columns)
            else 0
        )
        filas_resumen.append(
            {
                "codigo": codigo,
                "clasificacion": clasificacion,
                "registros": len(registros),
                "personas_dni": personas_dni,
            }
        )

    if "curso" not in datos:
        datos["curso"] = "Sin especificar"
    por_curso = (
        datos.groupby(
            ["curso", "codigo", "clasificacion"],
            dropna=False,
        )
        .size()
        .rename("registros")
        .reset_index()
    )
    orden = {
        clasificacion: indice
        for indice, clasificacion in enumerate(_ORDEN_CLASIFICACIONES)
    }
    resumen = pd.DataFrame(filas_resumen, columns=columnas_resumen)
    por_curso["_orden"] = por_curso["clasificacion"].map(orden)
    por_curso = por_curso.sort_values(
        ["_orden", "registros"],
        ascending=[True, False],
    ).drop(columns="_orden")
    return resumen, por_curso[columnas_curso]


def resumir_trayectoria_por_jerarquia(
    df: pd.DataFrame,
) -> tuple[pd.DataFrame, dict[str, int]]:
    columnas = ["jerarquia", "un_curso", "varios_cursos"]
    totales = {
        "personas_analizadas": 0,
        "una_jerarquia_un_curso": 0,
        "una_jerarquia_varios_cursos": 0,
        "varias_jerarquias": 0,
    }
    requeridas = {
        "estado_dni",
        "cedula_limpia",
        "curso",
        "escala_nautica",
    }
    if df.empty or not requeridas.issubset(df.columns):
        return pd.DataFrame(columns=columnas), totales

    datos = df[
        (df["estado_dni"] == "Con DNI")
        & df["cedula_limpia"].notna()
    ].copy()
    datos["curso"] = datos["curso"].fillna("").astype(str).str.strip()
    datos["escala_nautica"] = (
        datos["escala_nautica"].fillna("").astype(str).str.strip()
    )
    datos = datos[
        datos["curso"].ne("")
        & datos["curso"].str.casefold().ne("sin especificar")
        & datos["escala_nautica"].ne("")
    ]
    if datos.empty:
        return pd.DataFrame(columns=columnas), totales

    personas = (
        datos.groupby("cedula_limpia")
        .agg(
            jerarquias=("escala_nautica", "nunique"),
            cursos_distintos=("curso", "nunique"),
            jerarquia_unica=("escala_nautica", "first"),
        )
    )
    solo_una_jerarquia = personas[personas["jerarquias"] == 1]
    totales = {
        "personas_analizadas": len(personas),
        "una_jerarquia_un_curso": int(
            (
                solo_una_jerarquia["cursos_distintos"] == 1
            ).sum()
        ),
        "una_jerarquia_varios_cursos": int(
            (
                solo_una_jerarquia["cursos_distintos"] > 1
            ).sum()
        ),
        "varias_jerarquias": int((personas["jerarquias"] > 1).sum()),
    }
    solo_una_jerarquia = solo_una_jerarquia.copy()
    solo_una_jerarquia["tipo_cursos"] = solo_una_jerarquia[
        "cursos_distintos"
    ].map(lambda cantidad: "un_curso" if cantidad == 1 else "varios_cursos")
    resumen = (
        solo_una_jerarquia.groupby(
            ["jerarquia_unica", "tipo_cursos"]
        )
        .size()
        .unstack(fill_value=0)
        .reindex(columns=["un_curso", "varios_cursos"], fill_value=0)
        .rename_axis("jerarquia")
        .reset_index()
    )
    return resumen, totales
