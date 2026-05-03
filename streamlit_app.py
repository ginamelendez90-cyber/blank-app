import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

# Configuración de la App
st.set_page_config(page_title="PrestApp Elite", page_icon="💰", layout="centered")

# --- DISEÑO ---
st.markdown("""
    <style>
    .stApp { background-color: #F2F2F7; }
    .card-caja { background-color: #1c1c1e; padding: 20px; border-radius: 20px; color: #32D74B; text-align: center; border: 2px solid #32D74B; }
    .card-calle { background-color: white; padding: 20px; border-radius: 20px; color: #FF453A; text-align: center; border: 1px solid #E5E5EA; }
    .main-btn div.stButton > button { background-color: #007AFF; color: white; border-radius: 12px; height: 3.5rem; font-weight: 700; }
    .info-cuota { background-color: #f0f0f5; padding: 10px; border-radius: 10px; border-left: 4px solid #007AFF; margin-bottom: 5px; font-size: 14px; }
    </style>
    """, unsafe_allow_html=True)

# --- INICIALIZACIÓN DE DATOS ---
if 'data' not in st.session_state:
    st.session_state.data = pd.DataFrame(columns=['ID', 'Cliente', 'Saldo_Inicial', 'Saldo_Actual', 'Cuota_Valor', 'Frecuencia', 'Vence'])
if 'historial_cuotas' not in st.session_state:
    st.session_state.historial_cuotas = pd.DataFrame(columns=['ID_Prestamo', 'Fecha_Pago', 'Monto_Abonado'])
if 'capital' not in st.session_state: st.session_state.capital = 0.0
if 'gastos_df' not in st.session_state:
    st.session_state.gastos_df = pd.DataFrame(columns=['Fecha', 'Concepto', 'Monto', 'Mes_Año'])
if 'recuperado' not in st.session_state: st.session_state.recuperado = 0.0
if 'prestado' not in st.session_state: st.session_state.prestado = 0.0
if 'movimientos' not in st.session_state:
    st.session_state.movimientos = pd.DataFrame(columns=['Fecha', 'Tipo', 'Detalle', 'Monto'])

# --- CÁLCULOS ---
total_gastos = st.session_state.gastos_df['Monto'].sum()
caja_real = st.session_state.capital + st.session_state.recuperado - st.session_state.prestado - total_gastos
en_la_calle = st.session_state.data['Saldo_Actual'].sum()

# --- MODALES ---

@st.dialog("➕ Nuevo Préstamo")
def modal_prestamo():
    clientes_ex = sorted(st.session_state.data['Cliente'].unique().tolist())
    tipo = st.radio("Registro:", ["Nuevo", "Renovación"], horizontal=True)
    nombre = st.text_input("Nombre").upper() if tipo == "Nuevo" else st.selectbox("Seleccione Cliente", clientes_ex)
    monto = st.number_input("Dinero a entregar ($)", min_value=0.0)
    tasa = st.number_input("Interés %", value=20)
    frec = st.selectbox("Frecuencia", ["Diario", "Semanal"])
    cuotas = st.number_input("N° Cuotas", min_value=1, value=20)
    
    if st.button("CREAR CRÉDITO"):
        if monto > caja_real: st.error("Fondos insuficientes en caja.")
        elif nombre:
            total = monto * (1 + (tasa/100))
            id_p = datetime.now().strftime("%Y%m%d%H%M%S")
            venc = (datetime.now() + timedelta(days=cuotas if frec=="Diario" else cuotas*7)).strftime('%d/%m/%y')
            n = pd.DataFrame([{'ID': id_p, 'Cliente': nombre, 'Saldo_Inicial': total, 'Saldo_Actual': total, 'Cuota_Valor': round(total/cuotas, 2), 'Frecuencia': frec, 'Vence': venc}])
            st.session_state.data = pd.concat([st.session_state.data, n], ignore_index=True)
            st.session_state.prestado += monto
            m = pd.DataFrame([{'Fecha': datetime.now().strftime("%H:%M"), 'Tipo': '🔴 PRÉSTAMO', 'Detalle': nombre, 'Monto': -monto}])
            st.session_state.movimientos = pd.concat([st.session_state.movimientos, m], ignore_index=True)
            st.rerun()

@st.dialog("📉 Registrar Gasto")
def modal_gasto():
    c = st.text_input("Concepto (Gasolina, Cobrador, etc.)")
    v = st.number_input("Valor ($)", min_value=0.0)
    f = st.date_input("Fecha", datetime.now())
    if st.button("GUARDAR GASTO"):
        mes_anio = f.strftime("%m/%Y")
        nuevo_g = pd.DataFrame([{'Fecha': f.strftime("%d/%m/%Y"), 'Concepto': c, 'Monto': v, 'Mes_Año': mes_anio}])
        st.session_state.gastos_df = pd.concat([st.session_state.gastos_df, nuevo_g], ignore_index=True)
        m = pd.DataFrame([{'Fecha': datetime.now().strftime("%H:%M"), 'Tipo': '🔴 GASTO', 'Detalle': c, 'Monto': -v}])
        st.session_state.movimientos = pd.concat([st.session_state.movimientos, m], ignore_index=True)
        st.rerun()

