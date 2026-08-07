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
# GESTIÓN DE LA TASA EN GOOGLE SHEETS
# ---------------------------------------------------------
def obtener_ws_config():
    try:
        ws = sheet.worksheet("CONFIGURACION")
    except gspread.exceptions.WorksheetNotFound:
        ws = sheet.add_worksheet(title="CONFIGURACION", rows="10", cols="2")
        ws.append_row(["Clave", "Valor"])
        ws.append_row(["Tasa_Dia", "40.80"])
    return ws

def cargar_tasa_guardada():
    try:
        ws = obtener_ws_config()
        datos = ws.get_all_records()
        for fila in datos:
            if str(fila.get("Clave")).strip() == "Tasa_Dia":
                try:
                    return float(str(fila.get("Valor")).replace(",", "."))
                except ValueError:
                    return 40.80
    except Exception:
        pass
    return 40.80

def guardar_nueva_tasa(nueva_tasa):
    try:
        ws = obtener_ws_config()
        filas = ws.get_all_values()
        
        fila_idx = None
        for idx, row in enumerate(filas):
            if len(row) > 0 and row[0].strip() == "Tasa_Dia":
                fila_idx = idx + 1
                break
                
        if fila_idx:
            ws.update_cell(fila_idx, 2, str(round(nueva_tasa, 2)))
        else:
            ws.append_row(["Tasa_Dia", str(round(nueva_tasa, 2))])
    except Exception as e:
        st.error(f"Error guardando tasa en Google Sheets: {e}")

def obtener_tasa_actual():
    if "tasa_cambio" not in st.session_state or st.session_state.get("tasa_cambio") is None:
        st.session_state["tasa_cambio"] = cargar_tasa_guardada()
    try:
        return float(st.session_state["tasa_cambio"])
    except (ValueError, TypeError):
        st.session_state["tasa_cambio"] = 40.80
        return 40.80

# Inicialización segura de tasa
_ = obtener_tasa_actual()

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
# CARGA Y REPARACIÓN AUTOMÁTICA DE TABLAS
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
    
    if len(encabezados_actuales) != len(columnas_oficiales) or encabezados_actuales != columnas_oficiales:
        try:
            ws.update([columnas_oficiales], 'A1')
        except Exception:
            pass
        encabezados_actuales = columnas_oficiales

    datos = filas[1:]
    datos_limpios = []
    
    for r in datos:
        fila_padded = r + [""] * (len(columnas_oficiales) - len(r))
        fila_padded = fila_padded[:len(columnas_oficiales)]
        if any(str(cell).strip() != "" for cell in fila_padded):
            datos_limpios.append(fila_padded)

    df = pd.DataFrame(datos_limpios, columns=columnas_oficiales)
    return ws, df

ws_prod, df_prod = cargar_y_reparar_hoja("PRODUCCION", COLUMNAS_PROD)
ws_vales, df_vales = cargar_y_reparar_hoja("VALES", COLUMNAS_VALES)

# ---------------------------------------------------------
# PROCESAMIENTO DINÁMICO
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

mecanicos_defecto = ["Carlos Pérez", "Pedro Gómez", "Luis Rodríguez"]
mecanicos_registrados = []
if not df_prod.empty:
    mecanicos_registrados += df_prod["Mecanico"].unique().tolist()
if not df_vales.empty:
    mecanicos_registrados += df_vales["Mecanico"].unique().tolist()

lista_mecanicos = sorted(list(set(mecanicos_defecto + [m for m in mecanicos_registrados if str(m).strip()])))

# ---------------------------------------------------------
# CONTROL DE ACCESO
# ---------------------------------------------------------
CLAVE_ADMIN = "1234"

st.sidebar.title("🔐 Acceso al Sistema")
rol = st.sidebar.radio("Seleccionar Rol:", ["🛠️ Trabajadores (Mecánicos)", "🔑 Administrador (Dueño)"])

es_admin = False

