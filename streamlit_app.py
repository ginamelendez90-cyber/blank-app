import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

st.set_page_config(page_title="PrestApp Elite", page_icon="💰", layout="centered")

# --- DISEÑO Y ESTILO ---
st.markdown("""
    <style>
    .stApp { background-color: #F2F2F7; }
    .card-caja { background-color: #1c1c1e; padding: 25px; border-radius: 20px; color: #32D74B; text-align: center; border: 2px solid #32D74B; }
    .card-calle { background-color: white; padding: 25px; border-radius: 20px; color: #FF453A; text-align: center; border: 2px solid #FF453A; }
    /* Estilo para los botones de la pantalla principal */
    .main-btn div.stButton > button { background-color: #007AFF; color: white; border-radius: 12px; height: 4rem; font-weight: 700; font-size: 18px; }
    </style>
    """, unsafe_allow_html=True)

# --- INICIALIZACIÓN ---
if 'data' not in st.session_state:
    st.session_state.data = pd.DataFrame(columns=['Cliente', 'Saldo', 'Cuota', 'Frecuencia', 'Vence'])
if 'capital' not in st.session_state: st.session_state.capital = 0.0
if 'gastos_acum' not in st.session_state: st.session_state.gastos_acum = 0.0
if 'recuperado' not in st.session_state: st.session_state.recuperado = 0.0
if 'prestado' not in st.session_state: st.session_state.prestado = 0.0
if 'movimientos' not in st.session_state:
    st.session_state.movimientos = pd.DataFrame(columns=['Fecha', 'Tipo', 'Detalle', 'Monto'])

# --- CÁLCULOS ---
caja_real = st.session_state.capital + st.session_state.recuperado - st.session_state.prestado - st.session_state.gastos_acum
en_la_calle = st.session_state.data['Saldo'].sum()

# --- MODALES (VENTANAS FLOTANTES) ---
@st.dialog("➕ Nuevo Préstamo")
def modal_prestamo():
    nombre = st.text_input("Nombre del Cliente").upper()
    monto = st.number_input("Dinero a entregar ($)", min_value=0.0, step=50.0)
    tasa = st.number_input("Interés %", value=20)
    c1, c2 = st.columns(2)
    with c1: frec = st.selectbox("Frecuencia", ["Diario", "Semanal"])
    with c2: cuotas = st.number_input("N° Cuotas", min_value=1, value=20)
    if st.button("CONFIRMAR PRÉSTAMO"):
        if monto > caja_real: st.error("Fondos insuficientes.")
        elif nombre:
            total = monto * (1 + (tasa/100))
            venc = (datetime.now() + timedelta(days=cuotas if frec=="Diario" else cuotas*7)).strftime('%d/%m/%y')
            n = pd.DataFrame([{'Cliente': nombre, 'Saldo': total, 'Cuota': round(total/cuotas, 2), 'Frecuencia': frec, 'Vence': venc}])
            st.session_state.data = pd.concat([st.session_state.data, n], ignore_index=True)
            st.session_state.prestado += monto
            m = pd.DataFrame([{'Fecha': datetime.now().strftime("%H:%M"), 'Tipo': '🔴 PRÉSTAMO', 'Detalle': nombre, 'Monto': -monto}])
            st.session_state.movimientos = pd.concat([st.session_state.movimientos, m], ignore_index=True)
            st.rerun()

@st.dialog("💰 Cobrar Cuota")
def modal_cobro():
    if st.session_state.data.empty: return
    cli = st.selectbox("Cliente", st.session_state.data['Cliente'].unique())
    idx = st.session_state.data[st.session_state.data['Cliente'] == cli].index[0]
    monto = st.number_input("Monto Recibido", value=float(st.session_state.data.at[idx, 'Cuota']))
    if st.button("REGISTRAR PAGO"):
        st.session_state.data.at[idx, 'Saldo'] -= monto
        st.session_state.recuperado += monto
        m = pd.DataFrame([{'Fecha': datetime.now().strftime("%H:%M"), 'Tipo': '🟢 COBRO', 'Detalle': cli, 'Monto': monto}])
        st.session_state.movimientos = pd.concat([st.session_state.movimientos, m], ignore_index=True)
        st.rerun()

@st.dialog("📉 Gasto Administrativo")
def modal_gasto():
    det = st.text_input("Concepto del Gasto")
    val = st.number_input("Valor ($)", min_value=0.0)
    if st.button("GUARDAR GASTO"):
        st.session_state.gastos_acum += val
        m = pd.DataFrame([{'Fecha': datetime.now().strftime("%H:%M"), 'Tipo': '🔴 GASTO', 'Detalle': det, 'Monto': -val}])
        st.session_state.movimientos = pd.concat([st.session_state.movimientos, m], ignore_index=True)
        st.rerun()

@st.dialog("🏦 Inyección de Capital")
def modal_cap():
    m = st.number_input("Monto a Inyectar ($)", min_value=0.0)
    if st.button("CONFIRMAR INYECCIÓN"):
        st.session_state.capital += m
        m = pd.DataFrame([{'Fecha': datetime.now().strftime("%H:%M"), 'Tipo': '🟢 CAPITAL', 'Detalle': 'Inyección', 'Monto': m}])
        st.session_state.movimientos = pd.concat([st.session_state.movimientos, m], ignore_index=True)
        st.rerun()

# --- MENÚ LATERAL (LAS "3 RAYITAS") ---
with st.sidebar:
    st.title("Configuración")
    st.write("Gestión de Fondos")
    if st.button("🏦 Inyectar Capital"):
        modal_cap()
    if st.button("📉 Registrar Gasto"):
        modal_gasto()
    st.divider()
    st.info("Usa este menú para administrar el dinero base y los gastos operativos.")

# --- INTERFAZ PRINCIPAL ---
st.title("PrestApp Elite 🏦")

col_a, col_b = st.columns(2)
with col_a: st.markdown(f'<div class="card-caja"><small>DISPONIBLE</small><br><h2>${caja_real:,.0f}</h2></div>', unsafe_allow_html=True)
with col_b: st.markdown(f'<div class="card-calle"><small>EN LA CALLE</small><br><h2>${en_la_calle:,.0f}</h2></div>', unsafe_allow_html=True)

st.write("")
# Botones Principales más grandes
st.markdown('<div class="main-btn">', unsafe_allow_html=True)
c1, c2 = st.columns(2)
with c1: 
    if st.button("➕ NUEVO"): modal_prestamo()
with c2: 
    if st.button("💰 COBRAR"): modal_cobro()
st.markdown('</div>', unsafe_allow_html=True)

st.divider()

# --- CARTERA Y MOVIMIENTOS ---
st.subheader("📋 CARTERA ACTIVA")
if not st.session_state.data.empty:
    st.dataframe(st.session_state.data, use_container_width=True, hide_index=True)
else:
    st.info("Sin clientes activos.")

st.subheader("🕒 MOVIMIENTOS RECIENTES")
if not st.session_state.movimientos.empty:
    for _, row in st.session_state.movimientos.iloc[::-1].head(5).iterrows():
        color = "#32D74B" if row['Monto'] > 0 else "#FF453A"
        st.markdown(f"""
        <div style="background-color: white; padding: 12px; border-radius: 15px; margin-bottom: 8px; border-left: 6px solid {color}; shadow: 0 2px 4px rgba(0,0,0,0.05);">
            <small style="color: gray;">{row['Fecha']}</small> | <strong>{row['Tipo']}</strong><br>
            {row['Detalle']} <span style="float: right; color:{color}; font-weight:bold;">${abs(row['Monto']):,.0f}</span>
        </div>
        """, unsafe_allow_html=True)
