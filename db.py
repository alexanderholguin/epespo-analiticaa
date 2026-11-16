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
        return create_engine(database_url, pool_pre_ping=True)

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
        ),
        pool_pre_ping=True,
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


def actualizar_datos_persona(
    dni_anterior: str,
    nombres_anteriores: str,
    matricula_anterior: str,
    dni_nuevo: str,
    nombres_nuevos: str,
    matricula_nueva: str,
) -> int:
    if dni_anterior:
        identidad_sql = (
            "("
            "regexp_replace(COALESCE(cedula::text, ''), '[^0-9]', '', 'g') "
            "= :dni_anterior OR "
            "'0' || regexp_replace(COALESCE(cedula::text, ''), "
            "'[^0-9]', '', 'g') = :dni_anterior"
            ")"
        )
        parametros = {"dni_anterior": dni_anterior}
    else:
        if not nombres_anteriores.strip() or not matricula_anterior.strip():
            raise ValueError(
                "Sin una cédula previa, se necesitan nombres y matrícula "
                "para identificar los registros de forma segura."
            )
        identidad_sql = """
            lower(btrim(COALESCE(nombres, ''))) = lower(:nombres_anteriores)
            AND btrim(COALESCE(matricula::text, '')) = :matricula_anterior
            AND (
                regexp_replace(COALESCE(cedula::text, ''), '[^0-9]', '', 'g') = ''
                OR regexp_replace(COALESCE(cedula::text, ''), '[^0-9]', '', 'g') ~ '^0+$'
            )
        """
        parametros = {
            "nombres_anteriores": nombres_anteriores.strip(),
            "matricula_anterior": matricula_anterior.strip(),
        }

    consulta = text(
        f"""
        UPDATE graduados_epespo
        SET cedula = :dni_nuevo,
            nombres = :nombres_nuevos,
            matricula = :matricula_nueva
        WHERE {identidad_sql}
        """
    )
    parametros.update(
        {
            "dni_nuevo": dni_nuevo.strip() or None,
            "nombres_nuevos": nombres_nuevos.strip() or None,
            "matricula_nueva": matricula_nueva.strip() or None,
        }
    )

    with get_engine().begin() as connection:
        resultado = connection.execute(consulta, parametros)
    return resultado.rowcount