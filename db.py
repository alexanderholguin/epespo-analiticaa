import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text

@st.cache_resource
def get_engine():
    return create_engine(st.secrets["DATABASE_URL"], pool_pre_ping=True)

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