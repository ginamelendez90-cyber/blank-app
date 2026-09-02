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
    
    headers = ["Fecha", "Tipo", "Cliente_Concepto", "Monto", "Metodo", "Interes_Pct", "Total_Deuda"]
    current_headers = ws_movimientos.row_values(1)
    if not current_headers or current_headers != headers:
        ws_movimientos.update('A1:G1', [headers])

    try:
        ws_clientes = sh.worksheet("Clientes")
    except gspread.exceptions.WorksheetNotFound:
        ws_clientes = sh.add_worksheet(title="Clientes", rows=1000, cols=1)
    
    current_headers_cli = ws_clientes.row_values(1)
    if not current_headers_cli or current_headers_cli != ["Nombre"]:
        ws_clientes.update('A1', [["Nombre"]])

    return sh, ws_movimientos, ws_clientes

sh, ws_movimientos, ws_clientes = init_connection()

# --- CARGAR DATOS DESDE SHEETS ---
def load_clientes():
    try:
        values = ws_clientes.col_values(1)
        if len(values) > 1:
            return values[1:]
    except Exception:
        pass
    return []

def load_movimientos():
    try:
        all_values = ws_movimientos.get_all_values()
        if len(all_values) <= 1:
            return pd.DataFrame(columns=['Fecha', 'Tipo', 'Cliente_Concepto', 'Monto', 'Metodo', 'Interes_Pct', 'Total_Deuda'])
        
        records = ws_movimientos.get_all_records()
        df = pd.DataFrame(records)
        
        if df.empty:
            return pd.DataFrame(columns=['Fecha', 'Tipo', 'Cliente_Concepto', 'Monto', 'Metodo', 'Interes_Pct', 'Total_Deuda'])
            
        for col in ['Interes_Pct', 'Total_Deuda', 'Monto']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0.0)
                
        return df
    except Exception as e:
        st.error(f"Error al leer Google Sheets: {e}")
        return pd.DataFrame(columns=['Fecha', 'Tipo', 'Cliente_Concepto', 'Monto', 'Metodo', 'Interes_Pct', 'Total_Deuda'])

st.cache_data.clear()

lista_clientes = load_clientes()
df_movimientos_total = load_movimientos()

# Asegurar formato de texto para la columna de fecha
if not df_movimientos_total.empty and 'Fecha' in df_movimientos_total.columns:
    df_movimientos_total['Fecha'] = df_movimientos_total['Fecha'].astype(str)

# --- NAVEGACIÓN POR PESTAÑAS ---
tab_operaciones, tab_saldos = st.tabs(["📝 Operaciones y Cuadre Diario", "📊 Estado de Cuenta (Saldos que Deben)"])

