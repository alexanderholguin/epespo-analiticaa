import hashlib
import hmac
import streamlit as st


# ============================================================
# EPESPO - SISTEMA DE AUTENTICACIÓN INSTITUCIONAL
# ============================================================


# ============================================================
# 1. VERIFICACIÓN DE CREDENCIALES
# ============================================================

def verificar_credenciales(usuario, password):
    usuario = usuario.strip().lower()
    usuarios_dict = st.secrets.get("users", {})
    
    if usuario not in usuarios_dict:
        return None

    datos = usuarios_dict[usuario]
    password_hash = str(datos.get("password_hash", ""))
    
    if len(password_hash) != 64:
        return None

    hash_ingresado = hashlib.sha256(password.encode("utf-8")).hexdigest()
    
    if hmac.compare_digest(password_hash, hash_ingresado):
        return {
            "nombre": str(datos.get("name", usuario)),
            "rol": str(datos.get("role", "")),
        }

    return None


# ============================================================
# 2. ESTILOS DEL LOGIN
# ============================================================

def aplicar_estilos_login():
    st.markdown(
        """
        <style>
        /* FONDO GENERAL */
        .stApp {
            background:
                radial-gradient(
                    circle at 85% 15%,
                    #E0F2FE 0%,
                    transparent 40%
                ),
                linear-gradient(
                    135deg,
                    #F5F9FE 0%,
                    #EAF3FC 100%
                );
        }

        /* CONTENEDOR PRINCIPAL */
        .block-container {
            max-width: 1100px;
            padding-top: 2rem;
            padding-bottom: 2rem;
        }

        /* OCULTAR DECORACIÓN SUPERIOR */
        [data-testid="stDecoration"] {
            display: none;
        }

        /* ENCABEZADO INSTITUCIONAL */
        .epespo-header {
            text-align: center;
            padding: 24px 15px 12px;
        }

        .epespo-logo {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            width: 78px;
            height: 78px;
            background: linear-gradient(135deg, #0A376D, #1976D2);
            border-radius: 22px;
            color: #FFFFFF;
            font-size: 38px;
            box-shadow: 0 10px 25px rgba(21, 101, 192, 0.20);
            margin-bottom: 20px;
        }

        .epespo-title {
            color: #103B70;
            font-size: 29px;
            font-weight: 800;
            letter-spacing: -0.5px;
            margin-bottom: 8px;
        }

        .epespo-subtitle {
            color: #64748B;
            font-size: 14px;
            line-height: 1.8;
        }

        .epespo-divider {
            width: 75px;
            height: 4px;
            background: linear-gradient(90deg, #0D47A1, #64B5F6);
            border-radius: 10px;
            margin: 20px auto 28px;
        }

        /* FORMULARIO */
        div[data-testid="stForm"] {
            background: #FFFFFF;
            border: 1px solid #DCE8F5;
            border-top: 4px solid #1976D2;
            border-radius: 18px;
            padding: 30px 28px;
            box-shadow: 0 12px 35px rgba(15, 54, 102, 0.09);
        }

        /* CAMPOS DE TEXTO */
        div[data-testid="stTextInput"] label {
            color: #254B70;
            font-weight: 600;
            font-size: 14px;
        }

        div[data-testid="stTextInput"] input {
            border-radius: 9px;
            border: 1px solid #D6E3F0;
            background: #FAFCFF;
            color: #17324D;
        }

        div[data-testid="stTextInput"] input:focus {
            border-color: #1976D2;
            box-shadow: 0 0 0 1px rgba(25, 118, 210, 0.12);
        }

        /* BOTÓN PRINCIPAL */
        div[data-testid="stFormSubmitButton"] button {
            width: 100%;
            min-height: 47px;
            background: linear-gradient(90deg, #0D47A1, #1976D2);
            color: #FFFFFF;
            border: none;
            border-radius: 10px;
            font-size: 15px;
            font-weight: 700;
            transition: all 0.2s ease;
        }

        div[data-testid="stFormSubmitButton"] button:hover {
            background: linear-gradient(90deg, #083778, #1565C0);
            color: #FFFFFF;
            border: none;
            box-shadow: 0 6px 16px rgba(21, 101, 192, 0.20);
        }

        /* PIE INSTITUCIONAL */
        .epespo-footer {
            text-align: center;
            color: #7A8DA3;
            font-size: 12px;
            line-height: 1.8;
            padding-top: 30px;
        }

        @media (max-width: 768px) {
            .epespo-title {
                font-size: 22px;
            }
            .epespo-subtitle {
                font-size: 12px;
            }
            div[data-testid="stForm"] {
                padding: 20px 16px;
            }
        }
        </style>
        """,
        unsafe_allow_html=True
    )


# ============================================================
# 3. PANTALLA DE INICIO DE SESIÓN (BYPASS TEMPORAL)
# ============================================================

def render_login():
    # BYPASS TEMPORAL: Acceso automático sin credenciales
    st.session_state.autenticado = True
    st.session_state.usuario = "admin@epespo.edu.ec"
    st.session_state.nombre = "Administrador Temporal"
    st.session_state.rol = "admin"
    return True


# ============================================================
# 4. CERRAR SESIÓN
# ============================================================

def cerrar_sesion():
    claves_autenticacion = [
        "autenticado",
        "usuario",
        "nombre",
        "rol",
        "login_usuario",
        "login_password"
    ]

    for clave in claves_autenticacion:
        st.session_state.pop(clave, None)

    st.rerun()