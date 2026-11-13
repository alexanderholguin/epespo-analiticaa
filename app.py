from calendar import monthrange
import os
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_squared_error, r2_score
from sklearn.preprocessing import PolynomialFeatures
from sqlalchemy import create_engine, inspect
import streamlit as st
import unicodedata

from auth import render_login, cerrar_sesion

st.set_page_config(
    page_title="EPESPO - Suite Analítica y Estratégica Marítima",
    page_icon="🧭",
    layout="wide",
    initial_sidebar_state="collapsed",
)

if not render_login():
  st.stop()


# =============================================================
# CONEXIÓN A LA BASE DE DATOS (CLOUD SQL / CLOUD RUN)
# =============================================================
@st.cache_resource
def obtener_motor_y_datos():
    # MODIFICA ESTOS TRES VALORES CON TUS CREDENCIALES REALES DE CLOUD SQL SI ES NECESARIO:
    db_user = os.environ.get("DB_USER", "postgres")
    db_pass = os.environ.get("DB_PASS", "epespo2026")
    db_name = os.environ.get("DB_NAME", "epespo_db")
    
    cloud_sql_connection_name = "epespo:us-east1:epespo-analitica"
    
    # Construcción de la URL de conexión usando el socket Unix oficial de Cloud Run
    DATABASE_URL = os.environ.get("DATABASE_URL")
    if not DATABASE_URL:
        DATABASE_URL = f"postgresql+psycopg2://{db_user}:{db_pass}@/{db_name}?host=/cloudsql/{cloud_sql_connection_name}"

    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace(
            "postgres://", "postgresql+psycopg2://", 1
        )
    elif DATABASE_URL.startswith("postgresql://") and "+psycopg2" not in DATABASE_URL:
        DATABASE_URL = DATABASE_URL.replace(
            "postgresql://", "postgresql+psycopg2://", 1
        )

    engine = create_engine(DATABASE_URL)
    return engine


engine = obtener_motor_y_datos()


def cargar_datos_completos():
    query = "SELECT * FROM registros_epespo"
    return pd.read_sql(query, con=engine)


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
    .hero-badge {
        background: rgba(255, 255, 255, 0.15);
        border: 1px solid rgba(255, 255, 255, 0.25);
        padding: 5px 12px;
        border-radius: 20px;
        font-size: 11.5px;
        font-weight: 700;
        color: #FFFFFF;
    }

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
  c = "".join([char for char in nfkd_form if not unicodedata.combining(char)]).upper()
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
  c = "".join([char for char in nfkd_form if not unicodedata.combining(char)]).upper()
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
  elif any(k in c for k in ["TIMONEL", "MARINERO DE MAQUINAS", "MARINERO PRIMERA"]):
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
df_raw["curso"] = df_raw["curso"].apply(normalizar_curso)
df_raw["modalidad"] = df_raw["modalidad"].apply(limpiar_texto_general)
df_raw["provincia"] = df_raw["provincia"].apply(normalizar_provincia)

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
  df_f = df_f[df_f["condicion"] == "Graduado"]
elif cond_sel == "No culminó":
  df_f = df_f[df_f["condicion"] == "No culminó"]

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
        <div class="hero-badge">SISTEMA OFICIAL DIRNEA</div>
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
    (len(df_f[df_f["condicion"] == "Graduado"]) / total_titulados * 100)
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
# PESTAÑAS DE NAVEGACIÓN ANALÍTICA COMPLETAS
# =============================================================
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "📈 Evolución Histórica",
    "🗺️ Geografía & Cobertura",
    "⚓ Áreas & Especialidades",
    "🔮 Proyección & Tendencias",
    "🔍 Auditoría de Datos",
    "📋 Base de Datos Completa",
])

with tab1:
  st.subheader("Evolución Temporal de Titulaciones (2002 - 2025)")
  if not df_f.empty and "anio" in df_f.columns:
    df_anio = (
        df_f[df_f["anio"] > 2000]
        .groupby("anio")
        .size()
        .reset_index(name="titulados")
    )
    fig_line = px.line(
        df_anio,
        x="anio",
        y="titulados",
        markers=True,
        line_shape="spline",
        color_discrete_sequence=["#0052CC"],
    )
    fig_line.update_layout(
        plot_bgcolor="white",
        paper_bgcolor="white",
        margin=dict(t=20, b=20, l=20, r=20),
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

with tab4:
  st.subheader("🔮 Modelo Predictivo y Proyección de Titulaciones")
  if not df_f.empty and "anio" in df_f.columns:
    df_p = (
        df_f[(df_f["anio"] >= 2010) & (df_f["anio"] <= 2025)]
        .groupby("anio")
        .size()
        .reset_index(name="total")
    )
    if len(df_p) > 3:
      X = df_p[["anio"]]
      y = df_p["total"]
      model = LinearRegression()
      model.fit(X, y)
      anios_futuros = np.array(
          [[2026], [2027], [2028], [2029], [2030]]
      )
      predicciones = model.predict(anios_futuros)

      df_futuro = pd.DataFrame(
          {"anio": [2026, 2027, 2028, 2029, 2030], "total": predicciones}
      )
      df_completo_pred = pd.concat([df_p, df_futuro])

      fig_pred = px.line(
          df_completo_pred,
          x="anio",
          y="total",
          markers=True,
          title="Tendencia Histórica y Proyección a Futuro",
      )
      fig_pred.update_traces(
          line=dict(dash="dash", color="red"),
          selector=dict(x=df_futuro["anio"]),
      )
      st.plotly_chart(fig_pred, use_container_width=True)
      st.success(
          "El modelo de regresión lineal muestra la tendencia estimada de"
          " egresados para los próximos años."
      )
    else:
      st.warning(
          "Se requieren más datos históricos para ejecutar la proyección."
      )

with tab5:
  st.subheader(
      "Auditoría y Control de Calidad (Registros Anómalos / Sin Cédula)"
  )
  mask_anomalo = (
      df_f["cedula_limpia"].str.contains("000000|nan", case=False, na=True)
      | (df_f["cedula_limpia"] == "")
      | (df_f["cedula_limpia"].str.len() < 10)
  )
  df_anomalos = df_f[mask_anomalo]
  st.metric("Registros Históricos con Cédulas Irregulares", len(df_anomalos))
  if not df_anomalos.empty:
    st.dataframe(
        df_anomalos[[
            "cedula",
            "nombres",
            "provincia",
            "curso",
            "anio",
            "condicion",
        ]],
        use_container_width=True,
    )
  else:
    st.success("¡Excelente calidad de datos! No se detectan anomalías graves.")

with tab6:
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