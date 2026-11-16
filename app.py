from calendar import monthrange
from datetime import datetime
from io import BytesIO
import os
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_squared_error, r2_score
from sklearn.preprocessing import PolynomialFeatures
from openpyxl.cell.cell import ILLEGAL_CHARACTERS_RE
from openpyxl.utils.exceptions import IllegalCharacterError
from sqlalchemy import inspect
from sqlalchemy.exc import SQLAlchemyError
import streamlit as st
import unicodedata

from auth import crear_gestor_cookies, render_login, cerrar_sesion
from db import actualizar_registros_ciudadano, get_engine

st.set_page_config(
    page_title="EPESPO - Suite Analítica y Estratégica Marítima",
    page_icon="🧭",
    layout="wide",
    initial_sidebar_state="collapsed",
)

cookie_manager = crear_gestor_cookies()
if not render_login(cookie_manager):
  st.stop()


# =============================================================
# CONEXIÓN A CLOUD SQL
# =============================================================
try:
  engine = get_engine()
except (RuntimeError, ValueError) as e:
  st.error(f"Configuración de Cloud SQL inválida: {e}")
  st.stop()


# FUNCIÓN DE CARGA CON LA TABLA 'graduados_epespo'
def cargar_datos_completos():
  try:
    inspector = inspect(engine)
    if not inspector.has_table("graduados_epespo"):
      st.error(
          "⚠️ La conexión fue exitosa, pero la tabla 'graduados_epespo' no"
          " existe en esta base de datos."
      )
      st.stop()

    query = """
        WITH registros AS (
            SELECT
                graduados_epespo.*,
                regexp_replace(
                    translate(
                        lower(COALESCE(modalidad::text, '')),
                        'áéíóúü',
                        'aeiouu'
                    ),
                    '[^a-z0-9]',
                    '',
                    'g'
                ) AS modalidad_clave_analitica
            FROM graduados_epespo
        )
        SELECT
            registros.*,
            CASE
                WHEN modalidad_clave_analitica IN (
                    'eld',
                    'estudiolibredirigido'
                )
                    THEN 'Estudio Libre Dirigido'
                WHEN modalidad_clave_analitica = 'nivelacion'
                    THEN 'Nivelación'
                ELSE NULLIF(BTRIM(registros.modalidad::text), '')
            END AS modalidad_analitica
        FROM registros
    """
    df = pd.read_sql(query, con=engine)
    return df.drop(columns=["modalidad_clave_analitica"])
  except Exception as e:
    st.error(f"Error al consultar la base de datos: {e}")
    st.stop()


def generar_excel_auditoria(df):
  df_excel = df.copy()

  def limpiar_valor_excel(valor):
    if isinstance(valor, str):
      return ILLEGAL_CHARACTERS_RE.sub("", valor)
    if isinstance(valor, datetime) and valor.tzinfo is not None:
      return valor.replace(tzinfo=None)
    return valor

  for columna in df_excel.select_dtypes(
      include=["object", "string"]
  ).columns:
    df_excel[columna] = df_excel[columna].map(limpiar_valor_excel)
  for columna, tipo in df_excel.dtypes.items():
    if isinstance(tipo, pd.DatetimeTZDtype):
      df_excel[columna] = df_excel[columna].dt.tz_localize(None)

  archivo = BytesIO()
  with pd.ExcelWriter(archivo, engine="openpyxl") as escritor:
    df_excel.to_excel(escritor, index=False, sheet_name="Registros")
  return archivo.getvalue()


@st.fragment
def mostrar_botones_descarga_auditoria(opciones_descarga):
  nombres_archivo = {
      "todos": "todos_los_registros",
      "sin_dni": "registros_sin_dni",
      "completos": "dni_e_informacion_completa",
  }
  columnas = st.columns(len(opciones_descarga))
  for columna, (clave, (titulo, df)) in zip(
      columnas,
      opciones_descarga.items(),
  ):
    with columna:
      st.markdown(f"**{titulo} ({len(df):,})**")
      st.download_button(
          "⬇️ Descargar CSV",
          data=df.to_csv(index=False).encode("utf-8-sig"),
          file_name=f"{nombres_archivo[clave]}.csv",
          mime="text/csv",
          use_container_width=True,
          key=f"auditoria_boton_{clave}_csv",
      )
      try:
        datos_excel = generar_excel_auditoria(df)
      except (
          IllegalCharacterError,
          ValueError,
          TypeError,
          OSError,
      ) as error:
        st.error(f"No se pudo generar el Excel de {titulo}: {error}")
      else:
        st.download_button(
            "⬇️ Descargar Excel",
            data=datos_excel,
            file_name=f"{nombres_archivo[clave]}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
            key=f"auditoria_boton_{clave}_excel",
        )


def mascara_informacion_completa(df):
  valores_invalidos = {
      "",
      "nan",
      "none",
      "null",
      "n/a",
      "na",
      "s/d",
      "sin dato",
      "sin especificar",
      "sin registro",
      "no registra",
      "no registrado",
      "no registrada",
  }
  campos_completos = {}
  for columna in ["nombres", "matricula", "curso", "modalidad"]:
    valores = (
        df[columna]
        .fillna("")
        .astype(str)
        .str.strip()
        .str.casefold()
    )
    valores_invalidos_campo = valores_invalidos.copy()
    if columna == "nombres":
      valores_invalidos_campo.add("sin nombre")
    campos_completos[columna] = ~valores.isin(valores_invalidos_campo)

  anio_valido = pd.to_numeric(df["anio"], errors="coerce").gt(0)
  fecha_valida = pd.to_datetime(df["fecha"], errors="coerce").notna()
  return (
      df["estado_dni"].eq("Con DNI")
      & campos_completos["nombres"]
      & campos_completos["matricula"]
      & campos_completos["curso"]
      & campos_completos["modalidad"]
      & (anio_valido | fecha_valida)
  )


# =============================================================
# ESTILOS CSS GLOBALES INSTITUCIONALES
# =============================================================
st.markdown(
    """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    .stApp { background-color: #F5F8FC; }
    .block-container { max-width: 1720px; padding: 1.8rem 2.2rem 3rem; }
    h1, h2, h3 { color: #153A60; letter-spacing: -.3px; }

    .hero-banner {
        background: linear-gradient(135deg, #0A2540 0%, #0F3E6D 50%, #0052CC 100%);
        padding: 22px 28px;
        border-radius: 12px;
        color: white;
        margin-bottom: 20px;
        box-shadow: 0 10px 25px -5px rgba(10, 37, 64, 0.2);
        display: flex;
        align-items: center;
        justify-content: space-between;
    }
    .hero-title { font-size: 24px; font-weight: 800; margin: 0; color: #FFFFFF; }
    .hero-subtitle { font-size: 13.5px; color: #D1E4FF; margin-top: 4px; margin-bottom: 0; }
    .kpi-container {
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 16px;
        margin-bottom: 20px;
    }
    @media (max-width: 1024px) {
        .kpi-container { grid-template-columns: repeat(2, 1fr); }
    }
    .kpi-card {
        background: #FFFFFF;
        border-radius: 12px;
        padding: 18px 20px;
        box-shadow: 0 2px 4px rgba(15, 23, 42, 0.04);
        border: 1px solid #E2E8F0;
        position: relative;
        overflow: hidden;
    }
    .kpi-card::before { content: ''; position: absolute; top: 0; left: 0; right: 0; height: 4px; }
    .kpi-blue::before { background: #0284C7; }
    .kpi-green::before { background: #10B981; }
    .kpi-teal::before { background: #0EA5E9; }
    .kpi-rose::before { background: #F43F5E; }

    .kpi-label { font-size: 11.5px; font-weight: 700; color: #64748B; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 6px; }
    .kpi-value { font-size: 26px; font-weight: 800; color: #0F172A; line-height: 1.15; }
    .kpi-unit { font-size: 13.5px; font-weight: 500; color: #94A3B8; margin-left: 5px; }
    .kpi-badge { display: inline-block; margin-top: 8px; padding: 3px 8px; border-radius: 6px; font-size: 11.5px; font-weight: 600; }
    .badge-green { background: #ECFDF5; color: #047857; }
    .badge-rose { background: #FFF1F2; color: #BE123C; }
    .badge-blue { background: #EFF6FF; color: #1D4ED8; }

    .stTabs [data-baseweb="tab-list"] { background: #E7EEF7; border-radius: 13px; padding: 6px; gap: 4px; }
    .stTabs [data-baseweb="tab"] { border-radius: 9px; padding: 10px 14px; color: #46627F; font-weight: 600; }
    .stTabs [data-baseweb="tab"][aria-selected="true"] { background: #FFFFFF !important; color: #0759B8 !important; box-shadow: 0 2px 8px rgba(15,54,102,.08); }
    
    div[data-testid="stPlotlyChart"] { background: #FFFFFF; border: 1px solid #E4EBF4; border-radius: 15px; padding: 7px; box-shadow: 0 3px 12px rgba(15,54,102,.025); }
    div[data-testid="stDataFrame"] { border: 1px solid #E3EAF4; border-radius: 12px; overflow: hidden; }
    .sidebar-user-card { background: #0A2540; color: white; padding: 12px 16px; border-radius: 10px; margin-bottom: 14px; }
</style>
""",
    unsafe_allow_html=True,
)


