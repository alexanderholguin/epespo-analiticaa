import streamlit as st
import pandas as pd
import numpy as np
import unicodedata
import plotly.express as px
import plotly.graph_objects as go
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import PolynomialFeatures
from sklearn.metrics import r2_score, mean_squared_error

from db import cargar_datos_completos, insertar_registros_masivos
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
# Se aplica sobre los estilos existentes sin alterar la lógica.
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

with st.sidebar.expander("📂 Carga y Actualización", expanded=False):
    st.markdown("Sube un archivo nuevo (.xlsx o .csv) para actualizar la base de datos.")
    archivo_subido = st.file_uploader("Seleccionar archivo:", type=["xlsx", "csv"])
    modo_carga = st.radio("Modo:", ["Añadir (Append)", "Reemplazar (Overwrite)"], index=0)

    if archivo_subido is not None:
        if st.button("🚀 Sincronizar Archivo", use_container_width=True):
            with st.spinner("Procesando datos..."):
                try:
                    if archivo_subido.name.endswith(".csv"):
                        df_subida = pd.read_csv(archivo_subido)
                    else:
                        xls_sub = pd.ExcelFile(archivo_subido)
                        hoja_a_leer = 'totaltituladosv3' if 'totaltituladosv3' in xls_sub.sheet_names else xls_sub.sheet_names[0]
                        df_subida = pd.read_excel(archivo_subido, sheet_name=hoja_a_leer)

                    df_procesado = pd.DataFrame()
                    col_ced = next((c for c in df_subida.columns if 'ced' in str(c).lower() or 'nui' in str(c).lower()), df_subida.columns[1])
                    cedula_raw = df_subida[col_ced].astype(str)
                    df_procesado["cedula"] = cedula_raw.str.replace(".0", "", regex=False).str.strip().str.zfill(10).replace("nan", "")

                    def obtener_prov(ced):
                        if not isinstance(ced, str) or len(ced) < 2: return "No Registrada"
                        mapping = {
                            '01': 'Azuay', '02': 'Bolívar', '03': 'Cañar', '04': 'Carchi', '05': 'Cotopaxi',
                            '06': 'Chimborazo', '07': 'El Oro', '08': 'Esmeraldas', '09': 'Guayas', '10': 'Imbabura',
                            '11': 'Loja', '12': 'Los Ríos', '13': 'Manabí', '14': 'Morona Santiago', '15': 'Napo',
                            '16': 'Pastaza', '17': 'Pichincha', '18': 'Tungurahua', '19': 'Zamora Chinchipe',
                            '20': 'Galápagos', '21': 'Sucumbíos', '22': 'Orellana', '23': 'Santo Domingo', '24': 'Santa Elena'
                        }
                        return mapping.get(ced[:2], 'No Registrada')

                    df_procesado["provincia"] = df_procesado["cedula"].apply(obtener_prov)

                    col_nom = next((c for c in df_subida.columns if 'nom' in str(c).lower()), None)
                    col_ape = next((c for c in df_subida.columns if 'apel' in str(c).lower()), None)
                    if col_nom and col_ape:
                        df_procesado["nombres"] = (df_subida[col_ape].astype(str) + " " + df_subida[col_nom].astype(str)).str.strip()
                    elif col_nom:
                        df_procesado["nombres"] = df_subida[col_nom].astype(str).str.strip()
                    else:
                        df_procesado["nombres"] = "Sin Nombre"

                    col_mat = next((c for c in df_subida.columns if 'matr' in str(c).lower()), None)
                    df_procesado["matricula"] = df_subida[col_mat].astype(str).str.strip() if col_mat else ""

                    col_imp = next((c for c in df_subida.columns if 'impres' in str(c).lower() or 'impr' in str(c).lower()), None)
                    if col_imp:
                        def limpiar_imp(val):
                            try:
                                v = int(float(val))
                                return v if v in [0, 1, 2] else 0
                            except:
                                return 0
                        df_procesado["impresion"] = df_subida[col_imp].apply(limpiar_imp)
                    else:
                        df_procesado["impresion"] = 0

                    col_cur = next((c for c in df_subida.columns if 'curso' in str(c).lower() or 'titul' in str(c).lower()), df_subida.columns[0])
                    df_procesado["curso"] = df_subida[col_cur].apply(normalizar_curso)

                    col_fec = next((c for c in df_subida.columns if 'fec' in str(c).lower() or 'date' in str(c).lower()), None)
                    if col_fec:
                        fechas = pd.to_datetime(df_subida[col_fec], errors="coerce")
                        df_procesado["fecha"] = fechas.dt.strftime("%Y-%m-%d").fillna("2020-01-01")
                        df_procesado["anio"] = fechas.dt.year.fillna(2020).astype(int)
                        df_procesado["mes"] = fechas.dt.month.fillna(1).astype(int)
                    else:
                        df_procesado["fecha"] = "2020-01-01"
                        df_procesado["anio"] = 2020
                        df_procesado["mes"] = 1

                    col_fec_ini = next((c for c in df_subida.columns if 'fec_ini' in str(c).lower() or 'inicio' in str(c).lower()), None)
                    if col_fec_ini:
                        df_procesado["fec_ini"] = pd.to_datetime(df_subida[col_fec_ini], errors="coerce").dt.strftime("%Y-%m-%d").fillna("No registrada")
                    else:
                        df_procesado["fec_ini"] = "No registrada"

                    col_fec_fin = next((c for c in df_subida.columns if 'fec_fin' in str(c).lower() or 'fin' in str(c).lower()), None)
                    if col_fec_fin:
                        df_procesado["fec_fin"] = pd.to_datetime(df_subida[col_fec_fin], errors="coerce").dt.strftime("%Y-%m-%d").fillna("No registrada")
                    else:
                        df_procesado["fec_fin"] = "No registrada"

                    col_mod = next((c for c in df_subida.columns if 'modal' in str(c).lower() or 'estud' in str(c).lower()), None)
                    df_procesado["modalidad"] = df_subida[col_mod].apply(limpiar_texto_general) if col_mod else "Presencial"

                    col_est = next((c for c in df_subida.columns if 'estad' in str(c).lower() or 'cond' in str(c).lower()), None)
                    if col_est:
                        estado_raw = df_subida[col_est].astype(str).str.strip().str.upper()
                        df_procesado["condicion"] = estado_raw.apply(lambda x: "Graduado" if "CUMPLE" in x or "APROB" in x else "No culminó")
                    else:
                        df_procesado["condicion"] = "Graduado"

                    tipo_modo = "append" if "Añadir" in modo_carga else "replace"
                    if insertar_registros_masivos(df_procesado, modo=tipo_modo):
                        st.success("¡Base actualizada con éxito!")
                        st.balloons()
                        st.rerun()
                except Exception as e:
                    st.error(f"Error al procesar archivo: {e}")

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

if dni_sidebar or ape_sidebar:
    c_dni = limpiar_dni(dni_sidebar) if dni_sidebar else ""
    c_ape = ape_sidebar.strip().lower() if ape_sidebar else ""

    if c_dni and c_ape:
        res_busqueda = df_raw[
            df_raw["cedula_limpia"].str.contains(c_dni, na=False) &
            df_raw["nombres"].astype(str).str.lower().str.contains(c_ape, na=False)
        ]
    elif c_dni:
        res_busqueda = df_raw[
            df_raw["cedula_limpia"].str.contains(c_dni, na=False) |
            df_raw["cedula"].astype(str).str.contains(dni_sidebar.strip(), na=False)
        ]
    else:
        res_busqueda = df_raw[df_raw["nombres"].astype(str).str.lower().str.contains(c_ape, na=False)]

    with st.expander("👤 EXPEDIENTE DEL CIUDADANO CONSULTADO", expanded=True):
        if not res_busqueda.empty:
            unicas = res_busqueda[["cedula_limpia", "nombres"]].drop_duplicates()
            if len(unicas) > 1:
                sel_idx = st.selectbox(
                    "Seleccione la persona específica encontrada:",
                    range(len(unicas)),
                    format_func=lambda i: f"{unicas.iloc[i]['nombres']} (DNI: {unicas.iloc[i]['cedula_limpia']})"
                )
                dni_eleg = unicas.iloc[sel_idx]["cedula_limpia"]
                df_pers = res_busqueda[res_busqueda["cedula_limpia"] == dni_eleg]
            else:
                df_pers = res_busqueda

            nom = df_pers.iloc[0]["nombres"]
            ced = df_pers.iloc[0]["cedula_limpia"]
            prv = df_pers.iloc[0]["provincia"]
            zon = df_pers.iloc[0]["zona_canton"]
            tot_c = len(df_pers)
            aprob = len(df_pers[df_pers["condicion"] == "Graduado"])
            no_ap = tot_c - aprob

            st.markdown(f"""
            <div style="background: #FFFFFF; border-left: 5px solid #0052CC; padding: 14px 18px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.04); margin-bottom: 15px;">
                <div style="font-size: 17px; font-weight: 700; color: #0F172A;">{nom}</div>
                <div style="display: flex; gap: 24px; margin-top: 6px; font-size: 13px; color: #475569;">
                    <span><b>Cédula/DNI:</b> {ced}</span>
                    <span><b>Provincia de Origen:</b> <span style="color: #0284C7; font-weight: bold;">{prv}</span> ({zon})</span>
                    <span><b>Historial:</b> <span style="color: #059669; font-weight: bold;">{aprob} Aprobados</span> / <span style="color: #DC2626; font-weight: bold;">{no_ap} Bajas</span></span>
                </div>
            </div>
            """, unsafe_allow_html=True)

            df_pers_exp = df_pers.copy()
            df_pers_exp["provincia_origen"] = df_pers_exp["provincia"]

            st.dataframe(
                df_pers_exp[[
                    "curso", "area_operativa", "provincia_origen", "tipo_tramite", "modalidad", "matricula", "fec_ini", "fec_fin", "fecha", "condicion"
                ]],
                column_config={
                    "curso": "Especialidad / Curso",
                    "area_operativa": "Área de Buque",
                    "provincia_origen": "Provincia",
                    "tipo_tramite": "Tipo Trámite",
                    "modalidad": "Modalidad",
                    "matricula": "Matrícula Marítima",
                    "fec_ini": "Fecha Inicio",
                    "fec_fin": "Fecha Fin",
                    "fecha": "Fecha Titulación",
                    "condicion": "Condición"
                },
                use_container_width=True,
                hide_index=True
            )
        else:
            st.warning("No se encontró ningún ciudadano registrado con los datos ingresados.")

# =============================================================
# PESTAÑAS PRINCIPALES DEL DASHBOARD
# =============================================================
tab1, tab_demanda, tab_cumple, tab_geo, tab_flota, tab_vedas, tab_pred, tab_ciclos = st.tabs([
    "📊 Diagnóstico y Eficiencia",
    "🔥 Demanda de Cursos",
    "📋 Cumplimiento y Trámites",
    "🗺️ Provincias y Cantones",
    "⚓ Cubierta vs. Máquinas",
    "🎣 Vedas de Atún",
    "📈 Proyecciones",
    "🔄 Ciclos y Reingresos"
])

