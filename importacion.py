from io import BytesIO
import os
import re
import unicodedata

import numpy as np
import pandas as pd

from db import COLUMNAS_REGISTRO_IMPORTACION


MAX_TAMANO_IMPORTACION = 10 * 1024 * 1024
MAX_FILAS_IMPORTACION = 100_000
COLUMNAS_FECHA_IMPORTACION = {"fecha", "fec_ini", "fec_fin"}
COLUMNAS_NUMERICAS_IMPORTACION = {"anio", "mes", "impresion"}
COLUMNAS_IDENTIFICACION_IMPORTACION = {"cedula", "matricula"}


def _normalizar_encabezado_importacion(encabezado):
    texto = unicodedata.normalize("NFKD", str(encabezado).strip().lower())
    texto = "".join(
        caracter for caracter in texto if not unicodedata.combining(caracter)
    )
    texto = re.sub(r"[^a-z0-9]+", "_", texto).strip("_")
    equivalencias = {
        "ano": "anio",
        "cedula_identidad": "cedula",
        "fecha_inicio": "fec_ini",
        "fecha_fin": "fec_fin",
    }
    return equivalencias.get(texto, texto)


def _texto_identificacion_importacion(valor):
    if pd.isna(valor):
        return pd.NA
    if isinstance(valor, (int, float, np.integer, np.floating)):
        if float(valor).is_integer():
            return str(int(valor))
    return str(valor).strip()


def _parsear_fecha_importacion(valor):
    if pd.isna(valor):
        return pd.NaT
    if isinstance(valor, (int, float, np.integer, np.floating)):
        return pd.to_datetime(
            valor,
            unit="D",
            origin="1899-12-30",
            errors="coerce",
        )
    return pd.to_datetime(valor, dayfirst=True, errors="coerce")


def leer_archivo_importacion(archivo):
    contenido = archivo.getvalue()
    if not contenido:
        raise ValueError("El archivo está vacío.")
    if len(contenido) > MAX_TAMANO_IMPORTACION:
        raise ValueError("El archivo supera el límite de 10 MB.")

    extension = os.path.splitext(archivo.name)[1].lower()
    if extension == ".csv":
        try:
            df = pd.read_csv(
                BytesIO(contenido),
                sep=None,
                engine="python",
                dtype="string",
                encoding="utf-8-sig",
            )
        except UnicodeDecodeError:
            df = pd.read_csv(
                BytesIO(contenido),
                sep=None,
                engine="python",
                dtype="string",
                encoding="cp1252",
            )
    elif extension == ".xlsx":
        df = pd.read_excel(BytesIO(contenido), engine="openpyxl")
    else:
        raise ValueError("Solo se admiten archivos CSV o Excel .xlsx.")

    df.columns = [
        _normalizar_encabezado_importacion(columna)
        for columna in df.columns
    ]
    if len(set(df.columns)) != len(df.columns):
        raise ValueError(
            "El archivo contiene encabezados repetidos después de "
            "normalizarlos."
        )

    columnas_requeridas = set(COLUMNAS_REGISTRO_IMPORTACION)
    columnas_recibidas = set(df.columns)
    faltantes = columnas_requeridas - columnas_recibidas
    adicionales = columnas_recibidas - columnas_requeridas
    if faltantes or adicionales:
        detalles = []
        if faltantes:
            detalles.append("faltan: " + ", ".join(sorted(faltantes)))
        if adicionales:
            detalles.append("no reconocidas: " + ", ".join(sorted(adicionales)))
        raise ValueError(
            "Las columnas del archivo no coinciden con la plantilla ("
            + "; ".join(detalles)
            + ")."
        )

    df = df.loc[:, list(COLUMNAS_REGISTRO_IMPORTACION)]
    df = df.dropna(how="all").reset_index(drop=True)
    if df.empty:
        raise ValueError("El archivo no contiene filas con datos.")
    if len(df) > MAX_FILAS_IMPORTACION:
        raise ValueError("El archivo supera el límite de 100.000 filas.")

    for columna in COLUMNAS_IDENTIFICACION_IMPORTACION:
        df[columna] = (
            df[columna]
            .map(_texto_identificacion_importacion)
            .astype("string")
            .str.strip()
            .replace("", pd.NA)
        )

    for columna in COLUMNAS_NUMERICAS_IMPORTACION:
        original = df[columna]
        numerica = pd.to_numeric(original, errors="coerce")
        invalidas = (
            original.notna()
            & original.astype("string").str.strip().ne("")
            & numerica.isna()
        )
        decimales = numerica.notna() & numerica.mod(1).ne(0)
        if invalidas.any() or decimales.any():
            filas_invalidas = [
                str(indice + 2)
                for indice, invalida in enumerate(invalidas | decimales)
                if invalida
            ]
            raise ValueError(
                f"El campo {columna} debe contener números enteros. "
                "Filas del archivo: "
                + ", ".join(filas_invalidas[:10])
                + "."
            )
        df[columna] = numerica.astype("Int64")

    for columna in COLUMNAS_FECHA_IMPORTACION:
        original = df[columna]
        fechas = original.map(_parsear_fecha_importacion)
        vacias = original.isna() | original.astype("string").str.strip().eq("")
        invalidas = ~vacias & fechas.isna()
        if invalidas.any():
            filas_invalidas = [
                str(indice + 2)
                for indice, invalida in enumerate(invalidas)
                if invalida
            ]
            raise ValueError(
                f"El campo {columna} contiene fechas inválidas. "
                "Filas del archivo: "
                + ", ".join(filas_invalidas[:10])
                + "."
            )
        df[columna] = fechas.dt.date

    columnas_texto = (
        columnas_requeridas
        - COLUMNAS_IDENTIFICACION_IMPORTACION
        - COLUMNAS_NUMERICAS_IMPORTACION
        - COLUMNAS_FECHA_IMPORTACION
    )
    for columna in columnas_texto:
        df[columna] = (
            df[columna]
            .astype("string")
            .str.strip()
            .replace("", pd.NA)
        )

    sin_identificacion = df[
        ["cedula", "nombres", "matricula"]
    ].isna().all(axis=1)
    if sin_identificacion.any():
        filas_invalidas = [
            str(indice + 2)
            for indice, invalida in enumerate(sin_identificacion)
            if invalida
        ]
        raise ValueError(
            "Cada fila debe incluir cédula, nombres o matrícula. "
            "Filas del archivo: "
            + ", ".join(filas_invalidas[:10])
            + "."
        )

    return df
