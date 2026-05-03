import streamlit as st
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Control de Préstamos", page_icon="💰")

st.title("🏦 Mi Sistema de Préstamos")

# Simulación de base de datos sencilla
if 'data' not in st.session_state:
    st.session_state.data = pd.DataFrame(columns=['Cliente', 'Monto', 'Vencimiento', 'Estado'])

# --- FORMULARIO DE REGISTRO ---
with st.expander("➕ Registrar Nuevo Préstamo"):
    cliente = st.text_input("Nombre del Cliente")
    monto = st.number_input("Monto ($)", min_value=0)
    fecha = st.date_input("Fecha de Pago")
    if st.button("Guardar Préstamo"):
        nuevo = pd.DataFrame([[cliente, monto, fecha, "Pendiente"]], 
                             columns=['Cliente', 'Monto', 'Vencimiento', 'Estado'])
        st.session_state.data = pd.concat([st.session_state.data, nuevo], ignore_index=True)
        st.success("¡Registrado!")

# --- VISTA DE COBROS ---
st.subheader("📋 Cartera de Clientes")
st.dataframe(st.session_state.data, use_container_width=True)

# Resumen rápido
total = st.session_state.data['Monto'].sum()
st.metric("Total en Calle", f"${total:,.2f}")

