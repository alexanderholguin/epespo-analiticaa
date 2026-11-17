from calendar import monthrange
from datetime import date
import unicodedata

import pandas as pd


URL_CALENDARIO_OFICIAL = (
    "https://www.produccion.gob.ec/calendario-de-vedas-en-ecuador/"
)
URL_PDF_CALENDARIO_2025 = (
    "https://www.produccion.gob.ec/wp-content/uploads/2025/08/"
    "Calendario-Vedas-Ecuador_2025.pdf"
)


ANIO_CALENDARIO_OFICIAL = 2025


def obtener_periodos_veda_atun(anios=None) -> pd.DataFrame:
    anios = [ANIO_CALENDARIO_OFICIAL] if anios is None else anios
    filas = []
    for anio in sorted(
        {
            int(valor)
            for valor in anios
            if 2001 <= int(valor) <= ANIO_CALENDARIO_OFICIAL
        }
    ):
        referencia = (
            "Oficial (2025)"
            if anio == ANIO_CALENDARIO_OFICIAL
            else "Estimación histórica"
        )
        filas.extend(
            [
                {
                    "anio_veda": anio,
                    "periodo": "Ventana 1",
                    "inicio": date(anio, 7, 29),
                    "fin": date(anio, 10, 8),
                    "referencia": referencia,
                },
                {
                    "anio_veda": anio,
                    "periodo": "Ventana 2",
                    "inicio": date(anio, 11, 9),
                    "fin": date(anio + 1, 1, 19),
                    "referencia": referencia,
                },
            ]
        )
    periodos = pd.DataFrame(filas)
    if periodos.empty:
        return periodos.assign(dias=pd.Series(dtype="int64"))
    periodos["dias"] = (
        pd.to_datetime(periodos["fin"]) - pd.to_datetime(periodos["inicio"])
    ).dt.days + 1
    return periodos


def _texto_identidad(valor) -> str:
    if pd.isna(valor):
        return ""
    texto = unicodedata.normalize("NFKD", str(valor).casefold())
    texto = "".join(
        caracter
        for caracter in texto
        if not unicodedata.combining(caracter)
    )
    return " ".join(texto.split())


def _clave_persona(fila):
    dni = fila.get("cedula_limpia", fila.get("cedula"))
    if not pd.isna(dni):
        digitos = "".join(
            caracter for caracter in str(dni) if caracter.isdigit()
        )
        if digitos and set(digitos) != {"0"}:
            return ("dni", digitos)

    nombres = _texto_identidad(fila.get("nombres"))
    matricula = _texto_identidad(fila.get("matricula"))
    if nombres and matricula:
        return ("nombre_matricula", nombres, matricula)
    return None


def _serie_fecha(df: pd.DataFrame, columna: str) -> pd.Series:
    if columna not in df:
        return pd.Series(pd.NaT, index=df.index, dtype="datetime64[ns]")
    return pd.to_datetime(df[columna], errors="coerce")


def _meses_completos_en_periodo(
    inicio: date,
    fin: date,
) -> set[tuple[int, int]]:
    meses = set()
    anio, mes = inicio.year, inicio.month
    while (anio, mes) <= (fin.year, fin.month):
        inicio_mes = date(anio, mes, 1)
        fin_mes = date(anio, mes, monthrange(anio, mes)[1])
        if inicio <= inicio_mes and fin_mes <= fin:
            meses.add((anio, mes))
        if mes == 12:
            anio, mes = anio + 1, 1
        else:
            mes += 1
    return meses


