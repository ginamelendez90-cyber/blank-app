import streamlit as st
import pandas as pd
from datetime import datetime

# --- 1. CONFIGURACIÓN ---
# Reemplaza con tu ID real
SHEET_ID = "1-g3icRDMsZu_L2nNHMRSHoPAU7n6k5hbZANUyV9WwEw" 
GID_USUARIOS = "0"          # Casi siempre es 0
GID_PRESTAMOS = "539541529" # El número que viste en la URL después de gid=

def cargar_datos(gid_pestana):
    url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={gid_pestana}"
    try:
        df = pd.read_csv(url)
        # 💡 TRUCO MAESTRO: Limpiar espacios y estandarizar nombres de columnas
        df.columns = df.columns.str.strip() # Quita espacios al inicio y final
        return df
    except Exception as e:
        st.error(f"Error en GID {gid_pestana}: {e}")
        return pd.DataFrame()

# --- 2. LÓGICA DE INICIO ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

# --- 3. PANTALLA DE LOGIN ---
if not st.session_state.logged_in:
    st.title("🔐 Acceso PrestApp")
    u_log = st.text_input("Usuario ID").strip()
    p_log = st.text_input("Contraseña", type="password").strip()
    
    if st.button("INGRESAR"):
        df_u = cargar_datos(GID_USUARIOS)
        if not df_u.empty:
            # Buscamos ignorando mayúsculas/minúsculas en el ID de usuario
            user_match = df_u[df_u['ID'].astype(str) == u_log]
            if not user_match.empty and str(user_match.iloc[0]['Clave']) == p_log:
                st.session_state.logged_in = True
                st.session_state.user_data = user_match.iloc[0].to_dict()
                st.rerun()
            else:
                st.error("❌ Credenciales incorrectas")
    st.stop()

# --- 4. CARGA DE CARTERA (Solo si está logueado) ---
user = st.session_state.user_data
es_admin = (user['Rol'] == "admin")

st.sidebar.write(f"Usuario: {user['Nombre']}")
if st.sidebar.button("Cerrar Sesión"):
    st.session_state.logged_in = False
    st.rerun()

df_p = cargar_datos(GID_PRESTAMOS)

# --- 5. SOLUCIÓN AL ERROR DE COLUMNAS ---
st.subheader("📋 Cartera Activa")

if not df_p.empty:
    # Verificamos qué columnas existen realmente para evitar que la app se cierre
    columnas_disponibles = df_p.columns.tolist()
    columnas_necesarias = ['Cliente', 'Saldo', 'Cobrador']
    
    # Solo intentamos mostrar si todas las columnas están presentes
    if all(col in columnas_disponibles for col in columnas_necesarias):
        # Filtro de seguridad
        query = (df_p['Estado'] == 'Activo')
        if not es_admin:
            query = query & (df_p['Cobrador'].astype(str) == str(user['ID']))
        
        vista = df_p[query]
        st.dataframe(vista[columnas_necesarias], use_container_width=True)
    else:
        st.error("⚠️ Error en Excel: No se encuentran las columnas exactas.")
        st.write("Columnas detectadas en tu Excel:", columnas_disponibles)
        st.info("Asegúrate de que en la primera fila de tu Excel diga: Cliente, Saldo, Cobrador, Estado")
else:
    st.warning("No hay datos en la pestaña de Prestamos.")
