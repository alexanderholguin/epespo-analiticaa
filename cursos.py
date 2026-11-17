import re
import unicodedata

import pandas as pd


_CURSOS_CANONICOS = {
    "ELD": "Estudio Libre Dirigido",
    "ESTUDIO LIBRE DIRIGIDO": "Estudio Libre Dirigido",
    "JEFE DE CUBIERTA DE B/P": "Jefe De Cubierta De B/P",
    "JEFE DE MAQUINA": "Jefe De Máquinas",
    "JEFE DE MAQUINAS": "Jefe De Máquinas",
    "MARINERO DE MAQUINAS": "Marinero De Máquinas",
    "MARINERO DE PRIMERA DE MAQUINAS DE B/P":
        "Marinero De Primera De Máquinas De B/P",
    "MARINERO DE PRIMERA DE PUENTE DE B/P":
        "Marinero De Primera De Puente De B/P",
    "MARINERO PESCADOR": "Marinero Pescador",
    "MARINERO PRIMERA DE MAQUINAS DE B/P":
        "Marinero De Primera De Máquinas De B/P",
    "MARINERO PRIMERA DE PUENTE DE B/P":
        "Marinero De Primera De Puente De B/P",
    "MOTORISTA DE BUQUE PESQUERO": "Motorista De Buque Pesquero",
    "OFICIAL/MAQUINISTA DE BUQUE PESQUERO":
        "Oficial / Maquinista De Buque Pesquero",
    "OPERADOR DE MAQUINAS": "Operador De Máquinas",
    "PATRON/CAPITAN DE PESCA DE ALTURA":
        "Patrón / Capitán De Pesca De Altura",
    "PATRON DE PESCA ARTESANAL": "Patrón De Pesca Artesanal",
    "PATRON DE PESCA COSTANERO": "Patrón De Pesca Costanero",
    "PESCADOR ARTESANAL": "Pescador Artesanal",
    "PRIMER OFICIAL DE MAQUINA": "Primer Oficial De Máquinas",
    "PRIMER OFICIAL DE MAQUINAS": "Primer Oficial De Máquinas",
    "TIMONEL/MARINERO DE PUENTE": "Timonel / Marinero De Puente",
}


def _clave_curso(curso: str) -> str:
    texto = unicodedata.normalize("NFKD", curso)
    texto = "".join(
        caracter for caracter in texto if not unicodedata.combining(caracter)
    )
    texto = texto.upper().replace(".", "")
    texto = re.sub(r"\s*/\s*", "/", texto)
    texto = re.sub(r"[^A-Z0-9/]+", " ", texto)
    return " ".join(texto.split())


def normalizar_curso(curso_raw) -> str:
    if pd.isna(curso_raw):
        return "Sin Especificar"

    texto = unicodedata.normalize("NFKD", str(curso_raw))
    texto = "".join(
        caracter for caracter in texto if not unicodedata.combining(caracter)
    )
    original = " ".join(texto.strip().upper().replace(".", "").split())
    original = re.sub(r"\s*/\s*", " / ", original)
    clave = _clave_curso(original)
    if clave in _CURSOS_CANONICOS:
        return _CURSOS_CANONICOS[clave]
    if "MARINERO DE MAQUINAS" in clave:
        return "Marinero De Máquinas"
    if "OPERADOR DE MAQUINAS" in clave:
        return "Operador De Máquinas"
    return original.title()


def resumir_cursos(cursos: pd.Series) -> pd.DataFrame:
    originales = cursos.map(
        lambda curso: (
            "(vacío)"
            if pd.isna(curso) or not str(curso).strip()
            else str(curso).strip()
        )
    )
    unificados = cursos.map(normalizar_curso)
    resumen = (
        pd.DataFrame(
            {
                "Curso unificado": unificados,
                "Nombre original": originales,
            }
        )
        .groupby(["Curso unificado", "Nombre original"], dropna=False)
        .size()
        .rename("Registros")
        .reset_index()
    )
    variantes_por_curso = resumen.groupby("Curso unificado")[
        "Nombre original"
    ].transform("nunique")
    es_variante = resumen["Nombre original"].ne(resumen["Curso unificado"])
    resumen = resumen.loc[variantes_por_curso.gt(1) | es_variante]
    return resumen.sort_values(
        ["Curso unificado", "Nombre original"]
    ).reset_index(drop=True)
