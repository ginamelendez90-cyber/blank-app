import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import datetime

st.set_page_config(page_title="Control Taller - Google Sheets", page_icon="🏍️", layout="wide")

# ---------------------------------------------------------
# CONEXIÓN DIRECTA CON GSPREAD
# ---------------------------------------------------------
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

@st.cache_resource
def obtener_cliente_gspread():
    # Carga las credenciales desde los secretos de Streamlit
    creds_dict = dict(st.secrets["connections"]["gsheets"])
    creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    return gspread.authorize(creds)

client = obtener_cliente_gspread()
# Abre el libro de trabajo usando la URL configurada en los Secrets
sheet = client.open_by_url(st.secrets["connections"]["gsheets"]["spreadsheet"])

def cargar_hoja(nombre_hoja):
    ws = sheet.worksheet(nombre_hoja)
    datos = ws.get_all_records()
    return pd.DataFrame(datos)

# Cargar DataFrames
df_prod = cargar_hoja("PRODUCCION")
df_vales = cargar_hoja("VALES")

# Tasa de cambio
if "tasa_cambio" not in st.session_state:
    st.session_state.tasa_cambio = 40.80

mecanicos = ["Carlos Pérez", "Pedro Gómez", "Luis Rodríguez"]

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
    total_mo = pd.to_numeric(df_prod["Mano_Obra_USD"], errors="coerce").sum() if not df_prod.empty else 0.0
    total_com = pd.to_numeric(df_prod["Ganancia_USD"], errors="coerce").sum() if not df_prod.empty else 0.0
    total_val = pd.to_numeric(df_vales["Total_USD"], errors="coerce").sum() if not df_vales.empty else 0.0
    neto_pagar = total_com - total_val
    
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Facturado (M.O)", f"${total_mo:.2f}")
    c2.metric("Comisiones Ganadas", f"${total_com:.2f}")
    c3.metric("Vales Entregados", f"${total_val:.2f}")
    c4.metric("Neto por Pagar", f"${neto_pagar:.2f}")

# ---------------------------------------------------------
# TAB 2: PRODUCCIÓN (INSERTAR NUEVA FILA)
# ---------------------------------------------------------
with tab_prod:
    st.subheader("Registrar Nuevo Trabajo")
    
    with st.form("form_prod", clear_on_submit=True):
        f1, f2, f3 = st.columns(3)
        orden = f1.text_input("N° Orden", value=f"#{len(df_prod)+101}")
        fecha_p = f2.date_input("Fecha", datetime.date.today())
        mecanico_p = f3.selectbox("Mecánico", mecanicos)
        
        f4, f5, f6 = st.columns(3)
        moto = f4.text_input("Moto", placeholder="Ej: Bera SBR 150")
        trabajo = f5.text_input("Trabajo Realizado", placeholder="Ej: Mantenimiento")
        mano_obra = f6.number_input("Mano de Obra ($)", min_value=0.0, step=5.0)
        comision_pct = st.slider("% Comisión", min_value=0, max_value=100, value=50)
        
        btn_prod = st.form_submit_button("💾 Guardar Trabajo")
        
        if btn_prod:
            ganancia = mano_obra * (comision_pct / 100.0)
            nueva_fila = [
                orden,
                str(fecha_p),
                mecanico_p,
                moto,
                trabajo,
                mano_obra,
                comision_pct,
                ganancia
            ]
            
            # Inserta únicamente la nueva fila al final
            ws_prod = sheet.worksheet("PRODUCCION")
            ws_prod.append_row(nueva_fila)
            st.success("✅ ¡Trabajo guardado exitosamente!")
            st.rerun()

    st.markdown("---")
    st.dataframe(df_prod, use_container_width=True)

# ---------------------------------------------------------
# TAB 3: VALES (INSERTAR NUEVA FILA)
# ---------------------------------------------------------
with tab_vales:
    st.subheader("Registrar Vale")
    
    with st.form("form_vales", clear_on_submit=True):
        v1, v2, v3 = st.columns(3)
        num_vale = v1.text_input("N° Vale", value=f"V-0{len(df_vales)+1}")
        fecha_v = v2.date_input("Fecha Vale", datetime.date.today())
        mecanico_v = v3.selectbox("Mecánico ", mecanicos)
        
        v4, v5, v6, v7 = st.columns(4)
        concepto = v4.text_input("Concepto", placeholder="Ej: Pasajes / Avance")
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
                monto,
                moneda,
                tasa_v,
                total_usd,
                forma_pago
            ]
            
            # Inserta únicamente la nueva fila al final
            ws_vales = sheet.worksheet("VALES")
            ws_vales.append_row(nuevo_vale)
            st.success("✅ Vale registrado exitosamente.")
            st.rerun()

    st.markdown("---")
    st.dataframe(df_vales, use_container_width=True)

# ---------------------------------------------------------
# TAB 4: LIQUIDACIÓN
# ---------------------------------------------------------
with tab_liq:
    st.subheader("🧮 Liquidación Calculada")
    
    liq_rows = []
    for m in mecanicos:
        gen = pd.to_numeric(df_prod[df_prod["Mecanico"] == m]["Ganancia_USD"], errors="coerce").sum() if not df_prod.empty and "Mecanico" in df_prod.columns else 0.0
        val = pd.to_numeric(df_vales[df_vales["Mecanico"] == m]["Total_USD"], errors="coerce").sum() if not df_vales.empty and "Mecanico" in df_vales.columns else 0.0
        neto = gen - val
        neto_ves = neto * st.session_state.tasa_cambio
        
        liq_rows.append({
            "Mecánico": m,
            "Ganancia Total ($)": gen,
            "Total Vales ($)": val,
            "Saldo Neto ($)": neto,
            "Saldo Neto (VES)": neto_ves
        })
    
    df_liq = pd.DataFrame(liq_rows)
    st.dataframe(df_liq, use_container_width=True)
