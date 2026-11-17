from calendar import monthrange
from datetime import date

import pandas as pd

from cursos import normalizar_curso


_ANIO_DESDE = 2021

_RUTAS_ASCENSO = {
    normalizar_curso("Marinero Pescador"): (
        "Cubierta",
        normalizar_curso("Marinero De Primera De Puente De B/P"),
        2,
    ),
    normalizar_curso("Marinero De Primera De Puente De B/P"): (
        "Cubierta",
        normalizar_curso("Patrón De Pesca Costanero"),
        2,
    ),
    normalizar_curso("Patrón De Pesca Costanero"): (
        "Cubierta",
        normalizar_curso("Patrón / Capitán De Pesca De Altura"),
        3,
    ),
    normalizar_curso("Patrón De Altura"): ("Cubierta", "Capitán", 3),
    normalizar_curso("Marinero De Máquinas"): (
        "Máquinas",
        normalizar_curso("Marinero De Primera De Máquinas De B/P"),
        2,
    ),
    normalizar_curso("Marinero De Primera De Máquinas De B/P"): (
        "Máquinas",
        normalizar_curso("Primer Oficial De Máquinas"),
        2,
    ),
    normalizar_curso("Primer Oficial De Máquinas"): (
        "Máquinas",
        normalizar_curso("Jefe De Máquinas"),
        3,
    ),
}

_COLUMNAS_CANDIDATOS = [
    "cedula_limpia",
    "nombres",
    "provincia",
    "area",
    "curso_origen",
    "curso_objetivo",
    "fecha_referencia",
    "fuente_fecha",
    "tiempo_espera",
    "umbral_anios",
]


def _sumar_anios(fecha: pd.Timestamp, anios: int) -> pd.Timestamp:
    return fecha + pd.DateOffset(years=anios)


def _sumar_meses(fecha: date, meses: int) -> date:
    mes_indice = fecha.month - 1 + meses
    anio = fecha.year + mes_indice // 12
    mes = mes_indice % 12 + 1
    dia = min(fecha.day, monthrange(anio, mes)[1])
    return date(anio, mes, dia)


def _formatear_tiempo(fecha_inicio: date, fecha_fin: date) -> str:
    anios = fecha_fin.year - fecha_inicio.year
    aniversario = _sumar_meses(fecha_inicio, anios * 12)
    if aniversario > fecha_fin:
        anios -= 1
        aniversario = _sumar_meses(fecha_inicio, anios * 12)

    meses = (
        (fecha_fin.year - aniversario.year) * 12
        + fecha_fin.month
        - aniversario.month
    )
    mes_aniversario = _sumar_meses(aniversario, meses)
    if mes_aniversario > fecha_fin:
        meses -= 1
        mes_aniversario = _sumar_meses(aniversario, meses)
    dias = (fecha_fin - mes_aniversario).days
    return f"{anios} a, {meses} m, {dias} d"


def _fechas_mes(
    anios: pd.Series,
    meses: pd.Series,
) -> pd.Series:
    resultado = pd.Series(pd.NaT, index=anios.index, dtype="datetime64[ns]")
    anio_num = pd.to_numeric(anios, errors="coerce")
    mes_num = pd.to_numeric(meses, errors="coerce")
    validos = (
        anio_num.notna()
        & anio_num.between(1900, 2200)
        & mes_num.notna()
        & mes_num.between(1, 12)
    )
    if validos.any():
        fechas_inicio = pd.to_datetime(
            anio_num.loc[validos].astype(int).astype(str)
            + "-"
            + mes_num.loc[validos].astype(int).astype(str).str.zfill(2)
            + "-01",
            errors="coerce",
        )
        resultado.loc[validos] = fechas_inicio + pd.offsets.MonthEnd(0)
    return resultado


