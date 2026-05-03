import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime
import urllib.parse

# --- 1. CONFIGURACIÓN ---
# Reemplaza con tu ID de la URL de Google Sheets
SHEET_ID = "1-g3icRDMsZu_L2nNHMRSHoPAU7n6k5hbZANUyV9WwEw" 
GID_USUARIOS = "0"

# --- 2. ESTILO VISUAL ---
st.set_page_config(page_title="PrestApp Elite Pro", page_icon="🏦", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #0e1117; color: white; }
    .metric-card {
        background-color: #1e2130;
        padding: 15px;
        border-radius: 12px;
        border: 1px solid #30363d;
        text-align: center;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 3. CONEXIÓN Y CARGA ---
conn = st.connection("gsheets", type=GSheetsConnection)

def cargar_datos_lectura(gid):
    # Usamos el método de exportación rápida para lectura para evitar errores de cache
    url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={gid}"
    try:
        df = pd.read_csv(url)
        df.columns = df.columns.str.strip()
        if 'Clientes' in df.columns:
            df = df.rename(columns={'Clientes': 'Cliente'})
        return df
    except:
        return pd.DataFrame()

# --- 4. SISTEMA DE LOGIN ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.title("🔐 Acceso al Sistema")
    with st.container():
        u = st.text_input("Usuario ID").strip()
        p = st.text_input("Contraseña", type="password").strip()
        if st.button("INGRESAR"):
            df_u = cargar_datos_lectura(GID_USUARIOS)
            if not df_u.empty:
                user_match = df_u[df_u['ID'].astype(str) == u]
                if not user_match.empty and str(user_match.iloc[0]['Clave']) == p:
                    st.session_state.logged_in = True
                    st.session_state.user = user_match.iloc[0].to_dict()
                    st.rerun()
                else:
                    st.error("Usuario o clave incorrectos")
    st.stop()

# --- 5. LÓGICA DE NEGOCIO ---
user = st.session_state.user
es_admin = (user['Rol'] == "admin")

# Cargar préstamos
df_p = cargar_datos_lectura("PON_AQUI_TU_GID_DE_PRESTAMOS") # Ejemplo: "12345678"

# Sidebar
with st.sidebar:
    st.header(f"👋 {user['Nombre']}")
    st.write(f"Rol: {user['Rol'].upper()}")
    if st.button("Cerrar Sesión"):
        st.session_state.logged_in = False
        st.rerun()

# --- PANTALLA PRINCIPAL ---
st.title("💰 Gestión de Cartera")

if not df_p.empty:
    # Filtrar según rol
    df_activos = df_p[df_p['Estado'] == 'Activo']
    if not es_admin:
        df_activos = df_activos[df_activos['Cobrador'].astype(str) == str(user['ID'])]

    # Métricas
    m1, m2, m3 = st.columns(3)
    with m1:
        st.markdown(f'<div class="metric-card"><h3>Clientes</h3><h2>{len(df_activos)}</h2></div>', unsafe_allow_html=True)
    with m2:
        st.markdown(f'<div class="metric-card"><h3>Total Calle</h3><h2 style="color:#2ecc71">${df_activos["Saldo"].sum():,.0f}</h2></div>', unsafe_allow_html=True)
    with m3:
        meta = df_activos["Cuota"].sum() if "Cuota" in df_activos.columns else 0
        st.markdown(f'<div class="metric-card"><h3>Meta Hoy</h3><h2 style="color:#3498db">${meta:,.0f}</h2></div>', unsafe_allow_html=True)

    # Tabs de acción
    t_cobros, t_admin = st.tabs(["💸 Registrar Cobro", "⚙️ Administración"])

    with t_cobros:
        st.subheader("Nuevo Abono")
        if not df_activos.empty:
            cliente_sel = st.selectbox("Seleccione Cliente", ["---"] + df_activos['Cliente'].tolist())
            if cliente_sel != "---":
                row = df_activos[df_activos['Cliente'] == cliente_sel].iloc[0]
                monto_pago = st.number_input(f"¿Cuánto pagó? (Deuda: ${row['Saldo']:,.0f})", min_value=0)
                
                if st.button("REGISTRAR PAGO"):
                    # Generar WhatsApp (El guardado manual requiere actualización en Google)
                    msg = f"✅ *RECIBO DE PAGO*\n\nHola *{cliente_sel}*,\nConfirmamos tu abono de: *${monto_pago:,.0f}*\nSaldo restante: *${(row['Saldo'] - monto_pago):,.0f}*"
                    url_wa = f"https://wa.me/?text={urllib.parse.quote(msg)}"
                    st.success("Pago procesado localmente")
                    st.markdown(f"[📲 Enviar Comprobante por WhatsApp]({url_wa})")

    with t_admin:
        if es_admin:
            st.subheader("Registrar Nuevo Préstamo")
            with st.form("form_nuevo"):
                n_cli = st.text_input("Nombre Completo").upper()
                n_mon = st.number_input("Capital", min_value=0)
                n_cuo = st.number_input("Cuota Diaria", min_value=0)
                n_cob = st.text_input("ID del Cobrador Asignado")
                
                if st.form_submit_button("SINCRONIZAR CON GOOGLE"):
                    try:
                        # Leer actual
                        df_actual = conn.read(worksheet="Prestamos")
                        # Crear nuevo
                        nuevo_reg = pd.DataFrame([{
                            "ID": datetime.now().strftime("%H%M%S"),
                            "Clientes": n_cli, # Asegurar que coincida con el Excel
                            "Saldo": n_mon,
                            "Cuota": n_cuo,
                            "Cobrador": n_cob,
                            "Estado": "Activo"
                        }])
                        # Unir y subir
                        df_upd = pd.concat([df_actual, nuevo_reg], ignore_index=True).fillna("")
                        conn.update(worksheet="Prestamos", data=df_upd)
                        st.success("✅ ¡Guardado en la nube exitosamente!")
                        st.balloons()
                    except Exception as e:
                        st.error(f"Error de sincronización: {e}")
        else:
            st.info("Solo el administrador puede registrar nuevos créditos.")

    # Tabla Visual
    st.divider()
    st.subheader("📋 Detalle de Clientes")
    st.dataframe(df_activos[['Cliente', 'Saldo', 'Cuota', 'Cobrador']], use_container_width=True)
else:
    st.warning("No se pudieron cargar datos. Revisa la conexión y el GID.")
