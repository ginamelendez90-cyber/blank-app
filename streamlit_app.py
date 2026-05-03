import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

st.set_page_config(page_title="PrestApp Gold", page_icon="💰", layout="centered")

# --- ESTILOS ---
st.markdown("""
    <style>
    .stApp { background-color: #F2F2F7; }
    .card-caja {
        background-color: #1c1c1e; padding: 20px; border-radius: 15px;
        color: #32D74B; text-align: center; margin-bottom: 10px;
    }
    .card-calle {
        background-color: white; padding: 20px; border-radius: 15px;
        color: #FF453A; text-align: center; border: 1px solid #E5E5EA;
    }
    </style>
    """, unsafe_allow_html=True)

# --- INICIALIZACIÓN ---
if 'data' not in st.session_state:
    st.session_state.data = pd.DataFrame(columns=['Cliente', 'Monto_Base', 'Saldo', 'Vence'])
if 'capital_inyectado' not in st.session_state:
    st.session_state.capital_inyectado = 0.0
if 'gastos_total' not in st.session_state:
    st.session_state.gastos_total = 0.0
if 'recuperado_total' not in st.session_state:
    st.session_state.recuperado_total = 0.0
if 'prestado_total' not in st.session_state:
    st.session_state.prestado_total = 0.0
if 'historial' not in st.session_state:
    st.session_state.historial = pd.DataFrame(columns=['Fecha', 'Tipo', 'Detalle', 'Monto'])

# --- CÁLCULOS DE ESTADO ---
# Caja = Lo que metí + lo que cobré - lo que presté - lo que gasté
caja_disponible = st.session_state.capital_inyectado + st.session_state.recuperado_total - st.session_state.prestado_total - st.session_state.gastos_total
en_la_calle = st.session_state.data['Saldo'].sum()

# --- FUNCIONES / DIÁLOGOS ---

@st.dialog("➕ Nuevo Préstamo")
def modal_nuevo():
    nombre = st.text_input("Cliente").upper()
    monto = st.number_input("Monto a entregar ($)", min_value=0.0, step=100.0)
    tasa = st.number_input("Interés %", value=20)
    cuotas = st.number_input("Cuotas", min_value=1, value=20)
    
    if st.button("DAR PRÉSTAMO"):
        if monto > caja_disponible:
            st.error(f"❌ No tienes suficiente dinero en caja. Disponible: ${caja_disponible:,.2f}")
        else:
            total_cobrar = monto * (1 + (tasa/100))
            venc = (datetime.now() + timedelta(days=cuotas)).strftime('%d/%m/%y')
            
            # Registrar préstamo
            nuevo = pd.DataFrame([{'Cliente': nombre, 'Monto_Base': monto, 'Saldo': total_cobrar, 'Vence': venc}])
            st.session_state.data = pd.concat([st.session_state.data, nuevo], ignore_index=True)
            
            # Actualizar contadores
            st.session_state.prestado_total += monto
            
            # Historial
            h = pd.DataFrame([{'Fecha': datetime.now().strftime("%d/%m %H:%M"), 'Tipo': 'PRÉSTAMO', 'Detalle': nombre, 'Monto': -monto}])
            st.session_state.historial = pd.concat([st.session_state.historial, h], ignore_index=True)
            st.rerun()

@st.dialog("💰 Cobrar Cuota")
def modal_cobro():
    if st.session_state.data.empty: return
    cli = st.selectbox("Cliente", st.session_state.data['Cliente'].unique())
    idx = st.session_state.data[st.session_state.data['Cliente'] == cli].index[0]
    monto = st.number_input("Monto recibido", value=float(st.session_state.data.at[idx, 'Saldo'] / 10)) # sugerencia
    
    if st.button("CONFIRMAR PAGO"):
        st.session_state.data.at[idx, 'Saldo'] -= monto
        st.session_state.recuperado_total += monto
        h = pd.DataFrame([{'Fecha': datetime.now().strftime("%d/%m %H:%M"), 'Tipo': 'COBRO', 'Detalle': cli, 'Monto': monto}])
        st.session_state.historial = pd.concat([st.session_state.historial, h], ignore_index=True)
        st.rerun()

@st.dialog("🏦 Inyectar Capital")
def modal_cap():
    m = st.number_input("Monto a inyectar", min_value=0.0)
    if st.button("INYECTAR"):
        st.session_state.capital_inyectado += m
        h = pd.DataFrame([{'Fecha': datetime.now().strftime("%d/%m %H:%M"), 'Tipo': 'INYECCIÓN', 'Detalle': 'Capital propio', 'Monto': m}])
        st.session_state.historial = pd.concat([st.session_state.historial, h], ignore_index=True)
        st.rerun()

# --- PANTALLA PRINCIPAL ---
st.title("Mi Negocio")

# Dashboard Visual
col_a, col_b = st.columns(2)
with col_a:
    st.markdown(f'<div class="card-caja"><small>EN CAJA</small><br><h2>${caja_disponible:,.2f}</h2></div>', unsafe_allow_html=True)
with col_b:
    st.markdown(f'<div class="card-calle"><small>EN LA CALLE</small><br><h2>${en_la_calle:,.2f}</h2></div>', unsafe_allow_html=True)

st.write("")
c1, c2, c3 = st.columns(3)
with c1: 
    if st.button("➕ Prest"): modal_nuevo()
with c2: 
    if st.button("💰 Cobr"): modal_cobro()
with c3: 
    if st.button("🏦 Cap"): modal_cap()

st.divider()
st.subheader("📋 Movimientos del día")
st.table(st.session_state.historial.tail(5))
