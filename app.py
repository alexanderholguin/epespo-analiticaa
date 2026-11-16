from calendar import monthrange
import os
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_squared_error, r2_score
from sklearn.preprocessing import PolynomialFeatures
from sqlalchemy import inspect
import streamlit as st
import unicodedata

from auth import render_login, cerrar_sesion
from db import get_engine

st.set_page_config(
    page_title="EPESPO - Suite Analítica y Estratégica Marítima",
    page_icon="🧭",
    layout="wide",
    initial_sidebar_state="collapsed",
)

if not render_login():
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

    query = "SELECT * FROM graduados_epespo"
    return pd.read_sql(query, con=engine)
  except Exception as e:
    st.error(f"Error al consultar la base de datos: {e}")
    st.stop()


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
df_raw["mes"] = (
    pd.to_numeric(df_raw["mes"], errors="coerce").fillna(1).astype(int)
)


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

with st.sidebar.expander("🔍 Búsqueda de Ciudadano", expanded=False):
  dni_sidebar = st.text_input(
      "Cédula / DNI:", placeholder="Ej: 1306296409", key="search_dni_side"
  )
  ape_sidebar = st.text_input(
      "O por Apellidos:", placeholder="Ej: RODRIGUEZ", key="search_ape_side"
  )
  if dni_sidebar or ape_sidebar:
    if st.button("✖️ Limpiar Búsqueda", use_container_width=True):
      st.session_state["search_dni_side"] = ""
      st.session_state["search_ape_side"] = ""
      st.rerun()

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
  df_f = df_f[df_f["cedula_limpia"].str.contains(dni_sidebar, na=False)]
if ape_sidebar:
  df_f = df_f[
      df_f["nombres"].str.upper().str.contains(ape_sidebar.upper(), na=False)
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
  df_evolucion = df_f[df_f["anio"] > 2000]
  if not df_evolucion.empty:
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
        title="Registros por año y condición",
    )
    fig_line.update_layout(
        plot_bgcolor="white",
        paper_bgcolor="white",
        margin=dict(t=45, b=20, l=20, r=20),
        xaxis_title="Año",
        yaxis_title="Registros",
    )
    st.plotly_chart(fig_line, use_container_width=True)
  else:
    st.info("No hay datos suficientes para mostrar la evolución temporal.")

with tab2:
  st.subheader("Distribución Geográfica y Provincial")
  if not df_f.empty and "provincia" in df_f.columns:
    col_m1, col_m2 = st.columns([2, 1])
    with col_m1:
      df_prov = df_f.groupby("provincia").size().reset_index(name="cantidad")
      fig_map = px.bar(
          df_prov.sort_values(by="cantidad", ascending=True),
          x="cantidad",
          y="provincia",
          orientation="h",
          color="cantidad",
          color_continuous_scale="Blues",
      )
      fig_map.update_layout(
          plot_bgcolor="white",
          paper_bgcolor="white",
          margin=dict(t=20, b=20, l=20, r=20),
      )
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
  if not df_f.empty:
    df_demanda = (
        df_f.groupby("curso")
        .agg(
            total=("curso", "size"),
            graduados=("es_graduado", "sum"),
        )
        .reset_index()
    )
    df_demanda["tasa_graduacion"] = (
        df_demanda["graduados"] / df_demanda["total"] * 100
    )
    df_demanda_top = df_demanda.nlargest(15, "total")
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
      )
      st.plotly_chart(fig_cumplimiento, use_container_width=True)
    df_modalidad = (
        df_f.groupby(["modalidad", "condicion"], dropna=False)
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
  if not df_f.empty and "anio" in df_f.columns:
    df_p = (
        df_f[
            (df_f["es_graduado"])
            & (df_f["anio"] >= 2010)
            & (df_f["anio"] <= 2025)
        ]
        .groupby("anio")
        .size()
        .reset_index(name="total")
    )
    if len(df_p) > 3:
      X = df_p[["anio"]]
      y = df_p["total"]
      model = LinearRegression()
      model.fit(X, y)
      anios_futuros = np.array([[2026], [2027], [2028], [2029], [2030]])
      predicciones = model.predict(anios_futuros)

      df_futuro = pd.DataFrame(
          {"anio": [2026, 2027, 2028, 2029, 2030], "total": predicciones}
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
      st.plotly_chart(fig_pred, use_container_width=True)
      st.success(
          "Estimación lineal basada en graduados históricos; es una referencia"
          " y no una garantía de resultados futuros."
      )
    else:
      st.warning(
          "Se requieren más datos históricos para ejecutar la proyección."
      )

with tab7:
  st.subheader("Auditoría de DNI y calidad de registros")
  st.caption(
      "Los resultados respetan los filtros globales. “Con DNI” indica un "
      "formato de 10 dígitos; no valida el dígito verificador oficial."
  )
  total_auditoria = len(df_f)
  sin_dni = int((df_f["estado_dni"] == "Sin DNI").sum())
  dni_irregular = int((df_f["estado_dni"] == "DNI irregular").sum())
  con_dni = int((df_f["estado_dni"] == "Con DNI").sum())
  ids_con_varios_registros = int(
      (
          df_f.loc[df_f["estado_dni"] == "Con DNI", "cedula_limpia"]
          .value_counts()
          > 1
      ).sum()
  )

  col_sin_dni, col_irregular, col_con_dni, col_repetidos = st.columns(4)
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
  col_repetidos.metric("DNI en varios registros", f"{ids_con_varios_registros:,}")
  st.caption(
      "Un DNI asociado a varios registros puede corresponder a varios cursos "
      "o reingresos; no implica por sí solo un duplicado. Los conteos son de "
      "registros y no de personas únicas cuando falta el DNI."
  )

  if not df_f.empty:
    df_auditoria_curso = (
        df_f.groupby("curso")
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
      df_tendencia_dni = df_f[df_f["anio"] > 2000]
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