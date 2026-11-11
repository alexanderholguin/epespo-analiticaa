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
# 3. PANTALLA DE INICIO DE SESIÓN
# ============================================================

def render_login():
    if "autenticado" not in st.session_state:
        st.session_state.autenticado = False

    if st.session_state.autenticado:
        return True

    aplicar_estilos_login()

    html_header = (
        '<div class="epespo-header">'
        '<div class="epespo-logo">⚓</div>'
        '<div class="epespo-title">EPESPO | SUITE MARÍTIMA</div>'
        '<div class="epespo-subtitle">'
        'Plataforma Institucional de Inteligencia Analítica'
        '<br>'
        'Gestión Estadística y Titulaciones Marítimas'
        '</div>'
        '<div class="epespo-divider"></div>'
        '</div>'
    )

    st.markdown(html_header, unsafe_allow_html=True)

    col_izq, col_centro, col_der = st.columns([1, 1.4, 1])

    with col_centro:
        with st.form("form_login"):
            st.markdown(
                '<h3 style="text-align:center;color:#103B70;font-size:22px;font-weight:750;margin-bottom:5px;">Acceso al Sistema</h3>',
                unsafe_allow_html=True
            )
            st.markdown(
                '<p style="text-align:center;color:#71859A;font-size:13px;margin-bottom:24px;">Ingrese sus credenciales institucionales</p>',
                unsafe_allow_html=True
            )

            usuario = st.text_input("Usuario", placeholder="Ingrese su usuario", key="login_usuario")
            password = st.text_input("Contraseña", type="password", placeholder="Ingrese su contraseña", key="login_password")

            st.write("")

            submit = st.form_submit_button("Ingresar al Sistema", use_container_width=True)

            if submit:
                if not usuario.strip() or not password:
                    st.warning("Por favor, ingrese su usuario y contraseña.")
                else:
                    usuario_normalizado = usuario.strip().lower()
                    user_data = verificar_credenciales(usuario_normalizado, password)

                    if user_data:
                        st.session_state.autenticado = True
                        st.session_state.usuario = usuario_normalizado
                        st.session_state.nombre = user_data["nombre"]
                        st.session_state.rol = user_data["rol"]
                        st.rerun()
                    else:
                        st.error("Credenciales incorrectas. Verifique su usuario y contraseña.")

    html_footer = (
        '<div class="epespo-footer">'
        'FUNDACIÓN ESCUELA DE PESCA DEL PACÍFICO ORIENTAL'
        '<br>'
        'Sistema de Consulta y Análisis Institucional'
        '<br>'
        '© 2026 EPESPO'
        '</div>'
    )

    st.markdown(html_footer, unsafe_allow_html=True)
    return False


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