# =============================================================
# DICCIONARIOS Y FUNCIONES DE NORMALIZACIÓN
# =============================================================
GEO_PROVINCIAS = {
    "Manabí": {"lat": -0.9538, "lon": -80.7089},
    "Guayas": {"lat": -2.1894, "lon": -79.8891},
    "Esmeraldas": {"lat": 0.9682, "lon": -79.6517},
    "Pichincha": {"lat": -0.2298, "lon": -78.5249},
    "Los Ríos": {"lat": -1.8022, "lon": -79.5344},
    "El Oro": {"lat": -3.2581, "lon": -79.9554},
    "Santa Elena": {"lat": -2.2262, "lon": -80.8587},
    "Cotopaxi": {"lat": -0.9333, "lon": -78.6167},
    "Santo Domingo": {"lat": -0.2530, "lon": -79.1754},
    "Sucumbíos": {"lat": 0.0833, "lon": -76.8833},
    "Azuay": {"lat": -2.9001, "lon": -79.0059},
    "Chimborazo": {"lat": -1.6667, "lon": -78.6500},
    "Imbabura": {"lat": 0.3500, "lon": -78.1167},
    "Loja": {"lat": -3.9931, "lon": -79.2042},
    "Tungurahua": {"lat": -1.2491, "lon": -78.6168},
    "Galápagos": {"lat": -0.7432, "lon": -90.3138},
    "Bolívar": {"lat": -1.5911, "lon": -79.0022},
    "Cañar": {"lat": -2.5562, "lon": -78.9386},
    "Carchi": {"lat": 0.8122, "lon": -77.7173},
    "Morona Santiago": {"lat": -2.3087, "lon": -78.1114},
    "Napo": {"lat": -0.9938, "lon": -77.8129},
    "Pastaza": {"lat": -1.4897, "lon": -77.9986},
    "Zamora Chinchipe": {"lat": -4.0692, "lon": -78.9567},
    "Orellana": {"lat": -0.4639, "lon": -76.9872},
}

NOMBRES_MESES = {
    1: "Enero",
    2: "Febrero",
    3: "Marzo",
    4: "Abril",
    5: "Mayo",
    6: "Junio",
    7: "Julio",
    8: "Agosto",
    9: "Septiembre",
    10: "Octubre",
    11: "Noviembre",
    12: "Diciembre",
}


def limpiar_texto_general(texto):
  if pd.isna(texto):
    return "Sin Especificar"
  return " ".join(str(texto).split()).title()


def normalizar_provincia(prov_raw):
  if pd.isna(prov_raw):
    return "No Registrada"
  p = str(prov_raw).strip().title()
  correcciones = {
      "Manabi": "Manabí",
      "Los Rios": "Los Ríos",
      "Bolivar": "Bolívar",
      "Galapagos": "Galápagos",
  }
  return correcciones.get(p, p)


def normalizar_curso(curso_raw):
  if pd.isna(curso_raw):
    return "Sin Especificar"
  nfkd_form = unicodedata.normalize("NFKD", str(curso_raw))
  c = "".join([char for char in nfkd_form if not unicodedata.combining(char)])
  c = c.strip().upper().replace(".", "")
  if c in ["ELD", "ESTUDIO LIBRE DIRIGIDO"]:
    return "Estudio Libre Dirigido"
  elif "MARINERO DE MAQUINAS" in c:
    return "Marinero De Máquinas"
  elif "OPERADOR DE MAQUINAS" in c:
    return "Operador De Máquinas"
  return " ".join(c.split()).title()


def clasificar_area_operativa(curso):
  nfkd_form = unicodedata.normalize("NFKD", str(curso))
  c = "".join(
      [char for char in nfkd_form if not unicodedata.combining(char)]
  ).upper()
  if any(k in c for k in ["MAQUINA", "MOTORISTA", "MAQUINISTA", "MECANIC"]):
    return "Área de Máquinas"
  elif any(
      k in c
      for k in [
          "PATRON",
          "CAPITAN",
          "CUBIERTA",
          "PUENTE",
          "TIMONEL",
          "PESCADOR",
          "MARINERO PESCADOR",
      ]
  ):
    return "Área de Cubierta"
  return "Servicios y Apoyo Marítimo"


def clasificar_escala_nautica(curso):
  nfkd_form = unicodedata.normalize("NFKD", str(curso))
  c = "".join(
      [char for char in nfkd_form if not unicodedata.combining(char)]
  ).upper()
  if any(k in c for k in ["ALTURA", "CAPITAN", "JEFE DE MAQUINAS"]):
    return "4. Mando Superior (Capitanes / Jefes)"
  elif any(
      k in c
      for k in [
          "COSTANERO",
          "OPERADOR",
          "OFICIAL",
          "MAQUINISTA",
          "JEFE DE CUBIERTA",
          "MOTORISTA",
      ]
  ):
    return "3. Mandos Medios y Técnicos"
  elif any(
      k in c for k in ["TIMONEL", "MARINERO DE MAQUINAS", "MARINERO PRIMERA"]
  ):
    return "2. Tripulación Calificada"
  return "1. Marinería Base y Artesanal"


def clasificar_tipo_estudiante(fila):
  if "impresion" in fila and pd.notna(fila["impresion"]):
    try:
      val = int(float(fila["impresion"]))
      if val == 2:
        return "Duplicado (Cód. 2)"
      elif val == 1:
        return "Recién Graduado (Cód. 1)"
      elif val == 0:
        return "Estudiante Normal (Cód. 0)"
    except (ValueError, TypeError):
      pass
  return "Estudiante Normal (Cód. 0)"


def limpiar_dni(val):
  if pd.isna(val):
    return ""
  s = str(val).strip()
  if s.endswith(".0"):
    s = s[:-2]
  s_digits = "".join([c for c in s if c.isdigit()])
  if len(s_digits) == 9:
    s_digits = "0" + s_digits
  return s_digits if s_digits else s


def texto_celda(valor):
  return "" if pd.isna(valor) else str(valor).strip()


def texto_entero(valor):
  if pd.isna(valor):
    return ""
  try:
    return str(int(float(valor)))
  except (OverflowError, TypeError, ValueError):
    return texto_celda(valor)


def texto_fecha(valor):
  if pd.isna(valor):
    return ""
  fecha = pd.to_datetime(valor, errors="coerce")
  return "" if pd.isna(fecha) else fecha.strftime("%Y-%m-%d")


def filtrar_por_periodo(df, clave):
  anios = sorted(
      int(anio)
      for anio in df["anio"].dropna().unique()
      if int(anio) > 2000
  )
  opciones_anio = ["Todos"] + anios
  clave_anio = f"{clave}_anio"
  if st.session_state.get(clave_anio, "Todos") not in opciones_anio:
    st.session_state[clave_anio] = "Todos"
  with st.container():
    col_anio, col_mes = st.columns(2)
    with col_anio:
      anio_sel = st.selectbox(
          "Año",
          opciones_anio,
          format_func=lambda valor: (
              "Todos los años" if valor == "Todos" else str(valor)
          ),
          key=clave_anio,
      )

    df_anio = (
        df if anio_sel == "Todos" else df[df["anio"] == anio_sel]
    )
    meses = sorted(
        int(mes)
        for mes in df_anio["mes"].dropna().unique()
        if 1 <= int(mes) <= 12
    )
    opciones_mes = ["Todos"] + meses
    clave_mes = f"{clave}_mes"
    if st.session_state.get(clave_mes, "Todos") not in opciones_mes:
      st.session_state[clave_mes] = "Todos"
    with col_mes:
      mes_sel = st.selectbox(
          "Mes",
          opciones_mes,
          format_func=lambda valor: (
              "Todos los meses"
              if valor == "Todos"
              else NOMBRES_MESES.get(valor, str(valor))
          ),
          key=clave_mes,
      )

  df_filtrado = df_anio
  if mes_sel != "Todos":
    df_filtrado = df_filtrado[df_filtrado["mes"] == mes_sel]
  return df_filtrado, anio_sel, mes_sel


