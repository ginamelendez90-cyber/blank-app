import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
from datetime import datetime

# Configuración de página
st.set_page_config(page_title="Control de Taller - Trabajos y Liquidación", layout="wide")

# ==========================================
# 1. CONEXIÓN Y CACHÉ CON GOOGLE SHEETS
# ==========================================

@st.cache_resource
def get_gspread_client():
    """Autentica y devuelve el cliente de gspread."""
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    credentials = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=scopes,
    )
    return gspread.authorize(credentials)

def get_spreadsheet():
    """Obtiene el libro de cálculo principal."""
    client = get_gspread_client()
    return client.open_by_url(st.secrets["connections"]["gsheets"]["spreadsheet"])

@st.cache_data(ttl=60)
def load_data(sheet_name):
    """Carga los datos de una pestaña específica y los devuelve como DataFrame."""
    try:
        sheet = get_spreadsheet()
        worksheet = sheet.worksheet(sheet_name)
        data = worksheet.get_all_records()
        df = pd.DataFrame(data)
        return df, worksheet
    except Exception as e:
        st.error(f"Error cargando la pestaña '{sheet_name}': {e}")
        return pd.DataFrame(), None

# ==========================================
# 2. FUNCIONES DE ACTUALIZACIÓN (ESCRITURA)
# ==========================================

def cambiar_estado_trabajo(row_index, nuevo_estado):
    """Actualiza la columna 'Estado' de una fila en la hoja Trabajos."""
    sheet = get_spreadsheet()
    worksheet = sheet.worksheet("Trabajos")
    # En gspread las filas empiezan en 1. Sumamos 2 por el encabezado.
    worksheet.update_cell(row_index + 2, 5, nuevo_estado)  # Columna 5 = Estado
    st.cache_data.clear()  # Limpiar caché para refrescar pantalla
    st.rerun()

def registrar_trabajo(fecha, trabajador, descripcion, monto):
    """Registra un nuevo trabajo con estado inicial 'Pendiente'."""
    sheet = get_spreadsheet()
    worksheet = sheet.worksheet("Trabajos")
    worksheet.append_row([str(fecha), trabajador, descripcion, float(monto), "Pendiente"])
    st.cache_data.clear()

def registrar_adelanto(fecha, trabajador, monto, concepto):
    """Registra un adelanto de dinero dado al trabajador."""
    sheet = get_spreadsheet()
    worksheet = sheet.worksheet("Adelantos")
    worksheet.append_row([str(fecha), trabajador, float(monto), concepto])
    st.cache_data.clear()


# ==========================================
# 3. INTERFAZ DE USUARIO (STREAMLIT)
# ==========================================

st.title("🛠️ Sistema de Control de Taller y Liquidación")

# Cargar datos
df_trabajos, ws_trabajos = load_data("Trabajos")
df_adelantos, ws_adelantos = load_data("Adelantos")

# Pestañas principales de navegación
tab_aprobar, tab_registro, tab_liquidacion = st.tabs([
    "✅ Aprobar / Rechazar Trabajos", 
    "📝 Registrar Trabajo / Adelanto", 
    "💰 Liquidación de Trabajadores"
])

# ------------------------------------------
# TAB 1: APROBAR / RECHAZAR TRABAJOS
# ------------------------------------------
with tab_aprobar:
    st.subheader("Trabajos Pendientes por Revisión")
    
    if not df_trabajos.empty and "Estado" in df_trabajos.columns:
        # Filtrar solo los pendientes
        pendientes = df_trabajos[df_trabajos["Estado"] == "Pendiente"]
        
        if pendientes.empty:
            st.info("🎉 No hay trabajos pendientes por aprobar.")
        else:
            for index, row in pendientes.iterrows():
                with st.container():
                    col1, col2, col3, col4, col5 = st.columns([1.5, 2, 3, 1.5, 2])
                    col1.write(f"**Fecha:** {row.get('Fecha', '')}")
                    col2.write(f"**Trabajador:** {row.get('Trabajador', '')}")
                    col3.write(f"**Trabajo:** {row.get('Descripcion', '')}")
                    col4.write(f"**Monto:** ${row.get('Monto', 0):,.2f}")
                    
                    # Botones de acción para cada trabajo
                    col_btn1, col_btn2 = col5.columns(2)
                    if col_btn1.button("✅ Aprobar", key=f"app_{index}"):
                        cambiar_estado_trabajo(index, "Aprobado")
                    if col_btn2.button("❌ Rechazar", key=f"rej_{index}"):
                        cambiar_estado_trabajo(index, "Rechazado")
                    st.divider()
    else:
        st.warning("No hay registros o la estructura de la hoja no es correcta.")

