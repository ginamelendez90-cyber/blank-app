import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import date

st.set_page_config(page_title="Control de Cobranza", layout="wide")
st.title("💸 Control Diario de Ruta")

# --- CONEXIÓN Y AUTO-CONFIGURACIÓN DE GOOGLE SHEETS ---
@st.cache_resource
def init_connection():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds_dict = st.secrets["gcp_service_account"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    sh = client.open_by_key(st.secrets["spreadsheet_id"])
    
    try:
        ws_movimientos = sh.worksheet("Movimientos")
    except gspread.exceptions.WorksheetNotFound:
        ws_movimientos = sh.add_worksheet(title="Movimientos", rows=1000, cols=5)
        ws_movimientos.append_row(["Fecha", "Tipo", "Cliente_Concepto", "Monto", "Metodo"])

    try:
        ws_clientes = sh.worksheet("Clientes")
    except gspread.exceptions.WorksheetNotFound:
        ws_clientes = sh.add_worksheet(title="Clientes", rows=1000, cols=1)
        ws_clientes.append_row(["Nombre"])

    return sh, ws_movimientos, ws_clientes

sh, ws_movimientos, ws_clientes = init_connection()

# --- CARGAR DATOS DESDE SHEETS ---
def load_clientes():
    records = ws_clientes.col_values(1)[1:]
    return records

def load_movimientos_hoy():
    records = ws_movimientos.get_all_records()
    df = pd.DataFrame(records)
    hoy = date.today().strftime("%Y-%m-%d")
    if not df.empty and 'Fecha' in df.columns:
        df = df[df['Fecha'] == hoy]
    else:
        df = pd.DataFrame(columns=['Fecha', 'Tipo', 'Cliente_Concepto', 'Monto', 'Metodo'])
    return df

lista_clientes = load_clientes()
df_hoy = load_movimientos_hoy()

# --- MENÚ LATERAL: DIRECTORIO DE CLIENTES ---
with st.sidebar:
    st.header("👥 Nuevo Cliente")
    nuevo_cliente = st.text_input("Nombre completo")
    if st.button("Guardar Cliente"):
        if nuevo_cliente and nuevo_cliente not in lista_clientes:
            ws_clientes.append_row([nuevo_cliente])
            st.success(f"{nuevo_cliente} guardado en la nube.")
            st.rerun()
        elif nuevo_cliente in lista_clientes:
            st.warning("El cliente ya existe.")
            
    st.divider()
    st.subheader("Clientes Registrados")
    if len(lista_clientes) > 0:
        st.dataframe(pd.DataFrame(lista_clientes, columns=["Nombre"]), hide_index=True)

# --- 1. FORMULARIO DE INGRESO ---
st.header("1. Registrar Movimiento")
col1, col2, col3, col4 = st.columns(4)

with col1:
    tipo = st.selectbox("Tipo", ["Cobro", "Préstamo", "Gasto"])

with col2:
    if tipo in ["Cobro", "Préstamo"]:
        if len(lista_clientes) == 0:
            st.warning("Agrega clientes primero 👈")
            cliente_concepto = None
        else:
            cliente_concepto = st.selectbox("Seleccionar Cliente", lista_clientes)
    else:
        cliente_concepto = st.text_input("Concepto del Gasto")

with col3:
    monto = st.number_input("Monto ($)", min_value=0.0, step=1.0)
    
with col4:
    metodo = st.selectbox("Método de Pago", ["Efectivo", "Transferencia", "Pago Móvil"])

# Cálculo previo en memoria para validación de efectivo antes de registrar
base_inicial_temp = st.session_state.get('base_input', 0.0)
total_cobrado_temp = 0.0
total_salidas_temp = 0.0

if not df_hoy.empty and 'Metodo' in df_hoy.columns:
    df_efec_temp = df_hoy[df_hoy['Metodo'] == 'Efectivo']
    total_cobrado_temp = float(df_efec_temp[df_efec_temp['Tipo'] == 'Cobro']['Monto'].sum()) if not df_efec_temp.empty else 0.0
    total_salidas_temp = float(df_efec_temp[df_efec_temp['Tipo'].isin(['Préstamo', 'Gasto'])]['Monto'].sum()) if not df_efec_temp.empty else 0.0

efectivo_disponible_actual = base_inicial_temp + total_cobrado_temp - total_salidas_temp

if st.button("Registrar Operación", type="primary"):
    if cliente_concepto and monto > 0:
        # Validación de seguridad: No puedes prestar/gastar más de lo que tienes en efectivo físico (si es en efectivo)
        if metodo == 'Efectivo' and tipo in ['Préstamo', 'Gasto'] and monto > efectivo_disponible_actual:
            st.error(f"❌ Fondos insuficientes en caja. Intentas registrar {tipo.lower()} por ${monto:.2f}, pero tu efectivo disponible en caja es ${efectivo_disponible_actual:.2f}.")
        else:
            fecha_hoy = date.today().strftime("%Y-%m-%d")
            ws_movimientos.append_row([fecha_hoy, tipo, cliente_concepto, monto, metodo])
            st.success("✅ Operación sincronizada con Google Sheets.")
            st.rerun()
    else:
        st.error("Completa todos los campos correctamente.")

# --- 2. DETALLE DE MOVIMIENTOS ---
st.header("2. Movimientos del Día")
st.dataframe(df_hoy, use_container_width=True)

# --- 3. CUADRE DE CAJA ---
st.header("3. Cuadre de Caja Físico")
base_inicial = st.number_input("Efectivo de Salida (Base Inicial):", min_value=0.0, step=1.0, key='base_input')

if not df_hoy.empty and 'Metodo' in df_hoy.columns:
    df_efectivo = df_hoy[df_hoy['Metodo'] == 'Efectivo']
    
    try:
        total_cobrado = float(df_efectivo[df_efectivo['Tipo'] == 'Cobro']['Monto'].sum()) if not df_efectivo.empty else 0.0
        total_prestamos = float(df_efectivo[df_efectivo['Tipo'] == 'Préstamo']['Monto'].sum()) if not df_efectivo.empty else 0.0
        total_gastos = float(df_efectivo[df_efectivo['Tipo'] == 'Gasto']['Monto'].sum()) if not df_efectivo.empty else 0.0
    except KeyError:
        total_cobrado = total_prestamos = total_gastos = 0.0

    # Cálculo real protegido contra negativos
    efectivo_calculado = base_inicial + total_cobrado - total_prestamos - total_gastos
    efectivo_esperado = max(0.0, efectivo_calculado) # Nunca baja de 0

    colA, colB, colC, colD, colE = st.columns(5)
    colA.metric("Base", f"${base_inicial:.2f}")
    colB.metric("Cobros (+)", f"${total_cobrado:.2f}")
    colC.metric("Préstamos (-)", f"${total_prestamos:.2f}")
    colD.metric("Gastos (-)", f"${total_gastos:.2f}")
    colE.metric("EFECTIVO ESPERADO", f"${efectivo_esperado:.2f}")

    if efectivo_calculado < 0:
        st.warning("⚠️ **Alerta de Caja:** Los préstamos y gastos en efectivo superan la base y los cobros acumulados. Revisa los montos registrados porque físicamente no puedes entregar más de lo que tienes.")
else:
    efectivo_esperado = base_inicial
    colA, colB, colC, colD, colE = st.columns(5)
    colA.metric("Base", f"${base_inicial:.2f}")
    colB.metric("Cobros (+)", "$0.00")
    colC.metric("Préstamos (-)", "$0.00")
    colD.metric("Gastos (-)", "$0.00")
    colE.metric("EFECTIVO ESPERADO", f"${base_inicial:.2f}")
    st.info("Aún no hay movimientos registrados hoy.")
