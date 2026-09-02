import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import date

st.set_page_config(page_title="Control de Cobranza", layout="wide")
st.title("💸 Control Diario de Ruta")

# --- CONEXIÓN A GOOGLE SHEETS ---
@st.cache_resource
def init_connection():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    # Leer credenciales desde secrets.toml
    creds_dict = st.secrets["gcp_service_account"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    return client.open_by_key(st.secrets["spreadsheet_id"])

sh = init_connection()
ws_movimientos = sh.worksheet("Movimientos")
ws_clientes = sh.worksheet("Clientes")

# --- CARGAR DATOS DESDE SHEETS ---
def load_clientes():
    # Trae la columna 1, omitiendo el encabezado
    records = ws_clientes.col_values(1)[1:]
    return records

def load_movimientos_hoy():
    # Trae todos los registros
    records = ws_movimientos.get_all_records()
    df = pd.DataFrame(records)
    # Filtrar solo los de la fecha actual para el cuadre
    hoy = date.today().strftime("%Y-%m-%d")
    if not df.empty:
        df = df[df['Fecha'] == hoy]
    else:
        df = pd.DataFrame(columns=['Fecha', 'Tipo', 'Cliente_Concepto', 'Monto', 'Metodo'])
    return df

# Cargar a variables locales (simulando estado)
lista_clientes = load_clientes()
df_hoy = load_movimientos_hoy()

# --- MENÚ LATERAL: DIRECTORIO DE CLIENTES ---
with st.sidebar:
    st.header("👥 Nuevo Cliente")
    nuevo_cliente = st.text_input("Nombre completo")
    if st.button("Guardar Cliente"):
        if nuevo_cliente and nuevo_cliente not in lista_clientes:
            # Impactar directamente en Google Sheets
            ws_clientes.append_row([nuevo_cliente])
            st.success(f"{nuevo_cliente} guardado en la nube.")
            st.rerun() # Recarga para actualizar la lista
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

if st.button("Registrar Operación", type="primary"):
    if cliente_concepto and monto > 0:
        fecha_hoy = date.today().strftime("%Y-%m-%d")
        # Escribir directamente en la hoja "Movimientos"
        ws_movimientos.append_row([fecha_hoy, tipo, cliente_concepto, monto, metodo])
        st.success("✅ Operación sincronizada con Google Sheets.")
        st.rerun() # Recarga para que se refleje en la tabla de abajo
    else:
        st.error("Completa todos los campos.")

# --- 2. DETALLE DE MOVIMIENTOS ---
st.header("2. Movimientos del Día")
st.dataframe(df_hoy, use_container_width=True)

# --- 3. CUADRE DE CAJA ---
st.header("3. Cuadre de Caja Físico")
base_inicial = st.number_input("Efectivo de Salida (Base Inicial):", min_value=0.0, step=1.0)

if not df_hoy.empty:
    df_efectivo = df_hoy[df_hoy['Metodo'] == 'Efectivo']
    
    # Manejar posibles errores si no hay registros de un tipo específico
    try:
        total_cobrado = float(df_efectivo[df_efectivo['Tipo'] == 'Cobro']['Monto'].sum())
        total_prestamos = float(df_efectivo[df_efectivo['Tipo'] == 'Préstamo']['Monto'].sum())
        total_gastos = float(df_efectivo[df_efectivo['Tipo'] == 'Gasto']['Monto'].sum())
    except KeyError:
        total_cobrado = total_prestamos = total_gastos = 0.0

    efectivo_esperado = base_inicial + total_cobrado - total_prestamos - total_gastos

    colA, colB, colC, colD, colE = st.columns(5)
    colA.metric("Base", f"${base_inicial:.2f}")
    colB.metric("Cobros (+)", f"${total_cobrado:.2f}")
    colC.metric("Préstamos (-)", f"${total_prestamos:.2f}")
    colD.metric("Gastos (-)", f"${total_gastos:.2f}")
    colE.metric("EFECTIVO ESPERADO", f"${efectivo_esperado:.2f}")
else:
    st.info("Aún no hay movimientos registrados hoy.")
