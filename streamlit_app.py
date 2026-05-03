import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

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

# --- INICIALIZACIÓN ---
if 'data' not in st.session_state:
    st.session_state.data = pd.DataFrame(columns=['ID', 'Cliente', 'Saldo_Inicial', 'Saldo_Actual', 'Cuota_Valor', 'Frecuencia', 'Vence'])
if 'historial_cuotas' not in st.session_state:
    st.session_state.historial_cuotas = pd.DataFrame(columns=['ID_Prestamo', 'Fecha_Pago', 'Monto_Abonado'])
if 'capital' not in st.session_state: st.session_state.capital = 0.0
if 'gastos_acum' not in st.session_state: st.session_state.gastos_acum = 0.0
if 'recuperado' not in st.session_state: st.session_state.recuperado = 0.0
if 'prestado' not in st.session_state: st.session_state.prestado = 0.0
if 'movimientos' not in st.session_state:
    st.session_state.movimientos = pd.DataFrame(columns=['Fecha', 'Tipo', 'Detalle', 'Monto'])

# --- CÁLCULOS ---
caja_real = st.session_state.capital + st.session_state.recuperado - st.session_state.prestado - st.session_state.gastos_acum
en_la_calle = st.session_state.data['Saldo_Actual'].sum()

# --- MODALES ---

@st.dialog("➕ Nuevo Préstamo")
def modal_prestamo():
    clientes_ex = sorted(st.session_state.data['Cliente'].unique().tolist())
    tipo = st.radio("Registro:", ["Nuevo", "Renovación"], horizontal=True)
    nombre = st.text_input("Nombre").upper() if tipo == "Nuevo" else st.selectbox("Cliente", clientes_ex)
    
    monto = st.number_input("Entregar ($)", min_value=0.0)
    tasa = st.number_input("Interés %", value=20)
    frec = st.selectbox("Frecuencia", ["Diario", "Semanal"])
    cuotas = st.number_input("N° Cuotas", min_value=1, value=20)
    
    if st.button("CREAR CRÉDITO"):
        if monto > caja_real: st.error("Sin fondos")
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

@st.dialog("💰 Cobrar Cuota")
def modal_cobro():
    activos = st.session_state.data[st.session_state.data['Saldo_Actual'] > 0]
    if activos.empty: return
    cli = st.selectbox("Cobrar a:", activos['Cliente'].unique())
    # Seleccionamos el préstamo más reciente de ese cliente
    p_idx = activos[activos['Cliente'] == cli].index[-1]
    id_p = activos.at[p_idx, 'ID']
    
    sug = activos.at[p_idx, 'Cuota_Valor']
    monto = st.number_input("Abono ($)", value=float(sug))
    
    if st.button("REGISTRAR ABONO"):
        st.session_state.data.at[p_idx, 'Saldo_Actual'] -= monto
        st.session_state.recuperado += monto
        # Registro en el historial de días de abonos
        nuevo_abono = pd.DataFrame([{'ID_Prestamo': id_p, 'Fecha_Pago': datetime.now().strftime("%d/%m/%Y"), 'Monto_Abonado': monto}])
        st.session_state.historial_cuotas = pd.concat([st.session_state.historial_cuotas, nuevo_abono], ignore_index=True)
        
        m = pd.DataFrame([{'Fecha': datetime.now().strftime("%H:%M"), 'Tipo': '🟢 COBRO', 'Detalle': cli, 'Monto': monto}])
        st.session_state.movimientos = pd.concat([st.session_state.movimientos, m], ignore_index=True)
        st.rerun()

# --- MENÚ LATERAL ---
with st.sidebar:
    st.title("Sistema")
    if st.button("🏦 Inyectar Capital"):
        @st.dialog("Inyectar")
        def iny():
            val = st.number_input("Monto", 0.0)
            if st.button("OK"):
                st.session_state.capital += val
                st.rerun()
        iny()
    if st.button("📉 Gasto"):
        @st.dialog("Gasto")
        def gas():
            c = st.text_input("Concepto")
            v = st.number_input("Valor", 0.0)
            if st.button("OK"):
                st.session_state.gastos_acum += v
                st.rerun()
        gas()

# --- PANTALLA PRINCIPAL ---
st.title("PrestApp Elite")

c_a, c_b = st.columns(2)
with c_a: st.markdown(f'<div class="card-caja"><small>EN CAJA</small><br><h2>${caja_real:,.0f}</h2></div>', unsafe_allow_html=True)
with c_b: st.markdown(f'<div class="card-calle"><small>EN CALLE</small><br><h2>${en_la_calle:,.0f}</h2></div>', unsafe_allow_html=True)

st.write("")
col1, col2 = st.columns(2)
with col1: 
    if st.button("➕ PRESTAR"): modal_prestamo()
with col2: 
    if st.button("💰 COBRAR"): modal_cobro()

st.divider()

# --- CARTERA CON REGISTRO DE DÍAS DE ABONO ---
st.subheader("📋 CARTERA Y DÍAS DE ABONOS")
if not st.session_state.data.empty:
    for index, row in st.session_state.data.iloc[::-1].iterrows():
        with st.expander(f"👤 {row['Cliente']} | Saldo: ${row['Saldo_Actual']:,.0f} | Cuota: ${row['Cuota_Valor']} ({row['Frecuencia']})"):
            st.write(f"**Vencimiento estimado:** {row['Vence']}")
            st.write("**Registro de Abonos:**")
            
            # Buscar abonos específicos de este préstamo
            abonos_cli = st.session_state.historial_cuotas[st.session_state.historial_cuotas['ID_Prestamo'] == row['ID']]
            
            if not abonos_cli.empty:
                for _, abono in abonos_cli.iterrows():
                    st.markdown(f"""<div class="info-cuota">📅 {abono['Fecha_Pago']} — Recibido: <b>${abono['Monto_Abonado']:,.0f}</b></div>""", unsafe_allow_html=True)
            else:
                st.write("No hay abonos registrados aún.")
            
            # Barra de progreso
            progreso = 1 - (row['Saldo_Actual'] / row['Saldo_Inicial'])
            st.progress(min(max(progreso, 0.0), 1.0))
            st.caption(f"Progreso de recuperación: {progreso*100:.1f}%")
else:
    st.info("No hay préstamos activos.")
