import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime
import urllib.parse

# --- 1. CONFIGURACIÓN MAESTRA ---
SHEET_ID = "1-g3icRDMsZu_L2nNHMRSHoPAU7n6k5hbZANUyV9WwEw"
GID_USUARIOS = "0" 
GID_PRESTAMOS = "539541529"

# --- 2. ESTILO VISUAL PRO ---
st.set_page_config(page_title="PrestApp Elite", page_icon="💰", layout="wide")

st.markdown("""
    <style>
    /* Fondo y contenedores */
    .stApp { background-color: #0c0c0e; color: #ffffff; }
    [data-testid="stSidebar"] { background-color: #161618; border-right: 1px solid #333; }
    
    /* Tarjetas de Diseño */
    .metric-card {
        background: linear-gradient(135deg, #1e1e21 0%, #111112 100%);
        padding: 20px;
        border-radius: 15px;
        border: 1px solid #333;
        text-align: center;
        margin-bottom: 15px;
    }
    .status-active { color: #32D74B; font-weight: bold; }
    
    /* Botones Pro */
    .stButton>button {
        width: 100%;
        border-radius: 10px;
        height: 3em;
        background-color: #007AFF;
        color: white;
        border: none;
        transition: 0.3s;
    }
    .stButton>button:hover { background-color: #0056b3; border: none; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. FUNCIONES DE DATOS ---
def cargar_datos(gid):
    url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={gid}"
    try:
        df = pd.read_csv(url)
        df.columns = df.columns.str.strip()
        # Flexibilidad de nombre de columna
        if 'Clientes' in df.columns:
            df = df.rename(columns={'Clientes': 'Cliente'})
        return df
    except:
        return pd.DataFrame()

# --- 4. SISTEMA DE LOGIN ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    cols = st.columns([1, 2, 1])
    with cols[1]:
        st.markdown("<h1 style='text-align: center;'>🏦 PrestApp Elite</h1>", unsafe_allow_html=True)
        with st.container():
            u = st.text_input("Usuario ID").strip()
            p = st.text_input("Contraseña", type="password").strip()
            if st.button("ACCEDER"):
                df_u = cargar_datos(GID_USUARIOS)
                user_match = df_u[df_u['ID'].astype(str) == u]
                if not user_match.empty and str(user_match.iloc[0]['Clave']) == p:
                    st.session_state.logged_in = True
                    st.session_state.user = user_match.iloc[0].to_dict()
                    st.rerun()
                else:
                    st.error("Credenciales Inválidas")
    st.stop()

# --- 5. DASHBOARD PRINCIPAL ---
user = st.session_state.user
es_admin = (user['Rol'] == "admin")
df_p = cargar_datos(GID_PRESTAMOS)

# Sidebar
with st.sidebar:
    st.markdown(f"### Bienvido, \n## {user['Nombre']}")
    st.markdown(f"🚩 Rol: **{user['Rol'].upper()}**")
    st.divider()
    if st.button("Cerrar Sesión"):
        st.session_state.logged_in = False
        st.rerun()

# --- MÉTRICAS TOP ---
st.title("📊 Resumen de Cartera")
c1, c2, c3 = st.columns(3)

if not df_p.empty:
    # Filtrar datos según el rol para las métricas
    datos_ver = df_p[df_p['Estado'] == 'Activo']
    if not es_admin:
        datos_ver = datos_ver[datos_ver['Cobrador'].astype(str) == str(user['ID'])]

    with c1:
        st.markdown(f'<div class="metric-card"><h3>Clientes</h3><h2>{len(datos_ver)}</h2></div>', unsafe_allow_html=True)
    with c2:
        total_calle = datos_ver['Saldo'].sum()
        st.markdown(f'<div class="metric-card"><h3>En Calle</h3><h2 style="color:#32D74B">${total_calle:,.0f}</h2></div>', unsafe_allow_html=True)
    with c3:
        prox_cobro = datos_ver['Cuota'].sum() if 'Cuota' in datos_ver.columns else 0
        st.markdown(f'<div class="metric-card"><h3>Meta Cobro</h3><h2 style="color:#007AFF">${prox_cobro:,.0f}</h2></div>', unsafe_allow_html=True)

# --- 6. ACCIONES PRO ---
t1, t2 = st.tabs(["💰 Cobros", "📝 Gestión"])

with t1:
    st.subheader("Registrar Abono Diario")
    if not df_p.empty:
        # Solo mostrar clientes activos del cobrador
        query = (df_p['Estado'] == 'Activo')
        if not es_admin:
            query = query & (df_p['Cobrador'].astype(str) == str(user['ID']))
        
        opciones_cli = df_p[query]['Cliente'].tolist()
        
        col_bus, col_pago = st.columns(2)
        with col_bus:
            seleccionado = st.selectbox("Seleccione Cliente", ["---"] + opciones_cli)
        
        if seleccionado != "---":
            datos_cli = df_p[df_p['Cliente'] == seleccionado].iloc[0]
            with col_pago:
                abono = st.number_input(f"Monto (Saldo: ${datos_cli['Saldo']:,.0f})", min_value=0)
            
            if st.button("CONFIRMAR COBRO"):
                # Simulación de éxito (La escritura requiere st.connection)
                nuevo_saldo = datos_cli['Saldo'] - abono
                st.success(f"Cobro exitoso para {seleccionado}")
                
                # Link de WhatsApp
                msg = f"✅ *COMPROBANTE DE PAGO*\n\nHola *{seleccionado}*,\nRecibimos tu abono de: *${abono:,.0f}*\nTu saldo restante es: *${nuevo_saldo:,.0f}*\n\n¡Gracias por tu puntualidad! 🙏"
                wa_url = f"https://wa.me/?text={urllib.parse.quote(msg)}"
                st.markdown(f"[📲 Enviar Recibo por WhatsApp]({wa_url})")

with t2:
    if es_admin:
        st.subheader("Control Administrativo")
        with st.expander("➕ CREAR NUEVO CRÉDITO"):
            c_nom = st.text_input("Nombre del Cliente")
            c_mon = st.number_input("Capital a entregar", min_value=0)
            c_cob = st.selectbox("Asignar a Cobrador", cargar_datos(GID_USUARIOS)['ID'].tolist())
            if st.button("DESEMBOLSAR"):
                st.info("Crédito registrado (Debe sincronizarse con Google Sheets)")
    else:
        st.info("Panel de gestión limitado para cobradores. Contacte al administrador para nuevos créditos.")

# --- 7. TABLA DE DATOS ---
st.divider()
st.subheader("📋 Detalle de Cartera")
if not df_p.empty:
    filtro_tabla = df_p[df_p['Estado'] == 'Activo']
    if not es_admin:
        filtro_tabla = filtro_tabla[filtro_tabla['Cobrador'].astype(str) == str(user['ID'])]
    
    # Buscador rápido
    busqueda = st.text_input("🔍 Buscar cliente en tabla...")
    if busqueda:
        filtro_tabla = filtro_tabla[filtro_tabla['Cliente'].str.contains(busqueda, case=False)]
    
    st.dataframe(filtro_tabla[['Cliente', 'Saldo', 'Cuota', 'Cobrador']], use_container_width=True)
else:
    st.error("No se encontraron datos en la base de datos de Google.")

# --- FUNCIÓN PARA GUARDAR EN LA NUBE ---
def guardar_nuevo_prestamo(nuevo_registro):
    try:
        # 1. Establecer conexión de escritura
        conn = st.connection("gsheets", type=GSheetsConnection)
        
        # 2. Leer lo que hay actualmente en la pestaña Prestamos
        df_existente = conn.read(worksheet="Prestamos")
        
        # 3. Concatenar el nuevo registro
        df_actualizado = pd.concat([df_existente, nuevo_registro], ignore_index=True)
        
        # 4. Subir la tabla completa de vuelta
        conn.update(worksheet="Prestamos", data=df_actualizado)
        
        st.cache_data.clear() # Limpia la memoria para que aparezca en la tabla
        return True
    except Exception as e:
        st.error(f"Fallo de sincronización: {e}")
        return False

# --- DENTRO DEL FORMULARIO DE ADMIN ---
if es_admin:
    with st.expander("➕ CREAR NUEVO CRÉDITO"):
        with st.form("nuevo_credito_form"):
            c_nom = st.text_input("Nombre del Cliente").upper()
            c_mon = st.number_input("Capital a entregar", min_value=0)
            c_cuo = st.number_input("Valor de la Cuota", min_value=0)
            c_cob = st.selectbox("Asignar a Cobrador (ID)", cargar_datos(GID_USUARIOS)['ID'].tolist())
            
            if st.form_submit_button("🚀 REGISTRAR Y SINCRONIZAR"):
                # Crear el DataFrame del nuevo préstamo
                nuevo_p = pd.DataFrame([{
                    "ID": datetime.now().strftime("%d%m%H%M"), # ID único basado en tiempo
                    "Clientes": c_nom,
                    "Saldo": c_mon,
                    "Cuota": c_cuo,
                    "Cobrador": c_cob,
                    "Estado": "Activo"
                }])
                
                if guardar_nuevo_prestamo(nuevo_p):
                    st.success(f"✅ ¡Sincronizado! {c_nom} ya está en Google Sheets.")
                    st.balloons()
