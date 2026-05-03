import streamlit as st
import pandas as pd
from datetime import datetime

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="PrestApp Secure Elite", page_icon="🔐", layout="centered")

# --- 2. BASE DE DATOS DE USUARIOS (ADMIN CONTROL) ---
# En un inicio, definimos el admin. Los cobradores los creas tú desde la app.
if 'usuarios_db' not in st.session_state:
    st.session_state.usuarios_db = {
        "admin": {"nombre": "Administrador", "clave": "admin123", "rol": "admin"},
    }

if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'user_id' not in st.session_state:
    st.session_state.user_id = None

# --- 3. PANTALLA DE LOGIN ---
def login_screen():
    st.markdown("<h2 style='text-align: center;'>🔐 Acceso PrestApp</h2>", unsafe_allow_html=True)
    with st.container():
        user_input = st.text_input("Usuario ID")
        pass_input = st.text_input("Contraseña", type="password")
        
        if st.button("INGRESAR AL SISTEMA", use_container_width=True):
            if user_input in st.session_state.usuarios_db and st.session_state.usuarios_db[user_input]['clave'] == pass_input:
                st.session_state.logged_in = True
                st.session_state.user_id = user_input
                st.rerun()
            else:
                st.error("❌ Usuario o contraseña incorrectos")

# --- 4. APLICACIÓN PROTEGIDA ---
if not st.session_state.logged_in:
    login_screen()
else:
    # Obtener información del usuario que inició sesión
    user_info = st.session_state.usuarios_db[st.session_state.user_id]
    rol = user_info['rol']
    nombre_usuario = user_info['nombre']

    # BARRA LATERAL
    with st.sidebar:
        st.title("🏦 PrestApp Elite")
        st.write(f"Conectado: **{nombre_usuario}**")
        st.write(f"Nivel: *{rol.capitalize()}*")
        
        if st.button("Cerrar Sesión"):
            st.session_state.logged_in = False
            st.rerun()
        
        st.divider()
        
        # PANEL DE CONTROL SOLO PARA EL ADMIN
        if rol == "admin":
            st.subheader("⚙️ Panel del Dueño")
            with st.expander("Crear nuevo acceso"):
                new_id = st.text_input("ID de acceso (ej: cobrador1)")
                new_name = st.text_input("Nombre real del empleado")
                new_pass = st.text_input("Asignar contraseña")
                if st.button("DAR ACCESO"):
                    if new_id and new_name and new_pass:
                        st.session_state.usuarios_db[new_id] = {
                            "nombre": new_name, "clave": new_pass, "rol": "cobrador"
                        }
                        st.success(f"Acceso creado para {new_name}")
                        st.rerun()

    # --- PANTALLA PRINCIPAL SEGÚN ROL ---
    if rol == "admin":
        st.header("Vista del Administrador")
        # Aquí pegas todo el código de CAJA, CALLE y GASTOS que hicimos antes
        st.success("Tienes acceso a todos los reportes financieros.")
        
        st.subheader("Lista de Cobradores con Acceso")
        for uid, info in st.session_state.usuarios_db.items():
            if info['rol'] == 'cobrador':
                st.write(f"📍 **{info['nombre']}** | ID: `{uid}` | Clave: `{info['clave']}`")
    
    else:
        st.header(f"Ruta de Cobro: {nombre_usuario}")
        # Aquí el cobrador solo ve sus préstamos
        st.info("Solo tienes acceso a los clientes asignados a tu usuario.")
        # Aquí va la lógica de CARTERA FILTRADA por Cobrador_ID