# -------------------------------------------------------------
# TAB 1: DIAGNÓSTICO
# -------------------------------------------------------------
with tab1:
    tot_general = len(df_filtrado)
    graduados_n = len(df_filtrado[df_filtrado["condicion"] == "Graduado"])
    no_grad = tot_general - graduados_n
    tasa_efectividad = (graduados_n / tot_general * 100) if tot_general > 0 else 0

    st.markdown(f"""
    <div class="kpi-container">
        <div class="kpi-card kpi-blue">
            <div class="kpi-label">Población Evaluada</div>
            <div class="kpi-value">{tot_general:,}<span class="kpi-unit">alumnos</span></div>
            <span class="kpi-badge badge-blue">Caudal Histórico</span>
        </div>
        <div class="kpi-card kpi-green">
            <div class="kpi-label">Titulados Efectivos</div>
            <div class="kpi-value">{graduados_n:,}<span class="kpi-unit">egresados</span></div>
            <span class="kpi-badge badge-green">Certificados DIRNEA</span>
        </div>
        <div class="kpi-card kpi-teal">
            <div class="kpi-label">Tasa de Titulación</div>
            <div class="kpi-value">{tasa_efectividad:.1f}%</div>
            <span class="kpi-badge badge-green">↑ {(tasa_efectividad - 80):.1f}% vs Meta (80%)</span>
        </div>
        <div class="kpi-card kpi-rose">
            <div class="kpi-label">No Culminaron / Brecha</div>
            <div class="kpi-value">{no_grad:,}<span class="kpi-unit">alumnos</span></div>
            <span class="kpi-badge badge-rose">Deserción Académica</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="filter-panel"><b>⚙️ Controles de Desglose Temporal</b>', unsafe_allow_html=True)
    col_v1, col_v2, col_v3 = st.columns([2.2, 1.8, 2])
    tipo_vista = col_v1.radio(
        "Desglose Temporal:",
        ["Por Año (Histórico Completo)", "Por Mes (Estacionalidad)", "Detalle Mensual de un Año"],
        horizontal=True
    )
    modo_grafico = col_v3.selectbox(
        "Estilo de Visualización:",
        ["Barras Agrupadas", "Barras Apiladas", "Líneas de Tendencia"]
    )

    if tipo_vista == "Por Año (Histórico Completo)":
        col_v2.info("📅 Vista anual completa (2002 - 2025)")
        df_plot = df_filtrado.groupby(["anio", "condicion"]).size().reset_index(name="alumnos")
        df_plot = df_plot[df_plot["anio"] > 0]
        eje_x = "anio"
        titulo_grafico = "Volumen de Titulados vs. No Culminados por Período Anual"
        etiqueta_x = "Año"

    elif tipo_vista == "Por Mes (Estacionalidad)":
        col_v2.info("🗓️ Estacionalidad de Enero a Diciembre")
        df_meses_validos = df_filtrado[df_filtrado["mes"].between(1, 12)].copy()
        df_meses_validos["mes_nombre"] = df_meses_validos["mes"].map(NOMBRES_MESES)
        df_plot = df_meses_validos.groupby(["mes", "mes_nombre", "condicion"]).size().reset_index(name="alumnos")
        df_plot = df_plot.sort_values("mes")
        eje_x = "mes_nombre"
        titulo_grafico = "Concentración Estacional de Alumnos por Mes de Titulación"
        etiqueta_x = "Mes Calendario"

    else:
        anios_disponibles = sorted([int(a) for a in df_filtrado["anio"].unique() if a > 0], reverse=True)
        anio_seleccionado = col_v2.selectbox("Seleccionar Año:", anios_disponibles)
        df_anio = df_filtrado[(df_filtrado["anio"] == anio_seleccionado) & (df_filtrado["mes"].between(1, 12))].copy()
        df_anio["mes_nombre"] = df_anio["mes"].map(NOMBRES_MESES)
        df_plot = df_anio.groupby(["mes", "mes_nombre", "condicion"]).size().reset_index(name="alumnos")
        df_plot = df_plot.sort_values("mes")
        eje_x = "mes_nombre"
        titulo_grafico = f"Comportamiento Mes a Mes del Año {anio_seleccionado}"
        etiqueta_x = f"Meses ({anio_seleccionado})"

    st.markdown('</div>', unsafe_allow_html=True)

    if not df_plot.empty:
        barmode_val = "stack" if "Apiladas" in modo_grafico else "group"
        color_map = {"Graduado": "#0052CC", "No culminó": "#F43F5E"}

        if "Líneas" in modo_grafico:
            fig_diag = px.line(
                df_plot,
                x=eje_x,
                y="alumnos",
                color="condicion",
                markers=True,
                color_discrete_map=color_map
            )
            fig_diag.update_traces(line=dict(width=3), marker=dict(size=7))
        else:
            fig_diag = px.bar(
                df_plot,
                x=eje_x,
                y="alumnos",
                color="condicion",
                barmode=barmode_val,
                color_discrete_map=color_map
            )
            fig_diag.update_traces(marker_cornerradius=5)

        fig_diag.update_traces(
            hovertemplate="<b>%{x}</b><br>Estado: %{data.name}<br>Alumnos: <b>%{y:,.0f}</b><extra></extra>"
        )

        fig_diag.update_layout(
            template="plotly_white",
            title=dict(text=f"<b>{titulo_grafico}</b>", font=dict(size=14, color="#1E293B")),
            xaxis=dict(title=etiqueta_x, gridcolor="#F1F5F9", linecolor="#CBD5E1"),
            yaxis=dict(title="Cantidad de Aspirantes", gridcolor="#F1F5F9", linecolor="#CBD5E1"),
            hovermode="x unified",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, title=""),
            margin=dict(l=10, r=10, t=50, b=10),
            height=390
        )
        st.plotly_chart(fig_diag, use_container_width=True)
    else:
        st.warning("No existen registros para el período temporal seleccionado.")

    st.markdown("#### 🚦 Semáforo de Rendimiento y Deserción por Modalidad")
    df_semaforo = df_filtrado.groupby("modalidad").agg(
        Total=("condicion", "count"),
        Graduados=("condicion", lambda x: (x == "Graduado").sum()),
        No_Culminados=("condicion", lambda x: (x == "No culminó").sum())
    ).reset_index()
    df_semaforo["Tasa_Exito"] = (df_semaforo["Graduados"] / df_semaforo["Total"] * 100).round(1)
    df_semaforo = df_semaforo.sort_values("Tasa_Exito", ascending=True)

    def categorizar_semaforo(tasa):
        if tasa >= 85: return "🟢 Alta Certificación (≥ 85%)"
        elif tasa >= 60: return "🟡 Rendimiento Moderado (60-84%)"
        return "🔴 Cuello de Botella (< 60%)"

    df_semaforo["Estado"] = df_semaforo["Tasa_Exito"].apply(categorizar_semaforo)

    st.dataframe(
        df_semaforo,
        column_config={
            "modalidad": "Modalidad de Estudio",
            "Total": st.column_config.NumberColumn("Matriculados", format="%d"),
            "Graduados": st.column_config.NumberColumn("Titulados", format="%d"),
            "No_Culminados": st.column_config.NumberColumn("No Culminaron", format="%d"),
            "Tasa_Exito": st.column_config.ProgressColumn(
                "Tasa de Éxito",
                format="%.1f%%",
                min_value=0,
                max_value=100
            ),
            "Estado": "Diagnóstico Operativo"
        },
        use_container_width=True,
        hide_index=True
    )

# -------------------------------------------------------------
# TAB 2: DEMANDA DE CURSOS
# -------------------------------------------------------------
with tab_demanda:
    st.subheader("Demanda Histórica y Preferencia de Especialidades")
    st.caption("Identificación de los cursos con mayor volumen de matrícula y su evolución en el tiempo.")

    df_dem = df_filtrado.groupby(["curso", "area_operativa"]).agg(
        Total_Inscritos=("condicion", "count"),
        Graduados=("condicion", lambda x: (x == "Graduado").sum()),
        No_Culminados=("condicion", lambda x: (x == "No culminó").sum())
    ).reset_index()
    df_dem["Tasa_Aprobacion"] = (df_dem["Graduados"] / df_dem["Total_Inscritos"] * 100).round(1)
    df_dem = df_dem.sort_values("Total_Inscritos", ascending=False)

    top_curso_nombre = df_dem.iloc[0]["curso"] if not df_dem.empty else "No disponible"
    top_curso_cant = df_dem.iloc[0]["Total_Inscritos"] if not df_dem.empty else 0
    cursos_activos = len(df_dem)

    kd1, kd2, kd3 = st.columns(3)
    kd1.metric("Especialidad Líder en Demanda", top_curso_nombre)
    kd2.metric(
        "Inscripciones en el Curso Líder",
        f"{top_curso_cant:,} aspirantes",
        f"{(top_curso_cant/len(df_filtrado)*100):.1f}% de la demanda total" if len(df_filtrado) else "0%"
    )
    kd3.metric("Oferta Total de Programas", f"{cursos_activos} cursos")

    st.markdown("---")
    col_dem1, col_dem2 = st.columns([3, 2.5])

    with col_dem1:
        st.markdown("#### Top 10 Cursos con Mayor Demanda")
        top_10_dem = df_dem.head(10).sort_values("Total_Inscritos", ascending=True)
        fig_dem_bar = px.bar(
            top_10_dem,
            x="Total_Inscritos",
            y="curso",
            orientation="h",
            color="area_operativa",
            color_discrete_map={
                "Área de Cubierta": "#0284C7",
                "Área de Máquinas": "#D97706",
                "Servicios y Apoyo Marítimo": "#64748B"
            }
        )
        fig_dem_bar.update_traces(
            marker_cornerradius=4,
            hovertemplate="<b>%{y}</b><br>Inscritos: <b>%{x:,}</b><extra></extra>"
        )
        fig_dem_bar.update_layout(
            template="plotly_white",
            xaxis=dict(title="Número de Aspirantes", gridcolor="#F1F5F9"),
            yaxis=dict(title="", tickfont=dict(size=11)),
            margin=dict(l=10, r=10, t=20, b=10),
            legend=dict(orientation="h", y=1.08, x=0.5, xanchor="center", title=""),
            height=380
        )
        st.plotly_chart(fig_dem_bar, use_container_width=True)

    with col_dem2:
        st.markdown("#### Desglose de Rendimiento por Curso")
        st.dataframe(
            df_dem.head(10),
            column_config={
                "curso": "Especialidad",
                "area_operativa": "Área",
                "Total_Inscritos": st.column_config.NumberColumn("Inscritos", format="%d"),
                "Graduados": st.column_config.NumberColumn("Titulados", format="%d"),
                "Tasa_Aprobacion": st.column_config.ProgressColumn(
                    "% Aprobación",
                    format="%.1f%%",
                    min_value=0,
                    max_value=100
                )
            },
            use_container_width=True,
            hide_index=True
        )

    st.markdown("---")
    st.markdown("#### Tendencia Temporal de los 5 Cursos Principales")
    top_5_nombres = df_dem.head(5)["curso"].tolist()
    df_top5_evo = df_filtrado[df_filtrado["curso"].isin(top_5_nombres)].groupby(["anio", "curso"]).size().reset_index(name="alumnos")
    fig_top5_evo = px.line(
        df_top5_evo,
        x="anio",
        y="alumnos",
        color="curso",
        markers=True,
        color_discrete_sequence=["#0284C7", "#10B981", "#F59E0B", "#8B5CF6", "#EC4899"]
    )
    fig_top5_evo.update_traces(line=dict(width=2.5), marker=dict(size=6))
    fig_top5_evo.update_layout(
        template="plotly_white",
        xaxis=dict(title="Año", gridcolor="#F1F5F9"),
        yaxis=dict(title="Aspirantes", gridcolor="#F1F5F9"),
        margin=dict(l=10, r=10, t=30, b=10),
        legend=dict(orientation="h", y=-0.2, x=0.5, xanchor="center", title=""),
        height=350
    )
    st.plotly_chart(fig_top5_evo, use_container_width=True)

# -------------------------------------------------------------
# TAB 3: CUMPLIMIENTO Y TRÁMITES
# -------------------------------------------------------------
with tab_cumple:
    st.subheader("Auditoría de Cumplimiento y Trámites de Titulación")
    st.caption("Tipificación institucional de trámites registrados en EPESPO, según los filtros activos.")

    TIPOS = [
        "Estudiante Normal (Cód. 0)",
        "Recién Graduado (Cód. 1)",
        "Duplicado (Cód. 2)",
    ]
    COLORES = ["#1565C0", "#0891B2", "#F59E0B"]
    df_tram = df_filtrado[df_filtrado["tipo_tramite"].isin(TIPOS)].copy()

    resumen = (
        df_tram.groupby("tipo_tramite")["condicion"]
        .agg(
            Total="size",
            Cumple=lambda v: int((v == "Graduado").sum()),
            No_Cumple=lambda v: int((v == "No culminó").sum()),
        )
        .reindex(TIPOS, fill_value=0)
        .reset_index()
    )
    resumen["%_Efectividad"] = (
        resumen["Cumple"].div(resumen["Total"].replace(0, float("nan")))
        .mul(100).fillna(0).round(1)
    )

    normal, recien, duplicado = [resumen.iloc[i] for i in range(3)]

    def fmt_num(v):
        return f"{int(v):,}".replace(",", ".")

    def fmt_pct(v):
        return f"{float(v):.1f}".replace(".", ",")

    def tarjeta_tramite(titulo, total, detalle, porcentaje, color, icono):
        # Se escapan los textos antes de incorporarlos al HTML.
        import html as _html
        titulo, detalle = _html.escape(titulo), _html.escape(detalle)
        porcentaje = max(0, min(100, float(porcentaje)))
        st.markdown(f"""
        <div class="ep-tram-card" style="--tram-accent:{color}">
          <div class="ep-tram-heading"><span>{titulo}</span><span class="ep-tram-icon">{icono}</span></div>
          <div class="ep-tram-number">{fmt_num(total)}</div>
          <div class="ep-tram-detail">{detalle}</div>
          <div class="ep-tram-track"><div style="width:{porcentaje:.2f}%;background:{color};height:100%;border-radius:20px"></div></div>
        </div>
        """, unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3, gap="medium")
    with c1:
        tarjeta_tramite(
            "ESTUDIANTE NORMAL · CÓD. 0", normal["Total"],
            f"{fmt_num(normal['Cumple'])} graduados · {fmt_pct(normal['%_Efectividad'])}%",
            normal["%_Efectividad"], COLORES[0], "🎓"
        )
    with c2:
        tarjeta_tramite(
            "RECIÉN GRADUADO · CÓD. 1", recien["Total"],
            f"{fmt_num(recien['Cumple'])} graduados · {fmt_pct(recien['%_Efectividad'])}%",
            recien["%_Efectividad"], COLORES[1], "📘"
        )
    with c3:
        # El duplicado es un trámite documental, no una culminación académica.
        tarjeta_tramite(
            "DUPLICADOS · CÓD. 2", duplicado["Total"],
            "Solicitudes registradas · trámite documental",
            100 if duplicado["Total"] else 0, COLORES[2], "📄"
        )

    st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)
    col_a, col_b = st.columns([1.3, 1], gap="medium")

    with col_a:
        st.markdown("#### Cumplimiento académico por tipo de trámite")
        st.caption("Comparación porcentual de registros graduados y no culminados. No incluye duplicados.")
        acad = resumen.iloc[:2].copy()
        acad["Otros"] = (acad["Total"] - acad["Cumple"] - acad["No_Cumple"]).clip(lower=0)
        fig_cumplimiento = go.Figure()
        for campo, nombre, color in [
            ("Cumple", "Graduado", "#1565C0"),
            ("No_Cumple", "No culminó", "#F43F5E"),
            ("Otros", "Otros estados", "#CBD5E1"),
        ]:
            valores = (acad[campo] / acad["Total"].replace(0, float("nan")) * 100).fillna(0)
            fig_cumplimiento.add_trace(go.Bar(
                y=["Estudiante Normal", "Recién Graduado"],
                x=valores,
                name=nombre,
                orientation="h",
                marker_color=color,
                customdata=acad[campo],
                hovertemplate=f"<b>%{{y}}</b><br>{nombre}: %{{customdata:,}}<br>%{{x:.1f}}%<extra></extra>",
                text=[f"{v:.1f}%" if v >= 8 else "" for v in valores],
                textposition="inside",
                insidetextanchor="middle",
            ))
        fig_cumplimiento.update_layout(
            barmode="stack", template="plotly_white", height=300,
            margin=dict(l=10, r=15, t=20, b=35),
            xaxis=dict(range=[0, 100], title="Participación (%)", ticksuffix="%", gridcolor="#EDF2F8"),
            yaxis=dict(title="", autorange="reversed"),
            legend=dict(orientation="h", y=1.2, x=0, title=""),
            bargap=0.52,
            font=dict(color="#17324D"),
        )
        st.plotly_chart(fig_cumplimiento, use_container_width=True)

    with col_b:
        st.markdown("#### Composición de trámites")
        st.caption("Participación de cada categoría en los registros filtrados.")
        total_tramites = int(resumen["Total"].sum())
        fig_dona = go.Figure(go.Pie(
            labels=["Estudiante Normal", "Recién Graduado", "Duplicado"],
            values=resumen["Total"], hole=0.73,
            marker=dict(colors=COLORES, line=dict(color="white", width=3)),
            textinfo="none", sort=False,
            hovertemplate="<b>%{label}</b><br>Trámites: %{value:,}<br>Participación: %{percent}<extra></extra>",
        ))
        fig_dona.update_layout(
            template="plotly_white", height=300,
            margin=dict(l=5, r=5, t=10, b=45),
            annotations=[dict(
                text=f"<b>{fmt_num(total_tramites)}</b><br><span style='font-size:12px'>trámites</span>",
                x=0.5, y=0.5, showarrow=False, font=dict(size=23, color="#153A60")
            )],
            legend=dict(orientation="h", y=-0.13, x=0.5, xanchor="center", title="", font=dict(size=10)),
        )
        st.plotly_chart(fig_dona, use_container_width=True)

    st.markdown("#### Detalle institucional por categoría")
    tabla = resumen.rename(columns={
        "tipo_tramite": "Categoría / Código",
        "Total": "Total de trámites",
        "Cumple": "Graduados registrados",
        "No_Cumple": "No culminaron",
        "%_Efectividad": "Graduación (%)",
    })
    # En duplicados la tasa académica no aplica.
    tabla.loc[tabla["Categoría / Código"] == TIPOS[2], "Graduación (%)"] = float("nan")
    st.dataframe(
        tabla,
        column_config={
            "Total de trámites": st.column_config.NumberColumn(format="%d"),
            "Graduados registrados": st.column_config.NumberColumn(format="%d"),
            "No culminaron": st.column_config.NumberColumn(format="%d"),
            "Graduación (%)": st.column_config.ProgressColumn(format="%.1f%%", min_value=0, max_value=100),
        },
        hide_index=True,
        use_container_width=True,
    )
    st.caption("Nota: la cantidad de duplicados representa solicitudes registradas. Para identificar emisiones efectivas se requiere un campo de estado de emisión.")

# -------------------------------------------------------------
# =============================================================
# 
# =============================================================
# TAB 4: DISTRIBUCIÓN GEOGRÁFICA — REDISEÑO INSTITUCIONAL
# =============================================================
with tab_geo:
    st.markdown('''
    <style>
    .geo-intro {padding:20px 24px; background:linear-gradient(105deg,#07396c,#0d65a9);border-radius:16px;color:white;margin-bottom:16px}
    .geo-intro h2 {color:white!important;margin:0;font-size:26px}
    .geo-intro p {color:#d8ebff;margin:7px 0 0;font-size:14px}
    .geo-section {background:linear-gradient(90deg,#073c70,#0875bc);color:white;padding:11px 16px;border-radius:11px;font-weight:700;font-size:15px;margin:12px 0 10px}
    .geo-footnote {color:#6a7f98;font-size:12px;margin:3px 0 12px}
    </style>
    <div class="geo-intro"><h2>🗺️ Distribución Geográfica</h2>
    <p>Inteligencia territorial de registros académicos y documentales por provincia y cantón.</p></div>
    ''', unsafe_allow_html=True)

    geo = df_filtrado.copy()
    geo['provincia'] = geo['provincia'].fillna('No Registrada').astype(str).str.strip()
    geo['anio'] = pd.to_numeric(geo['anio'], errors='coerce')
    geo['condicion'] = geo.get('condicion', pd.Series('', index=geo.index)).fillna('').astype(str).str.strip().str.casefold()
    geo['tipo_tramite'] = geo.get('tipo_tramite', pd.Series('', index=geo.index)).fillna('').astype(str)
    geo = geo[~geo['provincia'].str.casefold().isin(['no registrada','sin especificar','nan','none',''])].copy()

    # Los cantones NO pueden deducirse de la cédula: únicamente se usa
    # un campo cantonal explícito, si existe en los registros originales.
    canton_cols = ['canton', 'cantón', 'canton_residencia', 'canton_origen', 'ciudad_canton']
    canton_real = next((c for c in canton_cols if c in geo.columns), None)
    if canton_real:
        geo['canton_verificado'] = geo[canton_real].fillna('').astype(str).str.strip()
        geo.loc[geo['canton_verificado'].str.casefold().isin(['','nan','none','no determinado','sin especificar']), 'canton_verificado'] = ''
    else:
        geo['canton_verificado'] = ''

    if geo.empty:
        st.info('No existen provincias identificadas para los filtros actuales.')
    else:
        # Filtros locales (no modifican el resto de las pestañas).
        f1, f2, f3 = st.columns([1,1,1])
        anios_geo = sorted(geo['anio'].dropna().astype(int).unique().tolist())
        with f1:
            anio_geo = st.selectbox('📅 Año', ['Todos'] + anios_geo, key='geo2026_anio')
        with f2:
            provincia_geo = st.selectbox('📍 Provincia', ['Todas'] + sorted(geo['provincia'].unique().tolist()), key='geo2026_prov')
        with f3:
            tipo_geo = st.selectbox('📋 Tipo de registro', ['Todos','Estudiante Normal (Cód. 0)','Recién Graduado (Cód. 1)','Duplicado (Cód. 2)'], key='geo2026_tipo')
        if anio_geo != 'Todos':
            geo = geo[geo['anio'] == anio_geo].copy()
        if provincia_geo != 'Todas':
            geo = geo[geo['provincia'] == provincia_geo].copy()
        if tipo_geo != 'Todos':
            geo = geo[geo['tipo_tramite'] == tipo_geo].copy()

        total_geo = len(geo)
        valid_ids = geo['cedula_limpia'].fillna('').astype(str).str.strip() if 'cedula_limpia' in geo.columns else pd.Series('',index=geo.index)
        total_personas_geo = valid_ids[valid_ids.ne('')].nunique()
        total_provincias_geo = geo['provincia'].nunique()
        geo_cantones = geo[geo['canton_verificado'].ne('')].copy()
        total_cantones_geo = geo_cantones[['provincia','canton_verificado']].drop_duplicates().shape[0]
        c1,c2,c3,c4 = st.columns(4)
        c1.metric('📍 Provincias representadas', f'{total_provincias_geo:,}')
        c2.metric('🏙️ Cantones verificados', f'{total_cantones_geo:,}')
        c3.metric('📊 Registros territoriales', f'{total_geo:,}')
        c4.metric('👥 Identificaciones únicas', f'{total_personas_geo:,}')
        st.caption('Los indicadores muestran el universo filtrado; registros no equivalen necesariamente a matrículas o titulaciones.')

        provincias_geo = geo.groupby('provincia', as_index=False).size().rename(columns={'size':'Registros'})
        provincias_geo['Participación (%)'] = (provincias_geo['Registros'] / total_geo * 100).round(2) if total_geo else 0
        provincias_geo = provincias_geo.sort_values('Registros', ascending=False)
        top3 = provincias_geo.head(3)
        mapa_col, detalle_col = st.columns([1.12,1], gap='large')
        with mapa_col:
            st.markdown('<div class="geo-section">🌎 Mapa de participación provincial</div>', unsafe_allow_html=True)
            st.markdown('<div class="geo-footnote">Burbujas proporcionales al número de registros. Sitios aproximados al centro de cada provincia.</div>', unsafe_allow_html=True)
            mapa_data = provincias_geo.copy()
            mapa_data['lat'] = mapa_data['provincia'].map(lambda x: GEO_PROVINCIAS.get(x,{}).get('lat'))
            mapa_data['lon'] = mapa_data['provincia'].map(lambda x: GEO_PROVINCIAS.get(x,{}).get('lon'))
            mapa_data = mapa_data.dropna(subset=['lat','lon'])
            if not mapa_data.empty:
                fig_geo = px.scatter_geo(
                    mapa_data, lat='lat', lon='lon', size='Registros', color='Participación (%)',
                    hover_name='provincia', custom_data=['Registros','Participación (%)'],
                    size_max=48, color_continuous_scale=[[0,'#bfe4ff'],[.3,'#4ca8ec'],[1,'#064b98']],
                    projection='mercator'
                )
                fig_geo.update_traces(marker=dict(line=dict(width=1.3,color='#ffffff'),opacity=.87),
                    hovertemplate='<b>%{hovertext}</b><br>Registros: %{customdata[0]:,.0f}<br>Participación: %{customdata[1]:.1f}%<extra></extra>')
                fig_geo.update_geos(
                    scope='south america', center=dict(lat=-1.55,lon=-78.6),
                    projection_scale=5.0, showcoastlines=True, coastlinecolor='#8aaed0',
                    showcountries=True, countrycolor='#9bbad4', countrywidth=.8,
                    showland=True, landcolor='#eaf3fb', showocean=True, oceancolor='#d8efff',
                    showlakes=True, lakecolor='#d8efff', bgcolor='#f4faff',
                    lataxis_range=[-5.8,2.2], lonaxis_range=[-82.5,-75.0]
                )
                fig_geo.update_layout(height=500, margin=dict(l=0,r=0,t=0,b=0),
                    paper_bgcolor='white', coloraxis_colorbar=dict(title='%',thickness=10,len=.5))
                st.plotly_chart(fig_geo, use_container_width=True, key='geo2026_mapa')
                st.caption('Galápagos se encuentra fuera del encuadre continental. Sus registros se incluyen en los indicadores y la tabla.')
            else:
                st.info('No hay coordenadas disponibles para las provincias seleccionadas.')
        with detalle_col:
            st.markdown('<div class="geo-section"> Provincias con mayor participación</div>', unsafe_allow_html=True)
            ring_cols = st.columns(3)
            for idx, row in enumerate(top3.itertuples(index=False)):
                with ring_cols[idx]:
                    pct = float(provincias_geo.loc[provincias_geo['provincia'].eq(row.provincia), 'Participación (%)'].iloc[0])
                    ring = go.Figure(go.Pie(values=[pct, max(0,100-pct)],hole=.78,
                        marker=dict(colors=['#087fce','#e6edf5']),sort=False,textinfo='none',showlegend=False))
                    ring.update_layout(height=133,margin=dict(l=0,r=0,t=0,b=0),paper_bgcolor='rgba(0,0,0,0)',
                        annotations=[dict(text=f'<b>{pct:.1f}%</b>',x=.5,y=.5,showarrow=False,font=dict(size=17,color='#073d70'))])
                    st.plotly_chart(ring,use_container_width=True,key=f'geo2026_ring_{idx}',config={'displayModeBar':False})
                    st.markdown(f'<div style="text-align:center;font-weight:700;color:#123d68;font-size:12px">{row.provincia}</div>',unsafe_allow_html=True)
            st.markdown('<div class="geo-section">📋 Detalle de provincias</div>', unsafe_allow_html=True)
            st.dataframe(provincias_geo.rename(columns={'provincia':'Provincia'}),
                column_config={'Registros':st.column_config.NumberColumn('Registros',format='%d'),
                    'Participación (%)':st.column_config.ProgressColumn('Participación nacional',min_value=0,max_value=100,format='%.1f%%')},
                use_container_width=True,hide_index=True,height=300)
            st.download_button('⬇️ Exportar distribución provincial',
                data=provincias_geo.to_csv(index=False).encode('utf-8-sig'),
                file_name='EPESPO_distribucion_provincias.csv',mime='text/csv',use_container_width=True,key='geo2026_exportprov')

        st.markdown('---')
        st.markdown('<div class="geo-section">📈 Comparaciones y evolución territorial</div>', unsafe_allow_html=True)
        bottom1,bottom2 = st.columns([1,1],gap='large')
        with bottom1:
            ranking = provincias_geo.head(12).sort_values('Registros')
            fig_rank = px.bar(ranking,x='Registros',y='provincia',orientation='h',text='Registros',
                color='Registros',color_continuous_scale=['#b8e1fc','#218bd3','#075399'])
            fig_rank.update_traces(textposition='outside',cliponaxis=False)
            fig_rank.update_layout(title='Top 12 provincias por registros',height=440,showlegend=False,
                coloraxis_showscale=False,yaxis_title=None,xaxis_title='Registros',
                margin=dict(l=10,r=38,t=55,b=25),paper_bgcolor='white',plot_bgcolor='white',font=dict(color='#183f64'))
            st.plotly_chart(fig_rank,use_container_width=True,key='geo2026_ranking')
        with bottom2:
            tendencia = geo[geo['anio'].notna() & (geo['anio']>0)].copy()
            top_provs = provincias_geo.head(5)['provincia'].tolist()
            tendencia = tendencia[tendencia['provincia'].isin(top_provs)]
            if not tendencia.empty:
                serie = tendencia.groupby(['anio','provincia']).size().reset_index(name='Registros')
                fig_trend = px.line(serie,x='anio',y='Registros',color='provincia',markers=True,
                    color_discrete_sequence=['#064b98','#1383d4','#57b8ee','#0e9eb7','#a3c9e7'])
                fig_trend.update_layout(title='Evolución anual — principales provincias',height=440,
                    xaxis=dict(title='Año',tickformat='d'),yaxis_title='Registros',
                    margin=dict(l=10,r=10,t=55,b=25),paper_bgcolor='white',plot_bgcolor='white',
                    font=dict(color='#183f64'),legend_title_text='Provincia',hovermode='x unified')
                st.plotly_chart(fig_trend,use_container_width=True,key='geo2026_tendencia')
            else:
                st.info('No hay información temporal válida para representar tendencias.')

        # Análisis cantonal solo con información explícita y verificable.
        st.markdown('---')
        st.markdown('<div class="geo-section">🎯 Concentración territorial por cantón</div>',unsafe_allow_html=True)
        if geo_cantones.empty:
            st.warning('No se encontró un campo cantonal verificable en los registros. No se asignan cantones a partir de la cédula, porque esa inferencia no es fiable.')
            st.caption('Para activar el análisis cantonal, incorpore una columna denominada canton o canton_residencia en la fuente de datos.')
        else:
            cantones = geo_cantones.groupby(['provincia','canton_verificado'],as_index=False).size().rename(columns={'size':'Registros'})
            cantones['Participación nacional (%)'] = (cantones['Registros']/total_geo*100).round(2)
            ca,cb = st.columns([1,1],gap='large')
            with ca:
                fig_canton = px.scatter(cantones,x='Registros',y='Participación nacional (%)',
                    size='Registros',color='provincia',hover_name='canton_verificado',size_max=42)
                fig_canton.update_layout(title='Volumen y participación cantonal',height=410,
                    margin=dict(l=10,r=10,t=55,b=25),paper_bgcolor='white',plot_bgcolor='white',
                    legend_title_text='Provincia')
                st.plotly_chart(fig_canton,use_container_width=True,key='geo2026_cantonscatter')
            with cb:
                top_cantones = cantones.nlargest(10,'Registros').sort_values('Registros')
                fig_canton_rank = px.bar(top_cantones,x='Registros',y='canton_verificado',orientation='h',
                    text='Registros',color='Registros',color_continuous_scale=['#b8e1fc','#0a64af'])
                fig_canton_rank.update_layout(title='Top 10 cantones',height=410,
                    coloraxis_showscale=False,yaxis_title=None,margin=dict(l=10,r=35,t=55,b=25),
                    paper_bgcolor='white',plot_bgcolor='white')
                st.plotly_chart(fig_canton_rank,use_container_width=True,key='geo2026_cantonrank')
            st.dataframe(cantones.sort_values('Registros',ascending=False).rename(columns={'provincia':'Provincia','canton_verificado':'Cantón'}),
                use_container_width=True,hide_index=True,height=290)
            st.download_button('⬇️ Exportar cantones verificados',data=cantones.to_csv(index=False).encode('utf-8-sig'),
                file_name='EPESPO_cantones_verificados.csv',mime='text/csv',key='geo2026_exportcantones')


       
# -------------------------------------------------------------
# TAB 5: CUBIERTA VS. MÁQUINAS Y AUDITORÍA DE ESCALAFÓN JERÁRQUICO
# -------------------------------------------------------------
with tab_flota:
    st.subheader("Trayectoria Marítima y Auditoría de Escalafón Jerárquico")
    st.caption("Seguimiento individual por tripulante (DNI): análisis de cumplimiento hacia la máxima jerarquía, estancamientos y balance de flota.")

    df_personas = df_filtrado.copy()
    
    def id_seguro_persona(row):
        ced = str(row["cedula_limpia"]).strip()
        if ced.isdigit() and len(ced) >= 10 and ced != "0" * len(ced):
            return ced
        nom = str(row["nombres"]).strip()
        if nom and nom != "Sin Nombre":
            return f"Nom: {nom}"
        return f"Reg_Gen_{row.name}"

    df_personas["id_persona"] = df_personas.apply(id_seguro_persona, axis=1)

    resumen_jerarquia = df_personas.groupby("id_persona").agg(
        total_cursos=("curso", "count"),
        total_graduados=("condicion", lambda x: (x == "Graduado").sum()),
        max_escala=("escala_nautica", lambda x: list(x)),
        areas=("area_operativa", lambda x: list(x))
    ).reset_index()

    def alcanzo_maxima_jerarquia(escalas):
        return any("Mando Superior" in str(e) for e in escalas)

    resumen_jerarquia["llego_maxima"] = resumen_jerarquia["max_escala"].apply(alcanzo_maxima_jerarquia)

    total_estudio_flota = len(resumen_jerarquia)
    total_maxima_jerarquia = resumen_jerarquia["llego_maxima"].sum()
    total_sin_maxima = total_estudio_flota - total_maxima_jerarquia

    def determinar_tope_jerarquico(row):
        if row["llego_maxima"]:
            return "Cúspide: Mando Superior"
        escalas_str = str(row["max_escala"])
        if "Mandos Medios" in escalas_str:
            return "Tope en: Mandos Medios y Técnicos"
        elif "Tripulación Calificada" in escalas_str:
            return "Tope en: Tripulación Calificada"
        return "Tope en: Marinería Base y Artesanal"

    resumen_jerarquia["nivel_tope"] = resumen_jerarquia.apply(determinar_tope_jerarquico, axis=1)
    conteo_topes = resumen_jerarquia.groupby("nivel_tope", as_index=False)["id_persona"].count()
    conteo_topes.columns = ["Nivel Jerárquico", "Cantidad de Tripulantes"]

    orden_niveles = [
        "Tope en: Marinería Base y Artesanal",
        "Tope en: Tripulación Calificada",
        "Tope en: Mandos Medios y Técnicos",
        "Cúspide: Mando Superior"
    ]
    conteo_topes["Nivel Jerárquico"] = pd.Categorical(conteo_topes["Nivel Jerárquico"], categories=orden_niveles, ordered=True)
    conteo_topes = conteo_topes.sort_values("Nivel Jerárquico").dropna()

    fk1, fk2, fk3, fk4 = st.columns(4)
    fk1.metric("Tripulantes Evaluados", f"{total_estudio_flota:,}", "Base total única")
    fk2.metric("Alcanzaron Cúspide (Máxima Jerarquía)", f"{total_maxima_jerarquia:,}", f"{(total_maxima_jerarquia/total_estudio_flota*100):.1f}% de éxito directivo" if total_estudio_flota else "0%")
    fk3.metric("No Alcanzaron la Cúspide", f"{total_sin_maxima:,}", "En proceso o base operativa", delta_color="inverse")
    fk4.metric("Tasa de Ascenso Directivo", f"{(total_maxima_jerarquia/total_estudio_flota*100):.1f}%", "Efectividad institucional")

    st.markdown("---")
    
    col_emb1, col_emb2 = st.columns([1.3, 1])

    with col_emb1:
        st.markdown("#### ⚓ Embudo de Ascenso y Niveles de Escalafón en la Flota")
        st.caption("Visualización de conversión del talento: desde la marinería base hasta la cúspide.")

        fig_funnel = px.funnel(
            conteo_topes,
            x="Cantidad de Tripulantes",
            y="Nivel Jerárquico",
            color="Nivel Jerárquico",
            color_discrete_sequence=["#64748B", "#0EA5E9", "#0284C7", "#0052CC"],
            title="Estructura Piramidal del Escalafón Marítimo"
        )
        fig_funnel.update_traces(
            textinfo="value+percent initial",
            hovertemplate="<b>%{y}</b><br>Tripulantes: <b>%{x:,}</b><extra></extra>"
        )
        fig_funnel.update_layout(
            template="plotly_white",
            margin=dict(l=10, r=10, t=35, b=10),
            height=350,
            showlegend=False,
            xaxis=dict(title="Número de Tripulantes", gridcolor="#F1F5F9"),
            yaxis=dict(title="")
        )
        st.plotly_chart(fig_funnel, use_container_width=True)

    with col_emb2:
        st.markdown("#### 🎯 Diagnóstico de Retención y Cúspide")
        st.markdown("""
        * **Efectividad Piramidal:** El embudo refleja claramente la progresión y reducción natural de personal hacia las capitanías.
        * **Consistencia de Datos:** Las categorías han sido unificadas y estandarizadas globalmente en el sistema.
        """)
        
        st.dataframe(
            conteo_topes,
            column_config={
                "Nivel Jerárquico": "Escalafón Institucional",
                "Cantidad de Tripulantes": st.column_config.NumberColumn("Total Personas", format="%d")
            },
            use_container_width=True,
            hide_index=True
        )

    st.markdown("---")
    st.markdown("#### 🗺️ Mapa de Estructura Jerárquica por Bloques (Treemap)")
    st.caption("Visualización rectangular proporcional por Área Operativa, Escalafón Náutico y Condición de Egreso.")

    df_treemap = df_personas.groupby(["area_operativa", "escala_nautica", "condicion"]).size().reset_index(name="total_alumnos")
    
    fig_tree = px.treemap(
        df_treemap,
        path=["area_operativa", "escala_nautica", "condicion"],
        values="total_alumnos",
        color="area_operativa",
        color_discrete_map={
            "Área de Cubierta": "#0284C7",
            "Área de Máquinas": "#D97706",
            "Servicios y Apoyo Marítimo": "#64748B"
        },
        title="Distribución Proporcional de Tripulantes por Jerarquía"
    )
    fig_tree.update_traces(
        hovertemplate="<b>%{label}</b><br>Tripulantes: <b>%{value:,}</b><extra></extra>",
        textinfo="label+value"
    )
    fig_tree.update_layout(
        template="plotly_white",
        margin=dict(l=10, r=10, t=40, b=10),
        height=450
    )
    st.plotly_chart(fig_tree, use_container_width=True)

    st.markdown("---")
    col_fl1, col_fl2 = st.columns([2, 1])

    with col_fl1:
        df_areas = df_filtrado[df_filtrado["condicion"] == "Graduado"].groupby(["anio", "area_operativa"]).size().reset_index(name="titulados")
        fig_areas = px.line(
            df_areas,
            x="anio",
            y="titulados",
            color="area_operativa",
            markers=True,
            title="Evolución Temporal de Egresados: Cubierta vs. Máquinas",
            color_discrete_map={
                "Área de Cubierta": "#0052CC",
                "Área de Máquinas": "#D97706",
                "Servicios y Apoyo Marítimo": "#64748B"
            }
        )
        fig_areas.update_traces(line=dict(width=2.5), marker=dict(size=6), hovertemplate="<b>%{x}</b> (%{data.name}): <b>%{y:,}</b><extra></extra>")
        fig_areas.update_layout(
            template="plotly_white",
            xaxis=dict(title="Año", gridcolor="#F1F5F9"),
            yaxis=dict(title="Titulados", gridcolor="#F1F5F9"),
            margin=dict(l=10, r=10, t=30, b=10)
        )
        st.plotly_chart(fig_areas, use_container_width=True)

    with col_fl2:
        tot_cubierta = len(df_filtrado[(df_filtrado["area_operativa"] == "Área de Cubierta") & (df_filtrado["condicion"] == "Graduado")])
        tot_maquinas = len(df_filtrado[(df_filtrado["area_operativa"] == "Área de Máquinas") & (df_filtrado["condicion"] == "Graduado")])
        ratio_cm = (tot_cubierta / tot_maquinas) if tot_maquinas > 0 else tot_cubierta

        st.markdown("#### Ratio de Dotación de Flota")
        st.metric("Total Cubierta", f"{tot_cubierta:,} tripulantes")
        st.metric("Total Máquinas", f"{tot_maquinas:,} maquinistas")
        st.metric("Ratio Operativo (Cubierta / Máquinas)", f"{ratio_cm:.2f} a 1")

# -------------------------------------------------------------

# ============================================================
# EPESPO | ANÁLISIS DE VEDAS EN ECUADOR (2002-2026)
# ============================================================

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import unicodedata
from calendar import monthrange

# ============================================================
# 1. CONFIGURACIÓN GENERAL
# ============================================================

MESES = {
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
    12: "Diciembre"
}

COLORES = {
    "azul": "#1565C0",
    "azul_oscuro": "#0D47A1",
    "celeste": "#42A5F5",
    "turquesa": "#00838F",
    "gris": "#94A3B8",
    "claro": "#E3F2FD",
    "blanco": "#FFFFFF",
    "texto": "#263238"
}

COLORES_ESTADO = {
    "Documentado": "#1565C0",
    "Referencial": "#29B6F6",
    "Estimado": "#90A4AE"
}

# ============================================================
# 2. CALENDARIO REFERENCIAL DE VEDAS
# ============================================================

# IMPORTANTE:
# Este calendario contiene fechas documentadas,
# referenciales y estimadas.
#
# Los turnos A y B representan alternativas de veda,
# no necesariamente paralizaciones simultáneas.
#
# Las fechas sin respaldo nacional confirmado se
# utilizan exclusivamente para análisis exploratorio.
#
# La etiqueta "Documentado" identifica una referencia
# ecuatoriana previamente señalada, pero NO sustituye
# la verificación del acuerdo oficial aplicable.

VEDAS_ECUADOR = [

    (2002, "Única", "2002-12-01", "2002-12-31", "Referencial"),
    (2003, "Única", "2003-12-01", "2003-12-31", "Documentado"),

    (2004, "A", "2004-08-01", "2004-09-11", "Referencial"),
    (2005, "A", "2005-08-01", "2005-09-11", "Referencial"),
    (2006, "A", "2006-08-01", "2006-09-11", "Referencial"),
    (2007, "A", "2007-08-01", "2007-09-11", "Documentado"),
    (2008, "A", "2008-08-01", "2008-09-11", "Estimado"),

    (2009, "A", "2009-08-01", "2009-09-28", "Referencial"),
    (2009, "B", "2009-11-21", "2010-01-18", "Referencial"),

    (2010, "A", "2010-07-29", "2010-09-28", "Referencial"),
    (2010, "B", "2010-11-18", "2011-01-18", "Referencial"),

    (2011, "A", "2011-07-18", "2011-09-28", "Referencial"),
    (2011, "B", "2011-11-07", "2012-01-18", "Referencial"),

    (2012, "A", "2012-07-29", "2012-09-28", "Estimado"),
    (2012, "B", "2012-11-18", "2013-01-18", "Estimado"),

    (2013, "A", "2013-07-29", "2013-09-28", "Referencial"),
    (2013, "B", "2013-11-18", "2014-01-18", "Referencial"),

    (2014, "A", "2014-07-29", "2014-09-28", "Estimado"),
    (2014, "B", "2014-11-18", "2015-01-18", "Estimado"),

    (2015, "A", "2015-07-29", "2015-09-28", "Estimado"),
    (2015, "B", "2015-11-18", "2016-01-18", "Estimado"),

    (2016, "A", "2016-07-29", "2016-09-28", "Estimado"),
    (2016, "B", "2016-11-18", "2017-01-18", "Estimado"),

    (2017, "A", "2017-07-29", "2017-10-08", "Referencial"),
    (2017, "B", "2017-11-09", "2018-01-19", "Referencial"),

    (2018, "A", "2018-07-29", "2018-10-08", "Referencial"),
    (2018, "B", "2018-11-09", "2019-01-19", "Referencial"),

    (2019, "A", "2019-07-29", "2019-10-08", "Referencial"),
    (2019, "B", "2019-11-09", "2020-01-19", "Referencial"),

    (2020, "A", "2020-07-29", "2020-10-08", "Referencial"),
    (2020, "B", "2020-11-09", "2021-01-19", "Referencial"),

    (2021, "A", "2021-07-29", "2021-10-08", "Documentado"),
    (2021, "B", "2021-11-09", "2022-01-19", "Documentado"),

    (2022, "A", "2022-07-29", "2022-10-08", "Referencial"),
    (2022, "B", "2022-11-09", "2023-01-19", "Referencial"),

    (2023, "A", "2023-07-29", "2023-10-08", "Referencial"),
    (2023, "B", "2023-11-09", "2024-01-19", "Referencial"),

    (2024, "A", "2024-07-29", "2024-10-08", "Referencial"),
    (2024, "B", "2024-11-09", "2025-01-19", "Referencial"),

    (2025, "A", "2025-07-29", "2025-10-08", "Documentado"),
    (2025, "B", "2025-11-09", "2026-01-19", "Documentado"),

    (2026, "A", "2026-08-06", "2026-10-08", "Referencial"),
    (2026, "B", "2026-11-09", "2027-01-11", "Referencial"),
]


# ============================================================
# 3. FUNCIONES AUXILIARES
# ============================================================

def normalizar_texto(valor):
    """Normaliza texto para búsquedas y comparaciones."""

    if pd.isna(valor):
        return ""

    texto = str(valor).strip().lower()

    texto = "".join(
        caracter
        for caracter in unicodedata.normalize("NFD", texto)
        if unicodedata.category(caracter) != "Mn"
    )

    return texto


def obtener_calendario():

    df = pd.DataFrame(
        VEDAS_ECUADOR,
        columns=[
            "anio",
            "turno",
            "inicio",
            "fin",
            "estado"
        ]
    )

    df["inicio"] = pd.to_datetime(df["inicio"])
    df["fin"] = pd.to_datetime(df["fin"])

    df["dias"] = (
        df["fin"] - df["inicio"]
    ).dt.days + 1

    return df


def convertir_fechas(serie):
    """
    Convierte fechas con soporte para cadenas DD/MM/AAAA,
    fechas ISO y valores datetime de pandas.
    """

    if pd.api.types.is_datetime64_any_dtype(serie):
        return pd.to_datetime(
            serie,
            errors="coerce"
        ).dt.normalize()

    fechas = pd.to_datetime(
        serie,
        errors="coerce",
        dayfirst=True
    )

    return fechas.dt.normalize()


def preparar_datos(df, columna_fecha):

    datos = df.copy()

    # Si existe condición, filtrar graduados.
    if "condicion" in datos.columns:

        condicion = datos["condicion"].map(
            normalizar_texto
        )

        datos = datos[
            condicion.isin([
                "graduado",
                "graduada",
                "titulado",
                "titulada"
            ])
        ].copy()

    datos["fecha_analisis"] = convertir_fechas(
        datos[columna_fecha]
    )

    datos = datos[
        datos["fecha_analisis"].notna()
    ].copy()

    datos["anio_calendario"] = (
        datos["fecha_analisis"].dt.year
    )

    datos["mes_num"] = (
        datos["fecha_analisis"].dt.month
    )

    datos["mes_nombre"] = (
        datos["mes_num"].map(MESES)
    )

    return datos


def clasificar_vedas(datos, ventanas):

    datos = datos.copy()

    datos["en_veda"] = False
    datos["turno_veda"] = ""
    datos["periodo_veda"] = ""
    datos["respaldo_veda"] = ""
    datos["anio_veda"] = pd.NA

    # Una titulación puede coincidir con una o varias
    # ventanas, pero solo se cuenta una vez.

    for ventana in ventanas.itertuples(index=False):

        mascara = datos["fecha_analisis"].between(
            ventana.inicio,
            ventana.fin
        )

        datos.loc[mascara, "en_veda"] = True

        datos.loc[
            mascara, "turno_veda"
        ] += str(ventana.turno) + "; "

        datos.loc[
            mascara, "periodo_veda"
        ] += f"{ventana.anio}-{ventana.turno}; "

        datos.loc[
            mascara, "respaldo_veda"
        ] += str(ventana.estado) + "; "

        datos.loc[
            mascara, "anio_veda"
        ] = ventana.anio

    datos["clasificacion"] = datos["en_veda"].map({
        True: "Durante veda",
        False: "Fuera de veda"
    })

    return datos


def obtener_dias_mes_veda(inicio, fin, anio, mes):
    """
    Calcula cuántos días de una ventana corresponden
    exactamente al mes y año indicados.
    """

    primer_dia = pd.Timestamp(
        year=anio,
        month=mes,
        day=1
    )

    ultimo_dia = pd.Timestamp(
        year=anio,
        month=mes,
        day=monthrange(anio, mes)[1]
    )

    desde = max(inicio, primer_dia)
    hasta = min(fin, ultimo_dia)

    if desde > hasta:
        return 0

    return (hasta - desde).days + 1


def crear_calendario_mensual(ventanas, rango):
    """
    Construye el calendario por año y mes.
    También incluye enero del año siguiente cuando
    una veda seleccionada cruza de diciembre a enero.
    """

    registros = []

    anio_final = rango[1]

    if (
        not ventanas.empty
        and ventanas["fin"].dt.year.max() > anio_final
    ):
        anio_final += 1

    for anio in range(rango[0], anio_final + 1):

        for mes in range(1, 13):

            coincidencias = []

            for veda in ventanas.itertuples(index=False):

                dias = obtener_dias_mes_veda(
                    veda.inicio,
                    veda.fin,
                    anio,
                    mes
                )

                if dias > 0:

                    coincidencias.append({
                        "turno": veda.turno,
                        "inicio": veda.inicio,
                        "fin": veda.fin,
                        "estado": veda.estado,
                        "dias": dias,
                        "anio_normativo": veda.anio
                    })

            if coincidencias:

                turnos = sorted(
                    set(
                        str(v["turno"])
                        for v in coincidencias
                    )
                )

                # Se evita sumar días superpuestos.
                dias_cubiertos = set()

                for v in coincidencias:

                    inicio_mes = max(
                        v["inicio"],
                        pd.Timestamp(anio, mes, 1)
                    )

                    fin_mes = min(
                        v["fin"],
                        pd.Timestamp(
                            anio,
                            mes,
                            monthrange(anio, mes)[1]
                        )
                    )

                    for fecha in pd.date_range(
                        inicio_mes,
                        fin_mes,
                        freq="D"
                    ):
                        dias_cubiertos.add(fecha.date())

                dias_total = len(dias_cubiertos)

                if "A" in turnos and "B" in turnos:
                    codigo = 3
                    etiqueta_turno = "Turnos A y B"

                elif "A" in turnos:
                    codigo = 1
                    etiqueta_turno = "Turno A"

                elif "B" in turnos:
                    codigo = 2
                    etiqueta_turno = "Turno B"

                else:
                    codigo = 4
                    etiqueta_turno = "Período único"

                detalle = []

                for v in coincidencias:

                    detalle.append(
                        f"Año normativo: {v['anio_normativo']}"
                        f"<br>Turno: {v['turno']}"
                        f"<br>Inicio: {v['inicio']:%d/%m/%Y}"
                        f"<br>Fin: {v['fin']:%d/%m/%Y}"
                        f"<br>Días en este mes: {v['dias']}"
                        f"<br>Respaldo: {v['estado']}"
                    )

                descripcion = "<br><br>".join(detalle)

                estados = ", ".join(
                    sorted(
                        set(
                            v["estado"]
                            for v in coincidencias
                        )
                    )
                )

            else:

                codigo = 0
                dias_total = 0
                etiqueta_turno = "Sin ventana seleccionada"
                descripcion = (
                    "No hay una ventana de veda "
                    "representada para este mes."
                )
                estados = "Sin referencia seleccionada"

            registros.append({
                "anio": anio,
                "mes": mes,
                "mes_nombre": MESES[mes],
                "codigo": codigo,
                "dias_veda": dias_total,
                "turno": etiqueta_turno,
                "estado": estados,
                "detalle": descripcion
            })

    return pd.DataFrame(registros)


def detectar_columna_curso(df):

    candidatos = [
        "curso",
        "nombre_curso",
        "tipo_curso",
        "nom_curso",
        "capacitacion",
        "programa",
        "especialidad",
        "formacion",
        "nombre_del_curso"
    ]

    columnas = {
        normalizar_texto(c).replace(" ", "_"): c
        for c in df.columns
    }

    for candidato in candidatos:

        if candidato in columnas:
            return columnas[candidato]

    return None


# ============================================================
# 4. INTERFAZ PRINCIPAL
# ============================================================

with tab_vedas:

    st.subheader(
        "🎣 Análisis de Vedas en Ecuador (2002–2026)"
    )

    st.markdown("""
    Este módulo permite analizar la distribución de las
    titulaciones registradas por **EPESPO** durante los
    períodos de veda en Ecuador, identificando tendencias,
    coincidencias temporales y comportamientos por curso.
    """)

    calendario = obtener_calendario()

    # ========================================================
    # CALENDARIO HISTÓRICO DESPLEGABLE
    # ========================================================

    with st.expander(
        "📚 Consultar calendario de vedas 2002–2026",
        expanded=False
    ):

        tabla_calendario = calendario.copy()

        tabla_calendario["inicio"] = (
            tabla_calendario["inicio"]
            .dt.strftime("%d/%m/%Y")
        )

        tabla_calendario["fin"] = (
            tabla_calendario["fin"]
            .dt.strftime("%d/%m/%Y")
        )

        tabla_calendario = tabla_calendario.rename(
            columns={
                "anio": "Año",
                "turno": "Turno",
                "inicio": "Inicio",
                "fin": "Finalización",
                "estado": "Respaldo",
                "dias": "Duración (días)"
            }
        )

        st.dataframe(
            tabla_calendario,
            use_container_width=True,
            hide_index=True
        )

        st.info(
            "Las fechas referenciales y estimadas "
            "se incluyen con fines exploratorios. "
            "Los turnos A y B representan alternativas "
            "de paralización."
        )

    # ========================================================
    # FILTROS
    # ========================================================

    st.markdown("#### 🔎 Filtros del análisis")

    f1, f2, f3 = st.columns(3)

    with f1:

        rango = st.slider(
            "Rango de años",
            min_value=2002,
            max_value=2026,
            value=(2002, 2026),
            key="veda_rango_2026"
        )

    with f2:

        estados = st.multiselect(
            "Nivel de respaldo",
            [
                "Documentado",
                "Referencial",
                "Estimado"
            ],
            default=[
                "Documentado",
                "Referencial",
                "Estimado"
            ],
            key="veda_estados_2026"
        )

    with f3:

        columnas_fecha = [
            c for c in ["fecha", "fec_ini"]
            if c in df_filtrado.columns
        ]

        if not columnas_fecha:

            st.error(
                "No se encontró una columna de fecha "
                "compatible ('fecha' o 'fec_ini')."
            )
            st.stop()

        fecha_col = st.selectbox(
            "Fecha de referencia",
            columnas_fecha,
            key="veda_fecha_2026"
        )

    # Filtro opcional de turno
    turnos_disponibles = [
        t for t in ["A", "B", "Única"]
        if t in calendario["turno"].unique()
    ]

    turnos = st.multiselect(
        "Turnos de veda",
        options=turnos_disponibles,
        default=turnos_disponibles,
        key="veda_turnos_2026"
    )

    ventanas = calendario[
        calendario["anio"].between(*rango)
        & calendario["estado"].isin(estados)
        & calendario["turno"].isin(turnos)
    ].copy()

    if ventanas.empty:

        st.warning(
            "No existen ventanas para los filtros "
            "seleccionados."
        )

        st.stop()

    # ========================================================
    # PREPARACIÓN DE DATOS
    # ========================================================

    datos = preparar_datos(
        df_filtrado,
        fecha_col
    )

    # Se analiza el rango de años calendario seleccionado.
    # Enero puede coincidir con la veda del año anterior
    # si dicha ventana está incluida en los filtros.

    inicio_rango = pd.Timestamp(
        rango[0], 1, 1
    )

    fin_rango = pd.Timestamp(
        rango[1], 12, 31
    )

    datos = datos[
        datos["fecha_analisis"].between(
            inicio_rango,
            fin_rango
        )
    ].copy()

    if datos.empty:

        st.warning(
            "No existen titulaciones para "
            "los años seleccionados."
        )

        st.stop()

    datos = clasificar_vedas(
        datos,
        ventanas
    )

    # ========================================================
    # 5. INDICADORES KPI
   
    # ========================================================
   
    # ========================================================
  
    # ========================================================
    # 5. INDICADORES KPI - ESTILO EPESPO
    # ========================================================

    st.markdown("#### 📊 Indicadores de Titulación")

    # Cálculo de indicadores
    total = len(datos)
    durante = int(datos["en_veda"].sum())
    fuera = total - durante

    porcentaje = (
        (durante / total) * 100
        if total > 0 else 0
    )

    # Formato de valores
    total_fmt = f"{total:,}".replace(",", ".")
    durante_fmt = f"{durante:,}".replace(",", ".")
    fuera_fmt = f"{fuera:,}".replace(",", ".")
    porcentaje_fmt = f"{porcentaje:.1f}%"

    # CSS de las tarjetas
    st.markdown(
        """
        <style>
        .epespo-veda-kpi {
            background-color: #F2F7FD;
            border: 1px solid #D4E5F6;
            border-top: 4px solid #1680E8;
            border-radius: 16px;
            padding: 20px;
            min-height: 155px;
            box-sizing: border-box;
            box-shadow: 0 4px 14px rgba(15, 60, 110, 0.07);
            font-family: Arial, sans-serif;
        }

        .epespo-veda-kpi-title {
            font-size: 14px;
            font-weight: 400;
            color: #294760;
            margin-bottom: 14px;
        }

        .epespo-veda-kpi-value {
            font-size: 31px;
            font-weight: 750;
            color: #10449C;
            line-height: 1.15;
            margin-bottom: 12px;
        }

        .epespo-veda-kpi-detail {
            font-size: 14px;
            line-height: 1.4;
        }

        .epespo-veda-green {
            color: #00A83C;
        }

        .epespo-veda-red {
            color: #FF3030;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    # Función para generar cada tarjeta
    def tarjeta_veda(titulo, valor, detalle, color):

        return (
            '<div class="epespo-veda-kpi">'
            '<div class="epespo-veda-kpi-title">'
            + str(titulo) +
            '</div>'
            '<div class="epespo-veda-kpi-value">'
            + str(valor) +
            '</div>'
            '<div class="epespo-veda-kpi-detail '
            + str(color) + '">'
            + str(detalle) +
            '</div>'
            '</div>'
        )

    # Distribución en cuatro columnas
    k1, k2, k3, k4 = st.columns(4, gap="medium")

    with k1:
        st.markdown(
            tarjeta_veda(
                "Graduados Analizados",
                total_fmt,
                "↑ Base total de titulaciones",
                "epespo-veda-green"
            ),
            unsafe_allow_html=True
        )

    with k2:
        st.markdown(
            tarjeta_veda(
                "Coinciden con Veda",
                durante_fmt,
                f"↑ {porcentaje_fmt} del total analizado",
                "epespo-veda-green"
            ),
            unsafe_allow_html=True
        )

    with k3:
        st.markdown(
            tarjeta_veda(
                "Fuera de Ventanas",
                fuera_fmt,
                "↑ Sin coincidencia temporal",
                "epespo-veda-red"
            ),
            unsafe_allow_html=True
        )

    with k4:
        st.markdown(
            tarjeta_veda(
                "Porcentaje de Coincidencia",
                porcentaje_fmt,
                "↑ Coincidencia con vedas",
                "epespo-veda-green"
            ),
            unsafe_allow_html=True
        )

    st.markdown("---")

    # ========================================================
    # 6. SERIE DE TIEMPO - PRIMER GRÁFICO
    # ========================================================

    st.markdown(
        "#### 📈 Serie de Tiempo de Titulaciones"
    )

    agrupacion = st.radio(
        "Agrupación temporal",
        ["Anual", "Mensual"],
        horizontal=True,
        key="veda_serie_agrupacion_2026"
    )

    datos_veda = datos[
        datos["en_veda"]
    ].copy()

    if datos_veda.empty:

        st.info(
            "No se encontraron titulaciones "
            "coincidentes con las ventanas seleccionadas."
        )

    else:

        if agrupacion == "Anual":

            resumen_serie = (
                datos_veda.groupby("anio_calendario")
                .size()
                .reindex(
                    range(
                        rango[0],
                        rango[1] + 1
                    ),
                    fill_value=0
                )
                .rename_axis("Año")
                .reset_index(name="Titulaciones")
            )

            fig_serie = px.line(
                resumen_serie,
                x="Año",
                y="Titulaciones",
                markers=True,
                title=(
                    "Evolución Anual de Titulaciones "
                    "Coincidentes con Vedas"
                ),
                color_discrete_sequence=[
                    COLORES["azul"]
                ]
            )

            fig_serie.update_xaxes(
                dtick=1
            )

        else:

            datos_veda["periodo"] = (
                datos_veda["fecha_analisis"]
                .dt.to_period("M")
                .dt.to_timestamp()
            )

            resumen_serie = (
                datos_veda.groupby("periodo")
                .size()
                .reset_index(name="Titulaciones")
            )

            fig_serie = px.line(
                resumen_serie,
                x="periodo",
                y="Titulaciones",
                markers=True,
                title=(
                    "Evolución Mensual de Titulaciones "
                    "Coincidentes con Vedas"
                ),
                color_discrete_sequence=[
                    COLORES["azul"]
                ]
            )

        fig_serie.update_traces(
            line=dict(width=3),
            marker=dict(size=7),
            hovertemplate=(
                "Titulaciones: %{y}<extra></extra>"
            )
        )

        fig_serie.update_layout(
            template="plotly_white",
            height=430,
            yaxis_title="Número de titulaciones",
            hovermode="x unified",
            margin=dict(
                l=20,
                r=20,
                t=65,
                b=20
            )
        )

        st.plotly_chart(
            fig_serie,
            use_container_width=True
        )

    st.markdown("---")

    # ========================================================
    # 7. CALENDARIO VISUAL INTERACTIVO
  
    # ========================================================
    # 7. CALENDARIO VISUAL INTERACTIVO - EPESPO
    # ========================================================

    st.markdown("#### 🗓️ Calendario Histórico de Vedas")

    st.caption(
        "Consulta los períodos de veda por año y mes. "
        "Pasa el cursor sobre las celdas para conocer "
        "fechas, duración y nivel de respaldo."
    )

    # --------------------------------------------------------
    # SELECTORES DE VISUALIZACIÓN
    # --------------------------------------------------------

    col_vista, col_inicio = st.columns([1, 2])

    with col_vista:
        vista = st.selectbox(
            "Años a visualizar",
            options=[
                "5 años",
                "10 años",
                "Todos los años"
            ],
            index=1,
            key="veda_vista_calendario"
        )

    cantidad = {
        "5 años": 5,
        "10 años": 10,
        "Todos los años": rango[1] - rango[0] + 1
    }[vista]

    cantidad = min(
        cantidad,
        rango[1] - rango[0] + 1
    )

    if vista == "Todos los años":
        anio_inicio = rango[0]

        with col_inicio:
            st.info(
                f"Visualizando de {rango[0]} a {rango[1]}"
            )

    else:
        # Por defecto, mostrar los años más recientes.
        inicio_predeterminado = max(
            rango[0],
            rango[1] - cantidad + 1
        )

        with col_inicio:
            anio_inicio = st.selectbox(
                "Año inicial",
                options=list(
                    range(
                        rango[0],
                        rango[1] - cantidad + 2
                    )
                ),
                index=inicio_predeterminado - rango[0],
                key="veda_anio_inicio_calendario"
            )

    anio_fin = min(
        anio_inicio + cantidad - 1,
        rango[1]
    )

    # --------------------------------------------------------
    # PREPARAR CALENDARIO
    # --------------------------------------------------------

    calendario_visual = crear_calendario_mensual(
        ventanas,
        rango
    )

    calendario_visual = calendario_visual[
        calendario_visual["anio"].between(
            anio_inicio,
            anio_fin
        )
    ].copy()

    matriz = (
        calendario_visual.pivot(
            index="anio",
            columns="mes",
            values="codigo"
        )
        .reindex(
            index=range(anio_inicio, anio_fin + 1),
            columns=range(1, 13),
            fill_value=0
        )
        .fillna(0)
    )

    # --------------------------------------------------------
    # INFORMACIÓN INTERACTIVA
    # --------------------------------------------------------

    hover_texto = []

    for anio in matriz.index:

        fila_hover = []

        for mes in range(1, 13):

            registro = calendario_visual[
                (calendario_visual["anio"] == anio)
                & (calendario_visual["mes"] == mes)
            ].iloc[0]

            texto = (
                f"<b>{MESES[mes]} de {anio}</b>"
                f"<br>Período: {registro['turno']}"
                f"<br>Días de veda: {registro['dias_veda']}"
                f"<br>Respaldo: {registro['estado']}"
                f"<br><br>{registro['detalle']}"
            )

            fila_hover.append(texto)

        hover_texto.append(fila_hover)

    # --------------------------------------------------------
    # GRÁFICO COMPACTO
    # --------------------------------------------------------

    escala_colores = [
        [0.000, "#F1F5F9"],
        [0.199, "#F1F5F9"],
        [0.200, "#1565C0"],
        [0.399, "#1565C0"],
        [0.400, "#64B5F6"],
        [0.599, "#64B5F6"],
        [0.600, "#00838F"],
        [0.799, "#00838F"],
        [0.800, "#94A3B8"],
        [1.000, "#94A3B8"]
    ]

    fig_calendario = go.Figure()

    fig_calendario.add_trace(
        go.Heatmap(
            z=matriz.values,
            x=list(range(1, 13)),
            y=matriz.index.tolist(),
            zmin=0,
            zmax=4,
            colorscale=escala_colores,
            showscale=False,
            text=hover_texto,
            hovertemplate="%{text}<extra></extra>",
            xgap=3,
            ygap=3
        )
    )

    # Altura según los años seleccionados
    altura = max(
        190,
        len(matriz.index) * 24 + 80
    )

    fig_calendario.update_layout(
        template="plotly_white",
        height=altura,
        autosize=True,
        margin=dict(
            l=35,
            r=10,
            t=35,
            b=15
        ),
        xaxis=dict(
            tickmode="array",
            tickvals=list(range(1, 13)),
            ticktext=[
                "ENE", "FEB", "MAR", "ABR",
                "MAY", "JUN", "JUL", "AGO",
                "SEP", "OCT", "NOV", "DIC"
            ],
            side="top",
            showgrid=False,
            zeroline=False,
            fixedrange=True
        ),
        yaxis=dict(
            tickmode="array",
            tickvals=matriz.index.tolist(),
            ticktext=[
                str(anio)
                for anio in matriz.index
            ],
            autorange="reversed",
            tickfont=dict(size=11),
            showgrid=False,
            zeroline=False,
            fixedrange=True
        ),
        plot_bgcolor="#FFFFFF",
        paper_bgcolor="#FFFFFF"
    )

    st.plotly_chart(
        fig_calendario,
        use_container_width=True,
        config={
            "displayModeBar": False,
            "scrollZoom": False
        }
    )

    # --------------------------------------------------------
    # LEYENDA
    # --------------------------------------------------------

    st.markdown(
        """
        <div style="
            display:flex;
            flex-wrap:wrap;
            gap:18px;
            font-size:12px;
            color:#526579;
            margin:5px 0 12px 0;
        ">
            <span>🔵 Turno A</span>
            <span>🩵 Turno B</span>
            <span>🟢 Turnos A y B</span>
            <span>⚪ Sin ventana</span>
            <span>⬜ Período único</span>
        </div>
        """,
        unsafe_allow_html=True
    )

    st.caption(
        f"Mostrando {anio_inicio}–{anio_fin}. "
        "Los colores representan ventanas temporales "
        "de veda, no la cantidad de titulaciones."
    )

    st.markdown("---")


    # ========================================================
    # 8. COMPARACIÓN DURANTE Y FUERA DE VEDAS
    # ========================================================

    st.markdown(
        "#### 📊 Comparación de Titulaciones "
        "Durante y Fuera de Vedas"
    )

    resumen_comparacion = (
        datos.groupby(
            ["anio_calendario", "clasificacion"]
        )
        .size()
        .unstack(fill_value=0)
        .reindex(
            index=range(
                rango[0],
                rango[1] + 1
            ),
            fill_value=0
        )
    )

    for columna in [
        "Durante veda",
        "Fuera de veda"
    ]:

        if columna not in resumen_comparacion.columns:
            resumen_comparacion[columna] = 0

    resumen_comparacion = (
        resumen_comparacion[
            ["Durante veda", "Fuera de veda"]
        ]
        .reset_index()
        .rename(
            columns={
                "anio_calendario": "Año"
            }
        )
    )

    comparacion_larga = resumen_comparacion.melt(
        id_vars="Año",
        value_vars=[
            "Durante veda",
            "Fuera de veda"
        ],
        var_name="Clasificación",
        value_name="Titulaciones"
    )

    fig_comparacion = px.bar(
        comparacion_larga,
        x="Año",
        y="Titulaciones",
        color="Clasificación",
        barmode="stack",
        title=(
            "Titulaciones Anuales Según "
            "Coincidencia con Vedas"
        ),
        color_discrete_map={
            "Durante veda": COLORES["azul"],
            "Fuera de veda": COLORES["celeste"]
        }
    )

    fig_comparacion.update_layout(
        template="plotly_white",
        height=460,
        xaxis=dict(dtick=1),
        yaxis_title="Número de titulaciones",
        legend_title_text="Clasificación",
        hovermode="x unified",
        margin=dict(
            l=20,
            r=20,
            t=65,
            b=20
        )
    )

    st.plotly_chart(
        fig_comparacion,
        use_container_width=True
    )

    st.caption(
        "Las barras representan cantidades de "
        "titulaciones, no tasas ajustadas por la "
        "duración de las ventanas. 'Fuera de veda' "
        "significa fuera de las ventanas seleccionadas, "
        "no ausencia comprobada de una veda oficial."
    )

    st.markdown("---")

    # ========================================================
    # 9. DISTRIBUCIÓN POR TIPO DE CURSO
    # ========================================================

    st.markdown(
        "#### 🎓 Distribución de Titulaciones "
        "por Tipo de Curso"
    )

    columna_curso = detectar_columna_curso(
        datos
    )

    if columna_curso is None:

        st.info(
            "No se identificó automáticamente la "
            "columna de cursos. Verifica si tu base "
            "utiliza nombres como 'curso', "
            "'nombre_curso' o 'tipo_curso'."
        )

    else:

        datos_cursos = datos[
            datos["en_veda"]
        ].copy()

        datos_cursos["curso_analisis"] = (
            datos_cursos[columna_curso]
            .astype("string")
            .str.strip()
            .fillna("Sin especificar")
        )

        datos_cursos.loc[
            datos_cursos["curso_analisis"].eq(""),
            "curso_analisis"
        ] = "Sin especificar"

        if datos_cursos.empty:

            st.info(
                "No existen titulaciones coincidentes "
                "con vedas para analizar por curso."
            )

        else:

            cantidad_cursos = st.slider(
                "Número de cursos a visualizar",
                min_value=5,
                max_value=20,
                value=10,
                key="veda_top_cursos_2026"
            )

            resumen_cursos = (
                datos_cursos.groupby("curso_analisis")
                .size()
                .reset_index(name="Titulaciones")
                .sort_values(
                    "Titulaciones",
                    ascending=False
                )
                .head(cantidad_cursos)
            )

            fig_cursos = px.bar(
                resumen_cursos,
                x="Titulaciones",
                y="curso_analisis",
                orientation="h",
                text="Titulaciones",
                title=(
                    "Cursos con Mayor Número de "
                    "Titulaciones Coincidentes con Vedas"
                ),
                color="Titulaciones",
                color_continuous_scale="Blues"
            )

            fig_cursos.update_layout(
                template="plotly_white",
                height=max(
                    400,
                    42 * len(resumen_cursos) + 130
                ),
                yaxis=dict(
                    autorange="reversed",
                    title=""
                ),
                xaxis_title="Número de titulaciones",
                coloraxis_showscale=False,
                margin=dict(
                    l=25,
                    r=25,
                    t=65,
                    b=25
                )
            )

            fig_cursos.update_traces(
                textposition="outside",
                cliponaxis=False
            )

            st.plotly_chart(
                fig_cursos,
                use_container_width=True
            )

            curso_principal = resumen_cursos.iloc[0]

            st.info(
                "El curso con mayor cantidad de "
                "titulaciones coincidentes con las "
                "ventanas seleccionadas es "
                f"**{curso_principal['curso_analisis']}**, "
                f"con **{int(curso_principal['Titulaciones'])}** "
                "registros."
            )

    # ========================================================
    # 10. EXPORTACIÓN DE RESULTADOS
    # ========================================================

    st.markdown("---")

    st.markdown("#### 📥 Exportación del análisis")

    # Resumen agregado, sin mostrar registros individuales.
    exportacion = resumen_comparacion.copy()

    exportacion["Total"] = (
        exportacion["Durante veda"]
        + exportacion["Fuera de veda"]
    )

    exportacion["Porcentaje en veda"] = (
        exportacion["Durante veda"]
        .div(
            exportacion["Total"].replace(0, float("nan"))
        )
        .mul(100)
        .fillna(0)
        .round(2)
    )

    csv = exportacion.to_csv(
        index=False
    ).encode("utf-8-sig")

    st.download_button(
        label="📥 Descargar resumen de vedas CSV",
        data=csv,
        file_name=(
            "EPESPO_Analisis_Vedas_Ecuador_2002_2026.csv"
        ),
        mime="text/csv",
        key="veda_descarga_2026"
    )

    st.caption(
        "EPESPO | Análisis de Vedas en Ecuador "
        "(2002–2026). Resultados exploratorios "
        "basados en el calendario y filtros seleccionados."
    )




# -------------------------------------------------------------
# TAB 7: PROYECCIONES PREDICTIVAS
# -------------------------------------------------------------

with tab_pred:
    st.subheader("Modelos Predictivos de Demanda de Titulación (2026 - 2030)")

    col_cfg1, col_cfg2, col_cfg3 = st.columns(3)
    tipo_modelo = col_cfg1.selectbox(
        "Algoritmo Predictivo:",
        ["Regresión Lineal Simple", "Regresión Polinomial (Grado 2)"]
    )
    aislar_atipico = col_cfg2.checkbox(
        "Aislar Plan Extraordinario 2025 (Outlier)",
        value=True,
        help="Aislar la campaña masiva de 2025 produce proyecciones realistas."
    )
    confianza = col_cfg3.selectbox("Intervalo de Confianza:", [90, 95, 99], index=1)

    df_grad = df_filtrado[df_filtrado["condicion"] == "Graduado"]
    if aislar_atipico:
        df_grad = df_grad[df_grad["anio"] < 2025]

    serie_tiempo = df_grad.groupby("anio").size().reset_index(name="graduados")

    if len(serie_tiempo) >= 5:
        rango_a = pd.RangeIndex(start=int(serie_tiempo["anio"].min()), stop=int(serie_tiempo["anio"].max()) + 1, name="anio")
        serie_tiempo = serie_tiempo.set_index("anio").reindex(rango_a, fill_value=0).reset_index()

        X = serie_tiempo[["anio"]].values
        y = serie_tiempo["graduados"].values

        anios_fut = np.arange(2026, 2031).reshape(-1, 1)

        if "Polinomial" in tipo_modelo:
            poly = PolynomialFeatures(degree=2)
            X_poly = poly.fit_transform(X)
            modelo = LinearRegression().fit(X_poly, y)
            y_pred = modelo.predict(X_poly)
            r2 = r2_score(y, y_pred)
            rmse = np.sqrt(mean_squared_error(y, y_pred))
            predicciones = np.maximum(0, modelo.predict(poly.transform(anios_fut)))
        else:
            modelo = LinearRegression().fit(X, y)
            y_pred = modelo.predict(X)
            r2 = r2_score(y, y_pred)
            rmse = np.sqrt(mean_squared_error(y, y_pred))
            predicciones = np.maximum(0, modelo.predict(anios_fut))

        valor_z = {90: 1.645, 95: 1.96, 99: 2.576}[confianza]
        piso_minimo = max(int(serie_tiempo["graduados"].replace(0, np.nan).min(skipna=True) or 150), int(predicciones.min() * 0.35))
        limite_inf = np.maximum(piso_minimo, predicciones - valor_z * (rmse * 0.6))
        limite_sup = predicciones + valor_z * (rmse * 0.6)

        km1, km2, km3 = st.columns(3)
        km1.metric("Bondad de Ajuste (R²)", f"{r2:.3f}")
        km2.metric("Margen de Error (RMSE)", f"± {rmse:.1f} estudiantes")
        km3.metric("Graduados Estimados para 2026", f"{int(predicciones[0]):,} alumnos")

        fig_pred = go.Figure()
        df_real_comp = df_filtrado[df_filtrado["condicion"] == "Graduado"].groupby("anio").size().reset_index(name="graduados")
        fig_pred.add_trace(go.Scatter(
            x=df_real_comp["anio"],
            y=df_real_comp["graduados"],
            mode="lines+markers",
            name="Histórico Real",
            line=dict(color="#0A2540", width=3),
            marker=dict(size=6),
            hovertemplate="Año %{x}: <b>%{y:,}</b> graduados<extra></extra>"
        ))
        fig_pred.add_trace(go.Scatter(
            x=anios_fut.flatten(),
            y=np.round(predicciones),
            mode="lines+markers",
            name="Proyección del Modelo",
            line=dict(color="#0066CC", dash="dash", width=3),
            marker=dict(size=7),
            hovertemplate="Proyección %{x}: <b>%{y:,.0f}</b> alumnos<extra></extra>"
        ))
        fig_pred.add_trace(go.Scatter(
            x=np.concatenate([anios_fut.flatten(), anios_fut.flatten()[::-1]]),
            y=np.concatenate([limite_sup, limite_inf[::-1]]),
            fill="toself",
            fillcolor="rgba(0, 102, 204, 0.12)",
            line=dict(color="rgba(255,255,255,0)"),
            name=f"Banda de Confianza ({confianza}%)",
            hoverinfo="skip"
        ))
        fig_pred.update_layout(
            template="plotly_white",
            title=dict(text="<b>Curva de Demanda Estimada al Horizonte 2030</b>", font=dict(size=14, color="#1E293B")),
            hovermode="x unified",
            xaxis=dict(title="Año", gridcolor="#F1F5F9"),
            yaxis=dict(title="Egresados", gridcolor="#F1F5F9"),
            margin=dict(l=10, r=10, t=40, b=10),
            legend=dict(orientation="h", y=1.05, x=1, xanchor="right", title="")
        )
        st.plotly_chart(fig_pred, use_container_width=True)

        df_proy_tabla = pd.DataFrame({
            "Año": [int(a) for a in anios_fut.flatten()],
            "Estimación Nominal": np.round(predicciones).astype(int),
            "Escenario Pesimista (Mín)": np.round(limite_inf).astype(int),
            "Escenario Optimista (Máx)": np.round(limite_sup).astype(int)
        })

        st.dataframe(
            df_proy_tabla,
            column_config={
                "Año": st.column_config.NumberColumn("Año Proyectado", format="%d"),
                "Estimación Nominal": st.column_config.NumberColumn("Estimación Nominal", format="%d"),
                "Escenario Pesimista (Mín)": st.column_config.NumberColumn("Escenario Pesimista (Mín)", format="%d"),
                "Escenario Optimista (Máx)": st.column_config.NumberColumn("Escenario Optimista (Máx)", format="%d")
            },
            use_container_width=True,
            hide_index=True
        )
    else:
        st.warning("Se requieren al menos 5 períodos históricos para generar proyecciones.")

# -------------------------------------------------------------
# TAB 8: CICLOS, REINGRESOS Y DETECCIÓN DE ANOMALÍAS
# -------------------------------------------------------------

# =============================================================
# TAB 8: CICLOS, REINGRESOS Y DETECCIÓN DE ANOMALÍAS
# EPESPO | DISEÑO INSTITUCIONAL
# =============================================================

with tab_ciclos:

    st.markdown("""
    <style>
    .ciclo-hero {
        background: linear-gradient(115deg, #073565, #086EB4);
        border-radius: 16px;
        padding: 23px 27px;
        margin-bottom: 19px;
    }
    .ciclo-hero h2 {
        color: #FFFFFF !important;
        margin: 0;
        font-size: 25px;
        font-weight: 800;
    }
    .ciclo-hero p {
        color: #DCEEFF;
        font-size: 13px;
        margin: 8px 0 0;
    }
    .ciclo-section {
        background: linear-gradient(90deg, #073E74, #0879BC);
        border-radius: 11px;
        padding: 12px 18px;
        color: #FFFFFF;
        font-size: 16px;
        font-weight: 700;
        margin: 18px 0 12px;
    }
    </style>

    <div class="ciclo-hero">
        <h2>🔄 Ciclos Formativos y Reingresos</h2>
        <p>
            Análisis longitudinal de estudiantes, actividad
            histórica, trayectorias académicas y trámites.
        </p>
    </div>
    """, unsafe_allow_html=True)

    # =========================================================
    # 1. PREPARACIÓN DE DATOS
    # =========================================================

    df_avanzado = df_filtrado.copy()

    def ciclo_columna(nombre, defecto=""):
        if nombre not in df_avanzado.columns:
            df_avanzado[nombre] = defecto

    for columna in [
        "cedula_limpia",
        "nombres",
        "curso",
        "area_operativa",
        "tipo_tramite",
        "condicion"
    ]:
        ciclo_columna(columna)

    ciclo_columna("anio", np.nan)
    ciclo_columna("mes", np.nan)
    ciclo_columna("impresion", np.nan)

    df_avanzado["anio"] = pd.to_numeric(
        df_avanzado["anio"], errors="coerce"
    )

    df_avanzado["mes"] = pd.to_numeric(
        df_avanzado["mes"], errors="coerce"
    )

    df_avanzado["impresion"] = pd.to_numeric(
        df_avanzado["impresion"], errors="coerce"
    )

    for columna in [
        "cedula_limpia",
        "nombres",
        "curso",
        "area_operativa",
        "tipo_tramite",
        "condicion"
    ]:
        df_avanzado[columna] = (
            df_avanzado[columna]
            .fillna("")
            .astype(str)
            .str.strip()
        )

    # Identificación:
    # Se agrupan cédulas válidas por formato.
    # Los registros sin cédula utilizable se mantienen
    # separados para evitar fusionar personas distintas.

    cedulas_ciclo = df_avanzado["cedula_limpia"]

    cedulas_validas = (
        cedulas_ciclo.str.fullmatch(r"\d{10,}")
        & ~cedulas_ciclo.str.fullmatch(r"0+")
    ).fillna(False)

    df_avanzado["id_unico"] = [
        cedula if valida else f"SIN_ID_{indice}"
        for indice, (cedula, valida) in enumerate(
            zip(cedulas_ciclo, cedulas_validas)
        )
    ]

    df_avanzado["identidad_verificada"] = (
        cedulas_validas.to_numpy()
    )

    # Los duplicados documentales no representan
    # una nueva formación académica.

    df_formativo = df_avanzado[
        df_avanzado["impresion"] != 2
    ].copy()

    df_formativo["curso_normalizado"] = (
        df_formativo["curso"]
        .str.upper()
        .str.strip()
    )

    df_formativo["condicion_normalizada"] = (
        df_formativo["condicion"]
        .str.casefold()
    )

    df_formativo["area_operativa"] = (
        df_formativo["area_operativa"]
        .replace("", "Sin clasificar")
    )

    # Solo identificaciones utilizables para
    # los análisis de trayectoria personal.

    df_personas = df_formativo[
        df_formativo["identidad_verificada"]
    ].copy()

    # =========================================================
    # 2. PERFILES ACADÉMICOS
    # =========================================================

    if not df_personas.empty:

        df_perfiles = (
            df_personas
            .groupby("id_unico")
            .agg(
                total_registros=("curso", "size"),
                cursos_distintos=(
                    "curso_normalizado",
                    lambda s: s[
                        ~s.isin(["", "SIN ESPECIFICAR"])
                    ].nunique()
                ),
                primer_anio=("anio", "min"),
                ultimo_anio=("anio", "max"),
                total_aprobados=(
                    "condicion_normalizada",
                    lambda s: (s == "graduado").sum()
                )
            )
            .reset_index()
        )

        duplicados_por_persona = (
            df_avanzado[
                df_avanzado["identidad_verificada"]
                & df_avanzado["impresion"].eq(2)
            ]
            .groupby("id_unico")
            .size()
        )

        df_perfiles["total_duplicados"] = (
            df_perfiles["id_unico"]
            .map(duplicados_por_persona)
            .fillna(0)
            .astype(int)
        )

        df_perfiles["tipo_tripulante"] = np.select(
            [
                df_perfiles["cursos_distintos"] <= 1,
                df_perfiles["cursos_distintos"] == 2
            ],
            [
                "Una especialidad",
                "Dos especialidades"
            ],
            default="Tres o más especialidades"
        )

        df_perfiles["span_anios"] = (
            df_perfiles["ultimo_anio"]
            - df_perfiles["primer_anio"]
        )

    else:

        df_perfiles = pd.DataFrame(
            columns=[
                "id_unico",
                "total_registros",
                "cursos_distintos",
                "primer_anio",
                "ultimo_anio",
                "total_aprobados",
                "total_duplicados",
                "tipo_tripulante",
                "span_anios"
            ]
        )

    # =========================================================
    # 3. INDICADORES PRINCIPALES
    # =========================================================

    total_personas = len(df_perfiles)

    multicursos_n = (
        int(
            (df_perfiles["cursos_distintos"] > 1).sum()
        )
        if total_personas else 0
    )

    personas_duplicados = (
        df_avanzado[
            df_avanzado["identidad_verificada"]
            & df_avanzado["impresion"].eq(2)
        ]["id_unico"].nunique()
    )

    tasa_multicurso = (
        multicursos_n / total_personas * 100
        if total_personas else 0
    )

    promedio_especialidades = (
        df_perfiles["cursos_distintos"].mean()
        if total_personas else 0
    )

    st.markdown(
        '<div class="ciclo-section">'
        '📊 Indicadores de trayectoria académica'
        '</div>',
        unsafe_allow_html=True
    )

    k1, k2, k3, k4 = st.columns(4)

    k1.metric(
        "👥 Personas identificadas",
        f"{total_personas:,}"
    )

    k2.metric(
        "🔄 Personas multicurso",
        f"{multicursos_n:,}",
        f"{tasa_multicurso:.1f}%"
    )

    k3.metric(
        "📄 Personas con duplicados",
        f"{personas_duplicados:,}"
    )

    k4.metric(
        "📚 Especialidades por persona",
        f"{promedio_especialidades:.2f}"
    )

    st.caption(
        "Multicurso significa más de una especialidad "
        "distinta registrada. Los duplicados documentales "
        "no cuentan como nuevos cursos. Las personas sin "
        "identificación utilizable se excluyen de los "
        "indicadores de trayectoria individual."
    )

    # =========================================================
    # 4. FLUJO DE TRÁMITES Y CONDICIÓN
    # =========================================================

    st.markdown(
        '<div class="ciclo-section">'
        '🌊 Distribución de trámites y condición registrada'
        '</div>',
        unsafe_allow_html=True
    )

    st.caption(
        "El diagrama muestra asociaciones entre el tipo "
        "de trámite y la condición registrada. No implica "
        "una secuencia temporal ni una conversión causal."
    )

    df_sankey = df_avanzado.copy()

    df_sankey["tipo_tramite"] = (
        df_sankey["tipo_tramite"]
        .replace("", "Sin clasificar")
    )

    df_sankey["condicion"] = (
        df_sankey["condicion"]
        .replace("", "Sin condición registrada")
    )

    tabla_flujo = (
        df_sankey
        .groupby(
            ["tipo_tramite", "condicion"],
            dropna=False
        )
        .size()
        .reset_index(name="conteo")
    )

    if not tabla_flujo.empty:

        origenes = tabla_flujo[
            "tipo_tramite"
        ].unique().tolist()

        destinos = tabla_flujo[
            "condicion"
        ].unique().tolist()

        # Prefijos para impedir colisiones entre
        # nombres de trámites y condiciones.

        nodos_origen = [
            "Trámite: " + valor
            for valor in origenes
        ]

        nodos_destino = [
            "Condición: " + valor
            for valor in destinos
        ]

        etiquetas = nodos_origen + nodos_destino

        mapa_origen = {
            valor: i
            for i, valor in enumerate(origenes)
        }

        mapa_destino = {
            valor: len(origenes) + i
            for i, valor in enumerate(destinos)
        }

        fuentes = [
            mapa_origen[valor]
            for valor in tabla_flujo["tipo_tramite"]
        ]

        objetivos = [
            mapa_destino[valor]
            for valor in tabla_flujo["condicion"]
        ]

        fig_sankey = go.Figure(
            go.Sankey(
                arrangement="snap",
                node=dict(
                    label=etiquetas,
                    pad=22,
                    thickness=18,
                    color=(
                        ["#087AC2"] * len(origenes)
                        + ["#58B9E8"] * len(destinos)
                    ),
                    line=dict(
                        color="#FFFFFF",
                        width=1
                    )
                ),
                link=dict(
                    source=fuentes,
                    target=objetivos,
                    value=tabla_flujo[
                        "conteo"
                    ].tolist(),
                    color="rgba(8,122,194,0.22)"
                )
            )
        )

        fig_sankey.update_layout(
            height=370,
            paper_bgcolor="white",
            font=dict(
                family="Arial",
                size=12,
                color="#153B66"
            ),
            margin=dict(
                l=15,
                r=15,
                t=15,
                b=15
            )
        )

        st.plotly_chart(
            fig_sankey,
            use_container_width=True,
            key="ciclos_flujo_completo"
        )

    else:

        st.info(
            "No existen datos para mostrar el flujo."
        )

    # =========================================================
    # 5. MAPA DE CALOR Y TRAYECTORIA POR ÁREA
    # =========================================================

    st.markdown(
        '<div class="ciclo-section">'
        '🔥 Intensidad histórica y trayectoria formativa'
        '</div>',
        unsafe_allow_html=True
    )

    df_temporal = df_formativo.copy()

    df_temporal = df_temporal[
        df_temporal["anio"].between(1900, 2100)
    ].copy()

    df_meses = df_temporal[
        df_temporal["mes"].between(1, 12)
    ].copy()

    actividad_mensual = (
        df_meses
        .groupby(["anio", "mes"])
        .size()
        .reset_index(name="registros")
    )

    if not actividad_mensual.empty:

        periodo_pico = actividad_mensual.loc[
            actividad_mensual["registros"].idxmax()
        ]

        anio_pico = int(periodo_pico["anio"])
        mes_pico = int(periodo_pico["mes"])
        max_mensual = int(periodo_pico["registros"])

    else:

        anio_pico = None
        mes_pico = None
        max_mensual = 0

    meses_nombres = {
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
        12: "Diciembre"
    }

    st.markdown("##### Resumen temporal")

    kt1, kt2, kt3, kt4 = st.columns(4)

    kt1.metric(
        "Registros formativos",
        f"{len(df_temporal):,}"
    )

    kt2.metric(
        "Años con actividad",
        f"{df_temporal['anio'].nunique():,}"
    )

    kt3.metric(
        "Mes de mayor actividad",
        meses_nombres.get(
            mes_pico,
            "Sin datos"
        )
    )

    kt4.metric(
        "Máximo mensual",
        f"{max_mensual:,}",
        f"Año {anio_pico}"
        if anio_pico is not None
        else None
    )

    # =========================================================
    # 6. FILTROS VISUALES
    # =========================================================

    control_1, control_2 = st.columns(2)

    with control_1:

        escala_calor = st.selectbox(
            "Escala del mapa de calor",
            [
                "Contraste equilibrado",
                "Valores absolutos",
                "Comparación relativa por año"
            ],
            key="ciclos_calor_escala_final"
        )

    with control_2:

        vista_trayectoria = st.selectbox(
            "Visualización de trayectoria",
            [
                "Diagrama de cajas",
                "Distribución por rangos"
            ],
            key="ciclos_trayectoria_vista_final"
        )

    izquierda, derecha = st.columns(
        [1.15, 1],
        gap="large"
    )

    # =========================================================
    # 7. MAPA DE CALOR MEJORADO
    # =========================================================

    with izquierda:

        st.markdown(
            "#### 🗓️ Actividad académica por año y mes"
        )

        st.caption(
            "Identifica temporadas de mayor concentración "
            "de registros formativos."
        )

        if not actividad_mensual.empty:

            matriz = actividad_mensual.pivot_table(
                index="mes",
                columns="anio",
                values="registros",
                aggfunc="sum",
                fill_value=0
            )

            matriz = matriz.reindex(
                index=list(range(1, 13)),
                fill_value=0
            )

            anio_inicial = int(
                matriz.columns.min()
            )

            anio_final = int(
                matriz.columns.max()
            )

            matriz = matriz.reindex(
                columns=list(
                    range(
                        anio_inicial,
                        anio_final + 1
                    )
                ),
                fill_value=0
            )

            valores_reales = matriz.to_numpy(
                dtype=float
            )

            if escala_calor == "Contraste equilibrado":

                valores_visuales = np.log1p(
                    valores_reales
                )

                etiqueta_color = (
                    "Intensidad logarítmica"
                )

                max_escala = None

            elif escala_calor == "Comparación relativa por año":

                maximos = valores_reales.max(
                    axis=0
                )

                maximos = np.where(
                    maximos == 0,
                    1,
                    maximos
                )

                valores_visuales = (
                    valores_reales / maximos
                ) * 100

                etiqueta_color = (
                    "Intensidad anual (%)"
                )

                max_escala = 100

            else:

                valores_visuales = (
                    valores_reales.copy()
                )

                etiqueta_color = "Registros"

                max_escala = None

            fig_heat = go.Figure(
                go.Heatmap(
                    z=valores_visuales,
                    x=[
                        str(int(a))
                        for a in matriz.columns
                    ],
                    y=[
                        meses_nombres[m]
                        for m in range(1, 13)
                    ],
                    customdata=valores_reales,
                    colorscale=[
                        [0.00, "#F0F8FF"],
                        [0.10, "#D7ECFA"],
                        [0.30, "#8BC7ED"],
                        [0.55, "#3299D6"],
                        [0.80, "#0B65AB"],
                        [1.00, "#07396F"]
                    ],
                    zmin=0,
                    zmax=max_escala,
                    xgap=2,
                    ygap=2,
                    hovertemplate=(
                        "<b>%{y} de %{x}</b>"
                        "<br>Registros: "
                        "%{customdata:,.0f}"
                        "<extra></extra>"
                    ),
                    colorbar=dict(
                        title=dict(
                            text=etiqueta_color,
                            side="top"
                        ),
                        thickness=12,
                        len=0.70,
                        outlinewidth=0
                    )
                )
            )

            fig_heat.update_layout(
                height=470,
                paper_bgcolor="white",
                plot_bgcolor="white",
                font=dict(
                    family="Arial",
                    color="#173B60",
                    size=11
                ),
                margin=dict(
                    l=5,
                    r=10,
                    t=20,
                    b=55
                ),
                xaxis=dict(
                    title="Año",
                    type="category",
                    tickangle=-45,
                    showgrid=False
                ),
                yaxis=dict(
                    title=None,
                    autorange="reversed",
                    showgrid=False
                )
            )

            st.plotly_chart(
                fig_heat,
                use_container_width=True,
                key="ciclos_mapa_calor_final",
                config={
                    "displayModeBar": False
                }
            )

            st.caption(
                "Pasa el cursor por cada celda para "
                "consultar el número exacto de registros. "
                "La escala equilibrada mejora el contraste "
                "cuando existen meses con valores extremos."
            )

        else:

            st.info(
                "No existen registros con año y mes "
                "válidos para generar el mapa de calor."
            )

    # =========================================================
    # 8. TRAYECTORIA FORMATIVA POR ÁREA
    # =========================================================

    with derecha:

        st.markdown(
            "#### ⚓ Trayectoria académica por área"
        )

        st.caption(
            "Años transcurridos entre la primera y "
            "última participación formativa."
        )

        df_trayectoria = df_temporal[
            df_temporal["identidad_verificada"]
        ].copy()

        if not df_trayectoria.empty:

            df_intervalos = (
                df_trayectoria
                .groupby(
                    ["id_unico", "area_operativa"]
                )
                .agg(
                    primer_anio=("anio", "min"),
                    ultimo_anio=("anio", "max"),
                    registros=("curso", "size")
                )
                .reset_index()
            )

            df_intervalos["intervalo_anios"] = (
                df_intervalos["ultimo_anio"]
                - df_intervalos["primer_anio"]
            )

            df_intervalos = df_intervalos[
                df_intervalos[
                    "intervalo_anios"
                ].between(0, 110)
            ].copy()

        else:

            df_intervalos = pd.DataFrame(
                columns=[
                    "id_unico",
                    "area_operativa",
                    "primer_anio",
                    "ultimo_anio",
                    "registros",
                    "intervalo_anios"
                ]
            )

        colores_areas = {
            "Área de Cubierta": "#087AC2",
            "Área de Máquinas": "#10A1B4",
            "Servicios y Apoyo Marítimo": "#7894B1",
            "Sin clasificar": "#A6B4C5"
        }

        if not df_intervalos.empty:

            if vista_trayectoria == "Diagrama de cajas":

                fig_trayectoria = px.box(
                    df_intervalos,
                    x="intervalo_anios",
                    y="area_operativa",
                    color="area_operativa",
                    orientation="h",
                    points=False,
                    color_discrete_map=colores_areas,
                    labels={
                        "intervalo_anios": (
                            "Años entre registros"
                        ),
                        "area_operativa": (
                            "Área operativa"
                        )
                    }
                )

                fig_trayectoria.update_traces(
                    line=dict(width=2)
                )

                fig_trayectoria.update_layout(
                    xaxis=dict(
                        title=(
                            "Años entre primera "
                            "y última participación"
                        ),
                        rangemode="tozero",
                        gridcolor="#E9F0F7",
                        zeroline=False
                    ),
                    yaxis=dict(
                        title=None
                    ),
                    showlegend=False
                )

            else:

                df_intervalos["rango"] = pd.cut(
                    df_intervalos["intervalo_anios"],
                    bins=[
                        -0.1,
                        0.5,
                        2.5,
                        5.5,
                        10.5,
                        float("inf")
                    ],
                    labels=[
                        "Mismo año",
                        "1–2 años",
                        "3–5 años",
                        "6–10 años",
                        "11+ años"
                    ]
                )

                tabla_rangos = (
                    df_intervalos
                    .groupby(
                        [
                            "area_operativa",
                            "rango"
                        ],
                        observed=False
                    )
                    .size()
                    .reset_index(
                        name="Personas"
                    )
                )

                fig_trayectoria = px.bar(
                    tabla_rangos,
                    x="rango",
                    y="Personas",
                    color="area_operativa",
                    barmode="group",
                    color_discrete_map=colores_areas,
                    labels={
                        "rango": "Intervalo",
                        "area_operativa": "Área"
                    }
                )

                fig_trayectoria.update_layout(
                    xaxis_title="Intervalo de años",
                    yaxis_title="Personas por área",
                    legend=dict(
                        orientation="h",
                        y=-0.30,
                        x=0
                    )
                )

            fig_trayectoria.update_layout(
                height=470,
                paper_bgcolor="white",
                plot_bgcolor="white",
                font=dict(
                    family="Arial",
                    color="#173B60",
                    size=11
                ),
                margin=dict(
                    l=10,
                    r=15,
                    t=20,
                    b=70
                )
            )

            st.plotly_chart(
                fig_trayectoria,
                use_container_width=True,
                key="ciclos_trayectoria_final",
                config={
                    "displayModeBar": False
                }
            )

            st.caption(
                "Un intervalo de varios años no implica "
                "actividad continua. Cada persona puede "
                "aparecer en más de un área."
            )

        else:

            st.info(
                "No existen trayectorias identificables "
                "con años válidos."
            )

    # =========================================================
    # 9. TABLA DE RESUMEN POR ÁREA
    # =========================================================

    st.markdown(
        '<div class="ciclo-section">'
        '📋 Resumen estadístico por área operativa'
        '</div>',
        unsafe_allow_html=True
    )

    if not df_intervalos.empty:

        resumen_areas = (
            df_intervalos
            .groupby("area_operativa")
            .agg(
                Personas=("id_unico", "nunique"),
                Mediana=("intervalo_anios", "median"),
                Promedio=("intervalo_anios", "mean"),
                Maximo=("intervalo_anios", "max")
            )
            .reset_index()
        )

        resumen_areas = resumen_areas.rename(
            columns={
                "area_operativa": "Área operativa",
                "Mediana": "Mediana (años)",
                "Promedio": "Promedio (años)",
                "Maximo": "Máximo (años)"
            }
        )

        st.dataframe(
            resumen_areas,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Mediana (años)":
                    st.column_config.NumberColumn(
                        format="%.1f"
                    ),
                "Promedio (años)":
                    st.column_config.NumberColumn(
                        format="%.1f"
                    ),
                "Máximo (años)":
                    st.column_config.NumberColumn(
                        format="%.0f"
                    )
            }
        )

    else:

        st.info(
            "No existen datos suficientes "
            "para elaborar el resumen por área."
        )

    # =========================================================
    # 10. TENDENCIA HISTÓRICA
    # =========================================================

    st.markdown(
        '<div class="ciclo-section">'
        '📈 Evolución histórica de la actividad formativa'
        '</div>',
        unsafe_allow_html=True
    )

    st.caption(
        "Volumen anual de registros formativos, "
        "sin incluir duplicados documentales."
    )

    tendencia_anual = (
        df_temporal
        .groupby("anio")
        .size()
        .reset_index(name="Registros")
        .sort_values("anio")
    )

    if not tendencia_anual.empty:

        tendencia_anual["anio"] = (
            tendencia_anual["anio"].astype(int)
        )

        fig_tendencia = go.Figure()

        fig_tendencia.add_trace(
            go.Scatter(
                x=tendencia_anual["anio"],
                y=tendencia_anual["Registros"],
                mode="lines+markers",
                name="Registros formativos",
                line=dict(
                    color="#087AC2",
                    width=3,
                    shape="spline"
                ),
                marker=dict(
                    size=8,
                    color="#FFFFFF",
                    line=dict(
                        color="#087AC2",
                        width=2
                    )
                ),
                fill="tozeroy",
                fillcolor="rgba(8,122,194,0.09)",
                hovertemplate=(
                    "<b>Año %{x}</b>"
                    "<br>Registros: %{y:,.0f}"
                    "<extra></extra>"
                )
            )
        )

        # Promedio móvil de 3 años, solo si existe
        # información suficiente.

        if len(tendencia_anual) >= 3:

            tendencia_anual["media_movil"] = (
                tendencia_anual["Registros"]
                .rolling(
                    window=3,
                    min_periods=3
                )
                .mean()
            )

            fig_tendencia.add_trace(
                go.Scatter(
                    x=tendencia_anual["anio"],
                    y=tendencia_anual["media_movil"],
                    mode="lines",
                    name="Promedio móvil (3 años)",
                    line=dict(
                        color="#F29B38",
                        width=3,
                        dash="dash"
                    ),
                    hovertemplate=(
                        "Promedio móvil: %{y:,.1f}"
                        "<extra></extra>"
                    )
                )
            )

        fig_tendencia.update_layout(
            height=395,
            paper_bgcolor="white",
            plot_bgcolor="white",
            font=dict(
                family="Arial",
                color="#173B60"
            ),
            margin=dict(
                l=15,
                r=20,
                t=25,
                b=35
            ),
            xaxis=dict(
                title="Año",
                tickformat="d",
                gridcolor="#F0F4F9"
            ),
            yaxis=dict(
                title="Registros formativos",
                rangemode="tozero",
                gridcolor="#E9F0F7"
            ),
            legend=dict(
                orientation="h",
                y=1.13,
                x=0
            ),
            hovermode="x unified"
        )

        st.plotly_chart(
            fig_tendencia,
            use_container_width=True,
            key="ciclos_tendencia_final"
        )

    else:

        st.info(
            "No existen años válidos para "
            "generar la tendencia histórica."
        )

    # =========================================================
    # 11. DETECCIÓN DESCRIPTIVA DE AÑOS ATÍPICOS
    # =========================================================

    st.markdown(
        '<div class="ciclo-section">'
        '🔎 Detección de actividad anual atípica'
        '</div>',
        unsafe_allow_html=True
    )

    if len(tendencia_anual) >= 4:

        q1 = tendencia_anual["Registros"].quantile(
            0.25
        )

        q3 = tendencia_anual["Registros"].quantile(
            0.75
        )

        iqr = q3 - q1

        limite_superior = q3 + 1.5 * iqr
        limite_inferior = max(
            0,
            q1 - 1.5 * iqr
        )

        anomalias = tendencia_anual[
            (tendencia_anual["Registros"] > limite_superior)
            | (tendencia_anual["Registros"] < limite_inferior)
        ].copy()

        if not anomalias.empty:

            anomalias["Diagnóstico"] = np.where(
                anomalias["Registros"] > limite_superior,
                "Actividad inusualmente alta",
                "Actividad inusualmente baja"
            )

            st.dataframe(
                anomalias[
                    [
                        "anio",
                        "Registros",
                        "Diagnóstico"
                    ]
                ].rename(
                    columns={
                        "anio": "Año"
                    }
                ),
                use_container_width=True,
                hide_index=True
            )

        else:

            st.success(
                "No se identificaron años atípicos "
                "mediante el criterio estadístico IQR."
            )

        st.caption(
            "La detección utiliza el rango "
            "intercuartílico (1.5 × IQR). "
            "Una observación atípica no implica "
            "necesariamente un error de datos."
        )

    else:

        st.info(
            "Se requieren al menos cuatro años "
            "con actividad para evaluar valores atípicos."
        )

    # =========================================================
    # 12. PERFIL DE RECURRENCIA FORMATIVA
    # =========================================================

    st.markdown(
        '<div class="ciclo-section">'
        '🎓 Perfil de especialización y multicurso'
        '</div>',
        unsafe_allow_html=True
    )

    if not df_perfiles.empty:

        distribucion_perfiles = (
            df_perfiles["tipo_tripulante"]
            .value_counts()
            .reset_index()
        )

        distribucion_perfiles.columns = [
            "Perfil",
            "Personas"
        ]

        col_rec_1, col_rec_2 = st.columns(
            [1, 1]
        )

        with col_rec_1:

            fig_perfiles = px.pie(
                distribucion_perfiles,
                names="Perfil",
                values="Personas",
                hole=0.67,
                color_discrete_sequence=[
                    "#087AC2",
                    "#4AB4E7",
                    "#A8DDF5"
                ]
            )

            fig_perfiles.update_traces(
                textinfo="percent",
                textposition="outside",
                marker=dict(
                    line=dict(
                        color="white",
                        width=3
                    )
                )
            )

            fig_perfiles.update_layout(
                height=355,
                paper_bgcolor="white",
                margin=dict(
                    l=10,
                    r=10,
                    t=15,
                    b=15
                ),
                legend=dict(
                    orientation="h",
                    y=-0.10
                ),
                font=dict(
                    color="#173B60"
                )
            )

            st.plotly_chart(
                fig_perfiles,
                use_container_width=True,
                key="ciclos_perfiles_final"
            )

        with col_rec_2:

            st.markdown(
                "##### Distribución de personas por perfil"
            )

            distribucion_perfiles[
                "Participación (%)"
            ] = (
                distribucion_perfiles["Personas"]
                / total_personas * 100
            ).round(1)

            st.dataframe(
                distribucion_perfiles,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Participación (%)":
                        st.column_config.ProgressColumn(
                            min_value=0,
                            max_value=100,
                            format="%.1f%%"
                        )
                }
            )

            st.caption(
                "La clasificación se basa en el "
                "número de especialidades distintas, "
                "no en la cantidad de documentos emitidos."
            )

    else:

        st.info(
            "No existen identificaciones suficientes "
            "para calcular perfiles multicurso."
        )

    # =========================================================
    # 13. TOP 10 DE MAYOR DIVERSIDAD ACADÉMICA
    # =========================================================

    st.markdown(
        '<div class="ciclo-section">'
        '🏆 Top 10 de trayectorias multicurso'
        '</div>',
        unsafe_allow_html=True
    )

    if not df_perfiles.empty:

        top_multicurso = (
            df_perfiles
            .sort_values(
                [
                    "cursos_distintos",
                    "total_registros"
                ],
                ascending=False
            )
            .head(10)
            .copy()
        )

        tabla_top = top_multicurso[
            [
                "id_unico",
                "cursos_distintos",
                "total_registros",
                "total_aprobados",
                "primer_anio",
                "ultimo_anio",
                "total_duplicados"
            ]
        ].rename(
            columns={
                "id_unico": "Identificación",
                "cursos_distintos": "Especialidades",
                "total_registros": "Registros formativos",
                "total_aprobados": "Registros graduados",
                "primer_anio": "Primer año",
                "ultimo_anio": "Último año",
                "total_duplicados": "Duplicados"
            }
        )

        st.dataframe(
            tabla_top,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Especialidades":
                    st.column_config.NumberColumn(
                        format="%d"
                    ),
                "Registros formativos":
                    st.column_config.NumberColumn(
                        format="%d"
                    ),
                "Registros graduados":
                    st.column_config.NumberColumn(
                        format="%d"
                    ),
                "Duplicados":
                    st.column_config.NumberColumn(
                        format="%d"
                    )
            }
        )

        st.caption(
            "Tabla de uso interno. Contiene "
            "identificaciones personales y debe "
            "consultarse únicamente por usuarios "
            "institucionales autorizados."
        )

        # =====================================================
        # 14. EXPORTACIÓN
        # =====================================================

        csv_perfiles = (
            df_perfiles
            .to_csv(index=False)
            .encode("utf-8-sig")
        )

        st.download_button(
            "📥 Descargar análisis de trayectorias",
            data=csv_perfiles,
            file_name=(
                "EPESPO_ciclos_y_trayectorias.csv"
            ),
            mime="text/csv",
            use_container_width=True,
            key="ciclos_exportacion_final"
        )

    else:

        st.info(
            "No existen trayectorias para mostrar."
        )

    st.markdown("---")

    st.caption(
        "EPESPO | Suite Analítica y Estratégica Marítima. "
        "Resultados basados en los registros disponibles "
        "y en los filtros globales seleccionados."
    )

# =============================================================
# FIN DE LA PESTAÑA 8
# =============================================================
    

# =============================================================
# CIERRE DE SESIÓN AL FONDO ABSOLUTO DE LA BARRA LATERAL
# =============================================================
st.sidebar.markdown("<br><br><br><br><br>", unsafe_allow_html=True)
st.sidebar.markdown("---")
if st.sidebar.button("🔒 Cerrar Sesión", use_container_width=True):
    cerrar_sesion()