def calcular_cursos_en_vedas_atun(
    df: pd.DataFrame,
) -> tuple[pd.DataFrame, dict[str, int]]:
    columnas_resumen = [
        "anio_veda",
        "periodo",
        "inicio",
        "fin",
        "dias",
        "referencia",
        "personas_unicas",
        "personas_con_fecha_exacta",
        "personas_estimadas_por_mes",
        "registros_con_fecha_exacta",
        "registros_estimados_por_mes",
        "registros_sin_identidad",
    ]
    totales = {
        "personas_unicas": 0,
        "registros": 0,
        "registros_sin_identidad": 0,
    }
    if df.empty:
        return pd.DataFrame(columns=columnas_resumen), totales

    datos = df.reset_index(drop=True).copy()
    inicio_curso = _serie_fecha(datos, "fec_ini")
    fin_curso = _serie_fecha(datos, "fec_fin")
    fecha_inicio = inicio_curso.fillna(fin_curso)
    fecha_fin = fin_curso.fillna(inicio_curso)
    tiene_fecha = fecha_inicio.notna() & fecha_fin.notna()
    rango_valido = tiene_fecha & fecha_inicio.le(fecha_fin)
    solo_mes = fecha_inicio.isna()

    anio_registro = pd.to_numeric(
        datos.get(
            "anio",
            pd.Series(pd.NA, index=datos.index, dtype="object"),
        ),
        errors="coerce",
    )
    mes_registro = pd.to_numeric(
        datos.get(
            "mes",
            pd.Series(pd.NA, index=datos.index, dtype="object"),
        ),
        errors="coerce",
    )
    anios_datos = set()
    for anio in anio_registro.dropna():
        if float(anio).is_integer():
            anio_int = int(anio)
            if 2001 <= anio_int <= ANIO_CALENDARIO_OFICIAL + 1:
                anios_datos.add(anio_int)
    for fecha in fecha_inicio[fecha_inicio.notna()]:
        anios_datos.add(fecha.year)
    for fecha in fecha_fin[fecha_fin.notna()]:
        anios_datos.add(fecha.year)

    anios_veda = {
        anio
        for anio in anios_datos
        if 2001 <= anio <= ANIO_CALENDARIO_OFICIAL
    }
    anios_veda.update(
        anio - 1
        for anio in anios_datos
        if 2002 <= anio <= ANIO_CALENDARIO_OFICIAL + 1
    )
    periodos = obtener_periodos_veda_atun(anios_veda)
    if periodos.empty:
        return pd.DataFrame(columns=columnas_resumen), totales

    claves_persona = [
        _clave_persona(fila)
        for _, fila in datos.iterrows()
    ]
    filas_resumen = []
    registros_historicos = set()
    personas_historicas = set()
    registros_sin_identidad = set()

    for periodo in periodos.itertuples(index=False):
        inicio_veda = pd.Timestamp(periodo.inicio)
        fin_veda = pd.Timestamp(periodo.fin)
        coincide_fecha = (
            rango_valido
            & fecha_inicio.le(fin_veda)
            & fecha_fin.ge(inicio_veda)
        )
        meses_completos = _meses_completos_en_periodo(
            periodo.inicio,
            periodo.fin,
        )
        coincide_mes = solo_mes & pd.Series(
            [
                not pd.isna(anio)
                and not pd.isna(mes)
                and float(anio).is_integer()
                and float(mes).is_integer()
                and (int(anio), int(mes)) in meses_completos
                for anio, mes in zip(anio_registro, mes_registro)
            ],
            index=datos.index,
        )
        coincide = coincide_fecha | coincide_mes

        claves_fecha = {
            claves_persona[indice]
            for indice in datos.index[coincide_fecha]
            if claves_persona[indice] is not None
        }
        claves_mes = {
            claves_persona[indice]
            for indice in datos.index[coincide_mes]
            if claves_persona[indice] is not None
        }
        personas_periodo = claves_fecha | claves_mes
        filas_coincidentes = set(datos.index[coincide])
        sin_identidad = {
            indice
            for indice in filas_coincidentes
            if claves_persona[indice] is None
        }
        registros_historicos.update(filas_coincidentes)
        personas_historicas.update(personas_periodo)
        registros_sin_identidad.update(sin_identidad)
        filas_resumen.append(
            {
                "anio_veda": periodo.anio_veda,
                "periodo": periodo.periodo,
                "inicio": periodo.inicio,
                "fin": periodo.fin,
                "dias": periodo.dias,
                "referencia": periodo.referencia,
                "personas_unicas": len(personas_periodo),
                "personas_con_fecha_exacta": len(claves_fecha),
                "personas_estimadas_por_mes": len(claves_mes - claves_fecha),
                "registros_con_fecha_exacta": int(coincide_fecha.sum()),
                "registros_estimados_por_mes": int(
                    (coincide_mes & ~coincide_fecha).sum()
                ),
                "registros_sin_identidad": len(sin_identidad),
            }
        )

    totales.update(
        {
            "personas_unicas": len(personas_historicas),
            "registros": len(registros_historicos),
            "registros_sin_identidad": len(registros_sin_identidad),
        }
    )
    return pd.DataFrame(filas_resumen, columns=columnas_resumen), totales