def calcular_candidatos_ascenso(
    df: pd.DataFrame,
    fecha_corte: date | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, int]]:
    columnas_demanda = ["area", "curso_objetivo", "candidatos"]
    totales = {
        "personas_evaluadas": 0,
        "personas_con_ruta": 0,
        "personas_sin_ruta": 0,
        "sin_fecha": 0,
        "candidatos_potenciales": 0,
    }
    if df.empty:
        return (
            pd.DataFrame(columns=_COLUMNAS_CANDIDATOS),
            pd.DataFrame(columns=columnas_demanda),
            totales,
        )

    requeridas = {
        "cedula_limpia",
        "estado_dni",
        "nombres",
        "provincia",
        "curso",
        "anio",
        "mes",
    }
    if not requeridas.issubset(df.columns):
        raise ValueError(
            "Faltan columnas requeridas para planificar ascensos: "
            + ", ".join(sorted(requeridas - set(df.columns)))
        )
    if "es_graduado" not in df and "condicion" not in df:
        raise ValueError(
            "Se requiere es_graduado o condicion para filtrar cursos "
            "completados."
        )

    datos = df[
        pd.to_numeric(df["anio"], errors="coerce").ge(_ANIO_DESDE)
        & (df["estado_dni"] == "Con DNI")
        & df["cedula_limpia"].notna()
        & df["cedula_limpia"].astype(str).str.strip().ne("")
    ].copy()
    if datos.empty:
        return (
            pd.DataFrame(columns=_COLUMNAS_CANDIDATOS),
            pd.DataFrame(columns=columnas_demanda),
            totales,
        )
    if "es_graduado" in datos:
        graduados = datos["es_graduado"].fillna(False).astype(bool)
    else:
        graduados = (
            datos["condicion"]
            .fillna("")
            .astype(str)
            .str.strip()
            .str.casefold()
            .eq("graduado")
        )
    datos = datos.loc[graduados].copy()
    if datos.empty:
        return (
            pd.DataFrame(columns=_COLUMNAS_CANDIDATOS),
            pd.DataFrame(columns=columnas_demanda),
            totales,
        )

    fecha_fin = pd.to_datetime(
        datos.get("fec_fin", pd.Series(index=datos.index, dtype=object)),
        errors="coerce",
    )
    fecha_registro = pd.to_datetime(
        datos.get("fecha", pd.Series(index=datos.index, dtype=object)),
        errors="coerce",
    )
    fecha_mes = _fechas_mes(datos["anio"], datos["mes"])
    datos["fecha_referencia"] = (
        fecha_fin.combine_first(fecha_registro).combine_first(fecha_mes)
    )
    datos["fuente_fecha"] = "Año/mes (estimado)"
    datos.loc[fecha_registro.notna(), "fuente_fecha"] = "Fecha del registro"
    datos.loc[fecha_fin.notna(), "fuente_fecha"] = "Fin del curso"
    datos.loc[datos["fecha_referencia"].isna(), "fuente_fecha"] = "Sin fecha"
    datos["curso_normalizado"] = datos["curso"].map(normalizar_curso)

    ultimo_curso = (
        datos.sort_values(
            ["cedula_limpia", "fecha_referencia"],
            kind="stable",
            na_position="last",
        )
        .drop_duplicates("cedula_limpia", keep="last")
        .copy()
    )
    totales["personas_evaluadas"] = int(
        ultimo_curso["cedula_limpia"].nunique()
    )
    rutas = ultimo_curso["curso_normalizado"].map(_RUTAS_ASCENSO)
    tiene_ruta = rutas.notna()
    totales["personas_con_ruta"] = int(tiene_ruta.sum())
    totales["personas_sin_ruta"] = int((~tiene_ruta).sum())

    evaluables = ultimo_curso.loc[tiene_ruta].copy()
    rutas_evaluables = rutas.loc[tiene_ruta]
    evaluables["curso_origen"] = evaluables["curso_normalizado"]
    evaluables["area"] = rutas_evaluables.map(lambda ruta: ruta[0])
    evaluables["curso_objetivo"] = rutas_evaluables.map(lambda ruta: ruta[1])
    evaluables["umbral_anios"] = rutas_evaluables.map(lambda ruta: ruta[2])
    sin_fecha = evaluables["fecha_referencia"].isna()
    totales["sin_fecha"] = int(sin_fecha.sum())

    corte = fecha_corte or pd.Timestamp.now(
        tz="America/Guayaquil"
    ).date()
    evaluables = evaluables.loc[~sin_fecha].copy()
    evaluables["fecha_objetivo"] = evaluables.apply(
        lambda fila: _sumar_anios(
            pd.Timestamp(fila["fecha_referencia"]),
            int(fila["umbral_anios"]),
        ),
        axis=1,
    )
    listos = evaluables[
        evaluables["fecha_objetivo"].dt.date <= corte
    ].copy()
    listos["tiempo_espera"] = listos["fecha_referencia"].map(
        lambda inicio: _formatear_tiempo(inicio.date(), corte)
    )
    candidatos = listos[_COLUMNAS_CANDIDATOS].reset_index(drop=True)
    totales["candidatos_potenciales"] = len(candidatos)

    rutas_objetivo = list(
        dict.fromkeys((ruta[0], ruta[1]) for ruta in _RUTAS_ASCENSO.values())
    )
    indice_objetivos = pd.MultiIndex.from_tuples(
        rutas_objetivo,
        names=["area", "curso_objetivo"],
    )
    demanda = (
        candidatos.groupby(["area", "curso_objetivo"])
        .size()
        .reindex(indice_objetivos, fill_value=0)
        .rename("candidatos")
        .reset_index()
    )
    return candidatos, demanda, totales
