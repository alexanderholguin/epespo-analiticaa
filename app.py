import streamlit as st
import pandas as pd
import numpy as np
import unicodedata
import plotly.express as px
import plotly.graph_objects as go
from sqlalchemy import create_engine, inspect
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import PolynomialFeatures
from sklearn.metrics import r2_score, mean_squared_error
from calendar import monthrange

from auth import render_login, cerrar_sesion

st.set_page_config(
    page_title="EPESPO - Suite Analítica y Estratégica Marítima",
    page_icon="🧭",
    layout="wide",
    initial_sidebar_state="collapsed"
)

if not render_login():
    st.stop()

# =============================================================
# CONEXIÓN A RENDER (POSTGRESQL) Y MIGRACIÓN AUTOMÁTICA DEL EXCEL
# =============================================================
@st.cache_resource
def obtener_motor_y_datos():
    # 1. Obtener la URL de conexión desde los Secrets de Streamlit Cloud o respaldo local
    try:
        DATABASE_URL = st.secrets["RENDER_DB_URL"]
    except:
        # Cambia esto por tu External Database URL de Render si haces pruebas locales
        DATABASE_URL = "postgresql+psycopg2://usuario:contraseña@host.render.com:5432/nombre_db"

    # Asegurar el uso del driver psycopg2 compatible con SQLAlchemy
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+psycopg2://", 1)
    elif DATABASE_URL.startswith("postgresql://") and "+psycopg2" not in DATABASE_URL:
        DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg2://", 1)

    engine = create_engine(DATABASE_URL)
    inspector = inspect(engine)
    
    # 2. Migración automática: Si la tabla no existe en Render, la crea leyendo tu Excel de GitHub
    if not inspector.has_table("registros_epespo"):
        try:
            archivo_excel = "titulados_epespo.xlsx"
            df_excel = pd.read_excel(archivo_excel, sheet_name=0)
            df_excel.to_sql("registros_epespo", con=engine, if_exists="replace", index=False)
        except Exception as e:
            st.error(f"Error al migrar automáticamente el archivo Excel a Render: {e}")
            st.stop()
            
    return engine

engine = obtener_motor_y_datos()

# Función para cargar los datos desde Render
def cargar_datos_completos():
    query = "SELECT * FROM registros_epespo"
    return pd.read_sql(query, con=engine)

