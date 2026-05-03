import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

# Configuración de App Móvil
st.set_page_config(page_title="PrestApp Pro", page_icon="🏦", layout="centered")

# --- DISEÑO CSS ---
st.markdown("""
    <style>
    .stApp { background-color: #F2F2F7; }
    div.stButton > button {
        background-color: #007AFF; color: white; border-radius: 12px;
        height: 3rem; font-weight: 600; box-shadow: 0 4px 6px rgba(0,0,0,0.05);
    }
    .card {
        background-color: white; padding: 20px; border-radius: 15px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.05); margin-bottom: 10px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- INICIALIZACIÓN DE DATOS ---
if 'data' not in st.session_state:
    st.session_state.data = pd.DataFrame(columns=['Cliente', 'Total', 'Cuota', 'Saldo', 'Vence'])
if 'historial_pagos' not in st.session_state:
    st.session_state.historial_pagos = pd.DataFrame(columns=['Fecha', 'Cliente', 'Monto'])
if 'gastos' not in st.session_state:
    st.session_state.gastos = pd.DataFrame(columns=['Fecha', 'Concepto', 'Monto'])
if 'capital' not in st.session_state:
    st.session_state.capital = 0.0

# --- VENTANAS FLOTANTES (DIÁLOGOS) ---

@st.dialog("📥 Inyectar Capital")
def modal_capital():
    monto = st.number_input("Monto a ingresar ($)", min_value=0.0, step=100.0)
    if st.button("CONFIRMAR INYECCIÓN"):
        st.session_state.capital += monto
        st.success(f"Capital actualizado: ${st.session_state.capital:,.2f}")
        st.rerun()

@st.dialog("💸 Registrar Gasto")
def modal_gasto():
    concepto = st.text_input("Concepto del gasto (ej. Gasolina, Papelería)")
    monto = st.number_input("Monto del gasto ($)", min_value=0.0)
    if st.button("GUARDAR GASTO"):
        nuevo_g = pd.DataFrame([{'Fecha': datetime.now().strftime("%d/%m/%Y %H:%M"), 'Concepto': concepto, 'Monto': monto}])
        st.session_state.gastos = pd.concat([st.session_state.gastos, nuevo_g], ignore_index=True)
        st.toast("Gasto registrado")
        st.rerun()

@st.dialog("📝 Nuevo Préstamo")
def modal_nuevo():
    nombre = st.text_input("Nombre Cliente").upper()
    monto = st.number_input("Préstamo ($)", min_value=0)
    tasa = st.slider("Interés %", 0, 100, 20)
    metodo = st.selectbox("Frecuencia", ["Diario", "Semanal"])
    cuotas = st.number_input("Cuotas", min_value=1, value=20)
    
    if st.form_submit_button if False else st.button("CREAR"):
        total = monto * (1 + (tasa/100))
        valor_c = total / cuotas
        venc = (datetime.now() + timedelta(days=cuotas if metodo=="Diario" else cuotas*7)).strftime('%d/%m/%Y')
        nuevo = pd.DataFrame([{'Cliente': nombre, 'Total': total, 'Cuota': round(valor_c,2), 'Saldo': total, 'Vence': venc}])
        st.session_state.data = pd.concat([st.session_state.data, nuevo], ignore_index=True)
        st.rerun()

@st.dialog("💰 Cobrar Cuota")
def modal_cobrar():
    cliente = st.selectbox("Cliente", st.session_state.data['Cliente'].unique())
    idx = st.session_state.data[st.session_state.data['Cliente'] == cliente].index[0]
    monto = st.number_input("Monto Cobrado ($)", value=float(st.session_state.data.at[idx, 'Cuota']))
    if st.button("REGISTRAR PAGO"):
        st.session_state.data.at[idx, 'Saldo'] -= monto
        # Registro con fecha actual
        nuevo_p = pd.DataFrame([{'Fecha': datetime.now().strftime("%d/%m/%Y %H:%M"), 'Cliente': cliente, 'Monto': monto}])
        st.session_state.historial_pagos = pd.concat([st.session_state.historial_pagos, nuevo_p], ignore_index=True)
        st.success("Pago guardado")
        st.rerun()

# --- INTERFAZ PRINCIPAL ---
st.title("PrestApp Finanzas")

# Dashboard de Capital
total_gastos = st.session_state.gastos['Monto'].sum()
total_recuperado = st.session_state.historial_pagos['Monto'].sum()
caja_actual = st.session_state.capital + total_recuperado - total_gastos

st.markdown(f"""
    <div class="card">
        <small>CAJA ACTUAL DISPONIBLE</small>
        <h2 style="color:#28a745; margin:0;">${caja_actual:,.2f}</h2>
    </div>
    """, unsafe_allow_html=True)

# Botones de Acción
c1, c2, c3, c4 = st.columns(4)
with c1: 
    if st.button("➕"): modal_nuevo()
with c2: 
    if st.button("💰"): modal_cobrar()
with c3: 
    if st.button("📉"): modal_gasto()
with c4: 
    if st.button("🏦"): modal_capital()

# Reportes
tab1, tab2, tab3 = st.tabs(["Cartera", "Pagos Recientes", "Gastos"])

with tab1:
    st.dataframe(st.session_state.data[['Cliente', 'Saldo', 'Vence']], use_container_width=True, hide_index=True)

with tab2:
    st.table(st.session_state.historial_pagos.tail(5)) # Muestra los últimos 5 pagos con fecha

with tab3:
    st.write(f"Total Gastos: ${total_gastos:,.2f}")
    st.table(st.session_state.gastos)