with tab_operaciones:
    # Selector de fecha en la barra lateral
    st.sidebar.header("📅 Control de Fecha")
    fecha_seleccionada = st.sidebar.date_input("Selecciona el día a registrar/consultar", date.today())
    fecha_str = fecha_seleccionada.strftime("%Y-%m-%d")
    
    st.info(f"📌 Estás operando en la fecha: **{fecha_str}**")

    # Filtrar movimientos exclusivamente de la fecha seleccionada
    if not df_movimientos_total.empty and 'Fecha' in df_movimientos_total.columns:
        df_fecha = df_movimientos_total[df_movimientos_total['Fecha'] == fecha_str]
    else:
        df_fecha = pd.DataFrame(columns=['Fecha', 'Tipo', 'Cliente_Concepto', 'Monto', 'Metodo', 'Interes_Pct', 'Total_Deuda'])

    # --- MENÚ LATERAL: DIRECTORIO DE CLIENTES ---
    with st.sidebar:
        st.divider()
        st.header("👥 Nuevo Cliente")
        nuevo_cliente = st.text_input("Nombre completo")
        if st.button("Guardar Cliente"):
            if nuevo_cliente and nuevo_cliente not in lista_clientes:
                ws_clientes.append_row([nuevo_cliente])
                st.success(f"{nuevo_cliente} guardado.")
                st.rerun()
            elif nuevo_cliente in lista_clientes:
                st.warning("El cliente ya existe.")
                
        st.divider()
        st.subheader("Clientes Registrados")
        if len(lista_clientes) > 0:
            st.dataframe(pd.DataFrame(lista_clientes, columns=["Nombre"]), hide_index=True)

    # --- 1. FORMULARIO DE INGRESO ---
    st.header(f"1. Registrar Movimiento ({fecha_str})")
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

    interes_pct = 0.0
    total_deuda_generada = 0.0

    if tipo == "Préstamo":
        st.info("💡 Configuración del Crédito con Interés")
        interes_pct = st.number_input("Porcentaje de Interés (%)", min_value=0.0, value=10.0, step=1.0)
        total_deuda_generada = monto + (monto * (interes_pct / 100.0))
        st.write(f"➡️ **Total que el cliente pagará:** ${total_deuda_generada:.2f}")

    # Validación de efectivo disponible en caja (exclusivo para el día seleccionado)
    base_inicial_temp = st.session_state.get(f'base_input_{fecha_str}', 0.0)
    total_cobrado_temp = 0.0
    total_salidas_temp = 0.0

    if not df_fecha.empty and 'Metodo' in df_fecha.columns:
        df_efec_temp = df_fecha[df_fecha['Metodo'] == 'Efectivo']
        total_cobrado_temp = float(df_efec_temp[df_efec_temp['Tipo'] == 'Cobro']['Monto'].sum()) if not df_efec_temp.empty else 0.0
        total_salidas_temp = float(df_efec_temp[df_efec_temp['Tipo'].isin(['Préstamo', 'Gasto'])]['Monto'].sum()) if not df_efec_temp.empty else 0.0

    efectivo_disponible_actual = base_inicial_temp + total_cobrado_temp - total_salidas_temp

    if st.button("Registrar Operación", type="primary"):
        if cliente_concepto and monto > 0:
            if metodo == 'Efectivo' and tipo in ['Préstamo', 'Gasto'] and monto > efectivo_disponible_actual:
                st.error(f"❌ Fondos insuficientes en caja para el {fecha_str}. Tienes ${efectivo_disponible_actual:.2f} disponibles en efectivo.")
            else:
                ws_movimientos.append_row([
                    str(fecha_str), 
                    str(tipo), 
                    str(cliente_concepto), 
                    float(monto), 
                    str(metodo), 
                    float(interes_pct if tipo == "Préstamo" else 0.0), 
                    float(total_deuda_generada if tipo == "Préstamo" else 0.0)
                ])
                st.success(f"✅ ¡Operación guardada para el {fecha_str}!")
                st.rerun()
        else:
            st.error("Completa todos los campos correctamente.")

    # --- 2. MOVIMIENTOS DIVIDIDOS DE LA FECHA ---
    st.header(f"2. Movimientos del Día ({fecha_str})")

    if not df_fecha.empty:
        sub_cobros, sub_prestamos, sub_gastos = st.tabs(["🟢 Cobros Realizados", "🔴 Préstamos Entregados", "🟡 Gastos del Día"])

        with sub_cobros:
            df_cobros = df_fecha[df_fecha['Tipo'] == 'Cobro']
            if not df_cobros.empty:
                st.dataframe(df_cobros[['Cliente_Concepto', 'Monto', 'Metodo']], use_container_width=True, hide_index=True)
                st.metric("Total Cobrado Hoy", f"${df_cobros['Monto'].sum():.2f}")
            else:
                st.info("No hay cobros registrados en esta fecha.")

        with sub_prestamos:
            df_prestamos = df_fecha[df_fecha['Tipo'] == 'Préstamo']
            if not df_prestamos.empty:
                st.dataframe(df_prestamos[['Cliente_Concepto', 'Monto', 'Interes_Pct', 'Total_Deuda', 'Metodo']], use_container_width=True, hide_index=True)
                st.metric("Total Prestado Hoy (Capital)", f"${df_prestamos['Monto'].sum():.2f}")
            else:
                st.info("No hay préstamos registrados en esta fecha.")

        with sub_gastos:
            df_gastos = df_fecha[df_fecha['Tipo'] == 'Gasto']
            if not df_gastos.empty:
                st.dataframe(df_gastos[['Cliente_Concepto', 'Monto', 'Metodo']], use_container_width=True, hide_index=True)
                st.metric("Total Gastado Hoy", f"${df_gastos['Monto'].sum():.2f}")
            else:
                st.info("No hay gastos registrados en esta fecha.")
    else:
        st.info(f"No hay movimientos registrados para la fecha {fecha_str}.")

    # --- 3. CUADRE DE CAJA DIARIO ---
    st.header(f"3. Cuadre de Caja Físico Diario ({fecha_str})")
    
    # Input de base inicial independiente y guardado por fecha
    base_inicial = st.number_input(f"Efectivo de Salida (Base Inicial) para el {fecha_str}:", min_value=0.0, step=1.0, key=f'base_input_{fecha_str}')

    if not df_fecha.empty and 'Metodo' in df_fecha.columns:
        # Filtramos estrictamente los movimientos en EFECTIVO de la fecha seleccionada
        df_efectivo_dia = df_fecha[df_fecha['Metodo'] == 'Efectivo']
        
        try:
            total_cobrado_efec = float(df_efectivo_dia[df_efectivo_dia['Tipo'] == 'Cobro']['Monto'].sum()) if not df_efectivo_dia.empty else 0.0
            total_prestamos_efec = float(df_efectivo_dia[df_efectivo_dia['Tipo'] == 'Préstamo']['Monto'].sum()) if not df_efectivo_dia.empty else 0.0
            total_gastos_efec = float(df_efectivo_dia[df_efectivo_dia['Tipo'] == 'Gasto']['Monto'].sum()) if not df_efectivo_dia.empty else 0.0
        except KeyError:
            total_cobrado_efec = total_prestamos_efec = total_gastos_efec = 0.0

        efectivo_calculado = base_inicial + total_cobrado_efec - total_prestamos_efec - total_gastos_efec
        efectivo_esperado = max(0.0, efectivo_calculado)

        colA, colB, colC, colD, colE = st.columns(5)
        colA.metric("Base Inicial", f"${base_inicial:.2f}")
        colB.metric("Cobros Efectivo (+)", f"${total_cobrado_efec:.2f}")
        colC.metric("Préstamos Efectivo (-)", f"${total_prestamos_efec:.2f}")
        colD.metric("Gastos Efectivo (-)", f"${total_gastos_efec:.2f}")
        colE.metric("EFECTIVO ESPERADO EN CAJA", f"${efectivo_esperado:.2f}")

        if efectivo_calculado < 0:
            st.warning("⚠️ **Alerta de Caja:** Los préstamos y gastos en efectivo superan la base y los cobros del día.")
    else:
        colA, colB, colC, colD, colE = st.columns(5)
        colA.metric("Base Inicial", f"${base_inicial:.2f}")
        colB.metric("Cobros Efectivo (+)", "$0.00")
        colC.metric("Préstamos Efectivo (-)", "$0.00")
        colD.metric("Gastos Efectivo (-)", "$0.00")
        colE.metric("EFECTIVO ESPERADO EN CAJA", f"${base_inicial:.2f}")

