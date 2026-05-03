import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

st.set_page_config(page_title="PrestApp Elite", page_icon="💰", layout="centered")

# --- 1. ESTILOS VISUALES ---
st.markdown("""
    <style>
    .stApp { background-color: #F2F2F7; }
    .card-caja { background-color: #1c1c1e; padding: 20px; border-radius: 20px; color: #32D74B; text-align: center; border: 2px solid #32D74B; }
    .card-calle { background-color: white; padding: 20px; border-radius: 20px; color: #FF453A; text-align: center; border: 1px solid #E5E5EA; }
    .main-btn div.stButton > button { background-color: #007AFF; color: white; border-radius: 12px; height: 3.5rem; font-weight: 700; width: 100%; }
    .info-cuota { background-color: #f0f0f5; padding: 10px; border-radius: 10px; border-left: 4px solid #007AFF; margin-bottom: 5px; font-size: 14px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. BASE DE DATOS (MEMORIA) ---
if 'data' not in st.session_state:
    st.session_state.data = pd.DataFrame(columns=['ID', 'Cliente', 'Saldo_Inicial', 'Saldo_Actual', 'Cuota_Valor', 'Frecuencia', 'Vence', 'Estado'])
if 'historial_cuotas' not in st.session_state:
    st.session_state.historial_cuotas = pd.DataFrame(columns=['ID_Prestamo', 'Fecha_Pago', 'Monto_Abonado'])
if 'gastos_df' not in st.session_state:
    st.session_state.gastos_df = pd.DataFrame(columns=['Fecha', 'Concepto', 'Monto', 'Mes_Año'])
if 'capital' not in st.session_state: st.session_state.capital = 0.0
if 'recuperado' not in st.session_state: st.session_state.recuperado = 0.0
if 'prestado' not in st.session_state: st.session_state.prestado = 0.0

# --- 3. CÁLCULOS DE DINERO ---
total_gastos = st.session_state.gastos_df['Monto'].sum()
disponible = st.session_state.capital + st.session_state.recuperado - st.session_state.prestado - total_gastos
en_la_calle = st.session_state.data[st.session_state.data['Estado'] == 'Activo']['Saldo_Actual'].sum()

# --- 4. FUNCIONES (MODALES) ---

@st.dialog("➕ Nuevo Préstamo / Renovación")
def modal_prestamo():
    clientes_registrados = sorted(st.session_state.data['Cliente'].unique().tolist())
    tipo = st.radio("¿Es un cliente nuevo?", ["Sí, Nuevo", "No, Renovación"], horizontal=True)
    
    if tipo == "Sí, Nuevo":
        nombre = st.text_input("Nombre completo").upper()
    else:
        nombre = st.selectbox("Seleccione cliente de la lista", clientes_registrados) if clientes_registrados else st.text_input("Nombre").upper()
    
    monto = st.number_input("Dinero a entregar ($)", min_value=0.0, step=50.0)
    tasa = st.number_input("Interés %", value=20)
    f1, f2 = st.columns(2)
    with f1: frec = st.selectbox("Frecuencia", ["Diario", "Semanal"])
    with f2: cuotas = st.number_input("Cuotas", min_value=1, value=20)
    
    if st.button("CONFIRMAR CRÉDITO"):
        if monto > disponible: st.error("No tienes suficiente dinero en caja.")
        elif nombre:
            total = monto * (1 + (tasa/100))
            id_p = datetime.now().strftime("%Y%m%d%H%M%S")
            venc = (datetime.now() + timedelta(days=cuotas if frec=="Diario" else cuotas*7)).strftime('%d/%m/%y')
            nuevo = pd.DataFrame([{'ID': id_p, 'Cliente': nombre, 'Saldo_Inicial': total, 'Saldo_Actual': total, 'Cuota_Valor': round(total/cuotas, 2), 'Frecuencia': frec, 'Vence': venc, 'Estado': 'Activo'}])
            st.session_state.data = pd.concat([st.session_state.data, nuevo], ignore_index=True)
            st.session_state.prestado += monto
            st.rerun()

@st.dialog("💰 Cobrar Cuota")
def modal_cobro():
    activos = st.session_state.data[st.session_state.data['Estado'] == 'Activo']
    if activos.empty:
        st.warning("No hay nadie a quien cobrarle hoy.")
        return
    cli = st.selectbox("¿Quién va a pagar?", activos['Cliente'].unique())
    p_idx = activos[activos['Cliente'] == cli].index[-1]
    
    st.write(f"Saldo pendiente: **${activos.at[p_idx, 'Saldo_Actual']:,.0f}**")
    monto = st.number_input("Monto del abono", value=float(activos.at[p_idx, 'Cuota_Valor']))
    
    if st.button("REGISTRAR PAGO"):
        st.session_state.data.at[p_idx, 'Saldo_Actual'] -= monto
        st.session_state.recuperado += monto
        # Guardar el día exacto del abono
        abono = pd.DataFrame([{'ID_Prestamo': activos.at[p_idx, 'ID'], 'Fecha_Pago': datetime.now().strftime("%d/%m/%Y"), 'Monto_Abonado': monto}])
        st.session_state.historial_cuotas = pd.concat([st.session_state.historial_cuotas, abono], ignore_index=True)
        # Si pagó todo, finalizar
        if st.session_state.data.at[p_idx, 'Saldo_Actual'] <= 0:
            st.session_state.data.at[p_idx, 'Estado'] = 'Finalizado'
            st.balloons()
        st.rerun()

# --- 5. MENÚ LATERAL (3 RAYITAS) ---
with st.sidebar:
    st.title("Menú de Control")
    
    if st.button("🏦 Inyectar Capital (Base)"):
        @st.dialog("Cargar Dinero")
        def iny():
            m = st.number_input("Monto", 0.0)
            if st.button("Guardar"):
                st.session_state.capital += m
                st.rerun()
        iny()
        
    if st.button("📉 Registrar Gasto"):
        @st.dialog("Gasto")
        def gas():
            c = st.text_input("Concepto")
            v = st.number_input("Monto", 0.0)
            f = st.date_input("Fecha")
            if st.button("Guardar"):
                mes = f.strftime("%m/%Y")
                nuevo_g = pd.DataFrame([{'Fecha': f.strftime("%d/%m/%Y"), 'Concepto': c, 'Monto': v, 'Mes_Año': mes}])
                st.session_state.gastos_df = pd.concat([st.session_state.gastos_df, nuevo_g], ignore_index=True)
                st.rerun()
        gas()

    st.divider()
    st.subheader("📊 Reporte de Gastos")
    if not st.session_state.gastos_df.empty:
        mes_sel = st.selectbox("Seleccione Mes", st.session_state.gastos_df['Mes_Año'].unique())
        total_m = st.session_state.gastos_df[st.session_state.gastos_df['Mes_Año'] == mes_sel]['Monto'].sum()
        st.write(f"Gastado en {mes_sel}: **${total_m:,.0f}**")
    
    st.divider()
    st.subheader("✅ Historial de Pagados")
    pagados = st.session_state.data[st.session_state.data['Estado'] == 'Finalizado']
    for p in pagados['Cliente'].unique():
        st.write(f"🤝 {p}")

# --- 6. PANTALLA PRINCIPAL ---
st.title("PrestApp Elite")

c1, c2 = st.columns(2)
with c1: st.markdown(f'<div class="card-caja"><small>EN CAJA</small><br><h2>${disponible:,.0f}</h2></div>', unsafe_allow_html=True)
with c2: st.markdown(f'<div class="card-calle"><small>EN LA CALLE</small><br><h2>${en_la_calle:,.0f}</h2></div>', unsafe_allow_html=True)

st.write("")
b1, b2 = st.columns(2)
with b1: 
    if st.button("➕ NUEVO PRÉSTAMO"): modal_prestamo()
with b2: 
    if st.button("💰 COBRAR CUOTA"): modal_cobro()

st.divider()

st.subheader("📋 CLIENTES ACTIVOS (DEUDORES)")
activos = st.session_state.data[st.session_state.data['Estado'] == 'Activo']
if activos.empty:
    st.info("No hay préstamos activos.")
else:
    for idx, row in activos.iloc[::-1].iterrows():
        with st.expander(f"👤 {row['Cliente']} | Debe: ${row['Saldo_Actual']:,.0f}"):
            st.write(f"**Cuota:** ${row['Cuota_Valor']} | **Vence:** {row['Vence']}")
            # Mostrar los días de abono
            abonos = st.session_state.historial_cuotas[st.session_state.historial_cuotas['ID_Prestamo'] == row['ID']]
            if not abonos.empty:
                st.write("**Historial de Abonos:**")
                for _, a in abonos.iterrows():
                    st.markdown(f'<div class="info-cuota">📅 {a["Fecha_Pago"]} — ${a["Monto_Abonado"]:,.0f}</div>', unsafe_allow_html=True)
            else:
                st.caption("Aún no ha realizado abonos.")