def convertir_entero_formulario(valor, campo):
  if not valor.strip():
    return None
  try:
    return int(valor)
  except ValueError as error:
    raise ValueError(f"{campo} debe ser un número entero.") from error


def convertir_fecha_formulario(valor, campo):
  if not valor.strip():
    return None
  fecha = pd.to_datetime(valor, format="%Y-%m-%d", errors="coerce")
  if pd.isna(fecha):
    raise ValueError(f"{campo} debe tener el formato AAAA-MM-DD.")
  return fecha.strftime("%Y-%m-%d")


def clasificar_dni(val):
  if pd.isna(val):
    return "Sin DNI"

  raw = str(val).strip().lower()
  raw_normalizado = unicodedata.normalize("NFKD", raw)
  raw_normalizado = "".join(
      char
      for char in raw_normalizado
      if not unicodedata.combining(char)
  )
  if raw_normalizado in {
      "",
      "nan",
      "none",
      "null",
      "n/a",
      "na",
      "s/d",
      "sin dato",
      "sin cedula",
      "no registra",
      "no registrado",
  }:
    return "Sin DNI"

  if raw.endswith(".0") and raw[:-2].isdigit():
    raw = raw[:-2]
  digits = "".join(char for char in raw if char.isdigit())
  if not digits or set(digits) == {"0"}:
    return "Sin DNI"

  caracteres_no_validos = [
      char for char in raw if not char.isdigit() and char not in " .-"
  ]
  if caracteres_no_validos:
    return "DNI irregular"

  if len(digits) == 9:
    digits = "0" + digits
  return "Con DNI" if len(digits) == 10 else "DNI irregular"


def estimar_zona_cantonal(cedula_limpia, prov):
  s = str(cedula_limpia).strip()
  if not s.isdigit() or len(s) < 3:
    return "No Determinado"
  d3 = int(s[2])
  if prov == "Manabí":
    if d3 in [0, 1]:
      return "Manta / Montecristi / Jaramijó"
    elif d3 in [2, 3]:
      return "Portoviejo y Cuenca Central"
    elif d3 in [4, 5]:
      return "Sucre / San Vicente / Bahía"
    elif d3 in [6, 7]:
      return "Pedernales / Jama / Cojimíes"
    else:
      return "Zona Sur (Jipijapa / Puerto López)"
  elif prov == "Guayas":
    if d3 in [0, 1, 2]:
      return "Guayaquil Metropolitano"
    elif d3 in [3, 4]:
      return "Playas / Posorja / Golfo"
    else:
      return "Cantones Fluviales (Durán / Daule)"
  elif prov == "Esmeraldas":
    if d3 in [0, 1, 2]:
      return "Esmeraldas / Atacames"
    else:
      return "San Lorenzo / Eloy Alfaro"
  elif prov == "Santa Elena":
    return "La Libertad / Salinas / Santa Elena"
  return f"Cantones de {prov}"


# =============================================================
# CARGA Y PROCESAMIENTO ESTRICTO DE DATOS
# =============================================================
df_raw = cargar_datos_completos()
if df_raw.empty:
  st.error("No se encontraron registros en la base de datos.")
  st.stop()

df_original = df_raw.drop(columns=["modalidad_analitica"]).copy()
df_raw["modalidad"] = df_raw["modalidad_analitica"].fillna(df_raw["modalidad"])
df_raw.drop(columns=["modalidad_analitica"], inplace=True)
df_raw["cedula_limpia"] = df_raw["cedula"].apply(limpiar_dni)
df_raw["estado_dni"] = df_raw["cedula"].apply(clasificar_dni)
df_raw["curso"] = df_raw["curso"].apply(normalizar_curso)
df_raw["modalidad"] = df_raw["modalidad"].apply(limpiar_texto_general)
df_raw["provincia"] = df_raw["provincia"].apply(normalizar_provincia)
df_raw["es_graduado"] = (
    df_raw["condicion"]
    .fillna("")
    .astype(str)
    .str.strip()
    .str.casefold()
    .eq("graduado")
)

df_raw["area_operativa"] = df_raw["curso"].apply(clasificar_area_operativa)
df_raw["escala_nautica"] = df_raw["curso"].apply(clasificar_escala_nautica)
df_raw["zona_canton"] = df_raw.apply(
    lambda r: estimar_zona_cantonal(r["cedula_limpia"], r["provincia"]), axis=1
)
df_raw["tipo_tramite"] = df_raw.apply(clasificar_tipo_estudiante, axis=1)

df_raw["anio"] = (
    pd.to_numeric(df_raw["anio"], errors="coerce").fillna(0).astype(int)
)
df_raw["mes"] = pd.to_numeric(df_raw["mes"], errors="coerce")


# =============================================================
# SIDEBAR / CONTROLES GLOBALES Y FILTROS
# =============================================================
st.sidebar.markdown(
    f"""
    <div class="sidebar-user-card">
        <div style="font-size: 11px; text-transform: uppercase; color: #93C5FD; font-weight: 700;">Usuario Activo</div>
        <div style="font-size: 13.5px; font-weight: 600; margin-top: 2px;">{st.session_state.nombre}</div>
        <div style="margin-top: 6px;"><span style="background: rgba(16, 185, 129, 0.2); color: #34D399; font-size: 10.5px; padding: 2px 8px; border-radius: 12px; font-weight: 700;">ROL: {st.session_state.rol.upper()}</span></div>
    </div>
""",
    unsafe_allow_html=True,
)
st.sidebar.button(
    "🚪 Cerrar sesión",
    on_click=cerrar_sesion,
    use_container_width=True,
    key="cerrar_sesion_button",
)


def limpiar_busqueda_ciudadano():
  st.session_state["search_dni_side"] = ""
  st.session_state["search_ape_side"] = ""


resultados_principales = st.container()

