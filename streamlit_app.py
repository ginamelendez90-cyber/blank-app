import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import datetime

st.set_page_config(page_title="Control Taller - Google Sheets", page_icon="🏍️", layout="wide")

# ---------------------------------------------------------
# CONEXIÓN Y AUTENTICACIÓN
# ---------------------------------------------------------
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

@st.cache_resource
def obtener_cliente_gspread():
    creds_dict = dict(st.secrets["connections"]["gsheets"])
    creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    return gspread.authorize(creds)

client = obtener_cliente_gspread()
sheet = client.open_by_url(st.secrets["connections"]["gsheets"]["spreadsheet"])

# ---------------------------------------------------------
# CARGA ROBUSTA CON PREVENCIÓN DE COLUMNAS DUPLICADAS
# ---------------------------------------------------------
def cargar_o_crear_hoja(nombre_hoja, columnas_defecto):
    try:
        ws = sheet.worksheet(nombre_hoja)
    except gspread.exceptions.WorksheetNotFound:
        ws = sheet.add_worksheet(title=nombre_hoja, rows="100", cols=str(len(columnas_defecto)))
        ws.append_row(columnas_defecto)

    filas = ws.get_all_values()

    if not filas or len(filas) < 1:
        ws.append_row(columnas_defecto)
        return ws, pd.DataFrame(columns=columnas_defecto)

    encabezados = [str(c).strip() for c in filas[0]]
    datos = filas[1:]

    # Filtrar filas completamente vacías
    datos_limpios = [r for r in datos if any(str(cell).strip() != "" for cell in r)]

    df = pd.DataFrame(datos_limpios, columns=encabezados)

    # === CORRECCIÓN DEL ERROR: ELIMINAR COLUMNAS DUPLICADAS EN EL DATAFRAME ===
    df = df.loc[:, ~df.columns.duplicated()].copy()

    # Asegurar que existan todas las columnas clave
    for col in columnas_defecto:
        if col not in df.columns:
            df[col] = ""

    return ws, df

# Estandarización de columnas
COLUMNAS_PROD = [
    "Orden", "Fecha", "Mecanico", "Moto", "Trabajo", 
    "Moneda", "Monto_Cobrado", "Tasa", "Mano_Obra_USD", "Comision_Pct", "Ganancia_USD"
]
COLUMNAS_VALES = [
    "Vale", "Fecha", "Mecanico", "Concepto", "Monto", "Moneda", "Tasa", "Total_USD", "Forma_Pago"
]

# Carga de hojas
ws_prod, df_prod = cargar_o_crear_hoja("PRODUCCION", COLUMNAS_PROD)
ws_vales, df_vales = cargar_o_crear_hoja("VALES", COLUMNAS_VALES)

# FUNCIÓN PARA CONVERTIR TEXTO A NÚMERO (CORRIGE COMAS Y PUNTOS)
def a_numero(serie):
    if serie is None or len(serie) == 0:
        return pd.Series(dtype=float)
    limpio = serie.astype(str).str.replace(",", ".").str.replace("$", "").str.strip()
    return pd.to_numeric(limpio, errors="coerce").fillna(0.0)

# Limpieza en Producción
if not df_prod.empty:
    df_prod["Monto_Cobrado"] = a_numero(df_prod["Monto_Cobrado"])
    df_prod["Tasa"] = a_numero(df_prod["Tasa"])
    df_prod["Mano_Obra_USD"] = a_numero(df_prod["Mano_Obra_USD"])
    df_prod["Comision_Pct"] = a_numero(df_prod["Comision_Pct"])
    df_prod["Ganancia_USD"] = a_numero(df_prod["Ganancia_USD"])
    df_prod["Mecanico"] = df_prod["Mecanico"].astype(str).str.strip()

# Limpieza en Vales
if not df_vales.empty:
    df_vales["Monto"] = a_numero(df_vales["Monto"])
    df_vales["Tasa"] = a_numero(df_vales["Tasa"])
    df_vales["Total_USD"] = a_numero(df_vales["Total_USD"])
    df_vales["Mecanico"] = df_vales["Mecanico"].astype(str).str.strip()

# Lista de mecánicos
mecanicos_defecto = ["Carlos Pérez", "Pedro Gómez", "Luis Rodríguez"]
mecanicos_registrados = (
    df_prod["Mecanico"].unique().tolist() + df_vales["Mecanico"].unique().tolist()
    if not df_prod.empty else []
)
lista_mecanicos = sorted(list(set(mecanicos_defecto + [m for m in mecanicos_registrados if m])))

# Tasa de cambio global
if "tasa_cambio" not in st.session_state:
    st.session_state.tasa_cambio = 40.80

# ---------------------------------------------------------
# BARRA LATERAL
# ---------------------------------------------------------
st.sidebar.title("⚙️ Configuración Taller")
st.session_state.tasa_cambio = st.sidebar.number_input(
    "Tasa del Día (VES/USD):",
    value=float(st.session_state.tasa_cambio),
    min_value=1.0, step=0.10, format="%.2f"
)

# ---------------------------------------------------------
# PANEL PRINCIPAL
# ---------------------------------------------------------
st.title("🏍️ Control de Taller")

tab_dash, tab_prod, tab_vales, tab_liq = st.tabs(["📊 Dashboard", "🛠️ Producción", "💵 Vales", "🧮 Liquidación"])

