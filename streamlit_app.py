import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

st.set_page_config(page_title="PrestApp Elite", page_icon="💰", layout="centered")

# --- DISEÑO Y ESTILO ---
st.markdown("""
    <style>
    .stApp { background-color: #F2F2F7; }
    .card-caja { background-color: #1c1c1e; padding: 25px; border-radius: 20px; color: #32D74B; text-align: center; border: 2px solid #32D74B; }
    .card-calle { background-color: white; padding: 25px; border-radius: 20px; color: #FF453A; text-align: center; border: 2px solid #FF453A; }
    .main-btn div.stButton > button { background-color: #007AFF; color: white; border-radius: 12px; height: 4rem; font-weight: 700; font-size: 18px; }
    .stTabs [data-baseweb="tab-list"] { gap: 20px; }
    .stTabs [data-baseweb="tab"] { background-color: white; border-radius: 10px; padding: 10px 20px; }
    </style>
    """, unsafe_allow_html=True)

# --- INICIALIZACIÓN DE DATOS ---
if 'data' not in st.session_state:
    st.session_state.data = pd.DataFrame(columns=['Cliente', 'Saldo', 'Cuota', 'Frecuencia', 'Vence'])
if 'capital' not in st.session_state: st.session_state.capital = 0.0
if 'gastos_acum' not in st.session_state: st.session_state.gastos_acum = 0.0
if 'recuperado' not in st.session_state: st.session_state.recuperado = 0.0
if 'prestado' not in st.session_state: st.session_state.prestado = 0.0
if 'movimientos' not in st.session_state:
    st.session_state.movimientos = pd.DataFrame(columns=['Fecha', 'Tipo', 'Detalle', 'Monto'])

# --- CÁLCULOS ---
caja_real = st.session_state.capital + st.session_state.recuperado - st.session_state.prestado - st.session_state.gastos_acum
en_la_calle = st.session_state.data['Saldo'].sum()

# --- MODALES (VENTANAS FLOTANTES) ---

@st.dialog("➕ Nuevo Préstamo / Renovación")
def modal_prestamo():
    # Opción de Renovación: Lista de clientes que ya existen en el sistema
    lista_clientes = sorted(st.session_state.data['Cliente'].unique().tolist())
    
    tipo_registro = st.radio("Tipo de registro:", ["Nuevo Cliente", "Renovación (Cliente Existente)"], horizontal=True)
    
    if tipo_registro == "Nuevo Cliente":
        nombre = st.text_input("Nombre del Cliente").upper()
    else:
        if not lista_clientes:
            st.warning("No hay clientes registrados para renovar.")
            nombre = st.text_input("Nombre del Cliente (Manual)").upper()
        else:
            nombre = st.selectbox("Seleccione Cliente a Renovar", lista_clientes)

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
            
            # Si es renovación y ya existe, podemos optar por sumar al saldo o crear entrada nueva
            # Aquí creamos una entrada nueva o actualizamos la existente
            n = pd.DataFrame([{'Cliente': nombre, 'Saldo': total, 'Cuota': round(total/cuotas, 2), 'Frecuencia': frec, 'Vence': venc}])
            st.session_state.data = pd.concat([st.session_state.data, n], ignore_index=True)
            
            st.session_state.prestado += monto
            m = pd.DataFrame([{'Fecha': datetime.now().strftime("%H:%M"), 'Tipo': '🔴 PRÉSTAMO', 'Detalle': f"Renov: {nombre}" if tipo_registro == "Renovación" else nombre, 'Monto': -monto}])
            st.session_state.movimientos = pd.concat([st.session_state.movimientos, m], ignore_index=True)
            st.success(f"Préstamo para {nombre} registrado con éxito.")
            st.rerun()

