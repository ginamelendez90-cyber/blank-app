import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

st.set_page_config(page_title="Gestión de Préstamos", page_icon="💸", layout="wide")

# Título y configuración
st.title("🏦 Sistema de Control de Cobros")

# Inicialización de la base de datos en la sesión
if 'data' not in st.session_state:
    st.session_state.data = pd.DataFrame(columns=[
        'Cliente', 'Monto Inicial', 'Interés %', 'Total a Pagar', 'Pagado', 'Saldo Pendiente', 'Vencimiento'
    ])

# --- SECCIÓN 1: REGISTRO DE PRÉSTAMO ---
with st.expander("➕ Nuevo Préstamo"):
    with st.form("registro"):
        col1, col2 = st.columns(2)
        with col1:
            cliente = st.text_input("Nombre del Cliente").upper()
            monto = st.number_input("Monto Prestado ($)", min_value=0.0, step=10.0)
        with col2:
            tasa = st.number_input("Tasa de Interés (%)", min_value=0.0, value=20.0, step=1.0)
            plazo = st.number_input("Días de plazo", min_value=1, value=30)
        
        if st.form_submit_button("Registrar Préstamo"):
            total_pagar = monto * (1 + (tasa / 100))
            vencimiento = (datetime.now() + timedelta(days=plazo)).strftime('%Y-%m-%d')
            
            nuevo = pd.DataFrame([{
                'Cliente': cliente,
                'Monto Inicial': monto,
                'Interés %': tasa,
                'Total a Pagar': total_pagar,
                'Pagado': 0.0,
                'Saldo Pendiente': total_pagar,
                'Vencimiento': vencimiento
            }])
            
            st.session_state.data = pd.concat([st.session_state.data, nuevo], ignore_index=True)
            st.success(f"✅ Préstamo creado para {cliente}")

# --- SECCIÓN 2: REGISTRO DE PAGOS (ABONOS) ---
with st.expander("💰 Registrar Abono / Pago"):
    if not st.session_state.data.empty:
        cliente_pago = st.selectbox("Seleccionar Cliente", st.session_state.data['Cliente'].unique())
        monto_abono = st.number_input("Monto del Abono ($)", min_value=0.0, step=5.0)
        
        if st.button("Confirmar Pago"):
            # Buscar el índice del cliente y actualizar
            idx = st.session_state.data[st.session_state.data['Cliente'] == cliente_pago].index[0]
            st.session_state.data.at[idx, 'Pagado'] += monto_abono
            st.session_state.data.at[idx, 'Saldo Pendiente'] -= monto_abono
            st.success(f"Abono de ${monto_abono} registrado para {cliente_pago}")
    else:
        st.info("No hay clientes registrados aún.")

# --- SECCIÓN 3: RESUMEN Y CARTERA ---
st.divider()
st.subheader("📊 Resumen de Cartera")

if not st.session_state.data.empty:
    # Indicadores rápidos (Métricas)
    total_en_calle = st.session_state.data['Saldo Pendiente'].sum()
    total_ganancia_esperada = (st.session_state.data['Total a Pagar'] - st.session_state.data['Monto Inicial']).sum()
    
    m1, m2 = st.columns(2)
    m1.metric("Saldo Total Pendiente", f"${total_en_calle:,.2f}")
    m2.metric("Ganancia Estimada", f"${total_ganancia_esperada:,.2f}", delta_color="normal")

    # Tabla detallada
    st.dataframe(st.session_state.data.style.highlight_max(axis=0, subset=['Saldo Pendiente'], color='#FFCCCC'), use_container_width=True)
else:
    st.write("La cartera está vacía.")
