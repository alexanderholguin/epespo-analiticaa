import re
import unicodedata

import pandas as pd


_VALORES_SIN_REGISTRO = {
    "",
    "nan",
    "none",
    "null",
    "nulo",
    "sin registro",
}

_MODALIDADES_CANONICAS = {
    "actualizacion de conocimientos": "Actualización de Conocimientos",
    "actua cono": "Actualización de Conocimientos",
    "ascenso": "Ascenso",
    "capacitacion": "Capacitación",
    "convalidacion": "Convalidación",
    "estudio libre dirigido": "Estudio Libre Dirigido",
    "evaluacion": "Evaluación",
    "formacion": "Formación",
    "formacion regular": "Formación",
    "homologacion": "Homologación",
    "homologacion as": "Homologación-As",
    "nivelacion": "Nivelación",
    "otras modalidades": "Otras Modalidades",
    "perfeccionamiento": "Perfeccionamiento",
    "presencial": "Presencial",
}


def _clave_modalidad(valor: str) -> str:
    texto = unicodedata.normalize("NFKD", valor.casefold())
    texto = "".join(
        caracter for caracter in texto if not unicodedata.combining(caracter)
    )
    return " ".join(re.sub(r"[^a-z0-9]+", " ", texto).split())


def normalizar_modalidad(valor) -> str:
    if pd.isna(valor):
        return "Sin Registro"

    original = " ".join(str(valor).split())
    clave = _clave_modalidad(original)
    if clave in _VALORES_SIN_REGISTRO:
        return "Sin Registro"
    if clave in _MODALIDADES_CANONICAS:
        return _MODALIDADES_CANONICAS[clave]
    return original.title()


def resumir_modalidades(modalidades: pd.Series) -> pd.DataFrame:
    originales = modalidades.map(
        lambda valor: (
            "(vacío)"
            if pd.isna(valor) or not str(valor).strip()
            else str(valor).strip()
        )
    )
    unificadas = modalidades.map(normalizar_modalidad)
    resumen = (
        pd.DataFrame(
            {
                "Modalidad unificada": unificadas,
                "Nombre original": originales,
            }
        )
        .groupby(
            ["Modalidad unificada", "Nombre original"],
            dropna=False,
        )
        .size()
        .rename("Registros")
        .reset_index()
    )
    variantes_por_modalidad = resumen.groupby(
        "Modalidad unificada"
    )["Nombre original"].transform("nunique")
    es_variante = resumen["Nombre original"].ne(
        resumen["Modalidad unificada"]
    )
    resumen = resumen.loc[
        variantes_por_modalidad.gt(1) | es_variante
    ]
    return resumen.sort_values(
        ["Modalidad unificada", "Nombre original"]
    ).reset_index(drop=True)
