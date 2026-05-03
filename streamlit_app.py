import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import urllib.parse

# --- 1. CONFIGURACIÓN PROFESIONAL ---
st.set_page_config(page_title="PrestApp Pro Elite", page_icon="🏦", layout="centered")

# --- 2. DISEÑO Y COLORES DE ESTADO ---
st.markdown("""
    <style>
    .stApp { background-color: #F2F2F7; }
    /* Tarjetas de Resumen */
    .card-caja { background-color: #1c1c1e; padding: 20px; border-radius: 20px; color: #32D74B; text-align: center; border: 2px solid #32D74B; }
    .card-calle { background-color: white; padding: 20px; border-radius: 20px; color: #FF453A; text-align: center; border: 1px solid #E5E5EA; }
    /* Estilos de cuotas y alertas */
    .info-cuota { padding: 10px; border-radius: 10px; margin-bottom: 5px; font-size: 14px; border-left: 5px solid #007AFF; }
    .al-dia { background-color: #eaffea; border-left: 5px solid #32D74B; color: #1b5e20; }
    .pendiente { background-color: #fff9e6; border-left: 5px solid #FFD60A; color: #856404; }
    .en-mora { background-color: #ffe5e5; border-left: 5px solid #FF453A; color: #b71c1c; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. BASE DE DATOS INTEGRADA ---
if 'data' not in st.session_state:
    st.session_state.data = pd.DataFrame(columns=['ID', 'Cliente', 'WhatsApp', 'Saldo_Inicial', 'Saldo_Actual', 'Cuota_Valor', 'Frecuencia', 'Vence', 'Estado', 'Ultimo_Abono'])
if 'historial_cuotas' not in st.session_state:
    st.session_state.historial_cuotas = pd.DataFrame(columns=['ID_Prestamo', 'Fecha_Pago', 'Monto_Abonado'])
if 'gastos_df' not in st.session_state:
    st.session_state.gastos_df = pd.DataFrame(columns=['Fecha', 'Concepto', 'Monto', 'Mes_Año'])
if 'capital' not in st.session_state: st.session_state.capital = 0.0
if 'recuperado' not in st.session_state: st.session_state.recuperado = 0.0
if 'prestado' not in st.session_state: st.session_state.prestado = 0.0

# --- 4. CÁLCULOS DE CAJA ---
total_gastos = st.session_state.gastos_df['Monto'].sum()
caja_real = st.session_state.capital + st.session_state.recuperado - st.session_state.prestado - total_gastos
en_la_calle = st.session_state.data[st.session_state.data['Estado'] == 'Activo']['Saldo_Actual'].sum()

# --- 5. FUNCIONES PROFESIONALES (WHATSAPP) ---
def link_comprobante_wa(nombre, cel, monto, saldo):
    texto = f"✅ *RECIBO DE PAGO*\n\nHola *{nombre}*,\nRecibimos tu abono de: *${monto:,.0f}*\nTu saldo actual es: *${saldo:,.0f}*\n\n¡Gracias por tu puntualidad! 🙏"
    pago_url = urllib.parse.quote(texto)
    return f"https://wa.me/{cel}?text={pago_url}"

# --- 6. MODALES DE OPERACIÓN ---
@st.dialog("➕ REGISTRAR CRÉDITO")
def modal_prestamo():
    registrados = sorted(st.session_state.data['Cliente'].unique().tolist())
    tipo = st.radio("Cliente:", ["Nuevo", "Renovación"], horizontal=True)
    nombre = st.text_input("NOMBRE").upper() if tipo == "Nuevo" else st.selectbox("CLIENTE", registrados)
    wa = st.text_input("WHATSAPP (Ej: 573001234567)")
    
    col1, col2 = st.columns(2)
    with col1: monto = st.number_input("ENTREGAR $", min_value=0.0, step=1000.0)
    with col2: tasa = st.number_input("INTERÉS %", value=20)
    
    f1, f2 = st.columns(2)
    with f1: frec = st.selectbox("PAGOS", ["Diario", "Semanal"])
    with f2: cuotas = st.number_input("CUOTAS", min_value=1, value=20)
    
    if st.button("CREAR PRÉSTAMO"):
        if monto > caja_real: st.error("Sin fondos suficientes")
        elif nombre and wa:
            total = monto * (1 + (tasa/100))
            id_p = datetime.now().strftime("%Y%m%d%H%M%S")
            venc = (datetime.now() + timedelta(days=cuotas if frec=="Diario" else cuotas*7)).strftime('%d/%m/%y')
            nuevo = pd.DataFrame([{'ID': id_p, 'Cliente': nombre, 'WhatsApp': wa, 'Saldo_Inicial': total, 'Saldo_Actual': total, 'Cuota_Valor': round(total/cuotas, 2), 'Frecuencia': frec, 'Vence': venc, 'Estado': 'Activo', 'Ultimo_Abono': None}])
            st.session_state.data = pd.concat([st.session_state.data, nuevo], ignore_index=True)
            st.session_state.prestado += monto
            st.rerun()

@st.dialog("💰 COBRAR CUOTA")
def modal_cobro():
    activos = st.session_state.data[st.session_state.data['Estado'] == 'Activo']
    if activos.empty: return
    cli = st.selectbox("CLIENTE", activos['Cliente'].unique())
    idx = activos[activos['Cliente'] == cli].index[-1]
    monto = st.number_input("ABONO $", value=float(activos.at[idx, 'Cuota_Valor']))
    
    if st.button("CONFIRMAR ABONO"):
        st.session_state.data.at[idx, 'Saldo_Actual'] -= monto
        st.session_state.recuperado += monto
        st.session_state.data.at[idx, 'Ultimo_Abono'] = datetime.now().strftime("%d/%m/%Y")
        
        # Guardar en historial detallado
        nuevo_h = pd.DataFrame([{'ID_Prestamo': activos.at[idx, 'ID'], 'Fecha_Pago': datetime.now().strftime("%d/%m/%Y"), 'Monto_Abonado': monto}])
        st.session_state.historial_cuotas = pd.concat([st.session_state.historial_cuotas, nuevo_h], ignore_index=True)
        
        if st.session_state.data.at[idx, 'Saldo_Actual'] <= 0:
            st.session_state.data.at[idx, 'Estado'] = 'Finalizado'
            st.balloons()
        
        # Mostrar link de WhatsApp
        link = link_comprobante_wa(cli, activos.at[idx, 'WhatsApp'], monto, st.session_state.data.at[idx, 'Saldo_Actual'])
        st.success("¡Cobro registrado!")
        st.markdown(f'[📲 ENVIAR COMPROBANTE WHATSAPP]({link})')
        if st.button("TERMINAR"): st.rerun()

# --- 7. INTERFAZ PRINCIPAL ---
st.title("PrestApp Pro Elite 🏦")

c1, c2 = st.columns(2)
with c1: st.markdown(f'<div class="card-caja"><small>EN CAJA</small><h2>${caja_real:,.0f}</h2></div>', unsafe_allow_html=True)
with c2: st.markdown(f'<div class="card-calle"><small>EN CALLE</small><h2>${en_la_calle:,.0f}</h2></div>', unsafe_allow_html=True)

st.write("")
b1, b2 = st.columns(2)
with b1: 
    if st.button("➕ PRESTAR"): modal_prestamo()
with b2: 
    if st.button("💰 COBRAR"): modal_cobro()

st.divider()

# --- 8. CARTERA CON SEMÁFORO DE ESTADO ---
st.subheader("📋 CARTERA Y DÍAS DE ABONOS")
hoy = datetime.now().strftime("%d/%m/%Y")
activos_df = st.session_state.data[st.session_state.data['Estado'] == 'Activo']

if activos_df.empty:
    st.info("No tienes deudas pendientes por cobrar.")
else:
    for i, row in activos_df.iloc[::-1].iterrows():
        # Lógica de colores (Semáforo)
        if row['Ultimo_Abono'] == hoy:
            clase = "al-dia"
            msg = "✅ PAGÓ HOY"
        else:
            clase = "en-mora"
            msg = "⚠️ PENDIENTE"

        with st.expander(f"{msg} | {row['Cliente']} | Debe: ${row['Saldo_Actual']:,.0f}"):
            st.write(f"**WhatsApp:** {row['WhatsApp']} | **Cuota:** ${row['Cuota_Valor']}")
            st.write(f"**Vencimiento:** {row['Vence']}")
            
            # Ver días de abonos específicos
            dias = st.session_state.historial_cuotas[st.session_state.historial_cuotas['ID_Prestamo'] == row['ID']]
            if not dias.empty:
                st.write("**Registro de Pagos:**")
                for _, d in dias.iterrows():
                    st.markdown(f'<div class="info-cuota {clase}">📅 {d["Fecha_Pago"]} — ${d["Monto_Abonado"]:,.0f}</div>', unsafe_allow_html=True)
            else:
                st.caption("Aún no ha pagado su primera cuota.")

# --- 9. MENÚ LATERAL (GASTOS, CAPITAL Y FINALIZADOS) ---
with st.sidebar:
    st.header("Configuración")
    if st.button("🏦 Inyectar Capital"):
        @st.dialog("Cargar")
        def cap():
            m = st.number_input("Monto", 0.0)
            if st.button("OK"):
                st.session_state.capital += m
                st.rerun()
        cap()
        
    if st.button("📉 Registrar Gasto"):
        @st.dialog("Nuevo Gasto")
        def gas():
            c = st.text_input("Concepto")
            v = st.number_input("Valor", 0.0)
            f = st.date_input("Fecha")
            if st.button("Guardar"):
                nuevo_g = pd.DataFrame([{'Fecha': f.strftime("%d/%m/%Y"), 'Concepto': c, 'Monto': v, 'Mes_Año': f.strftime("%m/%Y")}])
                st.session_state.gastos_df = pd.concat([st.session_state.gastos_df, nuevo_g], ignore_index=True)
                st.rerun()
        gas()

    st.divider()
    st.subheader("📊 Gastos por Mes")
    if not st.session_state.gastos_df.empty:
        sel_mes = st.selectbox("Filtrar Mes", st.session_state.gastos_df['Mes_Año'].unique())
        total_m = st.session_state.gastos_df[st.session_state.gastos_df['Mes_Año'] == sel_mes]['Monto'].sum()
        st.write(f"Total: **${total_m:,.0f}**")
        
    st.divider()
    st.subheader("🤝 Clientes que ya Pagaron")
    fin = st.session_state.data[st.session_state.data['Estado'] == 'Finalizado']
    for p in fin['Cliente'].unique():
        st.caption(f"✅ {p}")
