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
    .cliente-finalizado { background-color: #e8f5e9; padding: 10px; border-radius: 10px; border-left: 4px solid #2e7d32; margin-bottom: 5px; color: #1b5e20; }
    </style>
    """, unsafe_allow_html=True)

# --- INICIALIZACIÓN DE DATOS ---
if 'data' not in st.session_state:
    st.session_state.data = pd.DataFrame(columns=['ID', 'Cliente', 'Saldo_Inicial', 'Saldo_Actual', 'Cuota_Valor', 'Frecuencia', 'Vence', 'Estado'])
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
# Solo sumamos los saldos de préstamos 'Activos'
en_la_calle = st.session_state.data[st.session_state.data['Estado'] == 'Activo']['Saldo_Actual'].sum()

# --- MODALES ---

@st.dialog("➕ Nuevo Préstamo")
def modal_prestamo():
    clientes_hist = sorted(st.session_state.data['Cliente'].unique().tolist())
    tipo = st.radio("Registro:", ["Nuevo", "Renovación"], horizontal=True)
    nombre = st.text_input("Nombre").upper() if tipo == "Nuevo" else st.selectbox("Seleccione Cliente", clientes_hist)
    monto = st.number_input("Dinero a entregar ($)", min_value=0.0)
    tasa = st.number_input("Interés %", value=20)
    frec = st.selectbox("Frecuencia", ["Diario", "Semanal"])
    cuotas = st.number_input("N° Cuotas", min_value=1, value=20)
    
    if st.button("CREAR CRÉDITO"):
        if monto > caja_real: st.error("Sin fondos en caja.")
        elif nombre:
            total = monto * (1 + (tasa/100))
            id_p = datetime.now().strftime("%Y%m%d%H%M%S")
            venc = (datetime.now() + timedelta(days=cuotas if frec=="Diario" else cuotas*7)).strftime('%d/%m/%y')
            n = pd.DataFrame([{
                'ID': id_p, 'Cliente': nombre, 'Saldo_Inicial': total, 'Saldo_Actual': total, 
                'Cuota_Valor': round(total/cuotas, 2), 'Frecuencia': frec, 'Vence': venc, 'Estado': 'Activo'
            }])
            st.session_state.data = pd.concat([st.session_state.data, n], ignore_index=True)
            st.session_state.prestado += monto
            m = pd.DataFrame([{'Fecha': datetime.now().strftime("%H:%M"), 'Tipo': '🔴 PRÉSTAMO', 'Detalle': nombre, 'Monto': -monto}])
            st.session_state.movimientos = pd.concat([st.session_state.movimientos, m], ignore_index=True)
            st.rerun()

@st.dialog("💰 Cobrar Cuota")
def modal_cobro():
    activos = st.session_state.data[st.session_state.data['Estado'] == 'Activo']
    if activos.empty:
        st.warning("No hay créditos activos.")
        return
    cli = st.selectbox("Cobrar a:", activos['Cliente'].unique())
    p_idx = activos[activos['Cliente'] == cli].index[-1]
    id_p = activos.at[p_idx, 'ID']
    sug = activos.at[p_idx, 'Cuota_Valor']
    monto = st.number_input("Abono ($)", value=float(sug))
    
    if st.button("REGISTRAR PAGO"):
        st.session_state.data.at[p_idx, 'Saldo_Actual'] -= monto
        st.session_state.recuperado += monto
        
        # Lógica de Finalización
        if st.session_state.data.at[p_idx, 'Saldo_Actual'] <= 0:
            st.session_state.data.at[p_idx, 'Saldo_Actual'] = 0
            st.session_state.data.at[p_idx, 'Estado'] = 'Finalizado'
            st.balloons() # Animación de éxito
            
        nuevo_abono = pd.DataFrame([{'ID_Prestamo': id_p, 'Fecha_Pago': datetime.now().strftime("%d/%m/%Y"), 'Monto_Abonado': monto}])
        st.session_state.historial_cuotas = pd.concat([st.session_state.historial_cuotas, nuevo_abono], ignore_index=True)
        m = pd.DataFrame([{'Fecha': datetime.now().strftime("%H:%M"), 'Tipo': '🟢 COBRO', 'Detalle': cli, 'Monto': monto}])
        st.session_state.movimientos = pd.concat([st.session_state.movimientos, m], ignore_index=True)
        st.rerun()

# --- MENÚ LATERAL ---
with st.sidebar:
    st.title("Histórico")
    st.subheader("✅ Créditos Pagados")
    finalizados = st.session_state.data[st.session_state.data['Estado'] == 'Finalizado']
    if not finalizados.empty:
        for _, f_row in finalizados.iterrows():
            st.markdown(f"""<div class="cliente-finalizado">🤝 <b>{f_row['Cliente']}</b><br><small>Finalizado con éxito</small></div>""", unsafe_allow_html=True)
    else:
        st.caption("Aún no hay créditos terminados.")
    
    st.divider()
    if st.button("📉 Ver Gastos por Mes"):
        # Muestra un pequeño resumen de gastos aquí o abre otro modal
        st.write(st.session_state.gastos_df[['Mes_Año', 'Monto']])

# --- PANTALLA PRINCIPAL ---
st.title("PrestApp Elite 🏦")

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

# --- CARTERA ACTIVA ---
st.subheader("📋 CARTERA ACTIVA")
activos_display = st.session_state.data[st.session_state.data['Estado'] == 'Activo']
if not activos_display.empty:
    for index, row in activos_display.iloc[::-1].iterrows():
        with st.expander(f"👤 {row['Cliente']} | Pendiente: ${row['Saldo_Actual']:,.0f}"):
            st.write(f"**Cuota pactada:** ${row['Cuota_Valor']} ({row['Frecuencia']})")
            abonos_cli = st.session_state.historial_cuotas[st.session_state.historial_cuotas['ID_Prestamo'] == row['ID']]
            if not abonos_cli.empty:
                st.write("**Historial de Abonos:**")
                for _, abono in abonos_cli.iterrows():
                    st.markdown(f'<div class="info-cuota">📅 {abono["Fecha_Pago"]} — ${abono["Monto_Abonado"]:,.0f}</div>', unsafe_allow_html=True)
            else:
                st.caption("Esperando primer abono.")
else:
    st.info("No hay créditos pendientes en la calle.")
