import streamlit as st
import pandas as pd
from supabase import create_client, Client
from datetime import datetime
import urllib.parse

# --- 1. CONEXIÓN ---
@st.cache_resource
def init_connection():
    url = st.secrets["https://netrbgledrnsjjuyhpui.supabase.co/rest/v1/"]
    key = st.secrets["sb_publishable_qH4a5QFumA-zqXfhZD6l-w_r5gTLRie"]
    return create_client(url, key)

supabase = init_connection()

# --- 2. ESTILO ---
st.set_page_config(page_title="PrestApp Supabase", page_icon="⚡", layout="wide")
st.markdown("""
    <style>
    .stApp { background-color: #0c0e14; color: white; }
    .metric-card {
        background: linear-gradient(145deg, #161b22, #0d1117);
        padding: 20px; border-radius: 15px; border: 1px solid #30363d;
        text-align: center; box-shadow: 5px 5px 15px rgba(0,0,0,0.3);
    }
    </style>
    """, unsafe_allow_html=True)

# --- 3. LÓGICA DE DATOS ---
def traer_datos(tabla):
    res = supabase.table(tabla).select("*").execute()
    return pd.DataFrame(res.data)

# --- 4. LOGIN ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.title("🛡️ Acceso Seguro")
    with st.form("login_form"):
        u = st.text_input("Usuario ID")
        p = st.text_input("Contraseña", type="password")
        if st.form_submit_button("INGRESAR"):
            df_u = traer_datos("usuarios")
            if not df_u.empty:
                user_match = df_u[(df_u['ID'].astype(str) == u) & (df_u['Clave'].astype(str) == p)]
                if not user_match.empty:
                    st.session_state.logged_in = True
                    st.session_state.user = user_match.iloc[0].to_dict()
                    st.rerun()
            st.error("Credenciales incorrectas")
    st.stop()

# --- 5. DASHBOARD ---
user = st.session_state.user
es_admin = (user['Rol'] == "admin")

# Cargar Cartera Activa
df_p = traer_datos("prestamos")
if not df_p.empty:
    df_p = df_p[df_p['estado'] == 'Activo']
    if not es_admin:
        df_p = df_p[df_p['cobrador'].astype(str) == str(user['ID'])]

# Métricas Top
st.title(f"📊 Control de Cartera: {user['Nombre']}")
c1, c2, c3 = st.columns(3)
with c1:
    st.markdown(f'<div class="metric-card"><h4>Clientes</h4><h2>{len(df_p)}</h2></div>', unsafe_allow_html=True)
with c2:
    total = df_p['saldo'].sum() if not df_p.empty else 0
    st.markdown(f'<div class="metric-card"><h4>Saldo en Calle</h4><h2 style="color:#32D74B">${total:,.0f}</h2></div>', unsafe_allow_html=True)
with c3:
    meta = df_p['cuota'].sum() if not df_p.empty else 0
    st.markdown(f'<div class="metric-card"><h4>Cobro del Día</h4><h2 style="color:#007AFF">${meta:,.0f}</h2></div>', unsafe_allow_html=True)

# Acciones
t_cobros, t_gestion = st.tabs(["💸 Registrar Cobro", "🛠️ Gestión de Créditos"])

with t_cobros:
    if not df_p.empty:
        sel_cli = st.selectbox("Seleccione Cliente", ["---"] + df_p['clientes'].tolist())
        if sel_cli != "---":
            datos_cli = df_p[df_p['clientes'] == sel_cli].iloc[0]
            abono = st.number_input(f"Abono (Deuda actual: ${datos_cli['saldo']:,.0f})", min_value=0)
            
            if st.button("PROCESAR PAGO"):
                nuevo_saldo = datos_cli['saldo'] - abono
                # ACTUALIZAR EN SUPABASE
                try:
                    supabase.table("prestamos").update({"saldo": nuevo_saldo}).eq("id", datos_cli['id']).execute()
                    st.success("✅ Pago registrado en la base de datos")
                    
                    # WhatsApp
                    msg = f"✅ *PAGO RECIBIDO*\n\nCliente: {sel_cli}\nAbono: *${abono:,.0f}*\nNuevo Saldo: *${nuevo_saldo:,.0f}*"
                    st.markdown(f"[📲 Enviar Comprobante](https://wa.me/?text={urllib.parse.quote(msg)})")
                    st.cache_data.clear()
                except Exception as e:
                    st.error(f"Error al guardar: {e}")

with t_gestion:
    if es_admin:
        with st.form("nuevo_p"):
            st.subheader("Nuevo Crédito")
            nc_nom = st.text_input("Nombre del Cliente").upper()
            nc_mon = st.number_input("Capital", min_value=0)
            nc_cuo = st.number_input("Cuota Diaria", min_value=0)
            nc_cob = st.selectbox("Cobrador Asignado", traer_datos("usuarios")['ID'].tolist())
            
            if st.form_submit_button("DESEMBOLSAR"):
                new_data = {
                    "clientes": nc_nom, "saldo": nc_mon, 
                    "cuota": nc_cuo, "cobrador": nc_cob, "estado": "Activo"
                }
                supabase.table("prestamos").insert(new_data).execute()
                st.success("🔥 Crédito Sincronizado!")
                st.balloons()
    else:
        st.info("Funciones administrativas restringidas.")

# Tabla
st.divider()
st.subheader("📋 Detalle de Cartera")
if not df_p.empty:
    st.dataframe(df_p[['clientes', 'saldo', 'cuota', 'cobrador']], use_container_width=True)
else:
    st.write("No hay créditos activos.")
