from calendar import monthrange
from datetime import datetime
from hashlib import sha256
from html import escape
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
from sqlalchemy.exc import SQLAlchemyError
import streamlit as st
import unicodedata

from auth import crear_gestor_cookies, render_login, cerrar_sesion
from branding import LOGO_DATA_URI, LOGO_NAVY_DATA_URI, LOGO_PATH
from cursos import normalizar_curso
from duplicados_trayectoria import (
    resumir_codigos_impresion,
    resumir_trayectoria_por_jerarquia,
)
from db import (
    COLUMNAS_REGISTRO_IMPORTACION,
    actualizar_registros_ciudadano,
    get_engine,
    insertar_registros_importados,
)
from estadisticas_areas import resumir_areas_especialidades
from estadisticas_historicas import (
    calcular_crecimiento_interanual,
    resumir_evolucion,
)
from estadisticas_provinciales import (
    calcular_tasas_graduacion_provinciales,
    comparar_registros_provinciales,
)
from importacion import MAX_TAMANO_IMPORTACION, leer_archivo_importacion
from geografia import estimar_zonas_cantonales
from modalidades import normalizar_modalidad
from planificacion_ascensos import calcular_candidatos_ascenso
from preparacion_datos import mapear_valores_unicos
from vedas_atun import (
    URL_CALENDARIO_OFICIAL,
    URL_PDF_CALENDARIO_2025,
    calcular_cursos_en_vedas_atun,
    obtener_periodos_veda_atun,
)

st.set_page_config(
    page_title="EPESPO - Suite Analítica y Estratégica Marítima",
    page_icon=str(LOGO_PATH),
    layout="wide",
    initial_sidebar_state="collapsed",
)


def mostrar_indicador_carga(mensaje):
  indicador = st.empty()
  indicador.markdown(
      f"""
      <style>
      @keyframes epespo-anchor-spin {{
        to {{ transform: rotate(360deg); }}
      }}
      .epespo-analysis-loader {{
        position: fixed;
        top: 50%;
        left: 50%;
        z-index: 999999;
        display: flex;
        align-items: center;
        gap: 14px;
        padding: 14px 20px;
        transform: translate(-50%, -50%);
        border: 1px solid #dbeafe;
        border-radius: 14px;
        background: rgba(255, 255, 255, 0.96);
        box-shadow: 0 8px 28px rgba(15, 23, 42, 0.18);
        color: #1e3a8a;
        font-weight: 600;
      }}
      .epespo-analysis-loader__ring {{
        display: grid;
        width: 42px;
        height: 42px;
        place-items: center;
        border: 3px solid #bfdbfe;
        border-top-color: #0284c7;
        border-radius: 50%;
        animation: epespo-anchor-spin 0.9s linear infinite;
        font-size: 21px;
      }}
      @media (prefers-reduced-motion: reduce) {{
        .epespo-analysis-loader__ring {{ animation: none; }}
      }}
      </style>
      <div class="epespo-analysis-loader" role="status" aria-live="polite">
        <span class="epespo-analysis-loader__ring">⚓</span>
        <span>{escape(mensaje)}</span>
      </div>
      """,
      unsafe_allow_html=True,
  )
  return indicador


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
@st.cache_data(ttl=600, show_spinner=False)
def cargar_datos_completos():
  try:
    return pd.read_sql(
        "SELECT * FROM graduados_epespo",
        con=engine,
    )
  except Exception as e:
    st.error(f"Error al consultar la base de datos: {e}")
    st.stop()


