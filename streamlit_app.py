import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

st.set_page_config(page_title="App Prestamista Pro", page_icon="📈", layout="wide")

st.title("🏦 Control de Préstamos y Cobranza")

if 'data' not in st.session_state:
    st.session_state.data = pd.DataFrame(columns=[
        'Cliente', 'Monto Inicial', 'Interés %', 'Total a Pagar', 
        'Método', 'Cuota $', 'Pagado', 'Saldo Pendiente', 'Vencimiento'
    ])

# --- SECCIÓN 1: REGISTRO CON CÁLCULO DE CUOTAS ---
with st.expander("➕ Registrar Nuevo Préstamo"):
    with st.form("registro"):
        col1, col2 = st.columns(2)
        with col1:
            cliente = st.text_input("Nombre del Cliente").upper()
            monto = st.number_input("Monto Prestado ($)", min_value=0.0, step=50.0)
            tasa = st.number_input("Tasa de Interés (%)", min_value=0.0, value=20.0)
            
        with col2:
            metodo = st.selectbox("Frecuencia de Pago", ["Diario", "Semanal"])
            plazo_tiempo = st.number_input(f"¿Cuántos/as {metodo}s?", min_value=1, value=4)
        
        if st.form_submit_button("Calcular y Guardar"):
            total_pagar = monto * (1 + (tasa / 100))
            # Cálculo de la cuota según el método
            cuota = total_pagar / plazo_tiempo
            
            # Cálculo de fecha de vencimiento
            dias_totales = plazo_tiempo if metodo == "Diario" else plazo_tiempo * 7
            vencimiento = (datetime.now() + timedelta(days=dias_totales)).strftime('%Y-%m-%d')
            
            nuevo = pd.DataFrame([{
                'Cliente': cliente,
                'Monto Inicial': monto,
                'Interés %': tasa,
                'Total a Pagar': total_pagar,
                'Método': metodo,
                'Cuota $': round(cuota, 2),
                'Pagado': 0.0,
                'Saldo Pendiente': total_pagar,
                'Vencimiento': vencimiento
            }])
            
            st.session_state.data = pd.concat([st.session_state.data, nuevo], ignore_index=True)
            st.success(f"✅ ¡Guardado! El cliente pagará {plazo_tiempo} cuotas de ${round(cuota, 2)} ({metodo})")

# --- SECCIÓN 2: COBRO RÁPIDO ---
with st.expander("💸 Registrar Cobro de Cuota"):
    if not st.session_state.data.empty:
        c_pago = st.selectbox("Cliente que paga:", st.session_state.data['Cliente'].unique())
        # Sugerir el monto de la cuota automáticamente
        idx_c = st.session_state.data[st.session_state.data['Cliente'] == c_pago].index[0]
        cuota_sugerida = st.session_state.data.at[idx_c, 'Cuota $']
        
        monto_recibido = st.number_input("Monto recibido ($)", value=float(cuota_sugerida))
        
        if st.button("Confirmar Cobro"):
            st.session_state.data.at[idx_c, 'Pagado'] += monto_recibido
            st.session_state.data.at[idx_c, 'Saldo Pendiente'] -= monto_recibido
            st.success(f"Cobro de ${monto_recibido} registrado para {c_pago}")
    else:
        st.info("No hay préstamos activos.")

# --- SECCIÓN 3: LISTA DE COBRANZA ---
st.divider()
st.subheader("📝 Hoja de Ruta de Cobros")

if not st.session_state.data.empty:
    # Filtro rápido para ver quién debe hoy
    busqueda = st.text_input("🔍 Buscar cliente por nombre")
    df_mostrar = st.session_state.data
    if busqueda:
        df_mostrar = df_mostrar[df_mostrar['Cliente'].str.contains(busqueda.upper())]

    # Resumen visual
    st.dataframe(df_mostrar.style.format({
        'Monto Inicial': '${:,.2f}',
        'Total a Pagar': '${:,.2f}',
        'Cuota $': '${:,.2f}',
        'Pagado': '${:,.2f}',
        'Saldo Pendiente': '${:,.2f}'
    }), use_container_width=True)
    
    # Resumen de caja
    c1, c2 = st.columns(2)
    c1.metric("Recaudado Total", f"${st.session_state.data['Pagado'].sum():,.2f}")
    c2.metric("Pendiente por Cobrar", f"${st.session_state.data['Saldo Pendiente'].sum():,.2f}")
