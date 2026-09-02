import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import date

st.set_page_config(page_title="Control de Cobranza y Créditos", layout="wide")
st.title("💸 Control Diario de Ruta y Saldos")

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
        ws_movimientos = sh.add_worksheet(title="Movimientos", rows=1000, cols=7)
        ws_movimientos.append_row(["Fecha", "Tipo", "Cliente_Concepto", "Monto", "Metodo", "Interes_Pct", "Total_Deuda"])

    try:
        ws_clientes = sh.worksheet("Clientes")
    except gspread.exceptions.WorksheetNotFound:
        ws_clientes = sh.add_worksheet(title="Clientes", rows=1000, cols=1)
        ws_clientes.append_row(["Nombre"])

    return sh, ws_movimientos, ws_clientes

sh, ws_movimientos, ws_clientes = init_connection()

# --- CARGAR DATOS DESDE SHEETS ---
def load_clientes():
    return ws_clientes.col_values(1)[1:]

def load_movimientos():
    records = ws_movimientos.get_all_records()
    df = pd.DataFrame(records)
    if df.empty:
        df = pd.DataFrame(columns=['Fecha', 'Tipo', 'Cliente_Concepto', 'Monto', 'Metodo', 'Interes_Pct', 'Total_Deuda'])
    else:
        # Asegurar columnas por compatibilidad
        for col in ['Interes_Pct', 'Total_Deuda']:
            if col not in df.columns:
                df[col] = 0.0
    return df

lista_clientes = load_clientes()
df_movimientos_total = load_movimientos()

# Filtrar movimientos de HOY para el cuadre diario
hoy = date.today().strftime("%Y-%m-%d")
df_hoy = df_movimientos_total[df_movimientos_total['Fecha'] == hoy] if not df_movimientos_total.empty else pd.DataFrame(columns=df_movimientos_total.columns)

# --- NAVEGACIÓN POR PESTAÑAS ---
tab_operaciones, tab_saldos = st.tabs(["📝 Operaciones del Día", "📊 Estado de Cuenta (Saldos que Deben)"])

with tab_operaciones:
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
        monto = st.number_input("Monto / Capital ($)", min_value=0.0, step=1.0)
        
    with col4:
        metodo = st.selectbox("Método de Pago", ["Efectivo", "Transferencia", "Pago Móvil"])

    # Campos adicionales si es un Préstamo (Interés)
    interes_pct = 0.0
    total_deuda_generada = 0.0

    if tipo == "Préstamo":
        st.info("💡 Configuración del Crédito con Interés")
        interes_pct = st.number_input("Porcentaje de Interés (%)", min_value=0.0, value=10.0, step=1.0)
        total_deuda_generada = monto + (monto * (interes_pct / 100.0))
        st.write(f"➡️ **Total que el cliente pagará (Capital + {interes_pct}%):** ${total_deuda_generada:.2f}")

    # Cálculo previo para validar efectivo en caja
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
            if metodo == 'Efectivo' and tipo in ['Préstamo', 'Gasto'] and monto > efectivo_disponible_actual:
                st.error(f"❌ Fondos insuficientes en caja. Intentas registrar {tipo.lower()} por ${monto:.2f}, pero tu efectivo disponible es ${efectivo_disponible_actual:.2f}.")
            else:
                fecha_hoy = date.today().strftime("%Y-%m-%d")
                # Estructura: Fecha, Tipo, Cliente_Concepto, Monto, Metodo, Interes_Pct, Total_Deuda
                ws_movimientos.append_row([
                    fecha_hoy, 
                    tipo, 
                    cliente_concepto, 
                    monto, 
                    metodo, 
                    interes_pct if tipo == "Préstamo" else 0.0, 
                    total_deuda_generada if tipo == "Préstamo" else 0.0
                ])
                st.success("✅ Operación sincronizada con Google Sheets.")
                st.rerun()
        else:
            st.error("Completa todos los campos correctamente.")

    # --- 2. DETALLE DE MOVIMIENTOS DE HOY ---
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

        efectivo_calculado = base_inicial + total_cobrado - total_prestamos - total_gastos
        efectivo_esperado = max(0.0, efectivo_calculado)

        colA, colB, colC, colD, colE = st.columns(5)
        colA.metric("Base", f"${base_inicial:.2f}")
        colB.metric("Cobros (+)", f"${total_cobrado:.2f}")
        colC.metric("Préstamos (-)", f"${total_prestamos:.2f}")
        colD.metric("Gastos (-)", f"${total_gastos:.2f}")
        colE.metric("EFECTIVO ESPERADO", f"${efectivo_esperado:.2f}")

        if efectivo_calculado < 0:
            st.warning("⚠️ **Alerta de Caja:** Los préstamos y gastos superan la base y los cobros.")
    else:
        colA, colB, colC, colD, colE = st.columns(5)
        colA.metric("Base", f"${base_inicial:.2f}")
        colB.metric("Cobros (+)", "$0.00")
        colC.metric("Préstamos (-)", "$0.00")
        colD.metric("Gastos (-)", "$0.00")
        colE.metric("EFECTIVO ESPERADO", f"${base_inicial:.2f}")
        st.info("Aún no hay movimientos registrados hoy.")

with tab_saldos:
    st.header("📊 Estado de Cuenta Actualizado por Cliente")
    st.write("Aquí puedes ver exactamente cuánto debe cada cliente en total. El saldo se incrementa cuando se le presta (con su respectivo interés) y disminuye automáticamente cada vez que abona.")

    if not df_movimientos_total.empty and len(lista_clientes) > 0:
        resumen_clientes = []
        
        for cliente in lista_clientes:
            # Filtrar movimientos de este cliente específico
            df_cli = df_movimientos_total[df_movimientos_total['Cliente_Concepto'] == cliente]
            
            if not df_cli.empty:
                # Sumar toda la deuda generada por préstamos con interés
                total_deuda = float(df_cli[df_cli['Tipo'] == 'Préstamo']['Total_Deuda'].sum())
                # Si algún préstamo antiguo no tiene Total_Deuda registrado, usar el monto base
                prestamos_sin_columna = df_cli[(df_cli['Tipo'] == 'Préstamo') & (df_cli['Total_Deuda'] == 0.0)]['Monto'].sum()
                total_deuda += prestamos_sin_columna
                
                # Sumar todos los abonos/cobros realizados por el cliente
                total_abonado = float(df_cli[df_cli['Tipo'] == 'Cobro']['Monto'].sum())
                
                # Saldo pendiente
                saldo_pendiente = total_deuda - total_abonado
            else:
                total_deuda = 0.0
                total_abonado = 0.0
                saldo_pendiente = 0.0
                
            resumen_clientes.append({
                "Cliente": cliente,
                "Total Prestado (Con Interés)": round(total_deuda, 2),
                "Total Abonado": round(total_abonado, 2),
                "Saldo Pendiente": round(max(0.0, saldo_pendiente), 2)
            })
            
        df_resumen = pd.DataFrame(resumen_clientes)
        st.dataframe(df_resumen, use_container_width=True, hide_index=True)
        
        # Métrica global
        deuda_total_calle = df_resumen["Saldo Pendiente"].sum()
        st.metric("💰 Dinero Total Pendiente en la Calle (Saldos)", f"${deuda_total_calle:.2f}")
    else:
        st.info("No hay suficientes datos o clientes registrados para generar el estado de cuenta.")