with st.sidebar.expander("🔍 Búsqueda de Ciudadano", expanded=False):
  dni_sidebar = st.text_input(
      "Cédula / DNI:", placeholder="Ej: 1306296409", key="search_dni_side"
  )
  ape_sidebar = st.text_input(
      "O por Apellidos:", placeholder="Ej: RODRIGUEZ", key="search_ape_side"
  )
  if dni_sidebar or ape_sidebar:
    st.button(
        "✖️ Limpiar Búsqueda",
        on_click=limpiar_busqueda_ciudadano,
        use_container_width=True,
    )

  if dni_sidebar or ape_sidebar:
    resultados_principales.subheader("Resultado de búsqueda")
    coincidencias = df_raw.copy()
    if dni_sidebar:
      busqueda_dni = "".join(
          caracter for caracter in dni_sidebar if caracter.isdigit()
      )
      if not busqueda_dni:
        busqueda_dni = dni_sidebar.strip()
      coincidencias = coincidencias[
          coincidencias["cedula_limpia"]
          .astype(str)
          .str.contains(busqueda_dni, na=False, regex=False)
      ]
    if ape_sidebar:
      coincidencias = coincidencias[
          coincidencias["nombres"]
          .fillna("")
          .astype(str)
          .str.contains(ape_sidebar.strip(), case=False, na=False, regex=False)
      ]

    resultados_principales.caption(
        f"Coincidencias encontradas: {len(coincidencias):,} registros"
    )
    if coincidencias.empty:
      resultados_principales.info(
          "No se encontraron ciudadanos con esos datos."
      )
    else:
      grupos_persona = {}
      for _, fila in coincidencias.iterrows():
        dni_digitos = "".join(
            caracter
            for caracter in str(fila["cedula_limpia"])
            if caracter.isdigit()
        )
        if dni_digitos and set(dni_digitos) != {"0"}:
          clave_persona = ("dni", dni_digitos)
        else:
          nombre_clave = texto_celda(fila["nombres"]).casefold()
          matricula_clave = texto_celda(fila["matricula"]).casefold()
          clave_persona = ("sin_dni", nombre_clave, matricula_clave)
        grupos_persona.setdefault(clave_persona, []).append(fila.name)

      claves_persona = list(grupos_persona)

      def etiqueta_persona(indice):
        clave = claves_persona[indice]
        filas = grupos_persona[clave]
        primera_fila = df_raw.loc[filas[0]]
        dni = texto_celda(primera_fila["cedula_limpia"])
        nombre = texto_celda(primera_fila["nombres"])
        matricula = texto_celda(primera_fila["matricula"])
        identificador = dni if clave[0] == "dni" else "Sin DNI"
        return (
            f"{identificador} · {nombre or 'Sin nombre'} · "
            f"Matrícula: {matricula or 'Sin matrícula'} · "
            f"{len(filas)} registro(s) · Resultado {indice + 1}"
        )

      indice_persona = resultados_principales.selectbox(
          "Ciudadano encontrado:",
          options=range(len(claves_persona)),
          format_func=etiqueta_persona,
          key="ciudadano_editar_seleccion",
      )
      clave_seleccionada = claves_persona[indice_persona]
      registros_persona = df_raw.loc[grupos_persona[clave_seleccionada]]
      columnas_resumen = [
          columna
          for columna in [
              "cedula",
              "nombres",
              "matricula",
              "curso",
              "anio",
              "fecha",
          ]
          if columna in registros_persona.columns
      ]
      resultados_principales.dataframe(
          registros_persona[columnas_resumen].drop_duplicates(),
          use_container_width=True,
          hide_index=True,
      )

      if st.session_state.get("rol") != "admin":
        resultados_principales.info(
            "Solo un usuario administrador puede editar ciudadanos."
        )
      else:
        def etiqueta_registro(indice):
          registro = registros_persona.loc[indice]
          return (
              f"{texto_celda(registro.get('curso')) or 'Sin curso'} · "
              f"Año {texto_entero(registro.get('anio')) or 's/d'} · "
              f"{texto_fecha(df_original.loc[indice].get('fecha')) or 'Sin fecha'}"
          )

        indice_registro = resultados_principales.selectbox(
            "Registro a editar:",
            options=registros_persona.index.tolist(),
            format_func=etiqueta_registro,
            key="ciudadano_registro_editar",
        )
        fila_seleccionada = registros_persona.loc[indice_registro]
        fila_original = df_original.loc[indice_registro]
        campos_registro = [
            columna
            for columna in [
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
            ]
            if columna in df_original.columns
        ]
        identidad_segura = (
            clave_seleccionada[0] == "dni"
            or bool(clave_seleccionada[1] and clave_seleccionada[2])
        )
        if not identidad_segura:
          resultados_principales.info(
              "No hay datos suficientes para agrupar a esta persona. Se "
              "actualizará solo el registro seleccionado, identificado por "
              "sus valores actuales; no se crearán filas nuevas."
          )
        else:
          resultados_principales.caption(
              "Cédula, nombres y matrícula se actualizan en todos los "
              "registros vinculados. Los demás campos solo cambian en el "
              "registro seleccionado."
          )

        dni_actual = "".join(
            caracter
            for caracter in str(fila_seleccionada["cedula_limpia"])
            if caracter.isdigit()
        )
        if set(dni_actual or "0") == {"0"}:
          dni_actual = ""

        etiquetas_campos = {
            "cedula": "Cédula (10 dígitos; vacío si no tiene)",
            "nombres": "Nombres y apellidos",
            "matricula": "Matrícula",
            "anio": "Año",
            "mes": "Mes (1-12; 0 o vacío si se desconoce)",
            "fecha": "Fecha (AAAA-MM-DD)",
            "fec_ini": "Fecha de inicio (AAAA-MM-DD)",
            "fec_fin": "Fecha de fin (AAAA-MM-DD)",
            "curso": "Curso",
            "modalidad": "Modalidad",
            "provincia": "Provincia",
            "condicion": "Condición",
            "impresion": "Código de impresión",
        }
        campos_enteros = {"anio", "mes", "impresion"}
        campos_fecha = {"fecha", "fec_ini", "fec_fin"}
        valores_formulario = {}
        valores_iniciales = {}

        with resultados_principales.form(
            f"form_editar_ciudadano_{indice_registro}"
        ):
          columna_personal, columna_academica = st.columns(2)
          for campo in campos_registro:
            contenedor = (
                columna_personal
                if campo in {"cedula", "nombres", "matricula", "anio", "mes", "fecha"}
                else columna_academica
            )
            if campo == "cedula":
              valor_inicial = dni_actual
            elif campo in campos_enteros:
              valor_inicial = texto_entero(fila_original.get(campo))
            elif campo in campos_fecha:
              valor_inicial = texto_fecha(fila_original.get(campo))
            else:
              valor_inicial = texto_celda(fila_original.get(campo))
            with contenedor:
              valores_iniciales[campo] = valor_inicial
              valores_formulario[campo] = st.text_input(
                  etiquetas_campos[campo],
                  value=valor_inicial,
                  key=f"editar_{campo}_{indice_registro}",
              ).strip()
          guardar_edicion = st.form_submit_button(
              "Guardar cambios",
              use_container_width=True,
          )

        if guardar_edicion:
          dni_nuevo = valores_formulario.get("cedula", "")
          if dni_nuevo and dni_nuevo != dni_actual and (
              not dni_nuevo.isdigit() or len(dni_nuevo) != 10
          ):
            resultados_principales.error(
                "La cédula debe tener exactamente 10 dígitos."
            )
          else:
            dni_anterior = (
                clave_seleccionada[1]
                if clave_seleccionada[0] == "dni"
                else ""
            )
            try:
              datos_nuevos = {}
              for campo, valor in valores_formulario.items():
                if valor == valores_iniciales[campo]:
                  continue
                if campo in campos_enteros:
                  datos_nuevos[campo] = convertir_entero_formulario(
                      valor,
                      etiquetas_campos[campo],
                  )
                elif campo in campos_fecha:
                  datos_nuevos[campo] = convertir_fecha_formulario(
                      valor,
                      etiquetas_campos[campo],
                  )
                else:
                  datos_nuevos[campo] = valor or None

              mes_parseado = datos_nuevos.get("mes")
              if mes_parseado is not None and not 0 <= mes_parseado <= 12:
                raise ValueError("Mes debe estar entre 0 y 12.")
              if not datos_nuevos:
                resultados_principales.info(
                    "No se detectaron cambios para guardar."
                )
              else:
                registro_original = fila_original[campos_registro].to_dict()
                registros_actualizados = actualizar_registros_ciudadano(
                    dni_anterior,
                    texto_celda(fila_original.get("nombres")),
                    texto_celda(fila_original.get("matricula")),
                    registro_original,
                    datos_nuevos,
                )
                if registros_actualizados:
                  st.session_state["mensaje_edicion_ciudadano"] = (
                      f"Se actualizaron {registros_actualizados} registro(s) "
                      "existentes; no se insertaron filas."
                  )
                  st.rerun()
                else:
                  resultados_principales.error(
                      "No se encontró ningún registro para actualizar."
                  )
            except ValueError as error:
              resultados_principales.error(str(error))
            except SQLAlchemyError as error:
              resultados_principales.error(
                  f"No se pudieron actualizar los registros: {error}"
              )

  if st.session_state.get("mensaje_edicion_ciudadano"):
    resultados_principales.success(
        st.session_state.pop("mensaje_edicion_ciudadano")
    )

with st.sidebar.expander("⚙️ Filtros Globales de Datos", expanded=False):
  provincias_disp = ["Todas las Provincias"] + sorted(
      [p for p in df_raw["provincia"].dropna().unique() if p != "No Registrada"]
  )
  prov_sel = st.sidebar.selectbox("Provincia:", provincias_disp)

  areas_disp = ["Todas las Áreas"] + sorted(
      df_raw["area_operativa"].unique().tolist()
  )
  area_sel = st.sidebar.selectbox("Área de Buque:", areas_disp)

  cursos_disp = ["Todas las Especialidades"] + sorted(
      df_raw["curso"].dropna().unique().tolist()
  )
  curso_sel = st.sidebar.selectbox("Especialidad:", cursos_disp)

  modalidades_disp = ["Todas las Modalidades"] + sorted(
      df_raw["modalidad"].dropna().unique().tolist()
  )
  mod_sel = st.sidebar.selectbox("Modalidad:", modalidades_disp)

  condiciones_disp = ["Todos", "Solo Graduados (Cumple)", "No culminó"]
  cond_sel = st.sidebar.selectbox("Condición:", condiciones_disp)

