import streamlit as st
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="App de Cobros", layout="centered")

st.title("💰 Registro de Pago Diario")

# Simulamos datos que vendrían de tu base de datos
cobradores = ["Ruta 1 - Carlos", "Ruta 2 - Miguel"]
creditos_activos = ["Juan Pérez - Saldo: $150", "María López - Saldo: $300"]

# Formulario de recaudo
with st.form("registro_pago"):
    cobrador = st.selectbox("Selecciona tu usuario", cobradores)
    cliente = st.selectbox("Cliente a cobrar", creditos_activos)
    
    col1, col2 = st.columns(2)
    with col1:
        monto = st.number_input("Monto recibido", min_value=0.0, step=1.0)
    with col2:
        tipo_moneda = st.selectbox("Tipo de caja", ["Efectivo Local", "Divisas", "Transferencia"])
        
    notas = st.text_input("Observaciones (Opcional)")
    
    submit = st.form_submit_button("Registrar Pago", use_container_width=True)

if submit:
    # Aquí insertarías la lógica de Pandas o SQL para actualizar la BD
    st.success(f"✅ Pago de {monto} registrado exitosamente para {cliente}.")