with tab_saldos:
    st.header("📊 Estado de Cuenta Actualizado por Cliente (Histórico Total)")
    st.write("Esta tabla calcula la deuda global de cada cliente sumando **todos sus préstamos con interés** y restando **todos sus abonos históricos**, sin importar de qué fecha sean.")

    if not df_movimientos_total.empty and len(lista_clientes) > 0:
        resumen_clientes = []
        
        for cliente in lista_clientes:
            df_cli = df_movimientos_total[df_movimientos_total['Cliente_Concepto'] == cliente]
            
            if not df_cli.empty:
                total_deuda = float(df_cli[df_cli['Tipo'] == 'Préstamo']['Total_Deuda'].sum())
                prestamos_sin_columna = df_cli[(df_cli['Tipo'] == 'Préstamo') & (df_cli['Total_Deuda'] == 0.0)]['Monto'].sum()
                total_deuda += prestamos_sin_columna
                
                total_abonado = float(df_cli[df_cli['Tipo'] == 'Cobro']['Monto'].sum())
                
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
        
        deuda_total_calle = df_resumen["Saldo Pendiente"].sum()
        st.metric("💰 Dinero Total Pendiente en la Calle (Saldos)", f"${deuda_total_calle:.2f}")
    else:
        st.info("Aún no hay clientes o movimientos suficientes para calcular los saldos.")
