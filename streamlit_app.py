import streamlit as st
import pandas as pd
from datetime import datetime
import os

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="PrestApp Control Total", page_icon="🔐")

# --- 2. GESTIÓN DE BASE DE DATOS FÍSICA (ARCHIVO CSV) ---
# Esto evita que los cobradores se borren al reiniciar
USUARIOS_FILE = "usuarios_registrados.csv"

def cargar_usuarios():
    if os.path.exists(USUARIOS_FILE):
        df = pd.read_csv(USUARIOS_FILE, index_col=0)
        return df.to_dict('index')
    else:
        # Usuario maestro por defecto
        return {"admin": {"nombre": "Dueño", "clave": "admin123", "rol": "admin"}}

def guardar_usuario(id_u, nombre, clave, rol):
    usuarios = cargar_usuarios()
    usuarios[id_u] = {"nombre": nombre, "clave": str(clave), "rol": rol}
    pd.DataFrame.from_dict(usuarios, orient='index').to_csv(USUARIOS_FILE)

# Cargar usuarios al inicio
if 'usuarios_db' not in st.session_state:
    st.session_state.usuarios_db = cargar_usuarios()

# --- 3. ESTADO DE SESIÓN ---
if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if 'user_id' not in st.session_state: st.session_state.user_id = None
if 'data' not in st.session_state: st.session_state.data = pd.DataFrame(columns=['ID', 'Cliente', 'Saldo', 'Cobrador', 'Estado'])

# --- 4. PANTALLA DE LOGIN ---
if not st.session_state.logged_in:
    st.markdown("<h2 style='text-align: center;'>🔐 Acceso Sistema de Cobro</h2>", unsafe_allow_html=True)
    
    # IMPORTANTE: Trim para evitar espacios en blanco accidentales
    u_input = st.text_input("Usuario ID").strip()
    p_input = st.text_input("Contraseña", type="password").strip()
    
    if st.button("INGRESAR", use_container_width=True):
        db = cargar_usuarios() # Recargar para asegurar nuevos registros
        if u_input in db and str(db[u_input]['clave']) == p_input:
            st.session_state.logged_in = True
            st.session_state.user_id = u_input
            st.session_state.usuarios_db = db
            st.rerun()
        else:
            st.error("❌ Credencial incorrecta. Verifica mayúsculas/minúsculas.")
    st.stop()

# --- 5. INTERFAZ PROTEGIDA ---
user_data = st.session_state.usuarios_db[st.session_state.user_id]
es_admin = (user_data['rol'] == "admin")

with st.sidebar:
    st.title("🏦 PrestApp")
    st.write(f"Sesión: **{user_data['nombre']}**")
    if st.button("Cerrar Sesión"):
        st.session_state.logged_in = False
        st.rerun()
    
    if es_admin:
        st.divider()
        st.subheader("⚙️ Registrar Cobrador")
        nuevo_id = st.text_input("ID de login (ej: carlos1)").strip()
        nuevo_nom = st.text_input("Nombre del empleado")
        nuevo_cla = st.text_input("Clave de acceso")
        
        if st.button("Guardar Cobrador"):
            if nuevo_id and nuevo_cla:
                guardar_usuario(nuevo_id, nuevo_nom, nuevo_cla, "cobrador")
                st.success(f"Cobrador {nuevo_id} guardado correctamente.")
                st.rerun()

# --- 6. OPERACIONES CENTRALIZADAS ---

if es_admin:
    st.header("Panel de Administración")
    # Solo el admin ve el botón de prestar
    if st.button("➕ CREAR NUEVO PRÉSTAMO"):
        @st.dialog("Nuevo Crédito")
        def modal_p():
            cliente = st.text_input("Nombre Cliente")
            monto = st.number_input("Monto $", min_value=0.0)
            # Lista de cobradores registrados
            cobs = [k for k, v in cargar_usuarios().items() if v['rol'] == 'cobrador']
            asig = st.selectbox("Asignar a Cobrador:", cobs)
            if st.button("Confirmar Desembolso"):
                id_p = datetime.now().strftime("%f")
                n = pd.DataFrame([{'ID': id_p, 'Cliente': cliente, 'Saldo': monto*1.2, 'Cobrador': asig, 'Estado': 'Activo'}])
                st.session_state.data = pd.concat([st.session_state.data, n], ignore_index=True)
                st.rerun()
        modal_p()
else:
    st.header(f"Ruta de: {user_data['nombre']}")
    # El cobrador NO tiene botón de préstamo, solo de cobro

if st.button("💰 REGISTRAR COBRO"):
    @st.dialog("Cobrar")
    def modal_c():
        # Filtro estricto: solo sus clientes
        query = (st.session_state.data['Estado'] == 'Activo')
        if not es_admin:
            query = query & (st.session_state.data['Cobrador'] == st.session_state.user_id)
        
        mis_c = st.session_state.data[query]
        if mis_c.empty:
            st.write("No tienes clientes asignados.")
        else:
            sel = st.selectbox("Cliente", mis_c['Cliente'])
            abono = st.number_input("Monto", min_value=0.0)
            if st.button("Guardar Pago"):
                idx = mis_c[mis_c['Cliente'] == sel].index[-1]
                st.session_state.data.at[idx, 'Saldo'] -= abono
                if st.session_state.data.at[idx, 'Saldo'] <= 0:
                    st.session_state.data.at[idx, 'Estado'] = 'Finalizado'
                st.rerun()
    modal_c()

# --- 7. TABLA DE CARTERA ---
st.divider()
st.subheader("Cartera Activa")
vista_query = (st.session_state.data['Estado'] == 'Activo')
if not es_admin:
    vista_query = vista_query & (st.session_state.data['Cobrador'] == st.session_state.user_id)

st.dataframe(st.session_state.data[vista_query][['Cliente', 'Saldo', 'Cobrador']], use_container_width=True)
