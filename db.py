from datetime import datetime, timedelta, timezone
from hashlib import sha256
import os

import streamlit as st
import pandas as pd
import psycopg2
from sqlalchemy import create_engine, text


def _get_setting(name: str):
    value = os.environ.get(name)
    if value:
        return value
    if os.environ.get("K_SERVICE"):
        return None
    try:
        return st.secrets.get(name)
    except FileNotFoundError:
        return None


@st.cache_resource
def get_engine():
    database_url = _get_setting("DATABASE_URL")
    if database_url:
        return create_engine(
            database_url,
            connect_args={"connect_timeout": 10},
            pool_pre_ping=True,
            pool_timeout=10,
        )

    connection_name = _get_setting("INSTANCE_CONNECTION_NAME")
    db_name = _get_setting("DB_NAME")
    db_user = _get_setting("DB_USER")
    db_password = _get_setting("DB_PASSWORD")
    missing = [
        name
        for name, value in (
            ("INSTANCE_CONNECTION_NAME", connection_name),
            ("DB_NAME", db_name),
            ("DB_USER", db_user),
            ("DB_PASSWORD", db_password),
        )
        if not value
    ]
    if missing:
        raise RuntimeError(
            "Falta configurar DATABASE_URL o estas variables: "
            + ", ".join(missing)
        )

    if len(connection_name.split(":")) != 3 or not all(
        connection_name.split(":")
    ):
        raise ValueError(
            "INSTANCE_CONNECTION_NAME debe tener el formato "
            "proyecto:región:instancia."
        )

    socket_path = f"/cloudsql/{connection_name}"
    return create_engine(
        "postgresql+psycopg2://",
        creator=lambda: psycopg2.connect(
            database=db_name,
            user=db_user,
            password=db_password,
            host=socket_path,
            connect_timeout=10,
        ),
        pool_pre_ping=True,
        pool_timeout=10,
    )

@st.cache_data(ttl=600)
def cargar_datos_completos() -> pd.DataFrame:
    query = """
        SELECT 
            cedula, 
            nombres, 
            matricula, 
            anio, 
            mes, 
            fecha, 
            fec_ini,
            fec_fin,
            curso, 
            modalidad, 
            provincia, 
            condicion, 
            impresion 
        FROM graduados_epespo 
        ORDER BY anio ASC, mes ASC;
    """
    try:
        engine = get_engine()
        df = pd.read_sql(query, con=engine)
        
        # Limpieza de fechas para evitar nulos
        if "fec_ini" in df.columns:
            df["fec_ini"] = pd.to_datetime(df["fec_ini"], errors="coerce").dt.strftime("%Y-%m-%d").fillna("No registrada")
        else:
            df["fec_ini"] = "No registrada"

        if "fec_fin" in df.columns:
            df["fec_fin"] = pd.to_datetime(df["fec_fin"], errors="coerce").dt.strftime("%Y-%m-%d").fillna("No registrada")
        else:
            df["fec_fin"] = "No registrada"

        return df
    except Exception as e:
        st.error(f"Error al conectar con la base de datos: {e}")
        return pd.DataFrame()

def insertar_registros_masivos(df_nuevo: pd.DataFrame, modo: str = "append") -> bool:
    try:
        engine = get_engine()
        st.cache_data.clear()
        df_nuevo.to_sql(
            "graduados_epespo",
            con=engine,
            if_exists=modo,
            index=False,
            chunksize=500
        )
        return True
    except Exception as e:
        st.error(f"Error al actualizar la base de datos en PostgreSQL: {e}")
        return False