if rol == "🔑 Administrador (Dueño)":
    clave_ingresada = st.sidebar.text_input("Clave de Administrador:", type="password")
    if clave_ingresada == CLAVE_ADMIN:
        es_admin = True
        st.sidebar.success("Acceso concedido")
    elif clave_ingresada != "":
        st.sidebar.error("Clave incorrecta")

tasa_actual = obtener_tasa_actual()

if es_admin:
    st.sidebar.markdown("---")
    st.sidebar.title("⚙️ Configuración Taller")

    with st.sidebar.form("form_tasa"):
        tasa_input = st.number_input(
            "Tasa del Día (VES/USD):",
            value=tasa_actual,
            min_value=1.0, step=0.10, format="%.2f"
        )
        btn_guardar_tasa = st.form_submit_button("💾 Guardar Tasa en Sheets")

        if btn_guardar_tasa:
            guardar_nueva_tasa(tasa_input)
            st.session_state["tasa_cambio"] = tasa_input
            st.sidebar.success(f"✅ Tasa guardada: {tasa_input:.2f} VES/USD")
            st.rerun()

    st.sidebar.info(f"📌 Tasa Activa: **{obtener_tasa_actual():.2f} VES/USD**")

# ---------------------------------------------------------
# INTERFAZ
# ---------------------------------------------------------
st.title("🏍️ Control de Taller")

def mostrar_formulario_produccion(es_modo_admin=False):
    st.subheader("Registrar Trabajo Realizado")
    t_actual = obtener_tasa_actual()
    
    with st.form("form_prod", clear_on_submit=True):
        f1, f2, f3 = st.columns(3)
        orden = f1.text_input("N° Orden", value=f"#{len(df_prod)+101}")
        fecha_p = f2.date_input("Fecha", datetime.date.today())
        mecanico_p = f3.selectbox("Mecánico", lista_mecanicos)
        
        f4, f5 = st.columns([2, 2])
        moto = f4.text_input("Moto", placeholder="Ej: Bera SBR 150")
        trabajo = f5.text_input("Trabajo Realizado", placeholder="Ej: Mantenimiento General")
        
        st.markdown("---")
        
        if es_modo_admin:
            c_mon, c_monto, c_tasa, c_com = st.columns(4)
            moneda_p = c_mon.selectbox("Moneda de Cobro", ["USD", "VES"])
            monto_cobrado = c_monto.number_input("Monto Mano de Obra", min_value=0.0, step=5.0)
            tasa_p = c_tasa.number_input("Tasa Aplicada (VES/USD)", value=t_actual)
            comision_pct = c_com.slider("% Comisión Mecánico", min_value=0, max_value=100, value=50)
        else:
            c_mon, c_monto = st.columns(2)
            moneda_p = c_mon.selectbox("Moneda de Cobro", ["USD", "VES"])
            monto_cobrado = c_monto.number_input("Monto Mano de Obra", min_value=0.0, step=5.0)
            tasa_p = t_actual
            comision_pct = 50
        
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
                str(round(comision_pct, 2)),
                str(round(ganancia_usd, 2))
            ]
            
            ws_prod.append_row(nueva_fila, value_input_option="USER_ENTERED")
            st.success("✅ Trabajo registrado correctamente.")
            st.rerun()

    st.markdown("---")
    st.subheader("Registro de Trabajos")
    
    if es_modo_admin:
        cols_mostrar = [c for c in COLUMNAS_PROD if c in df_prod.columns]
    else:
        cols_mostrar = ["Orden", "Fecha", "Mecanico", "Moto", "Trabajo", "Moneda", "Monto_Cobrado"]
        
    st.dataframe(df_prod[cols_mostrar], use_container_width=True, hide_index=True)


if not es_admin:
    st.info("💡 Modo Trabajador: Registra tus trabajos diarios. No tienes acceso a funciones administrativas.")
    mostrar_formulario_produccion(es_modo_admin=False)