# =============================================================
# ESTILOS CSS GLOBALES
# =============================================================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }
    
    .stApp {
        background-color: #F8FAFC;
    }

    /* Banner Principal */
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
    .hero-title {
        font-size: 24px;
        font-weight: 800;
        margin: 0;
        color: #FFFFFF;
    }
    .hero-subtitle {
        font-size: 13.5px;
        color: #D1E4FF;
        margin-top: 4px;
        margin-bottom: 0;
    }
    .hero-badge {
        background: rgba(255, 255, 255, 0.15);
        border: 1px solid rgba(255, 255, 255, 0.25);
        padding: 5px 12px;
        border-radius: 20px;
        font-size: 11.5px;
        font-weight: 700;
        color: #FFFFFF;
    }

    /* Tarjetas KPI */
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
    .kpi-card::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 4px;
    }
    .kpi-blue::before { background: #0284C7; }
    .kpi-green::before { background: #10B981; }
    .kpi-teal::before { background: #0EA5E9; }
    .kpi-rose::before { background: #F43F5E; }

    .kpi-label {
        font-size: 11.5px;
        font-weight: 700;
        color: #64748B;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-bottom: 6px;
    }
    .kpi-value {
        font-size: 26px;
        font-weight: 800;
        color: #0F172A;
        line-height: 1.15;
    }
    .kpi-unit {
        font-size: 13.5px;
        font-weight: 500;
        color: #94A3B8;
        margin-left: 5px;
    }
    .kpi-badge {
        display: inline-block;
        margin-top: 8px;
        padding: 3px 8px;
        border-radius: 6px;
        font-size: 11.5px;
        font-weight: 600;
    }
    .badge-green { background: #ECFDF5; color: #047857; }
    .badge-rose { background: #FFF1F2; color: #BE123C; }
    .badge-blue { background: #EFF6FF; color: #1D4ED8; }

    /* Pestañas */
    .stTabs [data-baseweb="tab-list"] {
        gap: 6px;
        background-color: #E2E8F0;
        padding: 5px;
        border-radius: 10px;
        border-bottom: none !important;
        margin-bottom: 18px;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px;
        padding: 8px 16px;
        font-size: 13.5px;
        font-weight: 600;
        color: #475569;
        background-color: transparent;
        border: none !important;
    }
    .stTabs [aria-selected="true"] {
        background-color: #FFFFFF !important;
        color: #0052CC !important;
        box-shadow: 0 2px 6px rgba(0, 0, 0, 0.08);
    }

    /* Caja de Controles */
    .filter-panel {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 12px;
        padding: 16px 20px;
        margin-bottom: 20px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.03);
    }
    
    .sidebar-user-card {
        background: #0A2540;
        color: white;
        padding: 12px 16px;
        border-radius: 10px;
        margin-bottom: 14px;
    }
</style>
""", unsafe_allow_html=True)

# =============================================================
# CAPA VISUAL EPESPO - DISEÑO INSTITUCIONAL 2026
# =============================================================
st.markdown("""
<style>
.stApp { background: #F5F8FC; }
.block-container { max-width: 1720px; padding: 1.8rem 2.2rem 3rem; }
h1, h2, h3 { color: #153A60; letter-spacing: -.3px; }
.stTabs [data-baseweb="tab-list"] { background: #E7EEF7; border-radius: 13px; padding: 6px; gap: 4px; }
.stTabs [data-baseweb="tab"] { border-radius: 9px; padding: 10px 14px; color: #46627F; white-space: nowrap; }
.stTabs [data-baseweb="tab"][aria-selected="true"] { background: #FFFFFF !important; color: #0759B8 !important; box-shadow: 0 2px 8px rgba(15,54,102,.08); }
div[data-testid="stPlotlyChart"] { background: #FFFFFF; border: 1px solid #E4EBF4; border-radius: 15px; padding: 7px; box-shadow: 0 3px 12px rgba(15,54,102,.025); }
div[data-testid="stMetric"] { background: #FFFFFF; border: 1px solid #E1EAF4; border-top: 3px solid #1680E8; border-radius: 13px; padding: 18px 20px; }
div[data-testid="stMetricValue"] { color: #10449C; font-weight: 750; }
div[data-testid="stDataFrame"] { border: 1px solid #E3EAF4; border-radius: 12px; overflow: hidden; }
.ep-tram-card { background:#FFFFFF; border:1px solid #E1EAF4; border-top:4px solid var(--tram-accent); border-radius:15px; padding:20px 21px 19px; min-height:166px; box-shadow:0 4px 15px rgba(13,71,161,.035); }
.ep-tram-heading { display:flex; align-items:center; justify-content:space-between; gap:10px; font-size:11px; letter-spacing:.5px; color:#64748B; font-weight:750; }
.ep-tram-icon { font-size:22px; }
.ep-tram-number { color:#10449C; font-size:34px; font-weight:800; margin:10px 0 3px; line-height:1.1; }
.ep-tram-detail { font-size:12px; color:#51677E; min-height:21px; }
.ep-tram-track { background:#EAF0F7; height:7px; border-radius:20px; overflow:hidden; margin-top:13px; }
@media(max-width:768px) { .block-container { padding-left:1rem; padding-right:1rem; } .ep-tram-card { min-height:145px; } }
</style>
""", unsafe_allow_html=True)

GEO_PROVINCIAS = {
    'Manabí': {'lat': -0.9538, 'lon': -80.7089},
    'Guayas': {'lat': -2.1894, 'lon': -79.8891},
    'Esmeraldas': {'lat': 0.9682, 'lon': -79.6517},
    'Pichincha': {'lat': -0.2298, 'lon': -78.5249},
    'Los Ríos': {'lat': -1.8022, 'lon': -79.5344},
    'El Oro': {'lat': -3.2581, 'lon': -79.9554},
    'Santa Elena': {'lat': -2.2262, 'lon': -80.8587},
    'Cotopaxi': {'lat': -0.9333, 'lon': -78.6167},
    'Santo Domingo': {'lat': -0.2530, 'lon': -79.1754},
    'Sucumbíos': {'lat': 0.0833, 'lon': -76.8833},
    'Azuay': {'lat': -2.9001, 'lon': -79.0059},
    'Chimborazo': {'lat': -1.6667, 'lon': -78.6500},
    'Imbabura': {'lat': 0.3500, 'lon': -78.1167},
    'Loja': {'lat': -3.9931, 'lon': -79.2042},
    'Tungurahua': {'lat': -1.2491, 'lon': -78.6168},
    'Galápagos': {'lat': -0.7432, 'lon': -90.3138},
    'Bolívar': {'lat': -1.5911, 'lon': -79.0022},
    'Cañar': {'lat': -2.5562, 'lon': -78.9386},
    'Carchi': {'lat': 0.8122, 'lon': -77.7173},
    'Morona Santiago': {'lat': -2.3087, 'lon': -78.1114},
    'Napo': {'lat': -0.9938, 'lon': -77.8129},
    'Pastaza': {'lat': -1.4897, 'lon': -77.9986},
    'Zamora Chinchipe': {'lat': -4.0692, 'lon': -78.9567},
    'Orellana': {'lat': -0.4639, 'lon': -76.9872}
}

NOMBRES_MESES = {
    1: 'Enero', 2: 'Febrero', 3: 'Marzo', 4: 'Abril',
    5: 'Mayo', 6: 'Junio', 7: 'Julio', 8: 'Agosto',
    9: 'Septiembre', 10: 'Octubre', 11: 'Noviembre', 12: 'Diciembre'
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
        "Galapagos": "Galápagos"
    }
    return correcciones.get(p, p)

def normalizar_curso(curso_raw):
    if pd.isna(curso_raw):
        return "Sin Especificar"
    
    nfkd_form = unicodedata.normalize('NFKD', str(curso_raw))
    c = "".join([char for char in nfkd_form if not unicodedata.combining(char)]).strip().upper()
    c_sin_puntos = c.replace(".", "")

    if c_sin_puntos in ["ELD", "ESTUDIO LIBRE DIRIGIDO"]:
        return "Estudio Libre Dirigido"
    elif "MARINERO DE MAQUINAS" in c_sin_puntos:
        return "Marinero De Máquinas"
    elif "OPERADOR DE MAQUINAS" in c_sin_puntos:
        return "Operador De Máquinas"
    
    return " ".join(c.split()).title()

def clasificar_area_operativa(curso):
    nfkd_form = unicodedata.normalize('NFKD', str(curso))
    c = "".join([char for char in nfkd_form if not unicodedata.combining(char)]).upper()
    if any(k in c for k in ["MAQUINA", "MOTORISTA", "MAQUINISTA", "MECANIC"]):
        return "Área de Máquinas"
    elif any(k in c for k in ["PATRON", "CAPITAN", "CUBIERTA", "PUENTE", "TIMONEL", "PESCADOR", "MARINERO PESCADOR"]):
        return "Área de Cubierta"
    return "Servicios y Apoyo Marítimo"

def clasificar_escala_nautica(curso):
    nfkd_form = unicodedata.normalize('NFKD', str(curso))
    c = "".join([char for char in nfkd_form if not unicodedata.combining(char)]).upper()
    if any(k in c for k in ["ALTURA", "CAPITAN", "JEFE DE MAQUINAS"]):
        return "4. Mando Superior (Capitanes / Jefes)"
    elif any(k in c for k in ["COSTANERO", "OPERADOR", "OFICIAL", "MAQUINISTA", "JEFE DE CUBIERTA", "MOTORISTA"]):
        return "3. Mandos Medios y Técnicos"
    elif any(k in c for k in ["TIMONEL", "MARINERO DE MAQUINAS", "MARINERO PRIMERA"]):
        return "2. Tripulación Calificada"
    return "1. Marinería Base y Artesanal"

def clasificar_tipo_estudiante(fila):
    if "impresion" in fila and pd.notna(fila["impresion"]):
        try:
            val = int(float(fila["impresion"]))
            if val == 2: return "Duplicado (Cód. 2)"
            elif val == 1: return "Recién Graduado (Cód. 1)"
            elif val == 0: return "Estudiante Normal (Cód. 0)"
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
        if d3 in [0, 1]: return "Manta / Montecristi / Jaramijó"
        elif d3 in [2, 3]: return "Portoviejo y Cuenca Central"
        elif d3 in [4, 5]: return "Sucre / San Vicente / Bahía"
        elif d3 in [6, 7]: return "Pedernales / Jama / Cojimíes"
        else: return "Zona Sur (Jipijapa / Puerto López)"
    elif prov == "Guayas":
        if d3 in [0, 1, 2]: return "Guayaquil Metropolitano"
        elif d3 in [3, 4]: return "Playas / Posorja / Golfo"
        else: return "Cantones Fluviales (Durán / Daule)"
    elif prov == "Esmeraldas":
        if d3 in [0, 1, 2]: return "Esmeraldas / Atacames"
        else: return "San Lorenzo / Eloy Alfaro"
    elif prov == "Santa Elena":
        return "La Libertad / Salinas / Santa Elena"
    return f"Cantones de {prov}"

df_raw = cargar_datos_completos()
if df_raw.empty:
    st.error("No se encontraron registros en la base de datos.")
    st.stop()

# =============================================================
# NORMALIZACIÓN GLOBAL ESTRICTA
# =============================================================
df_raw["cedula_limpia"] = df_raw["cedula"].apply(limpiar_dni)
df_raw["curso"] = df_raw["curso"].apply(normalizar_curso)
df_raw["modalidad"] = df_raw["modalidad"].apply(limpiar_texto_general)
df_raw["provincia"] = df_raw["provincia"].apply(normalizar_provincia)

df_raw["area_operativa"] = df_raw["curso"].apply(clasificar_area_operativa)
df_raw["escala_nautica"] = df_raw["curso"].apply(clasificar_escala_nautica)
df_raw["zona_canton"] = df_raw.apply(lambda r: estimar_zona_cantonal(r["cedula_limpia"], r["provincia"]), axis=1)
df_raw["tipo_tramite"] = df_raw.apply(clasificar_tipo_estudiante, axis=1)

df_raw["anio"] = pd.to_numeric(df_raw["anio"], errors='coerce').fillna(0).astype(int)
df_raw["mes"] = pd.to_numeric(df_raw["mes"], errors='coerce').fillna(1).astype(int)

# -------------------------------------------------------------
# SIDEBAR MODERNO Y CONTRAÍDO
# -------------------------------------------------------------
st.sidebar.markdown(f"""
    <div class="sidebar-user-card">
        <div style="font-size: 11px; text-transform: uppercase; color: #93C5FD; font-weight: 700;">Usuario Activo</div>
        <div style="font-size: 13.5px; font-weight: 600; margin-top: 2px;">{st.session_state.nombre}</div>
        <div style="margin-top: 6px;"><span style="background: rgba(16, 185, 129, 0.2); color: #34D399; font-size: 10.5px; padding: 2px 8px; border-radius: 12px; font-weight: 700;">ROL: {st.session_state.rol.upper()}</span></div>
    </div>
""", unsafe_allow_html=True)

with st.sidebar.expander("🔍 Búsqueda de Ciudadano", expanded=False):
    dni_sidebar = st.text_input("Cédula / DNI:", placeholder="Ej: 1306296409", key="search_dni_side")
    ape_sidebar = st.text_input("O por Apellidos:", placeholder="Ej: RODRIGUEZ", key="search_ape_side")

    if dni_sidebar or ape_sidebar:
        if st.button("✖️ Limpiar Búsqueda", use_container_width=True):
            st.session_state["search_dni_side"] = ""
            st.session_state["search_ape_side"] = ""
            st.rerun()

with st.sidebar.expander("⚙️ Filtros Globales de Datos", expanded=False):
    provincias_disp = ["Todas las Provincias"] + sorted([p for p in df_raw["provincia"].dropna().unique() if p != "No Registrada"])
    prov_sel = st.sidebar.selectbox("Provincia:", provincias_disp)

    areas_disp = ["Todas las Áreas"] + sorted(df_raw["area_operativa"].unique().tolist())
    area_sel = st.sidebar.selectbox("Área de Buque:", areas_disp)

    cursos_disp = ["Todas las Especialidades"] + sorted(df_raw["curso"].dropna().unique().tolist())
    curso_sel = st.sidebar.selectbox("Especialidad:", cursos_disp)

    modalidades_disp = ["Todas las Modalidades"] + sorted(df_raw["modalidad"].dropna().unique().tolist())
    mod_sel = st.sidebar.selectbox("Modalidad:", modalidades_disp)

    condiciones_disp = ["Todos", "Solo Graduados (Cumple)", "No culminó"]
    cond_sel = st.sidebar.selectbox("Condición:", condiciones_disp)

# Aplicar filtros globales
df_filtrado = df_raw.copy()
if 'prov_sel' in locals() and prov_sel != "Todas las Provincias":
    df_filtrado = df_filtrado[df_filtrado["provincia"] == prov_sel]
if 'area_sel' in locals() and area_sel != "Todas las Áreas":
    df_filtrado = df_filtrado[df_filtrado["area_operativa"] == area_sel]
if 'curso_sel' in locals() and curso_sel != "Todas las Especialidades":
    df_filtrado = df_filtrado[df_filtrado["curso"] == curso_sel]
if 'mod_sel' in locals() and mod_sel != "Todas las Modalidades":
    df_filtrado = df_filtrado[df_filtrado["modalidad"] == mod_sel]
if 'cond_sel' in locals():
    if cond_sel == "Solo Graduados (Cumple)":
        df_filtrado = df_filtrado[df_filtrado["condicion"] == "Graduado"]
    elif cond_sel == "No culminó":
        df_filtrado = df_filtrado[df_filtrado["condicion"] == "No culminó"]

# =============================================================
# BANNER PRINCIPAL
# =============================================================
st.markdown("""
    <div class="hero-banner">
        <div>
            <h1 class="hero-title">⚓ ESCUELA DE PESCA DEL PACÍFICO ORIENTAL (EPESPO)</h1>
            <p class="hero-subtitle">Plataforma de Inteligencia Analítica Marítima, Control de Flota y Gestión de Titulaciones</p>
        </div>
        <div class="hero-badge">SISTEMA OFICIAL DIRNEA</div>
    </div>
""", unsafe_allow_html=True)

# [El resto de tus pestañas y gráficos se mantienen exactamente igual...]