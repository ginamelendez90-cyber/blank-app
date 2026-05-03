import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="PrestApp Cloud Elite", page_icon="☁️")

# --- CONEXIÓN A LA NUBE ---
conn = st.connection("gsheets", type=GSheetsConnection)

# Función para cargar usuarios desde Google Sheets
def cargar_usuarios():
    return conn.read(worksheet="Usuarios")

# Función para guardar un nuevo crédito en Google Sheets
def guardar_prestamo_nube(nuevo_df):
    existing_data = conn.read(worksheet="Prestamos")
    updated_df = pd.concat([existing_data, nuevo_df], ignore_index=True)
    conn.update(worksheet="Prestamos", data=updated_df)
    st.cache_data.clear() # Limpia caché para ver cambios al instante

# --- LÓGICA DE LOGIN ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.title("🔐 Acceso Seguro")
    u_log = st.text_input("Usuario ID").strip()
    p_log = st.text_input("Contraseña", type="password").strip()
    
    if st.button("ENTRAR AL SISTEMA"):
        usuarios_df = cargar_usuarios()
        # Buscamos si existe el ID y la Clave en el Excel
        user_row = usuarios_df[(usuarios_df['ID'] == u_log) & (usuarios_df['Clave'].astype(str) == p_log)]
        
        if not user_row.empty:
            st.session_state.logged_in = True
            st.session_state.u_data = user_row.iloc[0].to_dict()
            st.rerun()
        else:
            st.error("❌ Credenciales incorrectas en la nube.")
    st.stop()

# --- INTERFAZ POST-LOGIN ---
u_actual = st.session_state.u_data
es_admin = (u_actual['Rol'] == "admin")

st.sidebar.success(f"Conectado: {u_actual['Nombre']}")

if es_admin:
    st.header("👑 Panel de Administración")
    
    with st.expander("➕ CREAR NUEVO CRÉDITO"):
        cliente = st.text_input("Cliente")
        monto = st.number_input("Monto $", min_value=0)
        # Cargamos cobradores del Excel para asignar
        todos_u = cargar_usuarios()
        cobradores = todos_u[todos_u['Rol'] == 'cobrador']['ID'].tolist()
        cob_asig = st.selectbox("Asignar a:", cobradores)
        
        if st.button("DESEMBOLSAR Y GUARDAR EN NUBE"):
            id_p = datetime.now().strftime("%f")
            nuevo_p = pd.DataFrame([{'ID': id_p, 'Cliente': cliente, 'Saldo': monto*1.2, 'Cobrador': cob_asig, 'Estado': 'Activo'}])
            guardar_prestamo_nube(nuevo_p)
            st.success("✅ Crédito registrado en Google Sheets")

else:
    st.header(f"🛵 Ruta: {u_actual['Nombre']}")
    # Los cobradores solo ven sus clientes desde el Excel
    all_p = conn.read(worksheet="Prestamos")
    mis_p = all_p[(all_p['Cobrador'] == u_actual['ID']) & (all_p['Estado'] == 'Activo')]
    st.dataframe(mis_p[['Cliente', 'Saldo']])

if st.sidebar.button("Cerrar Sesión"):
    st.session_state.logged_in = False
    st.rerun()