# Aplicar filtros globales al DataFrame
df_f = df_raw.copy()
if prov_sel != "Todas las Provincias":
  df_f = df_f[df_f["provincia"] == prov_sel]
if area_sel != "Todas las Áreas":
  df_f = df_f[df_f["area_operativa"] == area_sel]
if curso_sel != "Todas las Especialidades":
  df_f = df_f[df_f["curso"] == curso_sel]
if mod_sel != "Todas las Modalidades":
  df_f = df_f[df_f["modalidad"] == mod_sel]

if cond_sel == "Solo Graduados (Cumple)":
  df_f = df_f[df_f["es_graduado"]]
elif cond_sel == "No culminó":
  df_f = df_f[
      df_f["condicion"].fillna("").astype(str).str.strip().str.casefold()
      == "no culminó"
  ]

if dni_sidebar:
  df_f = df_f[
      df_f["cedula_limpia"]
      .astype(str)
      .str.contains(busqueda_dni, na=False, regex=False)
  ]
if ape_sidebar:
  df_f = df_f[
      df_f["nombres"]
      .fillna("")
      .astype(str)
      .str.contains(ape_sidebar.strip(), case=False, na=False, regex=False)
  ]

# =============================================================
# BANNER PRINCIPAL
# =============================================================
st.markdown(
    """
    <div class="hero-banner">
        <div>
            <h1 class="hero-title">⚓ ESCUELA DE PESCA DEL PACÍFICO ORIENTAL (EPESPO)</h1>
            <p class="hero-subtitle">Plataforma de Inteligencia Analítica Marítima, Control de Flota y Gestión de Titulaciones</p>
        </div>
    </div>
""",
    unsafe_allow_html=True,
)

# =============================================================
# TARJETAS KPI
# =============================================================
total_titulados = len(df_f)
provincias_activas = df_f["provincia"].nunique()
cursos_activos = df_f["curso"].nunique()
tasa_graduacion = (
    (df_f["es_graduado"].sum() / total_titulados * 100)
    if total_titulados > 0
    else 0
)

st.markdown(
    f"""
    <div class="kpi-container">
        <div class="kpi-card kpi-blue">
            <div class="kpi-label">Total Registros / Titulados</div>
            <div class="kpi-value">{total_titulados:,}<span class="kpi-unit">pers.</span></div>
            <span class="kpi-badge badge-blue">Filtro Activo</span>
        </div>
        <div class="kpi-card kpi-green">
            <div class="kpi-label">Tasa de Aprobación</div>
            <div class="kpi-value">{tasa_graduacion:.1f}<span class="kpi-unit">%</span></div>
            <span class="kpi-badge badge-green">Efectividad Histórica</span>
        </div>
        <div class="kpi-card kpi-teal">
            <div class="kpi-label">Provincias de Origen</div>
            <div class="kpi-value">{provincias_activas}<span class="kpi-unit">prov.</span></div>
            <span class="kpi-badge badge-blue">Cobertura Nacional</span>
        </div>
        <div class="kpi-card kpi-rose">
            <div class="kpi-label">Especialidades Náuticas</div>
            <div class="kpi-value">{cursos_activos}<span class="kpi-unit">cursos</span></div>
            <span class="kpi-badge badge-rose">Oferta Académica</span>
        </div>
    </div>
""",
    unsafe_allow_html=True,
)

# =============================================================
# PESTAÑAS DE NAVEGACIÓN ANALÍTICA
# =============================================================
tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9 = st.tabs([
    "📈 Evolución Histórica",
    "🗺️ Geografía & Cobertura",
    "⚓ Áreas & Especialidades",
    "🔥 Demanda & Cumplimiento",
    "🎓 Análisis por Curso",
    "🔮 Proyección & Tendencias",
    "🔍 Auditoría de Datos",
    "🔄 Ciclos y Reingresos",
    "📋 Base de Datos Completa",
])

with tab1:
  st.subheader("Evolución anual de registros y resultados")
  df_evolucion, anio_evolucion, mes_evolucion = filtrar_por_periodo(
      df_f, "evolucion"
  )
  df_evolucion = df_evolucion[df_evolucion["anio"] > 2000].copy()
  if not df_evolucion.empty:
    if anio_evolucion != "Todos" and mes_evolucion == "Todos":
      df_evolucion["periodo"] = df_evolucion["mes"].map(
          lambda mes: (
              NOMBRES_MESES.get(int(mes), "Mes no registrado")
              if pd.notna(mes)
              else "Mes no registrado"
          )
      )
      df_evolucion = (
          df_evolucion.groupby(["periodo", "condicion"], dropna=False)
          .size()
          .reset_index(name="registros")
      )
      fig_line = px.line(
          df_evolucion,
          x="periodo",
          y="registros",
          color="condicion",
          markers=True,
          category_orders={
              "periodo": list(NOMBRES_MESES.values()) + ["Mes no registrado"]
          },
          title=f"Registros mensuales de {anio_evolucion} por condición",
      )
      fig_line.update_xaxes(title_text="Mes")
    else:
      df_evolucion = (
          df_evolucion.groupby(["anio", "condicion"], dropna=False)
          .size()
          .reset_index(name="registros")
      )
      fig_line = px.line(
          df_evolucion,
          x="anio",
          y="registros",
          color="condicion",
          markers=True,
          title=(
              f"Registros por año y condición"
              + (
                  f" · {NOMBRES_MESES[mes_evolucion]}"
                  if mes_evolucion != "Todos"
                  else ""
              )
          ),
      )
      fig_line.update_xaxes(title_text="Año")
    fig_line.update_layout(
        plot_bgcolor="white",
        paper_bgcolor="white",
        margin=dict(t=45, b=20, l=20, r=20),
        yaxis_title="Registros",
        hovermode="x unified",
    )
    st.plotly_chart(fig_line, use_container_width=True)
  else:
    st.info("No hay datos suficientes para mostrar la evolución temporal.")

with tab2:
  st.subheader("Distribución Geográfica y Provincial")
  df_cobertura, _, _ = filtrar_por_periodo(df_f, "cobertura")
  if not df_cobertura.empty and "provincia" in df_cobertura.columns:
    col_m1, col_m2 = st.columns([2, 1])
    with col_m1:
      df_prov = (
          df_cobertura.groupby("provincia")
          .size()
          .reset_index(name="cantidad")
      )
      df_prov["porcentaje"] = (
          df_prov["cantidad"] / df_prov["cantidad"].sum() * 100
      )
      df_prov = df_prov.sort_values("cantidad", ascending=True)
      fig_map = px.bar(
          df_prov,
          x="cantidad",
          y="provincia",
          orientation="h",
          color="cantidad",
          color_continuous_scale="Blues",
          text="cantidad",
          custom_data=["porcentaje"],
          title="Registros por provincia",
      )
      fig_map.update_traces(
          texttemplate="%{x:,.0f}",
          textposition="outside",
          cliponaxis=False,
          hovertemplate=(
              "%{y}<br>Registros: %{x:,.0f}"
              "<br>Participación: %{customdata[0]:.1f}%<extra></extra>"
          ),
      )
      fig_map.update_layout(
          plot_bgcolor="white",
          paper_bgcolor="white",
          height=max(420, len(df_prov) * 32),
          margin=dict(t=55, b=35, l=20, r=55),
          coloraxis_showscale=False,
          xaxis_title="Cantidad de registros",
          yaxis_title="",
      )
      fig_map.update_yaxes(autorange="reversed")
      st.plotly_chart(fig_map, use_container_width=True)
    with col_m2:
      st.markdown("### Resumen por Provincia")
      st.dataframe(
          df_prov.sort_values(by="cantidad", ascending=False),
          use_container_width=True,
          hide_index=True,
      )