def actualizar_registros_ciudadano(
    dni_anterior: str,
    nombres_anteriores: str,
    matricula_anterior: str,
    registro_original: dict,
    datos_nuevos: dict,
) -> int:
    columnas_disponibles = (
        "cedula",
        "nombres",
        "matricula",
        "anio",
        "mes",
        "fecha",
        "fec_ini",
        "fec_fin",
        "curso",
        "modalidad",
        "provincia",
        "condicion",
        "impresion",
    )
    columnas_personales = {"cedula", "nombres", "matricula"}
    columnas_snapshot = tuple(
        columna
        for columna in columnas_disponibles
        if columna in registro_original
    )
    columnas = tuple(
        columna for columna in columnas_snapshot if columna in datos_nuevos
    )
    if not columnas_snapshot or not columnas:
        raise ValueError("No hay campos válidos para actualizar el registro.")

    snapshot_sql = " AND ".join(
        f"{columna} IS NOT DISTINCT FROM :original_{columna}"
        for columna in columnas_snapshot
    )
    parametros = {
        f"original_{columna}": _valor_sql(registro_original[columna])
        for columna in columnas_snapshot
    }

    if dni_anterior:
        digitos_sql = (
            "regexp_replace(COALESCE(cedula::text, ''), '[^0-9]', '', 'g')"
        )
        identidad_sql = (
            f"({digitos_sql} = :dni_anterior OR "
            f"'0' || {digitos_sql} = :dni_anterior)"
        )
        parametros["dni_anterior"] = dni_anterior
    else:
        if nombres_anteriores.strip() and matricula_anterior.strip():
            identidad_sql = """
                lower(btrim(COALESCE(nombres, ''))) = lower(:nombres_anteriores)
                AND lower(btrim(COALESCE(matricula::text, ''))) =
                    lower(:matricula_anterior)
                AND (
                    regexp_replace(COALESCE(cedula::text, ''), '[^0-9]', '', 'g') = ''
                    OR regexp_replace(COALESCE(cedula::text, ''), '[^0-9]', '', 'g') ~ '^0+$'
                )
            """
            parametros.update(
                {
                    "nombres_anteriores": nombres_anteriores.strip(),
                    "matricula_anterior": matricula_anterior.strip(),
                }
            )
        else:
            identidad_sql = snapshot_sql

    asignaciones = []
    for columna in columnas:
        nuevo_valor = _valor_sql(datos_nuevos[columna])
        parametros[f"nuevo_{columna}"] = nuevo_valor
        if columna in columnas_personales:
            asignaciones.append(f"{columna} = :nuevo_{columna}")
        else:
            asignaciones.append(
                f"{columna} = CASE WHEN ({snapshot_sql}) "
                f"THEN :nuevo_{columna} ELSE {columna} END"
            )

    consulta = text(
        f"""
        UPDATE graduados_epespo
        SET {", ".join(asignaciones)}
        WHERE {identidad_sql}
        """
    )
    with get_engine().begin() as connection:
        resultado = connection.execute(consulta, parametros)
    return resultado.rowcount


def _valor_sql(valor):
    if valor is None or pd.isna(valor):
        return None
    if isinstance(valor, pd.Timestamp):
        return valor.to_pydatetime()
    if hasattr(valor, "item"):
        return valor.item()
    return valor


def _hash_token_sesion(token: str) -> str:
    if not token:
        raise ValueError("El token de sesión no puede estar vacío.")
    return sha256(token.encode("utf-8")).hexdigest()


def _asegurar_tabla_sesiones(connection) -> None:
    connection.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS epespo_auth_sessions (
                token_hash VARCHAR(64) PRIMARY KEY,
                usuario VARCHAR(128) NOT NULL,
                expira_en TIMESTAMP WITH TIME ZONE NOT NULL,
                creado_en TIMESTAMP WITH TIME ZONE NOT NULL
                    DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
    )


def guardar_sesion_autenticacion(
    token: str,
    usuario: str,
    duracion_segundos: int,
) -> float:
    if duracion_segundos <= 0:
        raise ValueError("La duración de la sesión debe ser positiva.")

    expira_en = datetime.now(timezone.utc) + timedelta(
        seconds=duracion_segundos
    )
    parametros = {
        "token_hash": _hash_token_sesion(token),
        "usuario": usuario,
        "expira_en": expira_en,
    }
    with get_engine().begin() as connection:
        _asegurar_tabla_sesiones(connection)
        connection.execute(
            text(
                "DELETE FROM epespo_auth_sessions "
                "WHERE expira_en <= CURRENT_TIMESTAMP"
            )
        )
        connection.execute(
            text(
                """
                INSERT INTO epespo_auth_sessions
                    (token_hash, usuario, expira_en)
                VALUES (:token_hash, :usuario, :expira_en)
                """
            ),
            parametros,
        )
    return expira_en.timestamp()


def obtener_sesion_autenticacion(token: str):
    token_hash = _hash_token_sesion(token)
    with get_engine().begin() as connection:
        _asegurar_tabla_sesiones(connection)
        sesion = connection.execute(
            text(
                """
                SELECT usuario, expira_en
                FROM epespo_auth_sessions
                WHERE token_hash = :token_hash
                  AND expira_en > CURRENT_TIMESTAMP
                """
            ),
            {"token_hash": token_hash},
        ).mappings().one_or_none()

    if sesion is None:
        return None
    return sesion["usuario"], sesion["expira_en"].timestamp()


def revocar_sesion_autenticacion(token: str) -> None:
    token_hash = _hash_token_sesion(token)
    with get_engine().begin() as connection:
        _asegurar_tabla_sesiones(connection)
        connection.execute(
            text(
                "DELETE FROM epespo_auth_sessions "
                "WHERE token_hash = :token_hash"
            ),
            {"token_hash": token_hash},
        )