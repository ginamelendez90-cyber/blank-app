import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import datetime
import unicodedata

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
# COLUMNAS OFICIALES Y UTILIDADES
# ---------------------------------------------------------
COLUMNAS_PROD = [
    "Orden", "Fecha", "Mecanico", "Moto", "Trabajo", 
    "Moneda", "Monto_Cobrado", "Tasa", "Mano_Obra_USD", "Comision_Pct", "Ganancia_USD"
]
COLUMNAS_VALES = [
    "Vale", "Fecha", "Mecanico", "Concepto", "Monto", "Moneda", "Tasa", "Total_USD", "Forma_Pago"
]

def quitar_acentos_y_espacios(texto):
    if not isinstance(texto, str):
        return ""
    texto_norm = unicodedata.normalize('NFD', texto).encode('ascii', 'ignore').decode('utf-8')
    return texto_norm.strip().lower()

def a_numero(val):
    if pd.isna(val) or val is None:
        return 0.0
    s = str(val).replace(",", ".").replace("$", "").replace("Bs", "").strip()
    try:
        return float(s)
    except ValueError:
        return 0.0

# ---------------------------------------------------------
# CARGA Y REPARACIÓN AUTOMÁTICA DE GOOGLE SHEETS
# ---------------------------------------------------------
def cargar_y_reparar_hoja(nombre_hoja, columnas_oficiales):
    try:
        ws = sheet.worksheet(nombre_hoja)
    except gspread.exceptions.WorksheetNotFound:
        ws = sheet.add_worksheet(title=nombre_hoja, rows="100", cols=str(len(columnas_oficiales)))
        ws.append_row(columnas_oficiales)

    filas = ws.get_all_values()

    if not filas or len(filas) == 0:
        ws.append_row(columnas_oficiales)
        return ws, pd.DataFrame(columns=columnas_oficiales)

    encabezados_actuales = [str(c).strip() for c in filas[0]]
    
    # Auto-reparar el encabezado en Google Sheets si es viejos o faltan columnas
    if len(encabezados_actuales) != len(columnas_oficiales) or encabezados_actuales != columnas_oficiales:
        try:
            ws.update([columnas_oficiales], 'A1')
        except Exception:
            pass
        encabezados_actuales = columnas_oficiales

    datos = filas[1:]
    datos_limpios = []
    
    for r in datos:
        # Rellenar columnas faltantes en registros viejos
        fila_padded = r + [""] * (len(columnas_oficiales) - len(r))
        fila_padded = fila_padded[:len(columnas_oficiales)]
        if any(str(cell).strip() != "" for cell in fila_padded):
            datos_limpios.append(fila_padded)

    df = pd.DataFrame(datos_limpios, columns=columnas_oficiales)
    return ws, df

ws_prod, df_prod = cargar_y_reparar_hoja("PRODUCCION", COLUMNAS_PROD)
ws_vales, df_vales = cargar_y_reparar_hoja("VALES", COLUMNAS_VALES)

# ---------------------------------------------------------
# PROCESAMIENTO DINÁMICO Y CÁLCULO DE MONTOS
# ---------------------------------------------------------
if not df_prod.empty:
    df_prod["Monto_Cobrado_Num"] = df_prod["Monto_Cobrado"].apply(a_numero)
    df_prod["Tasa_Num"] = df_prod["Tasa"].apply(a_numero)
    df_prod["Mano_Obra_USD_Existente"] = df_prod["Mano_Obra_USD"].apply(a_numero)
    df_prod["Comision_Pct_Num"] = df_prod["Comision_Pct"].apply(a_numero)

    def calcular_mo_usd(row):
        moneda = str(row["Moneda"]).upper().strip()
        monto = row["Monto_Cobrado_Num"]
        tasa = row["Tasa_Num"]
        mo_exist = row["Mano_Obra_USD_Existente"]
        
        if moneda == "VES" and tasa > 0 and monto > 0:
            return round(monto / tasa, 2)
        elif moneda == "USD" and monto > 0:
            return round(monto, 2)
        elif monto > 0:
            return round(monto, 2)
        elif mo_exist > 0:
            return round(mo_exist, 2)
        return 0.0

    df_prod["Mano_Obra_USD"] = df_prod.apply(calcular_mo_usd, axis=1)
    df_prod["Ganancia_USD"] = df_prod.apply(lambda r: round(r["Mano_Obra_USD"] * (r["Comision_Pct_Num"] / 100.0), 2), axis=1)
    df_prod["Mecanico_Clean"] = df_prod["Mecanico"].apply(quitar_acentos_y_espacios)