with tab3:
  st.subheader("Análisis por Área Operativa y Especialidades")
  if not df_f.empty:
    col_a, col_b = st.columns(2)
    with col_a:
      df_area = (
          df_f.groupby("area_operativa").size().reset_index(name="total")
      )
      fig_pie = px.pie(
          df_area,
          names="area_operativa",
          values="total",
          hole=0.4,
          color_discrete_sequence=px.colors.qualitative.Bold,
      )
      st.plotly_chart(fig_pie, use_container_width=True)
    with col_b:
      df_curso = (
          df_f.groupby("curso")
          .size()
          .reset_index(name="total")
          .sort_values(by="total", ascending=False)
          .head(10)
      )
      fig_bar = px.bar(
          df_curso,
          x="total",
          y="curso",
          orientation="h",
          color_discrete_sequence=["#0EA5E9"],
      )
      fig_bar.update_layout(yaxis=dict(autorange="reversed"))
      st.plotly_chart(fig_bar, use_container_width=True)
    df_area_condicion = (
        df_f.groupby(["area_operativa", "condicion"], dropna=False)
        .size()
        .reset_index(name="registros")
    )
    fig_area_condicion = px.bar(
        df_area_condicion,
        x="area_operativa",
        y="registros",
        color="condicion",
        barmode="stack",
        title="Resultados por área operativa",
    )
    st.plotly_chart(fig_area_condicion, use_container_width=True)

with tab4:
  st.subheader("Demanda de cursos y tasa de graduación")
  df_demanda_periodo, _, _ = filtrar_por_periodo(df_f, "demanda")
  if not df_demanda_periodo.empty:
    df_demanda = (
        df_demanda_periodo.groupby("curso")
        .agg(
            total=("curso", "size"),
            graduados=("es_graduado", "sum"),
        )
        .reset_index()
    )
    df_demanda["tasa_graduacion"] = (
        df_demanda["graduados"] / df_demanda["total"] * 100
    )
    cantidad_cursos = st.selectbox(
        "Cursos a mostrar",
        [10, 15, 20, 30],
        index=1,
        key="demanda_cantidad_cursos",
    )
    df_demanda_top = df_demanda.nlargest(cantidad_cursos, "total")
    col_demanda, col_cumplimiento = st.columns(2)
    with col_demanda:
      fig_demanda = px.bar(
          df_demanda_top.sort_values("total"),
          x="total",
          y="curso",
          orientation="h",
          title="15 cursos con más registros",
          labels={"total": "Registros", "curso": "Curso"},
          color="total",
          color_continuous_scale="Blues",
      )
      fig_demanda.update_layout(
          height=max(430, len(df_demanda_top) * 30),
          coloraxis_showscale=False,
          xaxis_title="Registros",
          yaxis_title="",
      )
      st.plotly_chart(fig_demanda, use_container_width=True)
    with col_cumplimiento:
      fig_cumplimiento = px.bar(
          df_demanda_top.sort_values("tasa_graduacion"),
          x="tasa_graduacion",
          y="curso",
          orientation="h",
          title="Graduación por curso (entre los 15 de mayor demanda)",
          labels={
              "tasa_graduacion": "Graduados (%)",
              "curso": "Curso",
          },
          range_x=[0, 100],
          color="tasa_graduacion",
          color_continuous_scale="Teal",
          text="tasa_graduacion",
      )
      fig_cumplimiento.update_traces(
          texttemplate="%{x:.1f}%",
          textposition="outside",
          cliponaxis=False,
      )
      fig_cumplimiento.update_layout(
          height=max(430, len(df_demanda_top) * 30),
          coloraxis_showscale=False,
          yaxis_title="",
      )
      st.plotly_chart(fig_cumplimiento, use_container_width=True)
    df_modalidad = (
        df_demanda_periodo.groupby(["modalidad", "condicion"], dropna=False)
        .size()
        .reset_index(name="registros")
    )
    fig_modalidad = px.bar(
        df_modalidad,
        x="modalidad",
        y="registros",
        color="condicion",
        barmode="group",
        title="Resultados por modalidad",
    )
    st.plotly_chart(fig_modalidad, use_container_width=True)
    st.caption(
        "La tasa se calcula como graduados dividido para todos los registros "
        "del curso; no representa una cohorte si los periodos son distintos."
    )
  else:
    st.info("No hay registros con los filtros seleccionados.")

with tab5:
  st.subheader("Indicadores y trayectoria del curso seleccionado")
  cursos_curso = sorted(df_f["curso"].dropna().unique().tolist())
  if cursos_curso:
    curso_detalle = st.selectbox(
        "Selecciona un curso",
        cursos_curso,
        key="analisis_curso",
    )
    df_curso_detalle = df_f[df_f["curso"] == curso_detalle]
    cantidad_curso = len(df_curso_detalle)
    graduados_curso = int(df_curso_detalle["es_graduado"].sum())
    tasa_curso = (
        graduados_curso / cantidad_curso * 100 if cantidad_curso else 0
    )
    sin_dni_curso = int((df_curso_detalle["estado_dni"] == "Sin DNI").sum())
    tasa_sin_dni_curso = (
        sin_dni_curso / cantidad_curso * 100 if cantidad_curso else 0
    )
    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    kpi1.metric("Registros", f"{cantidad_curso:,}")
    kpi2.metric("Graduados", f"{graduados_curso:,}")
    kpi3.metric("Tasa de graduación", f"{tasa_curso:.1f}%")
    kpi4.metric(
        "Registros sin DNI",
        f"{sin_dni_curso:,}",
        f"{tasa_sin_dni_curso:.1f}%",
    )

    col_historia, col_provincia = st.columns(2)
    with col_historia:
      df_historia_curso = (
          df_curso_detalle[df_curso_detalle["anio"] > 2000]
          .groupby("anio")
          .size()
          .reset_index(name="registros")
      )
      if not df_historia_curso.empty:
        fig_historia_curso = px.line(
            df_historia_curso,
            x="anio",
            y="registros",
            markers=True,
            title=f"Evolución anual: {curso_detalle}",
        )
        st.plotly_chart(fig_historia_curso, use_container_width=True)
      else:
        st.info("No hay años válidos para graficar este curso.")
    with col_provincia:
      df_provincia_curso = (
          df_curso_detalle.groupby("provincia")
          .size()
          .reset_index(name="registros")
          .nlargest(10, "registros")
      )
      fig_provincia_curso = px.bar(
          df_provincia_curso.sort_values("registros"),
          x="registros",
          y="provincia",
          orientation="h",
          title="Principales provincias",
      )
      st.plotly_chart(fig_provincia_curso, use_container_width=True)

    df_modalidad_curso = (
        df_curso_detalle.groupby(["modalidad", "condicion"], dropna=False)
        .size()
        .reset_index(name="registros")
    )
    fig_modalidad_curso = px.bar(
        df_modalidad_curso,
        x="modalidad",
        y="registros",
        color="condicion",
        barmode="group",
        title="Resultados por modalidad del curso",
    )
    st.plotly_chart(fig_modalidad_curso, use_container_width=True)
  else:
    st.info("No hay cursos disponibles con los filtros seleccionados.")

