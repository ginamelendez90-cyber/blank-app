import streamlit as st
import pandas as pd

# 1. ID de tu hoja (el código largo que está en la URL)
SHEET_ID = "https://docs.google.com/spreadsheets/d/1-g3icRDMsZu_L2nNHMRSHoPAU7n6k5hbZANUyV9WwEw/edit?usp=drivesdk" 

def cargar_usuarios():
    # Esta URL fuerza a Google a soltar los datos sin redirecciones
    url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=Usuarios"
    return pd.read_csv(url)

def cargar_prestamos():
    url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=Prestamos"
    return pd.read_csv(url)

# --- EL RESTO DE TU CÓDIGO ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.title("🔐 Acceso PrestApp")
    u_log = st.text_input("Usuario ID").strip()
    p_log = st.text_input("Clave", type="password").strip()
    
    if st.button("ENTRAR"):
        try:
            usuarios_df = cargar_usuarios()
            # Buscamos el usuario
            user_row = usuarios_df[(usuarios_df['ID'].astype(str) == u_log) & (usuarios_df['Clave'].astype(str) == p_log)]
            
            if not user_row.empty:
                st.session_state.logged_in = True
                st.session_state.u_data = user_row.iloc[0].to_dict()
                st.rerun()
            else:
                st.error("❌ Usuario o clave incorrectos.")
        except Exception as e:
            st.error(f"Error de conexión: {e}")