# ---------------------------------------------------------
# TAB 1: DASHBOARD
# ---------------------------------------------------------
with tab_dash:
    total_mo = df_prod["Mano_Obra_USD"].sum() if not df_prod.empty else 0.0
    total_com = df_prod["Ganancia_USD"].sum() if not df_prod.empty else 0.0
    total_val = df_vales["Total_USD"].sum() if not df_vales.empty else 0.0
    neto_pagar = total_com - total_val
    
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Facturado Total (USD)", f"${total_mo:.2f}")
    c2.metric("Comisiones Ganadas", f"${total_com:.2f}")
    c3.metric("Vales Entregados", f"${total_val:.2f}")
    c4.metric("Neto por Pagar", f"${neto_pagar:.2f}")

# ---------------------------------------------------------
# TAB 2: PRODUCCIÓN
# ---------------------------------------------------------
with tab_prod:
    st.subheader("Registrar Nuevo Trabajo")
    
    with st.form("form_prod", clear_on_submit=True):
        f1, f2, f3 = st.columns(3)
        orden = f1.text_input("N° Orden", value=f"#{len(df_prod)+101}")
        fecha_p = f2.date_input("Fecha", datetime.date.today())
        mecanico_p = f3.selectbox("Mecánico", lista_mecanicos)
        
        f4, f5 = st.columns([2, 2])
        moto = f4.text_input("Moto", placeholder="Ej: Bera SBR 150")
        trabajo = f5.text_input("Trabajo Realizado", placeholder="Ej: Mantenimiento General")
        
        st.markdown("---")
        c_mon, c_monto, c_tasa, c_com = st.columns(4)
        moneda_p = c_mon.selectbox("Moneda de Cobro", ["USD", "VES"])
        monto_cobrado = c_monto.number_input("Monto Mano de Obra", min_value=0.0, step=5.0)
        tasa_p = c_tasa.number_input("Tasa Aplicada (VES/USD)", value=float(st.session_state.tasa_cambio))
        comision_pct = c_com.slider("% Comisión Mecánico", min_value=0, max_value=100, value=50)
        
        btn_prod = st.form_submit_button("💾 Guardar Trabajo")
        
        if btn_prod:
            if moneda_p == "VES":
                mano_obra_usd = monto_cobrado / tasa_p if tasa_p > 0 else 0.0
            else:
                mano_obra_usd = monto_cobrado
                
            ganancia_usd = mano_obra_usd * (comision_pct / 100.0)
            
            nueva_fila = [
                orden,
                str(fecha_p),
                mecanico_p,
                moto,
                trabajo,
                moneda_p,
                str(monto_cobrado),
                str(tasa_p),
                str(round(mano_obra_usd, 2)),
                str(comision_pct),
                str(round(ganancia_usd, 2))
            ]
            
            ws_prod.append_row(nueva_fila, value_input_option="USER_ENTERED")
            st.success("✅ Trabajo guardado con éxito en Google Sheets.")
            st.rerun()

    st.markdown("---")
    st.subheader("Histórico de Producción")
    st.dataframe(df_prod, use_container_width=True)

# ---------------------------------------------------------
# TAB 3: VALES
# ---------------------------------------------------------
with tab_vales:
    st.subheader("Registrar Vale")
    
    with st.form("form_vales", clear_on_submit=True):
        v1, v2, v3 = st.columns(3)
        num_vale = v1.text_input("N° Vale", value=f"V-0{len(df_vales)+1}")
        fecha_v = v2.date_input("Fecha Vale", datetime.date.today())
        mecanico_v = v3.selectbox("Mecánico ", lista_mecanicos)
        
        v4, v5, v6, v7 = st.columns(4)
        concepto = v4.text_input("Concepto", placeholder="Ej: Pasajes / Adelanto")
        monto = v5.number_input("Monto Entregado", min_value=0.0, step=5.0)
        moneda = v6.selectbox("Moneda", ["USD", "VES"])
        tasa_v = v7.number_input("Tasa Aplicada", value=float(st.session_state.tasa_cambio))
        forma_pago = st.selectbox("Forma Pago", ["Efectivo USD", "Efectivo VES", "Pago Móvil", "Transferencia"])
        
        btn_vale = st.form_submit_button("💵 Entregar Vale")
        
        if btn_vale:
            total_usd = monto if moneda == "USD" else (monto / tasa_v if tasa_v > 0 else 0.0)
            nuevo_vale = [
                num_vale,
                str(fecha_v),
                mecanico_v,
                concepto,
                str(monto),
                moneda,
                str(tasa_v),
                str(round(total_usd, 2)),
                forma_pago
            ]
            ws_vales.append_row(nuevo_vale, value_input_option="USER_ENTERED")
            st.success("✅ Vale registrado en Google Sheets.")
            st.rerun()

    st.markdown("---")
    st.dataframe(df_vales, use_container_width=True)

# ---------------------------------------------------------
# TAB 4: LIQUIDACIÓN
# ---------------------------------------------------------
with tab_liq:
    st.subheader("🧮 Liquidación Calculada")
    
    liq_rows = []
    for m in lista_mecanicos:
        gen = df_prod[df_prod["Mecanico"] == m]["Ganancia_USD"].sum() if not df_prod.empty else 0.0
        val = df_vales[df_vales["Mecanico"] == m]["Total_USD"].sum() if not df_vales.empty else 0.0
        neto = gen - val
        neto_ves = neto * st.session_state.tasa_cambio
        
        liq_rows.append({
            "Mecánico": m,
            "Ganancia Total ($)": round(gen, 2),
            "Total Vales ($)": round(val, 2),
            "Saldo Neto ($)": round(neto, 2),
            "Saldo Neto (VES)": round(neto_ves, 2)
        })
    
    df_liq = pd.DataFrame(liq_rows)
    st.dataframe(df_liq, use_container_width=True)
