import pandas as pd
from sqlalchemy import create_engine, text
import streamlit as st

engine = create_engine(st.secrets["DATABASE_URL"])
df_excel = pd.read_excel("titulados_epespo.xlsx", sheet_name="totaltituladosv3")
df_limpio = pd.DataFrame()

cedula_raw = df_excel["nced_nomi"].astype(str)
df_limpio["cedula"] = (
    cedula_raw.str.replace(".0", "", regex=False)
    .str.strip()
    .str.zfill(10)
    .replace("nan", "")
)


def obtener_provincia(ced):
  if not isinstance(ced, str) or len(ced) < 2:
    return "No registrada"
  pref = ced[:2]
  mapping = {
      "01": "Azuay",
      "02": "Bolívar",
      "03": "Cañar",
      "04": "Carchi",
      "05": "Cotopaxi",
      "06": "Chimborazo",
      "07": "El Oro",
      "08": "Esmeraldas",
      "09": "Guayas",
      "10": "Imbabura",
      "11": "Loja",
      "12": "Los Ríos",
      "13": "Manabí",
      "14": "Morona Santiago",
      "15": "Napo",
      "16": "Pastaza",
      "17": "Pichincha",
      "18": "Tungurahua",
      "19": "Zamora Chinchipe",
      "20": "Galápagos",
      "21": "Sucumbíos",
      "22": "Orellana",
      "23": "Santo Domingo",
      "24": "Santa Elena",
  }
  return mapping.get(pref, "No registrada")


df_limpio["provincia"] = df_limpio["cedula"].apply(obtener_provincia)

nombres = df_excel.get(
    "nombres", pd.Series([""] * len(df_excel))
).astype(str)
apellidos = df_excel.get("apellidos_", pd.Series([""] * len(df_excel))).astype(
    str
)
df_limpio["nombres"] = (apellidos + " " + nombres).str.strip().str.replace(
    "nan", "", regex=False
)
df_limpio["nombres"] = df_limpio["nombres"].replace("", "Sin Nombre Registrado")

df_limpio["matricula"] = (
    df_excel.get("num_matric", pd.Series([None] * len(df_excel)))
    .astype(str)
    .str.strip()
    .replace("nan", "", regex=False)
)


def limpiar_impresion(val):
  try:
    v = int(float(val))
    return v if v in [0, 1, 2] else 0
  except (ValueError, TypeError):
    return 0


df_limpio["impresion"] = df_excel["Impresion"].apply(limpiar_impresion)
df_limpio["curso"] = (
    df_excel.get("titulo", pd.Series(["Curso General"] * len(df_excel)))
    .astype(str)
    .str.strip()
)

# Fecha de Titulación
fechas = pd.to_datetime(df_excel.get("fecha", pd.NaT), errors="coerce")
df_limpio["fecha"] = fechas.dt.strftime("%Y-%m-%d").fillna("2020-01-01")
df_limpio["anio"] = fechas.dt.year.fillna(2020).astype(int)
df_limpio["mes"] = fechas.dt.month.fillna(1).astype(int)

# -------------------------------------------------------------
# NUEVO: Extracción de Fecha de Inicio y Fecha de Fin del Curso
# -------------------------------------------------------------
fechas_ini = pd.to_datetime(df_excel.get("fec_ini", pd.NaT), errors="coerce")
df_limpio["fec_ini"] = fechas_ini.dt.strftime("%Y-%m-%d").fillna("No registrada")

fechas_fin = pd.to_datetime(df_excel.get("fec_fin", pd.NaT), errors="coerce")
df_limpio["fec_fin"] = fechas_fin.dt.strftime("%Y-%m-%d").fillna("No registrada")
# -------------------------------------------------------------

df_limpio["modalidad"] = (
    df_excel.get("estudio", pd.Series(["Presencial"] * len(df_excel)))
    .astype(str)
    .str.strip()
)
estado_raw = (
    df_excel.get("estado", pd.Series(["CUMPLE"] * len(df_excel)))
    .astype(str)
    .str.strip()
    .str.upper()
)
df_limpio["condicion"] = estado_raw.apply(
    lambda x: "Graduado" if "CUMPLE" in x or "APROB" in x else "No culminó"
)

with engine.connect() as conn:
  conn.execute(text("DROP TABLE IF EXISTS graduados_epespo CASCADE;"))
  conn.commit()

df_limpio.to_sql(
    "graduados_epespo",
    con=engine,
    if_exists="replace",
    index=False,
    chunksize=500,
)
print("¡Base de datos restablecida con fechas de inicio, fin y todas las columnas!")