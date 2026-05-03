import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import urllib.parse

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="PrestApp Multi-Usuario", page_icon="👥", layout="centered")

# --- 2. ESTILOS ---
st.markdown("""
    <style>
    .stApp { background-color: #F2F2F7; }
    .card-caja { background-color: #1c1c1e; padding: 20px; border-radius: 15px; color: #32D74B; text-align: center; border: 2px solid #32D74B; }
    .card-user { background-color: #007AFF; padding: 10px; border-radius: 10px; color: white; text-align: center; margin-bottom: 20px; font-weight: bold; }
    .info-cuota { padding: 10px; border-radius: 10px; margin-bottom: 5px; font-size: 14px; border-left: 5px solid #007AFF; background-color: #f0f0f5; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. INICIALIZACIÓN DE DATOS ---
if 'data' not in st.session_state:
    st.session_state.data = pd.DataFrame(columns=['ID', 'Cliente', 'WhatsApp', 'Saldo_Actual', 'Cuota_Valor', 'Cobrador', 'Estado', 'Ultimo_Abono'])
if 'historial_cuotas' not in st.session_state:
    st.session_state.historial_cuotas = pd.DataFrame(columns=['ID_Prestamo', 'Fecha_Pago', 'Monto_Abonado', 'Cobrador_Accion'])
if 'usuarios' not in st.session_state:
    st.session_state.usuarios = ["Administrador", "Cobrador 1", "Cobrador 2"]
if 'capital' not in st.session_state: st.session_state.capital = 0.0
if 'recuperado' not in st.session_state: st.session_state.recuperado = 0.0
if 'prestado' not in st.session_state: st.session_state.prestado = 0.0

# --- 4. BARRA LATERAL (CONTROL DE ACCESO) ---
with st.sidebar:
    st.header("🔑 Acceso Personal")
    usuario_actual = st.selectbox("Quién está usando la App?", st.session_state.usuarios)
    es_admin = (usuario_actual == "Administrador")
    
    st.divider()
    if es_admin:
        st.subheader("⚙️ Panel de Control")
        nuevo_u = st.text_input("Añadir nuevo cobrador")
        if st.button("Registrar Cobrador") and nuevo_u:
            st.session_state.usuarios.append(nuevo_u)
            st.rerun()

# --- 5. CÁLCULOS GENERALES ---
disponible = st.session_state.capital + st.session_state.recuperado - st.session_state.prestado
en_la_calle = st.session_state.data[st.session_state.data['Estado'] == 'Activo']['Saldo_Actual'].sum()

# --- 6. INTERFAZ PRINCIPAL ---
st.markdown(f'<div class="card-user">👤 SESIÓN ACTIVA: {usuario_actual.upper()}</div>', unsafe_allow_html=True)

# El cobrador solo ve sus números si no es admin (opcional, aquí el admin ve todo)
if es_admin:
    c1, c2 = st.columns(2)
    with c1: st.markdown(f'<div class="card-caja"><small>DISPONIBLE</small><h2>${disponible:,.0f}</h2></div>', unsafe_allow_html=True)
    with c2: st.markdown(f'<div class="card-caja" style="color:#FF453A; border-color:#FF453A;"><small>TOTAL CALLE</small><h2>${en_la_calle:,.0f}</h2></div>', unsafe_allow_html=True)

# --- 7. MODALES DE OPERACIÓN ---
@st.dialog("➕ Nuevo Préstamo")
def modal_prestamo():
    nombre = st.text_input("NOMBRE DEL CLIENTE").upper()
    wa = st.text_input("WHATSAPP")
    monto = st.number_input("MONTO A ENTREGAR $", min_value=0.0)
    # Si es admin elige cobrador, si es cobrador se asigna a él mismo
    cobrador_asig = st.selectbox("ASIGNAR COBRO A:", st.session_state.usuarios) if es_admin else usuario_actual
    
    if st.button("CREAR CRÉDITO"):
        if nombre:
            total = monto * 1.20 # Ejemplo con 20%
            id_p = datetime.now().strftime("%Y%m%d%H%M%S")
            n = pd.DataFrame([{'ID': id_p, 'Cliente': nombre, 'WhatsApp': wa, 'Saldo_Actual': total, 'Cuota_Valor': total/20, 'Cobrador': cobrador_asig, 'Estado': 'Activo', 'Ultimo_Abono': None}])
            st.session_state.data = pd.concat([st.session_state.data, n], ignore_index=True)
            st.session_state.prestado += monto
            st.rerun()

@st.dialog("💰 Registrar Abono")
def modal_cobro():
    # El cobrador solo ve sus propios clientes asignados
    query = (st.session_state.data['Estado'] == 'Activo')
    if not es_admin:
        query = query & (st.session_state.data['Cobrador'] == usuario_actual)
    
    mis_clientes = st.session_state.data[query]
    
    if mis_clientes.empty:
        st.warning("No tienes clientes asignados pendientes.")
        return
        
    cli = st.selectbox("SELECCIONE CLIENTE", mis_clientes['Cliente'].unique())
    idx = mis_clientes[mis_clientes['Cliente'] == cli].index[-1]
    monto = st.number_input("MONTO RECIBIDO $", value=float(mis_clientes.at[idx, 'Cuota_Valor']))
    
    if st.button("GUARDAR PAGO"):
        st.session_state.data.at[idx, 'Saldo_Actual'] -= monto
        st.session_state.recuperado += monto
        st.session_state.data.at[idx, 'Ultimo_Abono'] = datetime.now().strftime("%d/%m/%Y")
        
        nuevo_h = pd.DataFrame([{'ID_Prestamo': mis_clientes.at[idx, 'ID'], 'Fecha_Pago': datetime.now().strftime("%d/%m/%Y"), 'Monto_Abonado': monto, 'Cobrador_Accion': usuario_actual}])
        st.session_state.historial_cuotas = pd.concat([st.session_state.historial_cuotas, nuevo_h], ignore_index=True)
        
        if st.session_state.data.at[idx, 'Saldo_Actual'] <= 0:
            st.session_state.data.at[idx, 'Estado'] = 'Finalizado'
        st.rerun()

# Botones de acción rápida
st.write("")
b1, b2 = st.columns(2)
with b1: 
    if st.button("➕ PRESTAR"): modal_prestamo()
with b2: 
    if st.button("💰 COBRAR"): modal_cobro()

st.divider()

# --- 8. VISTA DE CARTERA FILTRADA ---
st.subheader(f"📋 Cartera de: {usuario_actual}")
cartera_query = (st.session_state.data['Estado'] == 'Activo')
if not es_admin:
    cartera_query = cartera_query & (st.session_state.data['Cobrador'] == usuario_actual)

cartera_vista = st.session_state.data[cartera_query]

if cartera_vista.empty:
    st.info("Lista vacía.")
else:
    for _, row in cartera_vista.iloc[::-1].iterrows():
        with st.expander(f"👤 {row['Cliente']} | Debe: ${row['Saldo_Actual']:,.0f}"):
            st.write(f"Cobrador: **{row['Cobrador']}**")
            abonos = st.session_state.historial_cuotas[st.session_state.historial_cuotas['ID_Prestamo'] == row['ID']]
            if not abonos.empty:
                for _, a in abonos.iterrows():
                    st.markdown(f'<div class="info-cuota">📅 {a["Fecha_Pago"]} | ${a["Monto_Abonado"]:,.0f} <br><small>Recibido por: {a["Cobrador_Accion"]}</small></div>', unsafe_allow_html=True)
