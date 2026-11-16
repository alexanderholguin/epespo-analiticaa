from datetime import datetime, timedelta
import os
import secrets
import time

import extra_streamlit_components as stx
import streamlit as st
from sqlalchemy.exc import SQLAlchemyError

from db import (
    guardar_sesion_autenticacion,
    obtener_sesion_autenticacion,
    revocar_sesion_autenticacion,
)


# ============================================================
# EPESPO - SISTEMA DE AUTENTICACIÓN INSTITUCIONAL
# ============================================================

COOKIE_SESION = "epespo_session"
DURACION_SESION_SEGUNDOS = 60 * 60

USUARIOS_PERMITIDOS = {
    "admin_epespo": {
        "name": "Secretaría General",
        "role": "admin",
        "password": "admin1234"
    },
    "direccion_epespo": {
        "name": "Dirección Académica",
        "role": "viewer",
        "password": "viewer1234"
    }
}


def crear_gestor_cookies():
    return stx.CookieManager(key="epespo_auth_cookie_manager")


def _crear_token_sesion(usuario):
    token = secrets.token_urlsafe(32)
    expiracion = guardar_sesion_autenticacion(
        token,
        usuario,
        DURACION_SESION_SEGUNDOS,
    )
    return token, expiracion


def _sesion_desde_token(token):
    if not isinstance(token, str):
        return None

    sesion = obtener_sesion_autenticacion(token)
    if sesion is None:
        return None

    usuario, expiracion = sesion
    if usuario not in USUARIOS_PERMITIDOS:
        revocar_sesion_autenticacion(token)
        return None
    return usuario, expiracion


def _datos_usuario(usuario):
    datos = USUARIOS_PERMITIDOS.get(usuario)
    if not datos:
        return None
    return {
        "nombre": str(datos.get("name", usuario)),
        "rol": str(datos.get("role", "")),
    }


def _establecer_sesion(usuario, token, expiracion):
    datos = _datos_usuario(usuario)
    if not datos:
        return False
    st.session_state.autenticado = True
    st.session_state.usuario = usuario
    st.session_state.nombre = datos["nombre"]
    st.session_state.rol = datos["rol"]
    st.session_state["_token_sesion"] = token
    st.session_state["_expira_sesion"] = expiracion
    return True


def _limpiar_estado_sesion():
    for clave in (
        "autenticado",
        "usuario",
        "nombre",
        "rol",
        "_token_sesion",
        "_expira_sesion",
        "login_usuario",
        "login_password",
    ):
        st.session_state.pop(clave, None)


def _eliminar_cookie_sesion(cookie_manager):
    if cookie_manager.get(cookie=COOKIE_SESION) is not None:
        cookie_manager.delete(
            COOKIE_SESION,
            key="delete_epespo_auth_cookie",
        )


def _cookie_segura():
    predeterminado = "true" if os.environ.get("K_SERVICE") else "false"
    valor = os.environ.get("AUTH_COOKIE_SECURE", predeterminado)
    return valor.strip().lower() in {"1", "true", "yes"}


def _error_persistencia_sesion(error):
    st.error(f"No se pudo validar o guardar la sesión en la base de datos: {error}")


# ============================================================
# 1. VERIFICACIÓN DE CREDENCIALES (Texto Plano - Definitivo)
# ============================================================

def verificar_credenciales(usuario, password):
    usuario = usuario.strip().lower()
    password = password.strip()

    if usuario not in USUARIOS_PERMITIDOS:
        return None

    datos = USUARIOS_PERMITIDOS[usuario]
    return _datos_usuario(usuario) if password == datos["password"] else None


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

def render_login(cookie_manager):
    if st.session_state.pop("_cerrar_sesion_pendiente", False):
        _eliminar_cookie_sesion(cookie_manager)
        error_cierre = st.session_state.pop("_error_cierre_sesion", None)
        if error_cierre:
            st.warning(error_cierre)

    if st.session_state.get("autenticado"):
        token = st.session_state.get("_token_sesion")
        usuario = st.session_state.get("usuario")
        expiracion = st.session_state.get("_expira_sesion", 0)
        if (
            token
            and usuario in USUARIOS_PERMITIDOS
            and expiracion > time.time()
        ):
            _establecer_sesion(usuario, token, expiracion)
            return True
        if token:
            try:
                revocar_sesion_autenticacion(token)
            except (SQLAlchemyError, RuntimeError, ValueError) as error:
                _error_persistencia_sesion(error)
                st.stop()
        _limpiar_estado_sesion()
        _eliminar_cookie_sesion(cookie_manager)

    token_cookie = cookie_manager.get(cookie=COOKIE_SESION)
    try:
        sesion_cookie = _sesion_desde_token(token_cookie)
    except (SQLAlchemyError, RuntimeError, ValueError) as error:
        _error_persistencia_sesion(error)
        st.stop()
    if sesion_cookie:
        usuario_cookie, expiracion_cookie = sesion_cookie
        if _establecer_sesion(
            usuario_cookie,
            token_cookie,
            expiracion_cookie,
        ):
            return True
    if token_cookie is not None:
        _eliminar_cookie_sesion(cookie_manager)

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
                        try:
                            token, expiracion = _crear_token_sesion(
                                usuario_normalizado
                            )
                        except (
                            SQLAlchemyError,
                            RuntimeError,
                            ValueError,
                        ) as error:
                            _error_persistencia_sesion(error)
                        else:
                            st.session_state.autenticado = True
                            st.session_state.usuario = usuario_normalizado
                            st.session_state.nombre = user_data["nombre"]
                            st.session_state.rol = user_data["rol"]
                            _establecer_sesion(
                                usuario_normalizado,
                                token,
                                expiracion,
                            )
                            cookie_manager.set(
                                COOKIE_SESION,
                                token,
                                key="set_epespo_auth_cookie",
                                max_age=DURACION_SESION_SEGUNDOS,
                                expires_at=datetime.now()
                                + timedelta(
                                    seconds=DURACION_SESION_SEGUNDOS
                                ),
                                secure=_cookie_segura(),
                                same_site="strict",
                            )
                            return True
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
    token = st.session_state.get("_token_sesion")
    if token:
        try:
            revocar_sesion_autenticacion(token)
        except (SQLAlchemyError, RuntimeError, ValueError) as error:
            st.session_state["_error_cierre_sesion"] = (
                "No se pudo revocar la sesión en la base de datos; la cookie "
                f"se eliminará y el token expirará en una hora. Detalle: {error}"
            )

    _limpiar_estado_sesion()
    st.session_state["_cerrar_sesion_pendiente"] = True