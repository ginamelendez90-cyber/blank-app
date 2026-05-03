import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

st.set_page_config(page_title="PrestApp Pro", page_icon="💰", layout="centered")

# --- DISEÑO PROFESIONAL ---
st.markdown("""
    <style>
    .stApp { background-color: #F2F2F7; }
    .card-caja { background-color: #1c1c1e; padding: 20px; border-radius: 15px; color: #32D74B; text-align: center; }
    .card-calle { background-color: white; padding: 20px; border-radius: 15px; color: #FF453A; text-align: center; border: 1px solid #E5E5EA; }
    div.stButton > button { background-color: #007AFF; color: white; border-radius: 12px; height: 3rem; font-weight: 600; }
    </style>
    """, unsafe_allow_html=True)

# --- INICIALIZACIÓN DE DATOS ---
if 'data' not in st.session_state:
    st.session_state.data = pd.DataFrame(columns=['Cliente', 'Saldo', 'Cuota', 'Frecuencia', 'Vence'])
if 'capital' not in st.session_state:
    st.session_state.capital = 0.0
if 'gastos_acum' not in st.session_state:
    st.session_state.gastos_acum = 0.0
if 'recuperado' not in st.session_state:
    st.session_state.recuperado = 0.0
if 'prestado' not in st.session_state:
    st.session_state.prestado = 0.0
if 'movimientos' not in st.session_state:
    st.session_state.movimientos = pd.DataFrame(columns=['Fecha', 'Tipo', 'Detalle', 'Monto'])

# --- CÁLCULOS ---
caja_real = st.session_state.capital + st.session_state.recuperado - st.session_state.prestado - st.session_state.gastos_acum
en_la_calle = st.session_state.data['Saldo'].sum()

# --- VENTANAS FLOTANTES (DIÁLOGOS) ---

@st.dialog("➕ Nuevo Préstamo")
def modal_prestamo():
    nombre = st.text_input("Nombre del Cliente").upper()
    monto = st.number_input("Dinero a entregar ($)", min_value=0.0, step=50.0)
    tasa = st.number_input("Interés %", value=20)
    c1, c2 = st.columns(2)
    with c1: frec = st.selectbox("Frecuencia", ["Diario", "Semanal"])
    with c2: cuotas = st.number_input("N° Cuotas", min_value=1, value=20)
    
    if st.button("CONFIRMAR PRÉSTAMO"):
        if monto > caja_real:
            st.error("Fondos insuficientes en caja.")
        elif nombre:
            total = monto * (1 + (tasa/100))
            venc = (datetime.now() + timedelta(days=cuotas if frec=="Diario" else cuotas*7)).strftime('%d/%m/%y')
            # Registro
            n = pd.DataFrame([{'Cliente': nombre, 'Saldo': total, 'Cuota': round(total/cuotas, 2), 'Frecuencia': frec, 'Vence': venc}])
            st.session_state.data = pd.concat([st.session_state.data, n], ignore_index=True)
            # Contabilidad
            st.session_state.prestado += monto
            m = pd.DataFrame([{'Fecha': datetime.now().strftime("%d/%m %H:%M"), 'Tipo': 'PRÉSTAMO', 'Detalle': nombre, 'Monto': -monto}])
            st.session_state.movimientos = pd.concat([st.session_state.movimientos, m], ignore_index=True)
            st.rerun()

@st.dialog("📉 Registrar Gasto")
def modal_gasto():
    det = st.text_input("Concepto (Gasolina, Cobrador, etc.)")
    val = st.number_input("Valor del Gasto ($)", min_value=0.0)
    if st.button("GUARDAR GASTO"):
        st.session_state.gastos_acum += val
        m = pd.DataFrame([{'Fecha': datetime.now().strftime("%d/%m %H:%M"), 'Tipo': 'GASTO', 'Detalle': det, 'Monto': -val}])
        st.session_state.movimientos = pd.concat([st.session_state.movimientos, m], ignore_index=True)
        st.rerun()

@st.dialog("💰 Cobrar Cuota")
def modal_cobro():
    if st.session_state.data.empty: return
    cli = st.selectbox("Seleccione Cliente", st.session_state.data['Cliente'].unique())
    idx = st.session_state.data[st.session_state.data['Cliente'] == cli].index[0]
    monto = st.number_input("Monto Recibido ($)", value=float(st.session_state.data.at[idx, 'Cuota']))
    if st.button("REGISTRAR PAGO"):
        st.session_state.data.at[idx, 'Saldo'] -= monto
        st.session_state.recuperado += monto
        m = pd.DataFrame([{'Fecha': datetime.now().strftime("%d/%m %H:%M"), 'Tipo': 'COBRO', 'Detalle': cli, 'Monto': monto}])
        st.session_state.movimientos = pd.concat([st.session_state.movimientos, m], ignore_index=True)
        st.rerun()

@st.dialog("🏦 Inyección de Capital")
def modal_cap():
    m = st.number_input("Monto a inyectar ($)", min_value=0.0)
    if st.button("CONFIRMAR"):
        st.session_state.capital += m
        m = pd.DataFrame([{'Fecha': datetime.now().strftime("%d/%m %H:%M"), 'Tipo': 'INYECCIÓN', 'Detalle': 'Capital Propio', 'Monto': m}])
        st.session_state.movimientos = pd.concat([st.session_state.movimientos, m], ignore_index=True)
        st.rerun()

# --- INTERFAZ PRINCIPAL ---
st.title("Mi PrestApp")

# Dashboard de Totales
col_a, col_b = st.columns(2)
with col_a: st.markdown(f'<div class="card-caja"><small>DISPONIBLE</small><br><h2>${caja_real:,.0f}</h2></div>', unsafe_allow_html=True)
with col_b: st.markdown(f'<div class="card-calle"><small>EN LA CALLE</small><br><h2>${en_la_calle:,.0f}</h2></div>', unsafe_allow_html=True)

st.write("")
# Botones Rápidos
c1, c2, c3, c4 = st.columns(4)
with c1: 
    if st.button("➕"): modal_prestamo()
with c2: 
    if st.button("💰"): modal_cobro()
with c3: 
    if st.button("📉"): modal_gasto()
with c4: 
    if st.button("🏦"): modal_cap()

st.divider()

# Listado y Movimientos
t1, t2 = st.tabs(["Cartera", "Movimientos Hoy"])
with t1:
    st.dataframe(st.session_state.data[['Cliente', 'Cuota', 'Frecuencia', 'Saldo', 'Vence']], use_container_width=True, hide_index=True)
with t2:
    st.table(st.session_state.movimientos.tail(10))