else:
    tab_dash, tab_prod, tab_vales, tab_liq = st.tabs(["📊 Dashboard", "🛠️ Producción", "💵 Vales", "🧮 Liquidación"])

    with tab_dash:
        total_mo = df_prod["Mano_Obra_USD"].sum() if not df_prod.empty else 0.0
        total_com = df_prod["Ganancia_USD"].sum() if not df_prod.empty else 0.0
        ganancia_dueno = total_mo - total_com
        total_val = df_vales["Total_USD"].sum() if not df_vales.empty else 0.0
        neto_pagar = total_com - total_val
        
        st.subheader("📊 Ingresos y Ganancias del Taller")
        c1, c2, c3 = st.columns(3)
        c1.metric("Facturado Total (Mano de Obra)", f"${total_mo:.2f}")
        c2.metric(
            "🏢 Ganancia del Dueño / Taller", 
            f"${ganancia_dueno:.2f}", 
            delta=f"{(ganancia_dueno/total_mo*100):.1f}% de M.O" if total_mo > 0 else None
        )
        c3.metric("🔧 Comisiones Mecánicos", f"${total_com:.2f}")

        st.markdown("---")
        st.subheader("💵 Balance y Liquidación de Mecánicos")
        c4, c5 = st.columns(2)
        c4.metric("Vales Entregados", f"${total_val:.2f}")
        c5.metric("Neto Pendiente por Pagar", f"${neto_pagar:.2f}")

    with tab_prod:
        mostrar_formulario_produccion(es_modo_admin=True)

    with tab_vales:
        st.subheader("Registrar Vale")
        t_actual = obtener_tasa_actual()
        
        with st.form("form_vales", clear_on_submit=True):
            v1, v2, v3 = st.columns(3)
            num_vale = v1.text_input("N° Vale", value=f"V-0{len(df_vales)+1}")
            fecha_v = v2.date_input("Fecha Vale", datetime.date.today())
            mecanico_v = v3.selectbox("Mecánico ", lista_mecanicos)
            
            v4, v5, v6, v7 = st.columns(4)
            concepto = v4.text_input("Concepto", placeholder="Ej: Pasajes / Adelanto")
            monto = v5.number_input("Monto Entregado", min_value=0.0, step=5.0)
            moneda = v6.selectbox("Moneda", ["USD", "VES"])
            tasa_v = v7.number_input("Tasa Aplicada", value=t_actual)
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
        st.dataframe(df_vales[cols_mostrar_vales], use_container_width=True, hide_index=True)

    with tab_liq:
        st.subheader("🧮 Resumen de Liquidación a Pagar")
        
        liq_rows = []
        tasa_actual = obtener_tasa_actual()
        
        for m in lista_mecanicos:
            m_norm = quitar_acentos_y_espacios(m)
            
            # --- SECTOR DÓLARES Y BOLÍVARES ---
            if not df_prod.empty and "Mecanico_Clean" in df_prod.columns:
                df_m_prod = df_prod[df_prod["Mecanico_Clean"] == m_norm]
                prod_usd = df_m_prod[df_m_prod["Moneda"].astype(str).str.upper().str.strip() == "USD"]
                gan_usd = prod_usd["Ganancia_USD"].sum()
                
                prod_ves = df_m_prod[df_m_prod["Moneda"].astype(str).str.upper().str.strip() == "VES"]
                gan_ves = (prod_ves["Monto_Cobrado_Num"] * (prod_ves["Comision_Pct_Num"] / 100.0)).sum()
            else:
                gan_usd = 0.0
                gan_ves = 0.0
                
            if not df_vales.empty and "Mecanico_Clean" in df_vales.columns:
                df_m_vales = df_vales[df_vales["Mecanico_Clean"] == m_norm]
                vales_usd = df_m_vales[df_m_vales["Moneda"].astype(str).str.upper().str.strip() == "USD"]["Monto_Num"].sum()
                vales_ves = df_m_vales[df_m_vales["Moneda"].astype(str).str.upper().str.strip() == "VES"]["Monto_Num"].sum()
            else:
                vales_usd = 0.0
                vales_ves = 0.0
                
            saldo_usd = gan_usd - vales_usd
            saldo_ves = gan_ves - vales_ves
            
            liq_rows.append({
                "Mecanico": m,
                "Comisión USD ($)": round(gan_usd, 2),
                "Vales USD ($)": round(vales_usd, 2),
                "PAGO EN USD ($)": round(saldo_usd, 2),
                "Comisión VES (Bs)": round(gan_ves, 2),
                "Vales VES (Bs)": round(vales_ves, 2),
                "PAGO EN VES (Bs)": round(saldo_ves, 2)
            })
        
        df_liq = pd.DataFrame(liq_rows)
        
        # Totales globales
        tot_usd_pagar = df_liq["PAGO EN USD ($)"].sum() if not df_liq.empty else 0.0
        tot_ves_pagar = df_liq["PAGO EN VES (Bs)"].sum() if not df_liq.empty else 0.0
        
        m1, m2, m3 = st.columns(3)
        m1.metric("💵 Total Pendiente a Pagar en Dólares", f"${tot_usd_pagar:.2f}")
        m2.metric("🇻🇪 Total Pendiente a Pagar en Bolívares", f"{tot_ves_pagar:,.2f} Bs")
        m3.metric("📌 Tasa de Cambio Activa", f"{tasa_actual:.2f} VES/USD")
        
        st.markdown("---")
        st.subheader("📋 Tabla General de Liquidación")
        
        df_liq_display = df_liq.rename(columns={"Mecanico": "Mecánico"})
        st.dataframe(df_liq_display, use_container_width=True, hide_index=True)
        
        st.markdown("---")
        st.subheader("🧾 Recibo de Pago por Mecánico")
        
        mec_sel = st.selectbox("Seleccionar Mecánico para Liquidar:", lista_mecanicos)
        
        fila_mec = df_liq[df_liq["Mecanico"] == mec_sel]
        if not fila_mec.empty:
            p_usd = fila_mec["PAGO EN USD ($)"].values[0]
            p_ves = fila_mec["PAGO EN VES (Bs)"].values[0]
            
            c_rec1, c_rec2 = st.columns(2)
            
            with c_rec1:
                if p_usd < 0:
                    st.error(f"### 🔴 Le debe al dueño: **${abs(p_usd):.2f} USD**")
                else:
                    st.info(f"### 💵 Pago en Dólares: **${p_usd:.2f} USD**")
                st.caption(f"Comisiones: ${fila_mec['Comisión USD ($)'].values[0]:.2f} - Vales: ${fila_mec['Vales USD ($)'].values[0]:.2f}")
                
            with c_rec2:
                if p_ves < 0:
                    st.error(f"### 🔴 Le debe al dueño: **{abs(p_ves):,.2f} Bs**")
                else:
                    st.success(f"### 🇻🇪 Pago en Bolívares: **{p_ves:,.2f} Bs**")
                st.caption(f"Comisiones: {fila_mec['Comisión VES (Bs)'].values[0]:,.2f} Bs - Vales: {fila_mec['Vales VES (Bs)'].values[0]:,.2f} Bs")

            if p_ves != 0 or p_usd != 0:
                with st.expander("🔄 Ver conversión unificada de moneda"):
                    total_todo_usd = p_usd + (p_ves / tasa_actual if tasa_actual > 0 else 0.0)
                    total_todo_ves = (p_usd * tasa_actual) + p_ves
                    
                    if total_todo_usd < 0:
                        st.write(f"* **Estado Unificado (USD):** 🔴 Le debe al dueño **${abs(total_todo_usd):.2f} USD**")
                    else:
                        st.write(f"* **Si pagas todo en USD:** ${total_todo_usd:.2f} USD")
                        
                    if total_todo_ves < 0:
                        st.write(f"* **Estado Unificado (VES):** 🔴 Le debe al dueño **{abs(total_todo_ves):,.2f} Bs**")
                    else:
                        st.write(f"* **Si pagas todo en VES:** {total_todo_ves:,.2f} Bs")