with tab6:
  st.subheader("🔮 Modelo Predictivo y Proyección de Titulaciones")
  df_proyeccion = df_f[df_f["es_graduado"] & (df_f["anio"] > 2000)].copy()
  anios_proyeccion = sorted(df_proyeccion["anio"].unique().tolist())
  if anios_proyeccion:
    controles_proyeccion = st.columns(4)
    with controles_proyeccion[0]:
      if len(anios_proyeccion) > 1:
        clave_rango = "proyeccion_rango_anios"
        rango_actual = st.session_state.get(clave_rango)
        if (
            not rango_actual
            or rango_actual[0] not in anios_proyeccion
            or rango_actual[1] not in anios_proyeccion
        ):
          st.session_state[clave_rango] = (
              anios_proyeccion[0],
              anios_proyeccion[-1],
          )
        rango_anios = st.select_slider(
            "Rango histórico",
            options=anios_proyeccion,
            value=(anios_proyeccion[0], anios_proyeccion[-1]),
            key=clave_rango,
        )
        anio_inicio, anio_fin = rango_anios
      else:
        anio_inicio = anio_fin = anios_proyeccion[0]
        st.metric("Año disponible", anio_inicio)
    with controles_proyeccion[1]:
      meses_proyeccion = sorted(
          int(mes)
          for mes in df_proyeccion["mes"].dropna().unique()
          if 1 <= int(mes) <= 12
      )
      opciones_meses_proyeccion = ["Todos"] + meses_proyeccion
      if (
          st.session_state.get("proyeccion_mes", "Todos")
          not in opciones_meses_proyeccion
      ):
        st.session_state["proyeccion_mes"] = "Todos"
      mes_proyeccion = st.selectbox(
          "Mes para analizar",
          opciones_meses_proyeccion,
          format_func=lambda valor: (
              "Todos los meses"
              if valor == "Todos"
              else NOMBRES_MESES.get(valor, str(valor))
          ),
          key="proyeccion_mes",
      )
    with controles_proyeccion[2]:
      modalidades_proyeccion = ["Todas"] + sorted(
          df_proyeccion["modalidad"].dropna().unique().tolist()
      )
      if (
          st.session_state.get("proyeccion_modalidad", "Todas")
          not in modalidades_proyeccion
      ):
        st.session_state["proyeccion_modalidad"] = "Todas"
      modalidad_proyeccion = st.selectbox(
          "Modalidad",
          modalidades_proyeccion,
          key="proyeccion_modalidad",
      )
    with controles_proyeccion[3]:
      cursos_proyeccion = ["Todos"] + sorted(
          df_proyeccion["curso"].dropna().unique().tolist()
      )
      if (
          st.session_state.get("proyeccion_curso", "Todos")
          not in cursos_proyeccion
      ):
        st.session_state["proyeccion_curso"] = "Todos"
      curso_proyeccion = st.selectbox(
          "Curso",
          cursos_proyeccion,
          key="proyeccion_curso",
      )
    df_proyeccion = df_proyeccion[
        df_proyeccion["anio"].between(anio_inicio, anio_fin)
    ]
    if mes_proyeccion != "Todos":
      df_proyeccion = df_proyeccion[
          df_proyeccion["mes"] == mes_proyeccion
      ]
    if modalidad_proyeccion != "Todas":
      df_proyeccion = df_proyeccion[
          df_proyeccion["modalidad"] == modalidad_proyeccion
      ]
    if curso_proyeccion != "Todos":
      df_proyeccion = df_proyeccion[
          df_proyeccion["curso"] == curso_proyeccion
      ]
    df_p = (
        df_proyeccion.groupby("anio")
        .size()
        .reset_index(name="total")
    )
    horizonte = st.slider(
        "Años a proyectar",
        min_value=1,
        max_value=10,
        value=5,
        key="proyeccion_horizonte",
    )
    if len(df_p) > 3:
      X = df_p[["anio"]]
      y = df_p["total"]
      model = LinearRegression()
      model.fit(X, y)
      ultimo_anio = int(df_p["anio"].max())
      df_anios_futuros = pd.DataFrame(
          {
              "anio": np.arange(
                  ultimo_anio + 1, ultimo_anio + horizonte + 1
              )
          }
      )
      predicciones = model.predict(df_anios_futuros)

      df_futuro = pd.DataFrame(
          {
              "anio": df_anios_futuros["anio"],
              "total": np.maximum(predicciones, 0),
          }
      )

      fig_pred = px.line(
          df_p,
          x="anio",
          y="total",
          markers=True,
          title="Tendencia Histórica y Proyección a Futuro",
      )
      fig_pred.add_trace(
          go.Scatter(
              x=[df_p["anio"].iloc[-1], *df_futuro["anio"].tolist()],
              y=[df_p["total"].iloc[-1], *df_futuro["total"].tolist()],
              mode="lines+markers",
              name="Proyección",
              line=dict(dash="dash", color="red"),
          )
      )
      fig_pred.update_layout(
          xaxis_title="Año",
          yaxis_title="Graduados",
          hovermode="x unified",
      )
      st.plotly_chart(fig_pred, use_container_width=True)
      st.success(
          "Estimación lineal según los filtros seleccionados; es una referencia"
          " y no una garantía de resultados futuros."
      )
    else:
      st.warning(
          "Se requieren al menos cuatro años con registros para ejecutar la"
          " proyección. Amplía el rango o cambia los filtros."
      )
  else:
    st.info("No hay registros de graduados con año válido para proyectar.")

with tab7:
  st.subheader("Auditoría de DNI y calidad de registros")
  st.caption(
      "“Con DNI” indica un "
      "formato de 10 dígitos; no valida el dígito verificador oficial."
  )
  alcance_auditoria = st.radio(
      "Datos para la auditoría:",
      ["Toda la base de datos", "Aplicar filtros globales"],
      horizontal=True,
      key="auditoria_alcance",
  )
  df_auditoria = (
      df_raw
      if alcance_auditoria == "Toda la base de datos"
      else df_f
  )
  total_auditoria = len(df_auditoria)
  sin_dni = int((df_auditoria["estado_dni"] == "Sin DNI").sum())
  dni_irregular = int((df_auditoria["estado_dni"] == "DNI irregular").sum())
  con_dni = int((df_auditoria["estado_dni"] == "Con DNI").sum())
  df_con_info_completa = df_auditoria[
      mascara_informacion_completa(df_auditoria)
  ]
  df_con_info_completa_total = df_raw[
      mascara_informacion_completa(df_raw)
  ]
  ids_con_varios_registros = int(
      (
          df_auditoria.loc[
              df_auditoria["estado_dni"] == "Con DNI",
              "cedula_limpia",
          ]
          .value_counts()
          > 1
      ).sum()
  )

  (
      col_sin_dni,
      col_irregular,
      col_con_dni,
      col_completos,
      col_repetidos,
  ) = st.columns(5)
  col_sin_dni.metric(
      "Registros sin DNI",
      f"{sin_dni:,}",
      f"{sin_dni / total_auditoria * 100:.1f}%" if total_auditoria else "0%",
  )
  col_irregular.metric(
      "DNI con formato irregular",
      f"{dni_irregular:,}",
      (
          f"{dni_irregular / total_auditoria * 100:.1f}%"
          if total_auditoria
          else "0%"
      ),
  )
  col_con_dni.metric("Formato de DNI completo", f"{con_dni:,}")
  col_completos.metric(
      "DNI e información completa",
      f"{len(df_con_info_completa):,}",
  )
  col_repetidos.metric("DNI en varios registros", f"{ids_con_varios_registros:,}")
  st.caption(
      "Un DNI asociado a varios registros puede corresponder a varios cursos "
      "o reingresos; no implica por sí solo un duplicado. Los conteos son de "
      "registros. Para considerar la información completa se requiere DNI "
      "válido, nombres, matrícula, curso, modalidad y año o fecha."
  )

  if df_auditoria.empty:
    st.info(
        "Los filtros globales no encontraron registros. Selecciona "
        "«Toda la base de datos» para ver los gráficos."
    )

  st.markdown("#### Descargar registros")
  st.caption(
      "Las descargas usan toda la base de datos, independientemente de los "
      "filtros aplicados al tablero."
  )

  # CORRECCIÓN DEFINITIVA DE LOS SUBJUNTO DE EXPORTACIÓN
  df_todos_export = df_raw.copy()
  df_sin_dni_export = df_raw[df_raw["estado_dni"] == "Sin DNI"].copy()
  df_completos_export = df_raw[mascara_informacion_completa(df_raw)].copy()

  opciones_descarga_bruta = {
      "todos": ("Todos los registros", df_todos_export),
      "sin_dni": ("Registros sin DNI", df_sin_dni_export),
      "completos": ("DNI e información completa", df_completos_export),
  }

  opciones_descarga = {
      clave: (
          titulo,
          df_original.loc[datos.index].assign(
              cedula_limpia=datos["cedula_limpia"],
              estado_dni=datos["estado_dni"],
          ),
      )
      for clave, (titulo, datos) in opciones_descarga_bruta.items()
  }
  mostrar_botones_descarga_auditoria(opciones_descarga)

  st.markdown("#### Distribución del estado del DNI")
  df_estado_dni = (
      df_auditoria["estado_dni"]
      .value_counts()
      .reindex(["Con DNI", "DNI irregular", "Sin DNI"], fill_value=0)
      .rename_axis("Estado del DNI")
      .reset_index(name="Registros")
  )
  fig_estado_dni = px.bar(
      df_estado_dni,
      x="Estado del DNI",
      y="Registros",
      color="Estado del DNI",
      text="Registros",
      title="Registros según estado del DNI",
      category_orders={
          "Estado del DNI": ["Con DNI", "DNI irregular", "Sin DNI"]
      },
  )
  fig_estado_dni.update_layout(showlegend=False)
  st.plotly_chart(
      fig_estado_dni,
      use_container_width=True,
      key="auditoria_grafico_estado_dni",
  )

  if not df_auditoria.empty:
    df_auditoria_curso = (
        df_auditoria.assign(
            curso=df_auditoria["curso"].fillna("Sin curso")
        ).groupby("curso")
        .agg(
            total=("estado_dni", "size"),
            sin_dni=("estado_dni", lambda valores: (valores == "Sin DNI").sum()),
            irregulares=(
                "estado_dni",
                lambda valores: (valores == "DNI irregular").sum(),
            ),
            con_dni=("estado_dni", lambda valores: (valores == "Con DNI").sum()),
        )
        .reset_index()
    )
    df_auditoria_curso["sin_dni_pct"] = (
        df_auditoria_curso["sin_dni"] / df_auditoria_curso["total"] * 100
    )
    df_auditoria_curso["irregulares_pct"] = (
        df_auditoria_curso["irregulares"] / df_auditoria_curso["total"] * 100
    )
    df_auditoria_curso["alertas"] = (
        df_auditoria_curso["sin_dni"] + df_auditoria_curso["irregulares"]
    )

    col_auditoria_cursos, col_tendencia_dni = st.columns(2)
    with col_auditoria_cursos:
      df_alertas_top = df_auditoria_curso.nlargest(15, "alertas")
      df_alertas_grafico = df_alertas_top.melt(
          id_vars="curso",
          value_vars=["sin_dni", "irregulares"],
          var_name="tipo",
          value_name="registros",
      )
      df_alertas_grafico["tipo"] = df_alertas_grafico["tipo"].map({
          "sin_dni": "Sin DNI",
          "irregulares": "DNI irregular",
      })
      fig_auditoria_cursos = px.bar(
          df_alertas_grafico,
          x="registros",
          y="curso",
          color="tipo",
          barmode="stack",
          orientation="h",
          title="Registros por revisar en los 15 cursos con más alertas",
      )
      fig_auditoria_cursos.update_layout(yaxis=dict(autorange="reversed"))
      st.plotly_chart(fig_auditoria_cursos, use_container_width=True)
    with col_tendencia_dni:
      df_tendencia_dni = df_auditoria[
          pd.to_numeric(df_auditoria["anio"], errors="coerce") > 2000
      ]
      if not df_tendencia_dni.empty:
        df_tendencia_dni = (
            df_tendencia_dni.groupby(["anio", "estado_dni"])
            .size()
            .unstack(fill_value=0)
        )
        for categoria in ["Sin DNI", "DNI irregular", "Con DNI"]:
          if categoria not in df_tendencia_dni.columns:
            df_tendencia_dni[categoria] = 0
        df_tendencia_dni["total"] = df_tendencia_dni[
            ["Sin DNI", "DNI irregular", "Con DNI"]
        ].sum(axis=1)
        df_tendencia_dni["sin_dni_pct"] = (
            df_tendencia_dni["Sin DNI"] / df_tendencia_dni["total"] * 100
        )
        df_tendencia_dni["irregular_pct"] = (
            df_tendencia_dni["DNI irregular"]
            / df_tendencia_dni["total"]
            * 100
        )
        df_tendencia_dni = (
            df_tendencia_dni[["sin_dni_pct", "irregular_pct"]]
            .reset_index()
            .melt(
                id_vars="anio",
                var_name="tipo",
                value_name="porcentaje",
            )
        )
        df_tendencia_dni["tipo"] = df_tendencia_dni["tipo"].map({
            "sin_dni_pct": "Sin DNI",
            "irregular_pct": "DNI irregular",
        })
        fig_tendencia_dni = px.line(
            df_tendencia_dni,
            x="anio",
            y="porcentaje",
            color="tipo",
            markers=True,
            title="Porcentaje de alertas de DNI por año",
            labels={"anio": "Año", "porcentaje": "Registros (%)"},
        )
        fig_tendencia_dni.update_layout(yaxis_range=[0, 100])
        st.plotly_chart(fig_tendencia_dni, use_container_width=True)
      else:
        st.info("No hay años válidos para mostrar la tendencia de DNI.")

    df_auditoria_tabla = df_auditoria_curso.rename(columns={
        "curso": "Curso",
        "total": "Registros",
        "sin_dni": "Sin DNI",
        "sin_dni_pct": "Sin DNI (%)",
        "irregulares": "DNI irregular",
        "irregulares_pct": "Irregular (%)",
        "con_dni": "Con DNI",
        "alertas": "Total por revisar",
    })
    st.markdown("#### Resumen de auditoría por curso")
    st.dataframe(
        df_auditoria_tabla.sort_values(
            "Total por revisar",
            ascending=False,
        )[[
            "Curso",
            "Registros",
            "Sin DNI",
            "Sin DNI (%)",
            "DNI irregular",
            "Irregular (%)",
            "Con DNI",
        ]],
        use_container_width=True,
        hide_index=True,
    )
  else:
    st.info("No hay registros con los filtros seleccionados.")

