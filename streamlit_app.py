import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

# Configuración para que se vea como App nativa
st.set_page_config(page_title="PrestApp", page_icon="📲", layout="centered")

# --- DISEÑO DE INTERFAZ (CSS) ---
st.markdown("""
    <style>
    /* Fondo y tipografía */
    .stApp { background-color: #F2F2F7; }
    h1 { color: #1C1C1E; font-family: -apple-system, BlinkMacSystemFont, sans-serif; font-weight: 700; }
    
    /* Botones principales estilo iOS */
    div.stButton > button {
        background-color: #007AFF;
        color: white;
        border-radius: 12px;
        border: none;
        height: 3.5rem;
        font-size: 16px;
        font-weight: 600;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        transition: all 0.2s ease;
    }
    div.stButton > button:active { transform: scale(0.98); }

    /* Tarjetas de Métricas */
    [data-testid="stMetric"] {
        background-color: white;
        border-radius: 16px;
        padding: 15px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.05);
        border: 1px solid #E5E5EA;
    }
    </style>
    """, unsafe_allow_html=True)

# Inicializar sesión
if 'data' not in st.session_state:
    st.session_state.data = pd.DataFrame(columns=[
        'Cliente', 'Monto Inicial', 'Total', 'Cuota', 'Frecuencia', 'Pagado', 'Saldo', 'Vence'
    ])

# --- VENTANA FLOTANTE: NUEVO CLIENTE ---
@st.dialog("📝 Nuevo Préstamo")
def modal_nuevo_cliente():
    st.write("Complete los datos del crédito")
    with st.form("registro_form", clear_on_submit=True):
        nombre = st.text_input("Nombre del Cliente").upper()
        monto = st.number_input("Cantidad prestada ($)", min_value=0, step=100)
        tasa = st.slider("Interés (%)", 0, 100, 20)
        
        c1, c2 = st.columns(2)
        with c1:
            metodo = st.selectbox("Frecuencia", ["Diario", "Semanal"])
        with c2:
            cuotas = st.number_input("N° Cuotas", min_value=1, value=20)
            
        if st.form_submit_button("CREAR PRÉSTAMO"):
            total = monto * (1 + (tasa/100))
            valor_cuota = total / cuotas
            dias = cuotas if metodo == "Diario" else cuotas * 7
            vencimiento = (datetime.now() + timedelta(days=dias)).strftime('%d/%m/%Y')
            
            nuevo_p = pd.DataFrame([{
                'Cliente': nombre, 'Monto Inicial': monto, 'Total': total,
                'Cuota': round(valor_cuota, 2), 'Frecuencia': metodo,
                'Pagado': 0.0, 'Saldo': total, 'Vence': vencimiento
            }])
            st.session_state.data = pd.concat([st.session_state.data, nuevo_p], ignore_index=True)
            st.success("✅ Registro exitoso")
            st.rerun()

# --- VENTANA FLOTANTE: COBRAR ---
@st.dialog("💰 Registrar Cobro")
def modal_cobrar():
    if st.session_state.data.empty:
        st.error("No hay clientes activos.")
        return
    
    cliente_sel = st.selectbox("¿Quién paga?", st.session_state.data['Cliente'].unique())
    idx = st.session_state.data[st.session_state.data['Cliente'] == cliente_sel].index[0]
    sugerido = st.session_state.data.at[idx, 'Cuota']
    
    monto_abono = st.number_input("Monto del abono ($)", value=float(sugerido))
    
    if st.button("PROCESAR PAGO"):
        st.session_state.data.at[idx, 'Pagado'] += monto_abono
        st.session_state.data.at[idx, 'Saldo'] -= monto_abono
        st.balloons()
        st.success(f"Abono de ${monto_abono} registrado.")
        st.rerun()

# --- INTERFAZ PRINCIPAL ---
st.title("Mi Cartera")
st.caption("Gestión administrativa de préstamos personales")

# Panel de Botones (Acciones Rápidas)
col_btn1, col_btn2 = st.columns(2)
with col_btn1:
    if st.button("➕ Nuevo"):
        modal_nuevo_cliente()
with col_btn2:
    if st.button("💸 Cobrar"):
        modal_cobrar()

st.write("") # Espaciador

# Métricas de la App
m1, m2 = st.columns(2)
total_calle = st.session_state.data['Saldo'].sum()
total_clientes = len(st.session_state.data)

m1.metric("Dinero en Calle", f"${total_calle:,.0f}")
m2.metric("Total Clientes", f"{total_clientes}")

st.divider()

# Listado de Cobranza con buscador
st.subheader("📋 Lista de Cobro")
if not st.session_state.data.empty:
    search = st.text_input("🔍 Buscar por nombre...")
    df_v = st.session_state.data
    if search:
        df_v = df_v[df_v['Cliente'].str.contains(search.upper())]
    
    # Tabla optimizada para lectura rápida
    st.dataframe(
        df_v[['Cliente', 'Cuota', 'Saldo', 'Vence']],
        use_container_width=True,
        hide_index=True
    )
else:
    st.info("No hay préstamos registrados. Empieza tocando el botón 'Nuevo'.")