@st.dialog("💰 Cobrar Cuota")
def modal_cobro():
    # Filtrar solo clientes con saldo > 0
    clientes_con_deuda = st.session_state.data[st.session_state.data['Saldo'] > 0]
    if clientes_con_deuda.empty:
        st.info("No hay saldos pendientes por cobrar.")
        return
    
    cli = st.selectbox("Cliente que realiza abono", clientes_con_deuda['Cliente'].unique())
    idx = st.session_state.data[st.session_state.data['Cliente'] == cli].index[0]
    
    saldo_actual = st.session_state.data.at[idx, 'Saldo']
    cuota_sug = st.session_state.data.at[idx, 'Cuota']
    
    st.write(f"Saldo pendiente: **${saldo_actual:,.2f}**")
    monto_pago = st.number_input("Monto Recibido ($)", value=float(min(cuota_sug, saldo_actual)))
    
    if st.button("REGISTRAR PAGO"):
        st.session_state.data.at[idx, 'Saldo'] -= monto_pago
        st.session_state.recuperado += monto_pago
        m = pd.DataFrame([{'Fecha': datetime.now().strftime("%H:%M"), 'Tipo': '🟢 COBRO', 'Detalle': cli, 'Monto': monto_pago}])
        st.session_state.movimientos = pd.concat([st.session_state.movimientos, m], ignore_index=True)
        st.rerun()

@st.dialog("📉 Gasto Administrativo")
def modal_gasto():
    det = st.text_input("Concepto del Gasto")
    val = st.number_input("Valor ($)", min_value=0.0)
    if st.button("GUARDAR GASTO"):
        st.session_state.gastos_acum += val
        m = pd.DataFrame([{'Fecha': datetime.now().strftime("%H:%M"), 'Tipo': '🔴 GASTO', 'Detalle': det, 'Monto': -val}])
        st.session_state.movimientos = pd.concat([st.session_state.movimientos, m], ignore_index=True)
        st.rerun()

@st.dialog("🏦 Inyectar Capital")
def modal_cap():
    m = st.number_input("Monto a Inyectar ($)", min_value=0.0)
    if st.button("CONFIRMAR INYECCIÓN"):
        st.session_state.capital += m
        m = pd.DataFrame([{'Fecha': datetime.now().strftime("%H:%M"), 'Tipo': '🟢 CAPITAL', 'Detalle': 'Inyección', 'Monto': m}])
        st.session_state.movimientos = pd.concat([st.session_state.movimientos, m], ignore_index=True)
        st.rerun()

# --- MENÚ LATERAL ---
with st.sidebar:
    st.title("Administración")
    if st.button("🏦 Inyectar Capital"): modal_cap()
    if st.button("📉 Registrar Gasto"): modal_gasto()
    st.divider()
    st.write("Resumen General")
    st.write(f"Capital Inyectado: ${st.session_state.capital:,.0f}")
    st.write(f"Gastos Totales: ${st.session_state.gastos_acum:,.0f}")

# --- INTERFAZ PRINCIPAL ---
st.title("PrestApp Elite 🏦")

col_a, col_b = st.columns(2)
with col_a: st.markdown(f'<div class="card-caja"><small>DISPONIBLE</small><br><h2>${caja_real:,.0f}</h2></div>', unsafe_allow_html=True)
with col_b: st.markdown(f'<div class="card-calle"><small>EN LA CALLE</small><br><h2>${en_la_calle:,.0f}</h2></div>', unsafe_allow_html=True)

st.write("")
st.markdown('<div class="main-btn">', unsafe_allow_html=True)
c1, c2 = st.columns(2)
with c1: 
    if st.button("➕ PRESTAR"): modal_prestamo()
with c2: 
    if st.button("💰 COBRAR"): modal_cobro()
st.markdown('</div>', unsafe_allow_html=True)

st.divider()

# --- SECCIONES INFERIORES ---
tab_cartera, tab_mov = st.tabs(["📋 Cartera Activa", "🕒 Movimientos"])

with tab_cartera:
    if not st.session_state.data.empty:
        # Buscador de cliente
        search = st.text_input("🔍 Buscar cliente...")
        df_display = st.session_state.data
        if search:
            df_display = df_display[df_display['Cliente'].str.contains(search.upper())]
        
        st.dataframe(df_display, use_container_width=True, hide_index=True)
    else:
        st.info("No hay préstamos registrados.")

with tab_mov:
    if not st.session_state.movimientos.empty:
        for _, row in st.session_state.movimientos.iloc[::-1].head(10).iterrows():
            color = "#32D74B" if row['Monto'] > 0 else "#FF453A"
            st.markdown(f"""
            <div style="background-color: white; padding: 12px; border-radius: 15px; margin-bottom: 8px; border-left: 6px solid {color};">
                <small style="color: gray;">{row['Fecha']}</small> | <strong>{row['Tipo']}</strong><br>
                {row['Detalle']} <span style="float: right; color:{color}; font-weight:bold;">${abs(row['Monto']):,.0f}</span>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.write("No hay movimientos hoy.")