with tab8:
  st.subheader("Ciclos de participación y reingresos potenciales")
  st.caption(
      "Análisis agregado de registros con DNI en formato de 10 dígitos y año "
      "válido. Se considera reingreso potencial si vuelve a aparecer tras al "
      "menos un año calendario sin registros; no confirma reincorporación."
  )
  df_ciclos = df_f[
      (df_f["estado_dni"] == "Con DNI") & (df_f["anio"] > 2000)
  ].copy()
  if not df_ciclos.empty:
    df_anios_por_dni = df_ciclos.groupby("cedula_limpia")["anio"].agg(
        lambda valores: sorted(set(valores))
    )
    df_personas_ciclo = (
        df_ciclos.groupby("cedula_limpia")
        .agg(
            primer_anio=("anio", "min"),
            ultimo_anio=("anio", "max"),
            anios_distintos=("anio", "nunique"),
            cursos=("curso", "nunique"),
        )
    )
    df_personas_ciclo["reingreso_potencial"] = df_anios_por_dni.apply(
        lambda anios: any(
            anios[indice] - anios[indice - 1] >= 2
            for indice in range(1, len(anios))
        )
    )
    ids_multianuales = int((df_personas_ciclo["anios_distintos"] > 1).sum())
    ids_reingreso = int(df_personas_ciclo["reingreso_potencial"].sum())
    ids_multicurso = int((df_personas_ciclo["cursos"] > 1).sum())

    col_identificados, col_multianuales, col_reingreso, col_multicurso = (
        st.columns(4)
    )
    col_identificados.metric(
        "DNI identificados",
        f"{len(df_personas_ciclo):,}",
    )
    col_multianuales.metric(
        "Registrados en más de un año",
        f"{ids_multianuales:,}",
    )
    col_reingreso.metric(
        "Reingresos potenciales",
        f"{ids_reingreso:,}",
    )
    col_multicurso.metric(
        "Registrados en varios cursos",
        f"{ids_multicurso:,}",
    )

    col_anual, col_curso_reingreso = st.columns(2)
    with col_anual:
      df_personas_anio = (
          df_ciclos.drop_duplicates(["cedula_limpia", "anio"])
          .groupby("anio")
          .size()
          .reset_index(name="personas")
      )
      fig_personas_anio = px.line(
          df_personas_anio,
          x="anio",
          y="personas",
          markers=True,
          title="DNI identificados por año (sin duplicar por registro)",
          labels={"anio": "Año", "personas": "DNI únicos"},
      )
      st.plotly_chart(fig_personas_anio, use_container_width=True)
    with col_curso_reingreso:
      ids_con_reingreso = df_personas_ciclo.index[
          df_personas_ciclo["reingreso_potencial"]
      ]
      df_cursos_reingreso = (
          df_ciclos[df_ciclos["cedula_limpia"].isin(ids_con_reingreso)]
          .groupby("curso")["cedula_limpia"]
          .nunique()
          .reset_index(name="dni_identificados")
          .nlargest(10, "dni_identificados")
          .sort_values("dni_identificados")
      )
      if not df_cursos_reingreso.empty:
        fig_cursos_reingreso = px.bar(
            df_cursos_reingreso,
            x="dni_identificados",
            y="curso",
            orientation="h",
            title="Cursos con más DNI de reingreso potencial",
            labels={
                "dni_identificados": "DNI identificados",
                "curso": "Curso",
            },
        )
        st.plotly_chart(fig_cursos_reingreso, use_container_width=True)
      else:
        st.info("No se identificaron intervalos de reingreso potencial.")
  else:
    st.info("No hay DNI y años válidos para analizar ciclos.")

with tab9:
  st.subheader("📋 Explorador General de Registros y Base de Datos")
  st.dataframe(
      df_f[[
          "cedula_limpia",
          "nombres",
          "provincia",
          "curso",
          "modalidad",
          "anio",
          "condicion",
      ]],
      use_container_width=True,
  )