# --- MENÚ LATERAL (3 RAYITAS) ---
with st.sidebar:
    st.title("Administración")
    if st.button("🏦 Inyectar Capital"):
        @st.dialog("Inyección")
        def iny():
            val = st.number_input("Monto", 0.0)
            if st.button("OK"):
                st.session_state.capital += val
                st.rerun()
        iny()
    
    if st.button("📉 Registrar Gasto"):
        modal_gasto()
    
    st.divider()
    st.subheader("📊 Reporte de Gastos")
    if not st.session_state.gastos_df.empty:
        meses = sorted(st.session_state.gastos_df['Mes_Año'].unique().tolist(), reverse=True)
        mes_sel = st.selectbox("Filtrar por Mes", meses)
        gastos_mes = st.session_state.gastos_df[st.session_state.gastos_df['Mes_Año'] == mes_sel]
        st.metric(f"Total Gastos {mes_sel}", f"${gastos_mes['Monto'].sum():,.0f}")
        st.dataframe(gastos_mes[['Fecha', 'Concepto', 'Monto']], use_container_width=True, hide_index=True)
    else:
        st.info("No hay gastos registrados aún.")

# --- PANTALLA PRINCIPAL ---
st.title("PrestApp Elite")

col_a, col_b = st.columns(2)
with col_a: st.markdown(f'<div class="card-caja"><small>DISPONIBLE</small><br><h2>${caja_real:,.0f}</h2></div>', unsafe_allow_html=True)
with col_b: st.markdown(f'<div class="card-calle"><small>EN LA CALLE</small><br><h2>${en_la_calle:,.0f}</h2></div>', unsafe_allow_html=True)

st.write("")
c1, c2 = st.columns(2)
with c1: 
    if st.button("➕ PRESTAR"): modal_prestamo()
with c2: 
    @st.dialog("💰 Cobrar Cuota")
    def modal_cobro():
        activos = st.session_state.data[st.session_state.data['Saldo_Actual'] > 0]
        if activos.empty: return
        cli = st.selectbox("Cobrar a:", activos['Cliente'].unique())
        p_idx = activos[activos['Cliente'] == cli].index[-1]
        id_p = activos.at[p_idx, 'ID']
        sug = activos.at[p_idx, 'Cuota_Valor']
        monto = st.number_input("Abono ($)", value=float(sug))
        if st.button("REGISTRAR PAGO"):
            st.session_state.data.at[p_idx, 'Saldo_Actual'] -= monto
            st.session_state.recuperado += monto
            nuevo_abono = pd.DataFrame([{'ID_Prestamo': id_p, 'Fecha_Pago': datetime.now().strftime("%d/%m/%Y"), 'Monto_Abonado': monto}])
            st.session_state.historial_cuotas = pd.concat([st.session_state.historial_cuotas, nuevo_abono], ignore_index=True)
            m = pd.DataFrame([{'Fecha': datetime.now().strftime("%H:%M"), 'Tipo': '🟢 COBRO', 'Detalle': cli, 'Monto': monto}])
            st.session_state.movimientos = pd.concat([st.session_state.movimientos, m], ignore_index=True)
            st.rerun()
    if st.button("💰 COBRAR"): modal_cobro()

st.divider()

# --- CARTERA Y ABONOS ---
st.subheader("📋 CARTERA ACTIVA")
if not st.session_state.data.empty:
    for index, row in st.session_state.data.iloc[::-1].iterrows():
        if row['Saldo_Actual'] > 0:
            with st.expander(f"👤 {row['Cliente']} | Pendiente: ${row['Saldo_Actual']:,.0f}"):
                st.write(f"**Cuota:** ${row['Cuota_Valor']} ({row['Frecuencia']})")
                abonos_cli = st.session_state.historial_cuotas[st.session_state.historial_cuotas['ID_Prestamo'] == row['ID']]
                if not abonos_cli.empty:
                    st.write("**Días de Abono:**")
                    for _, abono in abonos_cli.iterrows():
                        st.markdown(f'<div class="info-cuota">📅 {abono["Fecha_Pago"]} — ${abono["Monto_Abonado"]:,.0f}</div>', unsafe_allow_html=True)
                else:
                    st.caption("Sin abonos registrados.")
else:
    st.info("Sin préstamos activos.")