@st.cache_data(ttl=600, max_entries=3)
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
  
  for clave, (titulo, df) in opciones_descarga.items():
    with st.container(border=True):
      col_info, col_csv, col_excel = st.columns([2, 1, 1])
      
      with col_info:
        st.markdown(f"**{titulo}**")
        st.caption(f"Total de registros disponibles: **{len(df):,}**")
        
      with col_csv:
        st.markdown("")
        st.download_button(
            "⬇️ Descargar CSV",
            data=df.to_csv(index=False).encode("utf-8-sig"),
            file_name=f"{nombres_archivo[clave]}.csv",
            mime="text/csv",
            use_container_width=True,
            key=f"auditoria_boton_{clave}_csv",
        )
        
      with col_excel:
        st.markdown("")
        try:
          datos_excel = generar_excel_auditoria(df)
          st.download_button(
              "⬇️ Descargar Excel",
              data=datos_excel,
              file_name=f"{nombres_archivo[clave]}.xlsx",
              mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
              use_container_width=True,
              key=f"auditoria_boton_{clave}_excel",
          )
        except (
            IllegalCharacterError,
            ValueError,
            TypeError,
            OSError,
        ) as error:
          st.error(f"Error al generar Excel: {error}")


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
        justify-content: flex-start;
        gap: 20px;
    }
    .hero-logo { width: 96px; height: auto; flex-shrink: 0; }
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

    /* Permitir desplazamiento horizontal fluido en la lista de pestañas */
    .stTabs [data-baseweb="tab-list"] { 
        background: #E7EEF7; 
        border-radius: 13px; 
        padding: 6px; 
        gap: 4px; 
        overflow-x: auto;
        flex-wrap: nowrap;
        scrollbar-width: thin;
    }
    .stTabs [data-baseweb="tab"] { 
        border-radius: 9px; 
        padding: 10px 14px; 
        color: #46627F; 
        font-weight: 600; 
        white-space: nowrap;
    }
    .stTabs [data-baseweb="tab"][aria-selected="true"] { background: #FFFFFF !important; color: #0759B8 !important; box-shadow: 0 2px 8px rgba(15,54,102,.08); }
    
    div[data-testid="stPlotlyChart"] { background: #FFFFFF; border: 1px solid #E4EBF4; border-radius: 15px; padding: 7px; box-shadow: 0 3px 12px rgba(15,54,102,.025); }
    div[data-testid="stDataFrame"] { border: 1px solid #E3EAF4; border-radius: 12px; overflow: hidden; }
    .sidebar-brand {
        padding: 10px 12px 4px;
        margin-bottom: 14px;
        border: 1px solid #D7E7F5;
        border-radius: 14px;
        background: linear-gradient(145deg, #E8F3FB, #FFFFFF);
    }
    .sidebar-brand img { display: block; width: min(150px, 100%); height: auto; margin: 0 auto; }
    .sidebar-user-card { background: #0A2540; color: white; padding: 12px 16px; border-radius: 10px; margin-bottom: 14px; }
    @media (max-width: 640px) {
        .hero-banner { padding: 18px; gap: 14px; }
        .hero-logo { width: 68px; }
        .hero-title { font-size: 18px; }
    }
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


# =============================================================
# CARGA Y PROCESAMIENTO ESTRICTO DE DATOS
# =============================================================
@st.cache_data(
    ttl=600,
    show_spinner="Conectando y preparando los datos...",
)
def cargar_datos_preparados():
  df_raw = cargar_datos_completos()
  if df_raw.empty:
    return df_raw, df_raw

  df_original = df_raw.copy()
  df_raw["cedula_limpia"] = df_raw["cedula"].map(limpiar_dni)
  df_raw["estado_dni"] = df_raw["cedula"].map(clasificar_dni)
  df_raw["curso"] = mapear_valores_unicos(
      df_raw["curso"],
      normalizar_curso,
  )
  df_raw["modalidad"] = mapear_valores_unicos(
      df_raw["modalidad"],
      normalizar_modalidad,
  )
  df_raw["provincia"] = mapear_valores_unicos(
      df_raw["provincia"],
      normalizar_provincia,
  )
  df_raw["es_graduado"] = (
      df_raw["condicion"]
      .fillna("")
      .astype(str)
      .str.strip()
      .str.casefold()
      .eq("graduado")
  )
  df_raw["area_operativa"] = mapear_valores_unicos(
      df_raw["curso"],
      clasificar_area_operativa,
  )
  df_raw["escala_nautica"] = mapear_valores_unicos(
      df_raw["curso"],
      clasificar_escala_nautica,
  )
  df_raw["zona_canton"] = estimar_zonas_cantonales(
      df_raw["cedula_limpia"],
      df_raw["provincia"],
  )
  impresion_fuente = df_raw.get(
      "impresion",
      pd.Series(index=df_raw.index, dtype=object),
  )
  impresion = pd.to_numeric(impresion_fuente, errors="coerce")
  impresion = impresion.replace([np.inf, -np.inf], np.nan).fillna(0)
  codigos_impresion = np.trunc(
      impresion.to_numpy(dtype=float)
  ).astype("int64")
  df_raw["tipo_tramite"] = np.select(
      [
          codigos_impresion == 2,
          codigos_impresion == 1,
          codigos_impresion == 0,
      ],
      [
          "Duplicado (Cód. 2)",
          "Recién Graduado (Cód. 1)",
          "Estudiante Normal (Cód. 0)",
      ],
      default="Estudiante Normal (Cód. 0)",
  )
  df_raw["anio"] = (
      pd.to_numeric(df_raw["anio"], errors="coerce").fillna(0).astype(int)
  )
  df_raw["mes"] = pd.to_numeric(df_raw["mes"], errors="coerce")
  return df_original, df_raw


df_original, df_raw = cargar_datos_preparados()


def mostrar_importacion_sidebar():
  resultado_importacion = st.session_state.pop(
      "_resultado_importacion",
      None,
  )
  if resultado_importacion:
    st.sidebar.success(resultado_importacion)

  if st.session_state.get("rol") != "admin":
    return

  with st.sidebar.expander("📥 Actualizar base de datos", expanded=False):
    st.caption(
        "Agrega filas nuevas desde CSV o Excel. No borra ni modifica "
        "registros existentes; omite duplicados idénticos."
    )
    st.download_button(
        "Descargar plantilla CSV",
        data=(
            ",".join(COLUMNAS_REGISTRO_IMPORTACION) + "\n"
        ).encode("utf-8-sig"),
        file_name="plantilla_registros_epespo.csv",
        mime="text/csv",
        use_container_width=True,
        key="descargar_plantilla_importacion",
    )
    archivo = st.file_uploader(
        "Selecciona un archivo CSV o Excel (.xlsx)",
        type=["csv", "xlsx"],
        key="archivo_importacion_registros",
    )
    if archivo is None:
      st.session_state.pop("_archivo_importacion_cache_digest", None)
      st.session_state.pop("_archivo_importacion_cache_df", None)
      return

    contenido_archivo = archivo.getvalue()
    if len(contenido_archivo) > MAX_TAMANO_IMPORTACION:
      st.error("El archivo supera el límite de 10 MB.")
      return

    hash_archivo = sha256(contenido_archivo).hexdigest()
    if st.session_state.get("_archivo_importado_digest") == hash_archivo:
      st.info("Este archivo ya fue procesado en esta sesión.")
      return
    if (
        st.session_state.get("_archivo_importacion_cache_digest")
        == hash_archivo
    ):
      df_importacion = st.session_state["_archivo_importacion_cache_df"]
    else:
      try:
        with st.spinner("Leyendo y validando el archivo..."):
          df_importacion = leer_archivo_importacion(archivo)
      except (
          OSError,
          UnicodeDecodeError,
          ValueError,
          pd.errors.ParserError,
      ) as error:
        st.error(f"No se pudo validar el archivo: {error}")
        return
      st.session_state["_archivo_importacion_cache_digest"] = hash_archivo
      st.session_state["_archivo_importacion_cache_df"] = df_importacion

    st.caption(f"Filas válidas para revisar: {len(df_importacion):,}")
    st.dataframe(
        df_importacion.head(5),
        hide_index=True,
        height=180,
    )
    confirmar = st.checkbox(
        "Confirmo agregar solo filas nuevas, sin borrar datos.",
        key=f"confirmar_importacion_{hash_archivo}",
    )
    if st.button(
        "Importar filas nuevas",
        type="primary",
        use_container_width=True,
        disabled=not confirmar,
        key="importar_registros_epespo",
    ):
      try:
        with st.spinner("Validando y guardando los registros..."):
          insertados, duplicados = insertar_registros_importados(
              df_importacion
          )
      except (
          OSError,
          RuntimeError,
          SQLAlchemyError,
          TypeError,
          ValueError,
      ) as error:
        st.error(f"No se pudo actualizar la base de datos: {error}")
      else:
        st.session_state["_archivo_importado_digest"] = hash_archivo
        st.session_state.pop("_archivo_importacion_cache_digest", None)
        st.session_state.pop("_archivo_importacion_cache_df", None)
        st.session_state["_resultado_importacion"] = (
            f"Importación completada: {insertados:,} filas nuevas agregadas; "
            f"{duplicados:,} duplicados idénticos omitidos."
        )
        st.rerun()


# =============================================================
# SIDEBAR / CONTROLES GLOBALES Y FILTROS
# =============================================================
st.sidebar.markdown(
    f'<div class="sidebar-brand"><img src="{LOGO_NAVY_DATA_URI}" alt="Logo EPESPO"></div>',
    unsafe_allow_html=True,
)
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
mostrar_importacion_sidebar()
if df_raw.empty:
  st.warning(
      "No hay registros en la base de datos. Un administrador puede "
      "cargar un archivo desde la barra lateral."
  )
  st.stop()


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
    indicador_busqueda = mostrar_indicador_carga(
        "Buscando información del ciudadano..."
    )
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
          .str.contains(
              ape_sidebar.strip(),
              case=False,
              na=False,
              regex=False,
          )
      ]

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
    indicador_busqueda.empty()

    resultados_principales.caption(
        f"Coincidencias encontradas: {len(coincidencias):,} registros"
    )
    if coincidencias.empty:
      resultados_principales.info(
          "No se encontraron ciudadanos con esos datos."
      )
    else:
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
                  cargar_datos_completos.clear()
                  cargar_datos_preparados.clear()
                  generar_excel_auditoria.clear()
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

df_f_todos_estados = df_f.copy()
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
  df_f_todos_estados = df_f_todos_estados[
      df_f_todos_estados["cedula_limpia"]
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
  df_f_todos_estados = df_f_todos_estados[
      df_f_todos_estados["nombres"]
      .fillna("")
      .astype(str)
      .str.contains(ape_sidebar.strip(), case=False, na=False, regex=False)
  ]

# =============================================================
# BANNER PRINCIPAL
# =============================================================
st.markdown(
    f"""
    <div class="hero-banner">
        <img class="hero-logo" src="{LOGO_DATA_URI}" alt="Logo EPESPO">
        <div>
            <h1 class="hero-title">ESCUELA DE PESCA DEL PACÍFICO ORIENTAL (EPESPO)</h1>
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
# SECCIONES DE NAVEGACIÓN ANALÍTICA (11 SECCIONES)
# =============================================================
secciones_analiticas = [
    "📈 Evolución Histórica",
    "🗺️ Geografía & Cobertura",
    "⚓ Áreas & Especialidades",
    "🔥 Demanda & Cumplimiento",
    "🎓 Análisis por Curso",
    "🔮 Proyección & Tendencias",
    "🔍 Auditoría de Datos",
    "🔄 Ciclos y Reingresos",
    "📊 Duplicados y Trayectoria",
    "⚓ Panel Estratégico de Ascensos y Planificación",
    "🐟 Veda de Atún",
]
seccion_activa = st.selectbox(
    "Sección de análisis:",
    secciones_analiticas,
    key="seccion_analitica",
)
seccion_cambio = (
    st.session_state.get("_seccion_analitica_renderizada") != seccion_activa
)
indicador_carga_seccion = None
if seccion_cambio:
  indicador_carga_seccion = mostrar_indicador_carga(
      "Cargando análisis..."
  )

if seccion_activa == secciones_analiticas[0]:
  st.subheader("Evolución anual de registros y resultados")
  df_historico = df_f_todos_estados[
      df_f_todos_estados["anio"] > 2000
  ].copy()
  rango_evolucion = st.segmented_control(
      "Zoom rápido por periodo",
      [
          "Últimos 5 años",
          "Últimos 10 años",
          "Histórico completo",
          "Post-pandemia (2020–actualidad)",
          "Personalizado",
      ],
      default="Histórico completo",
      key="rango_evolucion_historica",
  )

  anios_disponibles = df_historico["anio"].dropna()
  anio_maximo = (
      int(anios_disponibles.max()) if not anios_disponibles.empty else None
  )
  anio_evolucion = "Todos"
  mes_evolucion = "Todos"
  if rango_evolucion == "Personalizado":
    df_evolucion, anio_evolucion, mes_evolucion = filtrar_por_periodo(
        df_historico,
        "evolucion",
    )
  elif anio_maximo is not None:
    if rango_evolucion == "Últimos 5 años":
      anio_inicio = anio_maximo - 4
      df_evolucion = df_historico[
          df_historico["anio"].between(anio_inicio, anio_maximo)
      ].copy()
    elif rango_evolucion == "Últimos 10 años":
      anio_inicio = anio_maximo - 9
      df_evolucion = df_historico[
          df_historico["anio"].between(anio_inicio, anio_maximo)
      ].copy()
    elif rango_evolucion == "Post-pandemia (2020–actualidad)":
      df_evolucion = df_historico[
          df_historico["anio"].between(2020, anio_maximo)
      ].copy()
    else:
      df_evolucion = df_historico.copy()
  else:
    df_evolucion = df_historico.copy()

  st.caption(
      "La evolución incluye todos los estados para calcular correctamente "
      "graduación y brecha; respeta los demás filtros globales."
  )
  if rango_evolucion != "Personalizado" and anio_maximo is not None:
    st.caption(f"Rango basado en el último año con registros: {anio_maximo}.")

  if anio_evolucion != "Todos" and mes_evolucion == "Todos":
    anio_referencia = int(anio_evolucion)
  elif not df_evolucion.empty:
    anio_referencia = int(df_evolucion["anio"].max())
  else:
    anio_referencia = None

  mes_comparacion = (
      int(mes_evolucion) if mes_evolucion != "Todos" else None
  )
  if anio_referencia is not None:
    (
        registros_actuales,
        registros_anteriores,
        crecimiento_interanual,
    ) = calcular_crecimiento_interanual(
        df_historico,
        anio_referencia,
        mes_comparacion,
    )
  else:
    registros_actuales = 0
    registros_anteriores = 0
    crecimiento_interanual = None

  resumen_anual = resumir_evolucion(df_evolucion, "anio")
  resumen_historico_completo = resumir_evolucion(df_historico, "anio")
  if not resumen_historico_completo.empty:
    anio_mayor_exito = resumen_historico_completo.sort_values(
        ["tasa_graduacion", "periodo"],
        ascending=[False, False],
    ).iloc[0]
  else:
    anio_mayor_exito = None

  kpi_total, kpi_crecimiento, kpi_exito = st.columns(3)
  with kpi_total:
    st.metric("Total acumulado", f"{len(df_evolucion):,}")
  with kpi_crecimiento:
    if crecimiento_interanual is None:
      st.metric(
          "Crecimiento interanual",
          "—",
          (
              f"Sin base para comparar con {anio_referencia - 1}"
              if anio_referencia is not None
              else "Sin datos en el periodo"
          ),
          delta_color="off",
      )
    else:
      st.metric(
          "Crecimiento interanual",
          f"{registros_actuales:,}",
          f"{crecimiento_interanual:+.1f}% vs. {anio_referencia - 1}",
          delta_color="normal",
          help=(
              "Registros del año actual frente al anterior: "
              f"{registros_actuales:,} vs. {registros_anteriores:,}."
          ),
      )
  with kpi_exito:
    if anio_mayor_exito is None:
      st.metric("Año de mayor éxito", "—", "Sin registros", delta_color="off")
    else:
      st.metric(
          "Año de mayor éxito",
          str(int(anio_mayor_exito["periodo"])),
          (
              f"{anio_mayor_exito['tasa_graduacion']:.1f}% · "
              f"{int(anio_mayor_exito['graduados']):,}/"
              f"{int(anio_mayor_exito['registros']):,} registros"
          ),
          delta_color="off",
          help=(
              "Se calcula sobre todo el histórico disponible, "
              "independientemente del zoom seleccionado."
          ),
      )

  if not df_evolucion.empty:
    mostrar_evolucion_mensual = (
        anio_evolucion != "Todos" and mes_evolucion == "Todos"
    )
    if mostrar_evolucion_mensual:
      df_grafico_evolucion = df_evolucion.copy()
      df_grafico_evolucion["periodo"] = df_grafico_evolucion["mes"].map(
          lambda mes: (
              NOMBRES_MESES.get(int(mes), "Mes no registrado")
              if pd.notna(mes)
              else "Mes no registrado"
          )
      )
      resumen_grafico = resumir_evolucion(
          df_grafico_evolucion,
          "periodo",
      )
      resumen_grafico["orden"] = resumen_grafico["periodo"].map(
          {
              mes: indice
              for indice, mes in enumerate(
                  list(NOMBRES_MESES.values()) + ["Mes no registrado"]
              )
          }
      )
      resumen_grafico = resumen_grafico.sort_values("orden")
      eje_x = "Mes"
      titulo_grafico = f"Registros mensuales de {anio_evolucion}"
    else:
      resumen_grafico = resumen_anual
      eje_x = "Año"
      titulo_grafico = (
          "Registros y graduados por año"
          + (
              f" · {NOMBRES_MESES[mes_evolucion]}"
              if mes_evolucion != "Todos"
              else ""
          )
      )

    fig_line = go.Figure()
    fig_line.add_trace(
        go.Scatter(
            x=resumen_grafico["periodo"],
            y=resumen_grafico["registros"],
            name="Total de registros",
            mode="lines+markers",
            line=dict(color="#2563eb", width=3),
            customdata=resumen_grafico[
                ["graduados", "brecha"]
            ].to_numpy(),
            hovertemplate=(
                "%{x}<br>Total: %{y:,}"
                "<br>Graduados: %{customdata[0]:,}"
                "<br>Brecha: %{customdata[1]:,}<extra></extra>"
            ),
        )
    )
    fig_line.add_trace(
        go.Scatter(
            x=resumen_grafico["periodo"],
            y=resumen_grafico["graduados"],
            name="Graduados",
            mode="lines+markers",
            fill="tonexty",
            fillcolor="rgba(244, 63, 94, 0.18)",
            line=dict(color="#16a34a", width=3),
            customdata=resumen_grafico[
                ["brecha", "tasa_graduacion"]
            ].to_numpy(),
            hovertemplate=(
                "%{x}<br>Graduados: %{y:,}"
                "<br>Brecha: %{customdata[0]:,}"
                "<br>Tasa: %{customdata[1]:.1f}%<extra></extra>"
            ),
        )
    )
    fig_line.update_layout(
        title=titulo_grafico,
        plot_bgcolor="white",
        paper_bgcolor="white",
        margin=dict(t=55, b=20, l=20, r=20),
        xaxis_title=eje_x,
        yaxis_title="Registros",
        hovermode="x",
        legend_title_text="Resultados",
    )
    st.plotly_chart(fig_line, use_container_width=True)
    st.caption(
        "El área sombreada muestra la brecha entre registros y graduados; "
        "no representa por sí sola una deserción confirmada."
    )
  else:
    st.info("No hay datos suficientes para mostrar la evolución temporal.")

if seccion_activa == secciones_analiticas[1]:
  st.subheader("Distribución Geográfica y Provincial")
  df_cobertura_total, _, _ = filtrar_por_periodo(
      df_f_todos_estados,
      "cobertura",
  )
  df_cobertura = df_cobertura_total
  if cond_sel == "Solo Graduados (Cumple)":
    df_cobertura = df_cobertura[df_cobertura["es_graduado"]]
  elif cond_sel == "No culminó":
    df_cobertura = df_cobertura[
        df_cobertura["condicion"]
        .fillna("")
        .astype(str)
        .str.strip()
        .str.casefold()
        == "no culminó"
    ]
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
      df_mapa = df_prov.copy()
      df_mapa["lat"] = df_mapa["provincia"].map(
          lambda provincia: GEO_PROVINCIAS.get(provincia, {}).get("lat")
      )
      df_mapa["lon"] = df_mapa["provincia"].map(
          lambda provincia: GEO_PROVINCIAS.get(provincia, {}).get("lon")
      )
      df_mapa = df_mapa.dropna(subset=["lat", "lon"])
      fig_map = px.scatter_geo(
          df_mapa,
          lat="lat",
          lon="lon",
          size="cantidad",
          color="cantidad",
          text="provincia",
          hover_name="provincia",
          hover_data={
              "cantidad": ":,",
              "porcentaje": ":.1f",
              "lat": False,
              "lon": False,
          },
          color_continuous_scale="Blues",
          size_max=42,
          scope="south america",
          title="Registros por provincia",
      )
      fig_map.update_traces(
          marker_line_color="#0A2540",
          marker_line_width=1,
          textposition="top center",
      )
      fig_map.update_geos(
          center={"lat": -1.5, "lon": -80.5},
          lataxis_range=[-6, 2],
          lonaxis_range=[-92, -75],
          showcountries=True,
          countrycolor="#64748B",
          showland=True,
          landcolor="#F1F5F9",
          showocean=True,
          oceancolor="#EFF6FF",
          showcoastlines=True,
          coastlinecolor="#64748B",
          projection_type="mercator",
      )
      fig_map.update_layout(
          height=520,
          margin=dict(t=55, b=20, l=20, r=20),
          coloraxis_colorbar_title="Registros",
      )
      st.plotly_chart(fig_map, use_container_width=True)
      st.caption(
          "El tamaño del marcador representa la cantidad de registros. "
          "Las provincias sin coordenadas se muestran en la tabla."
      )
    with col_m2:
      st.markdown("### Resumen por Provincia")
      st.dataframe(
          df_prov.sort_values(by="cantidad", ascending=False),
          use_container_width=True,
          hide_index=True,
      )
  else:
    st.info("No hay datos geográficos para los filtros seleccionados.")

  st.markdown("### Tasa de graduación por provincia")
  st.caption(
      "Graduados ÷ total de registros de la provincia. Se muestra el tamaño "
      "de la muestra y se consideran todos los estados de condición para "
      "evitar que el filtro de condición altere el denominador."
  )
  resumen_tasa_provincia = calcular_tasas_graduacion_provinciales(
      df_cobertura_total
  )
  if resumen_tasa_provincia.empty:
    st.info("No hay registros para calcular tasas de graduación.")
  else:
    tabla_tasa_provincia = resumen_tasa_provincia.rename(
        columns={
            "provincia": "Provincia",
            "registros": "Registros (muestra)",
            "graduados": "Graduados",
            "tasa_graduacion": "Tasa de graduación (%)",
        }
    )
    tabla_tasa_provincia["Tasa de graduación (%)"] = (
        tabla_tasa_provincia["Tasa de graduación (%)"].round(1)
    )
    col_tasa_tabla, col_tasa_grafico = st.columns([1, 1.4])
    with col_tasa_tabla:
      st.dataframe(
          tabla_tasa_provincia,
          use_container_width=True,
          hide_index=True,
      )
    with col_tasa_grafico:
      fig_tasa_provincia = px.bar(
          resumen_tasa_provincia.sort_values("tasa_graduacion"),
          x="tasa_graduacion",
          y="provincia",
          orientation="h",
          text="tasa_graduacion",
          color="tasa_graduacion",
          color_continuous_scale="Blues",
          labels={
              "tasa_graduacion": "Tasa de graduación (%)",
              "provincia": "Provincia",
          },
          title="Tasa de graduación por provincia",
      )
      fig_tasa_provincia.update_traces(
          texttemplate="%{text:.1f}%",
          textposition="outside",
          cliponaxis=False,
      )
      fig_tasa_provincia.update_layout(
          coloraxis_showscale=False,
          margin=dict(t=45, b=20, l=20, r=35),
          xaxis_range=[
              0,
              min(
                  105,
                  max(
                      10,
                      float(
                          resumen_tasa_provincia["tasa_graduacion"].max()
                      )
                      * 1.15,
                  ),
              ),
          ],
      )
      st.plotly_chart(fig_tasa_provincia, use_container_width=True)

  st.markdown("### Comparación de periodos por provincia")
  st.caption(
      "Compara años completos (enero a diciembre). Se respetan los filtros "
      "globales de provincia, área, curso y modalidad; la comparación "
      "incluye todos los estados de condición."
  )
  anios_comparables = sorted(
      {
          int(anio)
          for anio in df_f_todos_estados["anio"].dropna().unique()
          if int(anio) > 2000
      }
  )
  if len(anios_comparables) < 2:
    st.info("Se necesitan al menos dos años con datos para comparar.")
  else:
    clave_anio_base = "geografia_anio_base"
    clave_anio_comparacion = "geografia_anio_comparacion"
    if st.session_state.get(clave_anio_base) not in anios_comparables:
      st.session_state[clave_anio_base] = anios_comparables[-2]
    with st.container():
      col_anio_base, col_anio_comparacion = st.columns(2)
      with col_anio_base:
        anio_base = st.selectbox(
            "Año base",
            anios_comparables,
            key=clave_anio_base,
        )
      opciones_anio_comparacion = [
          anio for anio in anios_comparables if anio != anio_base
      ]
      if (
          st.session_state.get(clave_anio_comparacion)
          not in opciones_anio_comparacion
      ):
        st.session_state[clave_anio_comparacion] = (
            opciones_anio_comparacion[-1]
        )
      with col_anio_comparacion:
        anio_comparacion = st.selectbox(
            "Comparar con",
            opciones_anio_comparacion,
            key=clave_anio_comparacion,
        )

    df_comparacion_provincia = comparar_registros_provinciales(
        df_f_todos_estados,
        anio_base,
        anio_comparacion,
    )
    if df_comparacion_provincia.empty:
      st.info("No hay registros para esos años y filtros.")
    else:
      tabla_comparacion_provincia = df_comparacion_provincia.rename(
          columns={
              "provincia": "Provincia",
              "registros_base": f"Registros {anio_base}",
              "registros_comparacion": f"Registros {anio_comparacion}",
              "cambio": "Cambio neto",
              "variacion_porcentual": "Variación (%)",
              "tendencia": "Tendencia",
          }
      )
      tabla_comparacion_provincia["Variación (%)"] = (
          tabla_comparacion_provincia["Variación (%)"].map(
              lambda valor: (
                  "—" if pd.isna(valor) else f"{valor:+.1f}%"
              )
          )
      )
      col_comparacion_tabla, col_comparacion_grafico = st.columns([1, 1.4])
      with col_comparacion_tabla:
        st.dataframe(
            tabla_comparacion_provincia,
            use_container_width=True,
            hide_index=True,
        )
      with col_comparacion_grafico:
        fig_comparacion_provincia = px.bar(
            df_comparacion_provincia.sort_values("cambio"),
            x="cambio",
            y="provincia",
            orientation="h",
            color="tendencia",
            color_discrete_map={
                "Aumentó": "#10B981",
                "Disminuyó": "#F43F5E",
                "Nuevo": "#0284C7",
                "Sin cambio": "#94A3B8",
            },
            labels={
                "cambio": "Cambio de registros",
                "provincia": "Provincia",
                "tendencia": "Tendencia",
            },
            title=f"Cambio de {anio_base} a {anio_comparacion}",
        )
        fig_comparacion_provincia.update_layout(
            margin=dict(t=45, b=20, l=20, r=20),
        )
        st.plotly_chart(
            fig_comparacion_provincia,
            use_container_width=True,
        )

if seccion_activa == secciones_analiticas[2]:
  st.subheader("Análisis por Área Operativa y Especialidades")
  enfoque_area = st.segmented_control(
      "Enfoque rápido por área",
      [
          "👁️ Panorama completo",
          "⚓ Área de Cubierta",
          "⚙️ Área de Máquinas",
      ],
      default="👁️ Panorama completo",
      key="enfoque_rapido_areas",
  )

  df_areas_base = df_raw.copy()
  if prov_sel != "Todas las Provincias":
    df_areas_base = df_areas_base[
        df_areas_base["provincia"] == prov_sel
    ]
  if curso_sel != "Todas las Especialidades":
    df_areas_base = df_areas_base[
        df_areas_base["curso"] == curso_sel
    ]
  if mod_sel != "Todas las Modalidades":
    df_areas_base = df_areas_base[
        df_areas_base["modalidad"] == mod_sel
    ]
  if dni_sidebar:
    df_areas_base = df_areas_base[
        df_areas_base["cedula_limpia"]
        .astype(str)
        .str.contains(busqueda_dni, na=False, regex=False)
    ]
  if ape_sidebar:
    df_areas_base = df_areas_base[
        df_areas_base["nombres"]
        .fillna("")
        .astype(str)
        .str.contains(ape_sidebar.strip(), case=False, na=False, regex=False)
    ]

  area_enfoque = {
      "👁️ Panorama completo": None,
      "⚓ Área de Cubierta": "Área de Cubierta",
      "⚙️ Área de Máquinas": "Área de Máquinas",
  }[enfoque_area]
  df_areas_panel = df_areas_base
  if area_enfoque is not None:
    df_areas_panel = df_areas_panel[
        df_areas_panel["area_operativa"] == area_enfoque
    ]
  st.caption(
      "El enfoque rápido reemplaza el filtro global de área en esta sección. "
      "La comparación de resultados incluye todos los estados de condición."
  )

  if not df_areas_panel.empty:
    df_resumen_area, df_resumen_curso = resumir_areas_especialidades(
        df_areas_panel
    )
    col_a, col_b = st.columns(2)
    with col_a:
      fig_pie = px.pie(
          df_resumen_area,
          names="area_operativa",
          values="registros",
          custom_data=["graduados", "no_culmino", "otros"],
          hole=0.55,
          color_discrete_sequence=px.colors.qualitative.Bold,
          title="Distribución de registros por área",
      )
      fig_pie.update_traces(
          textinfo="none",
          hovertemplate=(
              "<b>%{label}</b><br>"
              "Registros: %{value:,}<br>"
              "Participación: %{percent:.3%}<br>"
              "Graduados: %{customdata[0]:,}<br>"
              "No culminó: %{customdata[1]:,}<br>"
              "Otros / sin estado: %{customdata[2]:,}"
              "<extra></extra>"
          ),
      )
      fig_pie.update_layout(
          legend_title_text="Área",
          legend=dict(itemclick="toggle", itemdoubleclick="toggleothers"),
          margin=dict(t=55, b=20, l=20, r=20),
      )
      st.plotly_chart(fig_pie, use_container_width=True)
    with col_b:
      df_curso = df_resumen_curso.nlargest(10, "registros").sort_values(
          "registros"
      )
      fig_bar = px.bar(
          df_curso,
          x="registros",
          y="curso",
          orientation="h",
          color_discrete_sequence=["#0EA5E9"],
          labels={"registros": "Registros", "curso": "Especialidad"},
          title="10 especialidades con más registros",
      )
      fig_bar.update_layout(
          yaxis=dict(autorange="reversed"),
          margin=dict(t=55, b=20, l=20, r=20),
      )
      st.plotly_chart(fig_bar, use_container_width=True)

    st.markdown("### Indicadores destacados")
    col_especialidad, col_desercion = st.columns(2)
    if not df_resumen_curso.empty:
      curso_mayor_demanda = df_resumen_curso.sort_values(
          ["registros", "graduados"],
          ascending=[False, False],
      ).iloc[0]
      col_especialidad.metric(
          "🏆 Especialidad con más demanda",
          curso_mayor_demanda["curso"],
          (
              f"{int(curso_mayor_demanda['registros']):,} registros · "
              f"{int(curso_mayor_demanda['graduados']):,} graduados"
          ),
          delta_color="off",
      )

      cursos_con_no_culminacion = df_resumen_curso[
          df_resumen_curso["no_culmino"] > 0
      ]
      if cursos_con_no_culminacion.empty:
        col_desercion.metric(
            "⚠️ Mayor porcentaje de no culminación",
            "Sin casos registrados",
            "0% en los filtros actuales",
            delta_color="off",
        )
      else:
        curso_mayor_no_culminacion = cursos_con_no_culminacion.sort_values(
            ["tasa_no_culminacion", "registros"],
            ascending=[False, False],
        ).iloc[0]
        col_desercion.metric(
            "⚠️ Mayor porcentaje de no culminación",
            curso_mayor_no_culminacion["curso"],
            (
                f"{curso_mayor_no_culminacion['tasa_no_culminacion']:.1f}% · "
                f"{int(curso_mayor_no_culminacion['no_culmino']):,} de "
                f"{int(curso_mayor_no_culminacion['registros']):,} registros"
            ),
            delta_color="off",
        )

    df_resultados_area = df_resumen_area.melt(
        id_vars="area_operativa",
        value_vars=["graduados", "no_culmino", "otros"],
        var_name="condicion_resumen",
        value_name="cantidad",
    )
    df_resultados_area["condicion_resumen"] = df_resultados_area[
        "condicion_resumen"
    ].map(
        {
            "graduados": "Graduado",
            "no_culmino": "No culminó",
            "otros": "Otros / sin estado",
        }
    )
    fig_area_condicion = px.bar(
        df_resultados_area,
        x="area_operativa",
        y="cantidad",
        color="condicion_resumen",
        barmode="stack",
        title="Resultados por área operativa",
        labels={
            "area_operativa": "Área operativa",
            "cantidad": "Registros",
            "condicion_resumen": "Condición",
        },
        color_discrete_map={
            "Graduado": "#10B981",
            "No culminó": "#F43F5E",
            "Otros / sin estado": "#94A3B8",
        },
    )
    st.plotly_chart(fig_area_condicion, use_container_width=True)

    st.markdown("### Resumen cruzado: área y condición final")
    df_tabla_area = df_resumen_area.rename(
        columns={
            "area_operativa": "Área operativa",
            "registros": "Registros",
            "graduados": "Graduados",
            "graduados_pct": "Graduados (%)",
            "no_culmino": "No culminó",
            "no_culmino_pct": "No culminó (%)",
            "otros": "Otros / sin estado",
            "otros_pct": "Otros / sin estado (%)",
        }
    )
    for columna_porcentaje in (
        "Graduados (%)",
        "No culminó (%)",
        "Otros / sin estado (%)",
    ):
      df_tabla_area[columna_porcentaje] = df_tabla_area[
          columna_porcentaje
      ].round(1)
    st.dataframe(
        df_tabla_area,
        use_container_width=True,
        hide_index=True,
    )
    st.caption(
        "Los porcentajes se calculan sobre todos los registros del área; "
        "los estados distintos de «Graduado» y «No culminó» se agrupan "
        "como «Otros / sin estado»."
    )
  else:
    st.info("No hay datos para el enfoque y los filtros seleccionados.")

if seccion_activa == secciones_analiticas[3]:
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
          title=f"{cantidad_cursos} cursos con más registros",
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

if seccion_activa == secciones_analiticas[4]:
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

if seccion_activa == secciones_analiticas[5]:
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
    horizonte = st.selectbox(
        "Años a proyectar",
        options=list(range(1, 11)),
        index=4,
        format_func=lambda anios: f"{anios} años",
        key="proyeccion_horizonte_selector",
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

if seccion_activa == secciones_analiticas[6]:
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

  # Bloque de descargas ubicado al final de la sección
  st.markdown("---")
  st.markdown("#### 📥 Descarga de Registros por Rango de Años y Mes")
  st.caption("Filtra por periodo específico para mantener las descargas ligeras y rápidas.")

  anios_disponibles = sorted([int(a) for a in df_raw["anio"].dropna().unique() if a > 2000])
  if anios_disponibles:
    opciones_meses_descarga = ["Todos los meses"] + list(
        NOMBRES_MESES.keys()
    )
    periodo_previo = st.session_state.get("auditoria_periodo_aplicado")
    if periodo_previo and (
        periodo_previo.get("anio_desde") not in anios_disponibles
        or periodo_previo.get("anio_hasta") not in anios_disponibles
        or periodo_previo.get("mes") not in opciones_meses_descarga
    ):
      st.session_state.pop("auditoria_periodo_aplicado", None)
      periodo_previo = None
    valores_iniciales = {
        "auditoria_anio_desde": (
            periodo_previo["anio_desde"]
            if periodo_previo
            else anios_disponibles[0]
        ),
        "auditoria_anio_hasta": (
            periodo_previo["anio_hasta"]
            if periodo_previo
            else anios_disponibles[-1]
        ),
        "auditoria_mes_descarga": (
            periodo_previo["mes"]
            if periodo_previo
            else "Todos los meses"
        ),
    }
    for clave, valor_inicial in valores_iniciales.items():
      if st.session_state.get(clave) not in (
          anios_disponibles
          if clave != "auditoria_mes_descarga"
          else opciones_meses_descarga
      ):
        st.session_state[clave] = valor_inicial

    with st.form("auditoria_periodo_form"):
      col_ini, col_fin, col_mes = st.columns(3)
      with col_ini:
        anio_desde = st.selectbox(
            "Año inicial:",
            anios_disponibles,
            key="auditoria_anio_desde",
        )
      with col_fin:
        anio_hasta = st.selectbox(
            "Año final:",
            anios_disponibles,
            key="auditoria_anio_hasta",
        )
      with col_mes:
        mes_sel_descarga = st.selectbox(
            "Mes:",
            opciones_meses_descarga,
            format_func=lambda valor: (
                "Todos"
                if valor == "Todos los meses"
                else NOMBRES_MESES.get(valor, str(valor))
            ),
            key="auditoria_mes_descarga",
        )
      aplicar_periodo = st.form_submit_button(
          "Aplicar periodo",
          use_container_width=True,
      )

    if aplicar_periodo:
      if anio_desde > anio_hasta:
        st.session_state.pop("auditoria_periodo_aplicado", None)
        st.error("El año inicial no puede ser posterior al año final.")
      else:
        st.session_state["auditoria_periodo_aplicado"] = {
            "anio_desde": anio_desde,
            "anio_hasta": anio_hasta,
            "mes": mes_sel_descarga,
        }

    periodo_aplicado = st.session_state.get("auditoria_periodo_aplicado")
    if periodo_aplicado:
      anio_desde = periodo_aplicado["anio_desde"]
      anio_hasta = periodo_aplicado["anio_hasta"]
      mes_sel_descarga = periodo_aplicado["mes"]
      df_base_filtrado = df_raw[
          df_raw["anio"].between(anio_desde, anio_hasta)
      ].copy()
      if mes_sel_descarga != "Todos los meses":
        df_base_filtrado = df_base_filtrado[
            df_base_filtrado["mes"] == mes_sel_descarga
        ]
        etiqueta_periodo = (
            f"{anio_desde} - {anio_hasta} "
            f"({NOMBRES_MESES.get(mes_sel_descarga)})"
        )
      else:
        etiqueta_periodo = (
            f"{anio_desde} - {anio_hasta} (Todos los meses)"
        )
    else:
      st.info(
          "Selecciona un rango y pulsa «Aplicar periodo» para preparar "
          "las descargas."
      )
      df_base_filtrado = None
  else:
    df_base_filtrado = df_raw.copy()
    etiqueta_periodo = "Histórico completo"

  if df_base_filtrado is not None:
    df_todos_export = df_base_filtrado.copy()
    df_sin_dni_export = df_base_filtrado[
        df_base_filtrado["estado_dni"] == "Sin DNI"
    ].copy()
    df_completos_export = df_base_filtrado[
        mascara_informacion_completa(df_base_filtrado)
    ].copy()

    opciones_descarga_bruta = {
        "todos": (
            f"Todos los registros [{etiqueta_periodo}]",
            df_todos_export,
        ),
        "sin_dni": (
            f"Registros sin DNI [{etiqueta_periodo}]",
            df_sin_dni_export,
        ),
        "completos": (
            f"DNI e info completa [{etiqueta_periodo}]",
            df_completos_export,
        ),
    }

    opciones_descarga = {
        clave: (
            titulo,
            df_original.loc[datos.index].assign(
                cedula_limpia=datos["cedula_limpia"],
                estado_dni=datos["estado_dni"],
                curso=datos["curso"],
            )
            if not datos.empty
            else pd.DataFrame(columns=df_original.columns)
        )
        for clave, (titulo, datos) in opciones_descarga_bruta.items()
    }
    mostrar_botones_descarga_auditoria(opciones_descarga)

if seccion_activa == secciones_analiticas[7]:
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

if seccion_activa == secciones_analiticas[8]:
  st.subheader("Duplicados y trayectoria por jerarquía")
  st.markdown("### Clasificación por código de impresión")
  st.caption(
      "0 = estudiante normal, 1 = recién graduado y 2 = duplicado. "
      "El conteo es de registros; los DNI se cuentan aparte y sin exponerlos."
  )

  if df_f_todos_estados.empty:
    st.info("No hay registros con los filtros seleccionados.")
  else:
    df_codigos, df_codigos_curso = resumir_codigos_impresion(
        df_f_todos_estados
    )
    resumen_por_codigo = df_codigos.set_index("codigo")
    col_normal, col_graduado, col_duplicado = st.columns(3)
    col_normal.metric(
        "Estudiante normal (código 0)",
        f"{int(resumen_por_codigo.loc['0', 'registros']):,}",
    )
    col_graduado.metric(
        "Recién graduado (código 1)",
        f"{int(resumen_por_codigo.loc['1', 'registros']):,}",
    )
    col_duplicado.metric(
        "Duplicado (código 2)",
        f"{int(resumen_por_codigo.loc['2', 'registros']):,}",
        help=(
            "Registros marcados con código 2; no se eliminan ni se "
            "modifican."
        ),
    )
    st.dataframe(
        df_codigos.rename(
            columns={
                "codigo": "Código",
                "clasificacion": "Clasificación",
                "registros": "Registros",
                "personas_dni": "DNI únicos",
            }
        ),
        use_container_width=True,
        hide_index=True,
    )

    df_cursos_duplicados = (
        df_codigos_curso[df_codigos_curso["codigo"] == "2"]
        .nlargest(10, "registros")
        .sort_values("registros")
    )
    if df_cursos_duplicados.empty:
      st.info("No hay registros marcados como duplicados con estos filtros.")
    else:
      fig_cursos_duplicados = px.bar(
          df_cursos_duplicados,
          x="registros",
          y="curso",
          orientation="h",
          text="registros",
          title="Cursos con más registros marcados como duplicados",
          labels={
              "registros": "Registros con código 2",
              "curso": "Curso",
          },
      )
      st.plotly_chart(fig_cursos_duplicados, use_container_width=True)

  st.markdown("### Personas que no avanzaron de jerarquía")
  st.caption(
      "El historial completo se agrupa por DNI válido, sin aplicar filtros "
      "de curso. «Un curso» significa un solo curso distinto registrado; "
      "no confirma que la persona lo haya aprobado."
  )
  df_jerarquia, totales_jerarquia = resumir_trayectoria_por_jerarquia(
      df_raw
  )
  col_una_jerarquia, col_un_curso, col_varios_cursos, col_avance = (
      st.columns(4)
  )
  col_una_jerarquia.metric(
      "Personas en una jerarquía",
      (
          f"{totales_jerarquia['una_jerarquia_un_curso'] + totales_jerarquia['una_jerarquia_varios_cursos']:,}"
      ),
  )
  col_un_curso.metric(
      "Una jerarquía · un curso distinto",
      f"{totales_jerarquia['una_jerarquia_un_curso']:,}",
  )
  col_varios_cursos.metric(
      "Una jerarquía · varios cursos",
      f"{totales_jerarquia['una_jerarquia_varios_cursos']:,}",
  )
  col_avance.metric(
      "Registradas en varias jerarquías",
      f"{totales_jerarquia['varias_jerarquias']:,}",
  )
  if df_jerarquia.empty:
    if totales_jerarquia["personas_analizadas"]:
      st.info(
          "No se encontraron personas limitadas a una sola jerarquía; "
          "las personas analizadas aparecen en varias jerarquías."
      )
    else:
      st.info("No hay trayectorias con DNI válido y curso clasificado.")
  else:
    df_jerarquia_grafico = df_jerarquia.melt(
        id_vars="jerarquia",
        value_vars=["un_curso", "varios_cursos"],
        var_name="trayectoria",
        value_name="personas",
    )
    df_jerarquia_grafico["trayectoria"] = df_jerarquia_grafico[
        "trayectoria"
    ].map(
        {
            "un_curso": "Un curso distinto",
            "varios_cursos": "Varios cursos en la misma jerarquía",
        }
    )
    fig_jerarquia = px.bar(
        df_jerarquia_grafico,
        x="jerarquia",
        y="personas",
        color="trayectoria",
        barmode="stack",
        title="Personas en una sola jerarquía, por nivel registrado",
        labels={
            "jerarquia": "Jerarquía",
            "personas": "DNI únicos",
            "trayectoria": "Cursos distintos",
        },
    )
    st.plotly_chart(fig_jerarquia, use_container_width=True)
    st.dataframe(
        df_jerarquia.rename(
            columns={
                "jerarquia": "Jerarquía",
                "un_curso": "Un curso distinto",
                "varios_cursos": "Varios cursos en la misma jerarquía",
            }
        ),
        use_container_width=True,
        hide_index=True,
    )

if seccion_activa == secciones_analiticas[9]:
  st.subheader("⚓ Panel Estratégico de Ascensos y Planificación")
  st.markdown(
      "Identifica demanda académica potencial a partir del último curso "
      "graduado registrado por cada persona."
  )
  st.info(
      "**Planificación, no certificación legal:** la base registra formación "
      "académica, no tiempo de servicio en el mar. Los umbrales configurados "
      "(Cubierta: 2, 2, 3 y 3 años; Máquinas: 2, 2 y 3 años) son referencias "
      "de planificación, no confirman que alguien cumpla los requisitos de "
      "DIRNEA. Las rutas no reconocidas se omiten."
  )
  candidatos_ascenso, demanda_ascenso, totales_ascenso = (
      calcular_candidatos_ascenso(df_raw)
  )
  col_evaluados, col_listos, col_sin_ruta, col_sin_fecha = st.columns(4)
  col_evaluados.metric(
      "Personas evaluadas",
      f"{totales_ascenso['personas_evaluadas']:,}",
      help="Personas únicas con DNI válido y al menos un curso graduado.",
  )
  col_listos.metric(
      "Demanda potencial",
      f"{totales_ascenso['candidatos_potenciales']:,}",
      help="Personas cuyo tiempo desde el curso alcanza el umbral de planificación.",
  )
  col_sin_ruta.metric(
      "Sin ruta configurada",
      f"{totales_ascenso['personas_sin_ruta']:,}",
      help="El último curso graduado no coincide con una ruta reconocida.",
  )
  col_sin_fecha.metric(
      "Sin fecha utilizable",
      f"{totales_ascenso['sin_fecha']:,}",
      help="Personas con ruta reconocida, pero sin fecha de curso ni año/mes.",
  )
  st.caption(
      f"Rutas con curso reconocido: {totales_ascenso['personas_con_ruta']:,}. "
      "Se consideran registros desde 2021 y el historial no usa los "
      "filtros globales."
  )

  st.markdown("### Demanda potencial por curso objetivo")
  fig_demanda_ascenso = px.bar(
      demanda_ascenso.sort_values(["candidatos", "area"]),
      x="candidatos",
      y="curso_objetivo",
      color="area",
      barmode="group",
      orientation="h",
      text="candidatos",
      labels={
          "candidatos": "Personas que alcanzan el umbral de planificación",
          "curso_objetivo": "Curso objetivo",
          "area": "Área",
      },
      title="Demanda potencial por área y curso",
  )
  st.plotly_chart(fig_demanda_ascenso, use_container_width=True)

  st.markdown("### Lista operativa de candidatos potenciales")
  col_filtro_area, col_filtro_curso = st.columns(2)
  areas_disponibles = demanda_ascenso["area"].drop_duplicates().tolist()
  with col_filtro_area:
    area_seleccionada = st.selectbox(
        "Filtrar por área",
        options=["Todas"] + areas_disponibles,
        key="planificacion_ascensos_area",
    )
  candidatos_por_area = candidatos_ascenso
  cursos_disponibles = demanda_ascenso
  if area_seleccionada != "Todas":
    candidatos_por_area = candidatos_por_area[
        candidatos_por_area["area"] == area_seleccionada
    ]
    cursos_disponibles = cursos_disponibles[
        cursos_disponibles["area"] == area_seleccionada
    ]
  with col_filtro_curso:
    curso_objetivo_seleccionado = st.selectbox(
        "Filtrar por curso objetivo",
        options=["Todos"] + cursos_disponibles["curso_objetivo"].tolist(),
        key="planificacion_ascensos_curso",
    )
  candidatos_filtrados = candidatos_por_area
  if curso_objetivo_seleccionado != "Todos":
    candidatos_filtrados = candidatos_filtrados[
        candidatos_filtrados["curso_objetivo"]
        == curso_objetivo_seleccionado
    ]
  st.caption(
      "La lista contiene datos personales para uso institucional. Está "
      "disponible solo dentro de la sesión autenticada y no incluye "
      "exportación."
  )
  tabla_candidatos = candidatos_filtrados.rename(
      columns={
          "cedula_limpia": "Cédula",
          "nombres": "Nombre completo",
          "provincia": "Provincia",
          "area": "Área",
          "curso_origen": "Último curso graduado",
          "curso_objetivo": "Curso objetivo",
          "fecha_referencia": "Fecha usada para el cálculo",
          "fuente_fecha": "Origen de la fecha",
          "tiempo_espera": "Tiempo transcurrido",
          "umbral_anios": "Umbral de planificación (años)",
      }
  ).copy()
  tabla_candidatos.insert(0, "Estado", "✅ Umbral alcanzado")
  st.dataframe(
      tabla_candidatos,
      use_container_width=True,
      hide_index=True,
  )

if seccion_activa == secciones_analiticas[10]:
  st.subheader("Veda de atún en Ecuador")
  st.caption(
      "Calendario oficial de 2025 para atunes tropicales: barrilete "
      "(Katsuwonus pelamis), aleta amarilla (Thunnus albacares) y patudo "
      "(Thunnus obesus), aplicado a buques de cerco de clases 4, 5 y 6. "
      "Referencia: Acuerdo Ministerial MPCEIP-SRP-2024-0282-A."
  )

  df_vedas_atun = obtener_periodos_veda_atun()
  col_vedas, col_dias, col_anio = st.columns(3)
  col_vedas.metric("Ventanas publicadas", len(df_vedas_atun))
  col_dias.metric(
      "Duración de cada ventana",
      f"{int(df_vedas_atun['dias'].iloc[0])} días",
  )
  col_anio.metric("Calendario de referencia", "2025")

  st.markdown("### Calendario oficial de referencia")
  tabla_vedas_atun = df_vedas_atun.rename(
      columns={
          "periodo": "Ventana",
          "inicio": "Inicio",
          "fin": "Fin",
          "dias": "Días calendario",
      }
  )
  st.dataframe(
      tabla_vedas_atun,
      use_container_width=True,
      hide_index=True,
  )

  df_grafico_vedas_atun = df_vedas_atun.assign(
      fin_grafico=(
          pd.to_datetime(df_vedas_atun["fin"]) + pd.Timedelta(days=1)
      )
  )
  fig_vedas_atun = px.timeline(
      df_grafico_vedas_atun,
      x_start="inicio",
      x_end="fin_grafico",
      y="periodo",
      color="periodo",
      hover_data={
          "inicio": True,
          "fin": True,
          "fin_grafico": False,
          "dias": True,
      },
      title="Ventanas de veda del atún — calendario 2025",
  )
  fig_vedas_atun.update_yaxes(autorange="reversed", title_text="")
  fig_vedas_atun.update_xaxes(title_text="Fecha")
  fig_vedas_atun.update_layout(
      showlegend=False,
      margin=dict(t=50, b=20, l=20, r=20),
  )
  st.plotly_chart(fig_vedas_atun, use_container_width=True)

  st.markdown("### Personas con cursos durante las ventanas de veda")
  st.caption(
      "Para años anteriores a 2025 se repiten los días y meses del calendario "
      "2025 únicamente como estimación, no como fechas oficiales. Se usan "
      "fec_ini/fec_fin cuando existen; si faltan, se estima solo con meses "
      "completos dentro de la ventana a partir de anio/mes. Las personas se "
      "deduplican por DNI o, si falta, por nombres y matrícula."
  )

  df_estadisticas_veda, totales_veda = calcular_cursos_en_vedas_atun(
      df_f_todos_estados
  )
  col_personas_veda, col_registros_veda, col_sin_identidad_veda = st.columns(3)
  col_personas_veda.metric(
      "Personas identificables (incluye estimaciones)",
      f"{totales_veda['personas_unicas']:,}",
  )
  col_registros_veda.metric(
      "Registros de curso coincidentes",
      f"{totales_veda['registros']:,}",
  )
  col_sin_identidad_veda.metric(
      "Registros sin identidad suficiente",
      f"{totales_veda['registros_sin_identidad']:,}",
  )

  if df_estadisticas_veda.empty:
    st.info(
        "No hay fechas de curso ni pares de año/mes suficientes para estimar "
        "coincidencias con las ventanas de veda."
    )
  else:
    df_estadisticas_veda["etiqueta_periodo"] = (
        df_estadisticas_veda["anio_veda"].astype(str)
        + " · "
        + df_estadisticas_veda["periodo"]
    )
    fig_personas_veda = px.bar(
        df_estadisticas_veda,
        x="etiqueta_periodo",
        y="personas_unicas",
        color="referencia",
        barmode="group",
        labels={
            "etiqueta_periodo": "Año de inicio · ventana",
            "personas_unicas": "Personas identificables",
            "referencia": "Referencia",
        },
        title="Personas con cursos en cada ventana",
    )
    fig_personas_veda.update_layout(
        margin=dict(t=45, b=20, l=20, r=20),
        xaxis_title="Año de inicio · ventana",
        yaxis_title="Personas identificables",
    )
    st.plotly_chart(fig_personas_veda, use_container_width=True)

    tabla_estadisticas_veda = df_estadisticas_veda.rename(
        columns={
            "anio_veda": "Año de inicio",
            "periodo": "Ventana",
            "inicio": "Inicio",
            "fin": "Fin",
            "dias": "Días de referencia",
            "referencia": "Tipo de referencia",
            "personas_unicas": "Personas únicas",
            "personas_con_fecha_exacta": "Personas con fecha exacta",
            "personas_estimadas_por_mes": "Personas estimadas por mes",
            "registros_con_fecha_exacta": "Registros con fecha exacta",
            "registros_estimados_por_mes": "Registros estimados por mes",
            "registros_sin_identidad": "Registros sin identidad",
        }
    )
    st.dataframe(
        tabla_estadisticas_veda.drop(columns=["etiqueta_periodo"]),
        use_container_width=True,
        hide_index=True,
    )

  st.info(
      "La base de EPESPO contiene registros académicos, no datos de captura, "
      "embarcaciones ni desembarques; por eso esta sección describe el "
      "calendario de referencia y coincidencias de cursos, no actividad "
      "pesquera, cumplimiento ni impacto económico. Las cifras respetan los "
      "filtros generales y consideran todos los estados de condición."
  )
  st.markdown(
      f"[Consultar calendario oficial de vedas de Ecuador]({URL_CALENDARIO_OFICIAL})"
      f" · [Abrir PDF oficial 2025]({URL_PDF_CALENDARIO_2025})"
  )

if indicador_carga_seccion is not None:
  indicador_carga_seccion.empty()
  st.session_state["_seccion_analitica_renderizada"] = seccion_activa