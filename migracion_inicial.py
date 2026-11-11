import pandas as pd
from sqlalchemy import create_engine

# Ajusta el nombre de la base de datos a 'Epespo-Analisis' o 'epespo_db' según tu caso
DATABASE_URL = "postgresql://postgres:qwerty@localhost:5432/Epespo-Analisis"  # Cambia esto según tu configuración
EXCEL_FILE = "titulados_epespo.xlsx"

print("📂 Leyendo hoja consolidada del Excel...")
df = pd.read_excel(EXCEL_FILE, sheet_name="totaltituladosv3")

# Tratamiento de Fechas y Años
df["fecha_dt"] = pd.to_datetime(df["fecha"], errors="coerce")
df["anio"] = df["fecha_dt"].dt.year.fillna(0).astype(int)
df["mes"] = df["fecha_dt"].dt.month.fillna(0).astype(int)

# Provincias por Cédula Ecuatoriana
provincias = {
    1: "Azuay",
    2: "Bolívar",
    3: "Cañar",
    4: "Carchi",
    5: "Cotopaxi",
    6: "Chimborazo",
    7: "El Oro",
    8: "Esmeraldas",
    9: "Guayas",
    10: "Imbabura",
    11: "Loja",
    12: "Los Ríos",
    13: "Manabí",
    14: "Morona Santiago",
    15: "Napo",
    16: "Pastaza",
    17: "Pichincha",
    18: "Tungurahua",
    19: "Zamora Chinchipe",
    20: "Galápagos",
    21: "Sucumbíos",
    22: "Orellana",
    23: "Santo Domingo",
    24: "Santa Elena",
}


def obtener_provincia(val):
    s = str(val).strip().zfill(10)
    if s.isdigit() and len(s) == 10:
        cod = int(s[:2])
        return provincias.get(cod, "Otra")
    return "No registrada"


df["provincia"] = df["nced_nomi"].apply(obtener_provincia)


# Estandarización de Cursos Técnicos
def homologar_curso(txt):
    if not isinstance(txt, str):
        return "Otro Curso"
    t = txt.strip().upper()
    if "MARINERO PESCADOR" in t:
        return "Marinero Pescador"
    elif "PESCADOR ARTESANAL" in t:
        return "Pescador Artesanal"
    elif "OPERADOR DE MAQUINAS" in t:
        return "Operador de Máquinas de B/P"
    elif (
        "MARINERO DE MAQUINAS" in t
        or "MARINERO PRIMERA DE MAQUINAS" in t
        or "MARIMERO" in t
    ):
        return "Marinero de Máquinas de B/P"
    elif (
        "PATRON DE PESCA DE ALTURA" in t
        or "PATRON DE ALTURA" in t
        or "CAPITAN" in t
    ):
        return "Patrón / Capitán de Pesca de Altura"
    elif "PATRÓN DE PESCA COSTANERO" in t or "PATRON COSTANERO" in t:
        return "Patrón de Pesca Costanero"
    elif "PATRON DE PESCA ARTESANAL" in t:
        return "Patrón de Pesca Artesanal"
    elif (
        "JEFE DE MAQUINAS" in t
        or "PRIMER OFICIAL DE MAQUINAS" in t
        or "MAQUINISTA" in t
    ):
        return "Oficial / Maquinista de Buque Pesquero"
    elif "JEFE DE CUBIERTA" in t:
        return "Jefe de Cubierta de B/P"
    elif "PUENTE" in t or "TIMONEL" in t:
        return "Timonel / Marinero de Puente"
    elif "MOTORISTA" in t:
        return "Motorista de Buque Pesquero"
    return t.title()


df["curso"] = df["titulo"].apply(homologar_curso)


# Homologación de Modalidades
def homologar_modalidad(txt):
    if not isinstance(txt, str):
        return "Sin registro"
    m = txt.strip().upper()
    if "NIVELACION" in m:
        return "Nivelación"
    elif "CAPACITACI" in m:
        return "Capacitación"
    elif "REGULAR" in m or "FORMACION" in m:
        return "Formación Regular"
    elif "ASCENSO" in m:
        return "Ascenso"
    elif "LIBRE" in m or "E.L.D." in m:
        return "Estudio Libre Dirigido"
    elif "PERFECCIONAMIENTO" in m:
        return "Perfeccionamiento"
    return "Otras Modalidades"


df["modalidad"] = df["estudio"].apply(homologar_modalidad)

# Condición Académica
df["condicion"] = df["estado"].apply(
    lambda x: (
        "Graduado"
        if "cumple" in str(x).lower() and "no" not in str(x).lower()
        else "No culminó"
    )
)

# Estructurar DataFrame Final con datos personales y de titulación
df_final = pd.DataFrame(
    {
        "cedula": (
            df["nced_nomi"]
            .astype(str)
            .str.strip()
            .replace("nan", None)
            .replace("None", None)
        ),
        "nombres": (
            df["apellidos_"]
            .astype(str)
            .str.strip()
            .replace("nan", "SIN NOMBRE")
        ),
        "matricula": (
            df["num_matric"]
            .astype(str)
            .str.strip()
            .replace("nan", None)
            .replace("None", None)
        ),
        "anio": df["anio"],
        "mes": df["mes"],
        "fecha": df["fecha_dt"].dt.date,
        "curso": df["curso"],
        "modalidad": df["modalidad"],
        "provincia": df["provincia"],
        "condicion": df["condicion"],
    }
)
df_final = df_final[df_final["anio"] >= 2002]

print(f"📊 Registros preparados: {len(df_final):,}")
print("🚀 Cargando en PostgreSQL...")

engine = create_engine(DATABASE_URL)
df_final.to_sql(
    "graduados_epespo",
    con=engine,
    if_exists="append",
    index=False,
    chunksize=1000,
)
print("✅ ¡Base de datos repoblada con éxito!")