# ------------------------------------------
# TAB 2: REGISTRO DE TRABAJOS Y ADELANTOS
# ------------------------------------------
with tab_registro:
    col_left, col_right = st.columns(2)
    
    with col_left:
        st.subheader("➕ Registrar Nuevo Trabajo")
        with st.form("form_trabajo", clear_on_submit=True):
            fecha_t = st.date_input("Fecha", datetime.now(), key="f_trab")
            trabajador_t = st.text_input("Nombre del Trabajador")
            descripcion_t = st.text_area("Descripción del Trabajo / Reparación")
            monto_t = st.number_input("Monto / Generado ($)", min_value=0.0, step=10.0)
            
            submit_trabajo = st.form_submit_button("Guardar Trabajo (Queda Pendiente)")
            
            if submit_trabajo:
                if trabajador_t and monto_t > 0:
                    registrar_trabajo(fecha_t, trabajador_t, descripcion_t, monto_t)
                    st.success(f"Trabajo guardado como PENDIENTE para {trabajador_t}.")
                    st.rerun()
                else:
                    st.error("Por favor completa el nombre del trabajador y un monto válido.")

    with col_right:
        st.subheader("💸 Registrar Adelanto / Vale de Dinero")
        with st.form("form_adelanto", clear_on_submit=True):
            fecha_a = st.date_input("Fecha", datetime.now(), key="f_adel")
            trabajador_a = st.text_input("Nombre del Trabajador", key="t_adel")
            concepto_a = st.text_input("Motivo / Concepto del Adelanto")
            monto_a = st.number_input("Monto Entregado ($)", min_value=0.0, step=10.0)
            
            submit_adelanto = st.form_submit_button("Registrar Adelanto")
            
            if submit_adelanto:
                if trabajador_a and monto_a > 0:
                    registrar_adelanto(fecha_a, trabajador_a, monto_a, concepto_a)
                    st.success(f"Adelanto de ${monto_a} registrado para {trabajador_a}.")
                    st.rerun()
                else:
                    st.error("Por favor completa el nombre del trabajador y un monto válido.")

# ------------------------------------------
# TAB 3: LIQUIDACIÓN DE TRABAJADORES
# ------------------------------------------
with tab_liquidacion:
    st.subheader("📊 Resumen de Liquidación de Trabajadores")
    
    # Obtener lista única de trabajadores
    lista_trabajadores = []
    if not df_trabajos.empty and "Trabajador" in df_trabajos.columns:
        lista_trabajadores.extend(df_trabajos["Trabajador"].dropna().unique().tolist())
    if not df_adelantos.empty and "Trabajador" in df_adelantos.columns:
        lista_trabajadores.extend(df_adelantos["Trabajador"].dropna().unique().tolist())
    
    lista_trabajadores = sorted(list(set(lista_trabajadores)))
    
    if not lista_trabajadores:
        st.info("No hay registros de trabajadores aún.")
    else:
        filtro_trabajador = st.selectbox("Seleccionar Trabajador:", ["Todos"] + lista_trabajadores)
        
        # FILTRADO DE DATOS
        # ⚠️ AQUÍ ESTÁ LA REGLA CLAVE: Solo tomamos trabajos con Estado == 'Aprobado'
        trabajadores_evaluar = lista_trabajadores if filtro_trabajador == "Todos" else [filtro_trabajador]
        
        resumen_data = []
        
        for emp in trabajadores_evaluar:
            # Trabajos solo aprobados
            monto_generado_aprobado = 0.0
            if not df_trabajos.empty and "Estado" in df_trabajos.columns:
                aprobados_emp = df_trabajos[
                    (df_trabajos["Trabajador"] == emp) & 
                    (df_trabajos["Estado"] == "Aprobado")
                ]
                monto_generado_aprobado = aprobados_emp["Monto"].sum() if not aprobados_emp.empty else 0.0

            # Total adelantos
            monto_adelantos = 0.0
            if not df_adelantos.empty and "Trabajador" in df_adelantos.columns:
                adelantos_emp = df_adelantos[df_adelantos["Trabajador"] == emp]
                monto_adelantos = adelantos_emp["Monto"].sum() if not adelantos_emp.empty else 0.0

            saldo_neto = monto_generado_aprobado - monto_adelantos
            
            resumen_data.append({
                "Trabajador": emp,
                "Generado Aprobado ($)": monto_generado_aprobado,
                "Adelantos/Vales ($)": monto_adelantos,
                "Total a Liquidar ($)": saldo_neto
            })
        
        df_resumen = pd.DataFrame(resumen_data)
        
        # Tarjetas Métricas
        col_m1, col_m2, col_m3 = st.columns(3)
        col_m1.metric("Total Generado Aprobado", f"${df_resumen['Generado Aprobado ($)'].sum():,.2f}")
        col_m2.metric("Total Vales / Adelantos", f"${df_resumen['Adelantos/Vales ($)'].sum():,.2f}")
        col_m3.metric("Total Neto a Pagar", f"${df_resumen['Total a Liquidar ($)'].sum():,.2f}")
        
        st.divider()
        st.dataframe(df_resumen, use_container_width=True)
        
        # Mostrar detalle individual si seleccionó a uno en específico
        if filtro_trabajador != "Todos":
            st.subheader(f"🔍 Historial Aprobado y Adelantos de {filtro_trabajador}")
            
            c1, c2 = st.columns(2)
            with c1:
                st.write("**Trabajos Aprobados**")
                if not df_trabajos.empty:
                    df_ap = df_trabajos[(df_trabajos["Trabajador"] == filtro_trabajador) & (df_trabajos["Estado"] == "Aprobado")]
                    st.dataframe(df_ap[["Fecha", "Descripcion", "Monto"]], use_container_width=True)
            
            with c2:
                st.write("**Adelantos Recibidos**")
                if not df_adelantos.empty:
                    df_ad = df_adelantos[df_adelantos["Trabajador"] == filtro_trabajador]
                    st.dataframe(df_ad[["Fecha", "Concepto", "Monto"]], use_container_width=True)