else:
    df_prod["Mano_Obra_USD"] = 0.0
    df_prod["Ganancia_USD"] = 0.0
    df_prod["Mecanico_Clean"] = ""

if not df_vales.empty:
    df_vales["Monto_Num"] = df_vales["Monto"].apply(a_numero)
    df_vales["Tasa_Num"] = df_vales["Tasa"].apply(a_numero)
    df_vales["Total_USD_Existente"] = df_vales["Total_USD"].apply(a_numero)

    def calcular_vale_usd(row):
        moneda = str(row["Moneda"]).upper().strip()
        monto = row["Monto_Num"]
        tasa = row["Tasa_Num"]
        val_exist = row["Total_USD_Existente"]

        if moneda == "VES" and tasa > 0 and monto > 0:
            return round(monto / tasa, 2)
        elif moneda == "USD" and monto > 0:
            return round(monto, 2)
        elif monto > 0:
            return round(monto, 2)
        elif val_exist > 0:
            return round(val_exist, 2)
        return 0.0

    df_vales["Total_USD"] = df_vales.apply(calcular_vale_usd, axis=1)
    df_vales["Mecanico_Clean"] = df_vales["Mecanico"].apply(quitar_acentos_y_espacios)
else:
    df_vales["Total_USD"] = 0.0
    df_vales["Mecanico_Clean"] = ""

# Lista de Mecánicos Única
mecanicos_defecto = ["Carlos Pérez", "Pedro Gómez", "Luis Rodríguez"]
mecanicos_registrados = []
if not df_prod.empty:
    mecanicos_registrados += df_prod["Mecanico"].unique().tolist()
if not df_vales.empty:
    mecanicos_registrados += df_vales["Mecanico"].unique().tolist()

lista_mecanicos = sorted(list(set(mecanicos_defecto + [m for m in mecanicos_registrados if str(m).strip()])))

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
    cols_mostrar_prod = [c for c in COLUMNAS_PROD if c in df_prod.columns]
    st.dataframe(df_prod[cols_mostrar_prod], use_container_width=True)

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
    cols_mostrar_vales = [c for c in COLUMNAS_VALES if c in df_vales.columns]
    st.dataframe(df_vales[cols_mostrar_vales], use_container_width=True)

# ---------------------------------------------------------
# TAB 4: LIQUIDACIÓN
# ---------------------------------------------------------
with tab_liq:
    st.subheader("🧮 Liquidación Calculada")
    
    liq_rows = []
    for m in lista_mecanicos:
        m_norm = quitar_acentos_y_espacios(m)
        
        if not df_prod.empty and "Mecanico_Clean" in df_prod.columns:
            total_fact = df_prod[df_prod["Mecanico_Clean"] == m_norm]["Mano_Obra_USD"].sum()
            gen = df_prod[df_prod["Mecanico_Clean"] == m_norm]["Ganancia_USD"].sum()
        else:
            total_fact = 0.0
            gen = 0.0
            
        if not df_vales.empty and "Mecanico_Clean" in df_vales.columns:
            val = df_vales[df_vales["Mecanico_Clean"] == m_norm]["Total_USD"].sum()
        else:
            val = 0.0
            
        neto = gen - val
        neto_ves = neto * st.session_state.tasa_cambio
        
        liq_rows.append({
            "Mecánico": m,
            "Facturado Total ($)": round(total_fact, 2),
            "Ganancia Comisión ($)": round(gen, 2),
            "Total Vales ($)": round(val, 2),
            "Saldo Neto ($)": round(neto, 2),
            "Saldo Neto (VES)": round(neto_ves, 2)
        })
    
    df_liq = pd.DataFrame(liq_rows)
    st.dataframe(df_liq, use_container_width=True)
