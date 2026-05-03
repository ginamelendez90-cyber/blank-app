import streamlit as st
import pandas as pd
from datetime import datetime

# --- CONFIGURACIÓN DE LA HOJA DE GOOGLE ---
# Reemplaza esto con el ID que copiaste de tu URL de Google Sheets
SHEET_ID = "https://docs.google.com/spreadsheets/d/1-g3icRDMsZu_L2nNHMRSHoPAU7n6k5hbZANUyV9WwEw/edit?usp=drivesdk"

def get_google_sheet_url(sheet_name):
    return f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={sheet_name}"

# --- FUNCIONES DE PERSISTENCIA REAL ---
def cargar_datos_nube(pestana):
    try:
        url = get_google_sheet_url(pestana)
        return pd.read_csv(url)
    except:
        # Si la hoja está vacía o hay error, devuelve estructura básica
        if pestana == "Usuarios":
            return pd.DataFrame([{"ID": "admin", "Nombre": "Dueño", "Clave": "admin123", "Rol": "admin"}])
        return pd.DataFrame()

# --- INICIO DE LA APP ---
st.set_page_config(page_title="PrestApp Cloud", page_icon="☁️")

# Carga inicial desde la nube
if 'usuarios_db' not in st.session_state:
    df_u = cargar_datos_nube("Usuarios")
    st.session_state.usuarios_db = df_u.set_index('ID').to_dict('index')

# --- LÓGICA DE LOGIN ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.title("🔐 Acceso Remoto")
    u = st.text_input("Usuario").strip()
    p = st.text_input("Clave", type="password").strip()
    
    if st.button("CONECTAR"):
        db = st.session_state.usuarios_db
        if u in db and str(db[u]['Clave']) == p:
            st.session_state.logged_in = True
            st.session_state.user_id = u
            st.rerun()
        else:
            st.error("Error de acceso")
    st.stop()

# --- PANEL DE CONTROL (RESTRICCIONES) ---
user = st.session_state.usuarios_db[st.session_state.user_id]
es_admin = (user['Rol'] == "admin")

st.sidebar.title(f"☁️ Nube Activa")
st.sidebar.write(f"Usuario: {user['Nombre']}")

if es_admin:
    st.header("👑 Administración Central")
    with st.expander("➕ CREAR CRÉDITO (Solo Admin)"):
        cliente = st.text_input("Cliente")
        monto = st.number_input("Monto", min_value=0)
        # Aquí cargarías la lista de cobradores de la pestaña Usuarios
        if st.button("Registrar en la Nube"):
            st.success("Guardado en Google Sheets (Simulado)")
            # Nota: Para escribir de vuelta a Google Sheets desde Streamlit 
            # de forma automática se recomienda usar 'st.connection("gsheets")'
else:
    st.header("🛵 Panel de Cobrador")
    st.info("Solo ves tus clientes asignados en la nube.")

if st.button("Cerrar Sesión"):
    st.session_state.logged_in = False
    st.rerun()
