import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

# --- 1. CONFIGURACIÓN Y ESTILOS ---
st.set_page_config(page_title="Control de Cartera Pro", page_icon="🏦", layout="centered")

st.markdown("""
    <style>
    .stApp { background-color: #F2F2F7; }
    .card-admin { background-color: #1c1c1e; padding: 20px; border-radius: 15px; color: #32D74B; text-align: center; border: 2px solid #32D74B; margin-bottom: 20px; }
    .card-cobrador { background-color: #007AFF; padding: 15px; border-radius: 15px; color: white; text-align: center; margin-bottom: 20px; }
    .info-cuota { padding: 10px; border-radius: 10px; margin-bottom: 5px; font-size: 14px; border-left: 5px solid #007AFF; background-color: #f0f0f5; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. BASE DE DATOS (EN MEMORIA) ---
if 'usuarios_db' not in st.session_state:
    st.session_state.usuarios_db = {"admin": {"nombre": "Dueño", "clave": "admin123", "rol": "admin"}}
if 'data' not in st.session_state:
    st.session_state.data = pd.DataFrame(columns=['ID', 'Cliente', 'Saldo', 'Cuota', 'Cobrador', 'Estado'])
if 'historial' not in st.session_state:
    st.session_state.historial = pd.DataFrame(columns=['ID_P', 'Fecha', 'Monto', 'Quien_Cobro'])
if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if 'user_id' not in st.session_state: st.session_state.user_id = None

# --- 3. LÓGICA DE ACCESO ---
if not st.session_state.logged_in:
    st.markdown("<h2 style='text-align: center;'>🔐 Ingreso al Sistema</h2>", unsafe_allow_html=True)
    u = st.text_input("Usuario")
    p = st.text_input("Contraseña", type="password")
    if st.button("ENTRAR", use_container_width=True):
        if u in st.session_state.usuarios_db and st.session_state.usuarios_db[u]['clave'] == p:
            st.session_state.logged_in = True
            st.session_state.user_id = u
            st.rerun()
        else:
            st.error("Credenciales incorrectas")
    st.stop()

# --- 4. DATOS DEL USUARIO ACTUAL ---
user_actual = st.session_state.usuarios_db[st.session_state.user_id]
es_admin = (user_actual['rol'] == "admin")

# --- 5. MENÚ LATERAL ---
with st.sidebar:
    st.title("🏦 Menú")
    st.write(f"Usuario: **{user_actual['nombre']}**")
    if st.button("Cerrar Sesión"):
        st.session_state.logged_in = False
        st.rerun()
    
    st.divider()
    if es_admin:
        st.subheader("👥 Gestión de Personal")
        id_nuevo = st.text_input("ID Login (ej: juan)")
        nom_nuevo = st.text_input("Nombre Real")
        cla_nuevo = st.text_input("Clave")
        if st.button("Crear Cobrador"):
            if id_nuevo and nom_nuevo and cla_nuevo:
                st.session_state.usuarios_db[id_nuevo] = {"nombre": nom_nuevo, "clave": cla_nuevo, "rol": "cobrador"}
                st.success(f"Creado: {id_nuevo}")
                st.rerun()

# --- 6. FUNCIONES (MODALES) ---
@st.dialog("➕ Crear Nuevo Crédito")
def modal_nuevo_prestamo():
    st.write("### Solo el Administrador puede prestar")
    c = st.text_input("Nombre del Cliente").upper()
    m = st.number_input("Monto a entregar $", min_value=0.0)
    # Lista de cobradores para asignarles el trabajo
    lista_cobradores = [k for k, v in st.session_state.usuarios_db.items() if v['rol'] == 'cobrador']
    cob_asig = st.selectbox("Asignar cobro a:", lista_cobradores)
    
    if st.button("DESEMBOLSAR"):
        total = m * 1.20 # 20% de interés
        id_p = datetime.now().strftime("%H%M%S")
        nuevo = pd.DataFrame([{'ID': id_p, 'Cliente': c, 'Saldo': total, 'Cuota': total/20, 'Cobrador': cob_asig, 'Estado': 'Activo'}])
        st.session_state.data = pd.concat([st.session_state.data, nuevo], ignore_index=True)
        st.success("Crédito creado con éxito")
        st.rerun()

@st.dialog("💰 Registrar Cobro")
def modal_cobrar():
    # El cobrador solo ve sus clientes, el admin ve todos
    query = (st.session_state.data['Estado'] == 'Activo')
    if not es_admin:
        query = query & (st.session_state.data['Cobrador'] == st.session_state.user_id)
    
    mis_cli = st.session_state.data[query]
    if mis_cli.empty:
        st.warning("No hay clientes pendientes.")
        return
        
    seleccion = st.selectbox("Cliente", mis_cli['Cliente'].unique())
    idx = mis_cli[mis_cli['Cliente'] == seleccion].index[-1]
    abono = st.number_input("Monto Recibido", value=float(mis_cli.at[idx, 'Cuota']))
    
    if st.button("GUARDAR ABONO"):
        st.session_state.data.at[idx, 'Saldo'] -= abono
        # Registrar en historial
        hist = pd.DataFrame([{'ID_P': mis_cli.at[idx, 'ID'], 'Fecha': datetime.now().strftime("%d/%m"), 'Monto': abono, 'Quien_Cobro': user_actual['nombre']}])
        st.session_state.historial = pd.concat([st.session_state.historial, hist], ignore_index=True)
        
        if st.session_state.data.at[idx, 'Saldo'] <= 0:
            st.session_state.data.at[idx, 'Estado'] = 'Finalizado'
        st.rerun()

# --- 7. PANTALLA PRINCIPAL ---
if es_admin:
    st.markdown(f'<div class="card-admin">💼 PANEL DE DUEÑO<br>Suma en Calle: ${st.session_state.data[st.session_state.data["Estado"]=="Activo"]["Saldo"].sum():,.0f}</div>', unsafe_allow_html=True)
    if st.button("➕ NUEVO CRÉDITO", use_container_width=True):
        modal_nuevo_prestamo()
else:
    st.markdown(f'<div class="card-cobrador">🛵 RUTA DE COBRO: {user_actual["nombre"]}</div>', unsafe_allow_html=True)

if st.button("💰 REGISTRAR COBRO", use_container_width=True):
    modal_cobrar()

st.divider()

# --- 8. VISTA DE CARTERA ---
st.subheader("📋 Clientes Activos")
q_cartera = (st.session_state.data['Estado'] == 'Activo')
if not es_admin:
    q_cartera = q_cartera & (st.session_state.data['Cobrador'] == st.session_state.user_id)

cartera = st.session_state.data[q_cartera]

for _, r in cartera.iloc[::-1].iterrows():
    with st.expander(f"👤 {r['Cliente']} | Debe: ${r['Saldo']:,.0f}"):
        st.write(f"Cobrador responsable: **{r['Cobrador']}**")
        pagos = st.session_state.historial[st.session_state.historial['ID_P'] == r['ID']]
        if not pagos.empty:
            for _, p in pagos.iterrows():
                st.markdown(f'<div class="info-cuota">📅 {p["Fecha"]} | ${p["Monto"]:,.0f} | Cobró: {p["Quien_Cobro"]}</div>', unsafe_allow_html=True)
