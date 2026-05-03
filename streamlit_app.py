import streamlit as st
import pandas as pd
from datetime import datetime
import urllib.parse

# --- 1. CONFIGURACIÓN DEL GOOGLE SHEET ---
# REEMPLAZA ESTE ID con el código largo de tu URL
SHEET_ID = "https://docs.google.com/spreadsheets/d/1-g3icRDMsZu_L2nNHMRSHoPAU7n6k5hbZANUyV9WwEw/edit?usp=drivesdk"

def obtener_url(pestana):
    # Pestaña Usuarios suele ser gid=0, Prestamos gid= (ver en tu URL de Google)
    gid = "0" if pestana == "Usuarios" else "TU_GID_DE_PRESTAMOS" 
    return f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={gid}"

# --- 2. CARGA DE DATOS ---
def cargar_datos(pestana):
    try:
        return pd.read_csv(obtener_url(pestana))
    except Exception as e:
        st.error(f"Error cargando {pestana}: {e}")
        return pd.DataFrame()

# --- 3. CONFIGURACIÓN DE PÁGINA Y ESTILOS ---
st.set_page_config(page_title="PrestApp Pro Cloud", page_icon="🏦", layout="centered")

st.markdown("""
    <style>
    .stApp { background-color: #F2F2F7; }
    .card-admin { background-color: #1c1c1e; padding: 20px; border-radius: 15px; color: #32D74B; text-align: center; border: 2px solid #32D74B; margin-bottom: 20px; }
    .card-cobrador { background-color: #007AFF; padding: 15px; border-radius: 15px; color: white; text-align: center; margin-bottom: 20px; }
    </style>
    """, unsafe_allow_html=True)

# --- 4. SISTEMA DE ACCESO (LOGIN) ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.markdown("<h2 style='text-align: center;'>🔐 Sistema de Gestión</h2>", unsafe_allow_html=True)
    u_log = st.text_input("Usuario ID").strip()
    p_log = st.text_input("Contraseña", type="password").strip()
    
    if st.button("INGRESAR", use_container_width=True):
        df_u = cargar_datos("Usuarios")
        if not df_u.empty:
            # Validar credenciales
            user_match = df_u[(df_u['ID'].astype(str) == u_log) & (df_u['Clave'].astype(str) == p_log)]
            if not user_match.empty:
                st.session_state.logged_in = True
                st.session_state.user_data = user_match.iloc[0].to_dict()
                st.rerun()
            else:
                st.error("Acceso denegado: Usuario o clave incorrectos.")
    st.stop()

# --- 5. INTERFAZ SEGÚN ROL ---
user = st.session_state.user_data
es_admin = (user['Rol'] == "admin")

# Cargar préstamos para la sesión
df_p = cargar_datos("Prestamos")

with st.sidebar:
    st.title("🏦 PrestApp")
    st.write(f"Conectado: **{user['Nombre']}**")
    st.write(f"Rol: *{user['Rol'].capitalize()}*")
    if st.button("Cerrar Sesión"):
        st.session_state.logged_in = False
        st.rerun()

# --- 6. FUNCIONALIDADES ---

if es_admin:
    st.markdown(f'<div class="card-admin">💼 PANEL ADMINISTRADOR<br>Total en Calle: ${df_p[df_p["Estado"]=="Activo"]["Saldo"].sum() if not df_p.empty else 0:,.0f}</div>', unsafe_allow_html=True)
    
    # OPCIÓN ÚNICA PARA ADMIN: CREAR CRÉDITOS
    with st.expander("➕ REGISTRAR NUEVO CRÉDITO"):
        with st.form("form_prestamo"):
            cliente = st.text_input("Nombre del Cliente").upper()
            monto = st.number_input("Monto a Entregar $", min_value=0)
            
            # Cargar cobradores disponibles desde el Excel
            df_u_all = cargar_datos("Usuarios")
            lista_cobradores = df_u_all[df_u_all['Rol'] == 'cobrador']['ID'].tolist()
            cob_asig = st.selectbox("Asignar Cobro a:", lista_cobradores)
            
            if st.form_submit_button("DESEMBOLSAR"):
                # Aquí iría la lógica para guardar (Requiere st-gsheets-connection o API)
                st.warning("⚠️ Los datos se verán reflejados cuando los subas a Google Sheets.")
                st.info(f"Asignando {monto} a {cliente} bajo la ruta de {cob_asig}")

else:
    # VISTA COBRADOR
    st.markdown(f'<div class="card-cobrador">🛵 RUTA DE COBRO: {user["Nombre"]}</div>', unsafe_allow_html=True)

# --- 7. REGISTRO DE COBROS (DISPONIBLE PARA AMBOS, PERO FILTRADO) ---
st.subheader("💰 Registrar Abono")
if not df_p.empty:
    # Filtrar: Si es cobrador, solo sus clientes. Si es admin, todos.
    query = (df_p['Estado'] == 'Activo')
    if not es_admin:
        query = query & (df_p['Cobrador'].astype(str) == str(user['ID']))
    
    mis_clientes = df_p[query]
    
    if mis_clientes.empty:
        st.info("No hay clientes pendientes en esta ruta.")
    else:
        with st.form("form_cobro"):
            sel_cli = st.selectbox("Seleccione Cliente", mis_clientes['Cliente'].unique())
            monto_pago = st.number_input("Monto Recibido $", min_value=0)
            
            if st.form_submit_button("GUARDAR PAGO"):
                # Generar link de WhatsApp para comprobante
                row = mis_clientes[mis_clientes['Cliente'] == sel_cli].iloc[0]
                nuevo_saldo = row['Saldo'] - monto_pago
                texto_wa = f"✅ *RECIBO DE PAGO*\nCliente: {sel_cli}\nAbono: ${monto_pago:,.0f}\nSaldo Restante: ${nuevo_saldo:,.0f}"
                url_wa = f"https://wa.me/?text={urllib.parse.quote(texto_wa)}"
                
                st.success(f"Cobro registrado para {sel_cli}")
                st.markdown(f"[📲 Enviar Comprobante por WhatsApp]({url_wa})")

# --- 8. VISTA DE CARTERA ---
st.divider()
st.subheader("📋 Cartera Activa")
if not df_p.empty:
    vista_cartera = df_p[query] if not es_admin else df_p[df_p['Estado'] == 'Activo']
    st.dataframe(vista_cartera[['Cliente', 'Saldo', 'Cobrador']], use_container_width=True)
