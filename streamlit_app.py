import streamlit as st
import gspread
from gspread.cell import Cell
from google.oauth2.service_account import Credentials
import pandas as pd
import datetime
import unicodedata
import urllib.parse

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
# GESTIÓN DE MECÁNICOS
# ---------------------------------------------------------
def obtener_ws_mecanicos():
    try:
        ws = sheet.worksheet("MECANICOS")
    except gspread.exceptions.WorksheetNotFound:
        ws = sheet.add_worksheet(title="MECANICOS", rows=50, cols=2)
        ws.append_row(["Nombre"])
        ws.append_rows([["Carlos Pérez"], ["Pedro Gómez"], ["Luis Rodríguez"]])
    return ws

def cargar_mecanicos():
    try:
        ws = obtener_ws_mecanicos()
        filas = ws.get_all_values()
        if len(filas) > 1:
            mecanicos = [f[0].strip() for f in filas[1:] if len(f) > 0 and f[0].strip()]
            if mecanicos:
                return sorted(list(set(mecanicos)))
    except Exception:
        pass
    return ["Carlos Pérez", "Pedro Gómez", "Luis Rodríguez"]

def agregar_mecanico(nombre):
    nombre = nombre.strip()
    if not nombre:
        return False, "El nombre no puede estar vacío."
    ws = obtener_ws_mecanicos()
    mecanicos_actuales = cargar_mecanicos()
    if nombre.lower() in [m.lower() for m in mecanicos_actuales]:
        return False, "El mecánico ya existe en la lista."
    ws.append_row([nombre])
    return True, f"Mecánico '{nombre}' agregado exitosamente."

def eliminar_mecanico(nombre):
    ws = obtener_ws_mecanicos()
    filas = ws.get_all_values()
    fila_a_borrar = None
    for idx, r in enumerate(filas):
        if idx > 0 and len(r) > 0 and r[0].strip().lower() == nombre.strip().lower():
            fila_a_borrar = idx + 1
            break
    if fila_a_borrar:
        ws.delete_rows(fila_a_borrar)
        return True, f"Mecánico '{nombre}' eliminado exitosamente."
    return False, "No se encontró el mecánico a eliminar."

# ---------------------------------------------------------
# GESTIÓN DE CONFIGURACIÓN Y TELÉFONO
# ---------------------------------------------------------
def obtener_ws_config():
    try:
        ws = sheet.worksheet("CONFIGURACION")
    except gspread.exceptions.WorksheetNotFound:
        ws = sheet.add_worksheet(title="CONFIGURACION", rows=10, cols=2)
        ws.append_row(["Clave", "Valor"])
        ws.append_row(["Tasa_Dia", "40.80"])
        ws.append_row(["Telefono_Dueno", "584120000000"])
    return ws

def cargar_config_guardada(clave, valor_defecto):
    try:
        ws = obtener_ws_config()
        datos = ws.get_all_records()
        for fila in datos:
            if str(fila.get("Clave")).strip() == clave:
                val = str(fila.get("Valor")).strip()
                return val if val else valor_defecto
    except Exception:
        pass
    return valor_defecto

def guardar_config_clave(clave, valor):
    try:
        ws = obtener_ws_config()
        filas = ws.get_all_values()
        fila_idx = None
        for idx, row in enumerate(filas):
            if len(row) > 0 and row[0].strip() == clave:
                fila_idx = idx + 1
                break
        if fila_idx:
            ws.update_cell(fila_idx, 2, str(valor))
        else:
            ws.append_row([clave, str(valor)])
    except Exception as e:
        st.error(f"Error guardando configuración: {e}")

def obtener_tasa_actual():
    if "tasa_cambio" not in st.session_state or st.session_state.get("tasa_cambio") is None:
        val_str = cargar_config_guardada("Tasa_Dia", "40.80")
        try:
            st.session_state["tasa_cambio"] = float(val_str.replace(",", "."))
        except ValueError:
            st.session_state["tasa_cambio"] = 40.80
    try:
        return float(st.session_state["tasa_cambio"])
    except (ValueError, TypeError):
        st.session_state["tasa_cambio"] = 40.80
        return 40.80

def obtener_telefono_dueno():
    if "telefono_dueno" not in st.session_state:
        st.session_state["telefono_dueno"] = cargar_config_guardada("Telefono_Dueno", "584120000000")
    return st.session_state["telefono_dueno"]

_ = obtener_tasa_actual()
_ = obtener_telefono_dueno()
lista_mecanicos = cargar_mecanicos()

# ---------------------------------------------------------
# COLUMNAS OFICIALES Y UTILIDADES
# ---------------------------------------------------------
COLUMNAS_PROD = [
    "Orden", "Fecha", "Mecanico", "Moto", "Trabajo", 
    "Moneda", "Monto_Cobrado", "Tasa", "Mano_Obra", "Comision_Pct", "Ganancia", "Estado"
]
COLUMNAS_VALES = [
    "Vale", "Fecha", "Mecanico", "Concepto", "Monto", "Moneda", "Tasa", "Total", "Forma_Pago", "Estado"
]
COLUMNAS_CIERRES = [
    "ID_Cierre", "Fecha_Cierre", "Mecanico", "Comision_USD", "Vales_USD", "Pago_USD", "Comision_VES", "Vales_VES", "Pago_VES", "Tasa"
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

def limpiar_telefono(tel):
    return "".join([c for c in str(tel) if c.isdigit()])

# ---------------------------------------------------------
# CARGA Y REPARACIÓN AUTOMÁTICA DE TABLAS
# ---------------------------------------------------------
def cargar_y_reparar_hoja(nombre_hoja, columnas_oficiales):
    try:
        ws = sheet.worksheet(nombre_hoja)
    except Exception:
        try:
            ws = sheet.add_worksheet(title=nombre_hoja, rows=100, cols=len(columnas_oficiales))
            ws.append_row(columnas_oficiales)
        except Exception:
            ws = sheet.worksheet(nombre_hoja)

    filas = ws.get_all_values()

    if not filas or len(filas) == 0:
        ws.append_row(columnas_oficiales)
        return ws, pd.DataFrame(columns=columnas_oficiales)

    encabezados_actuales = [str(c).strip() for c in filas[0]]
    
    if len(encabezados_actuales) != len(columnas_oficiales) or encabezados_actuales != columnas_oficiales:
        try:
            ws.update(range_name='A1', values=[columnas_oficiales])
        except Exception:
            pass

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
ws_cierres, df_cierres = cargar_y_reparar_hoja("CIERRES", COLUMNAS_CIERRES)

# ---------------------------------------------------------
# PROCESAMIENTO NATIVO EN MONEDA ORIGINAL (SIN CONVERTIR)
# ---------------------------------------------------------
if not df_prod.empty:
    df_prod["Monto_Cobrado_Num"] = df_prod["Monto_Cobrado"].apply(a_numero)
    df_prod["Tasa_Num"] = df_prod["Tasa"].apply(a_numero)
    
    col_mo = "Mano_Obra" if "Mano_Obra" in df_prod.columns else "Mano_Obra_USD"
    col_gan = "Ganancia" if "Ganancia" in df_prod.columns else "Ganancia_USD"
    
    df_prod["Mano_Obra_Num"] = df_prod[col_mo].apply(a_numero)
    df_prod["Ganancia_Num"] = df_prod[col_gan].apply(a_numero)
    df_prod["Comision_Pct_Num"] = df_prod["Comision_Pct"].apply(a_numero)
    
    if "Estado" not in df_prod.columns:
        df_prod["Estado"] = "⏳ Pendiente"
    df_prod["Estado"] = df_prod["Estado"].apply(lambda x: x if str(x).strip() else "⏳ Pendiente")

    def calcular_mo(row):
        if row["Mano_Obra_Num"] > 0:
            return round(row["Mano_Obra_Num"], 2)
        return round(row["Monto_Cobrado_Num"], 2)

    def calcular_ganancia(row):
        if row["Ganancia_Num"] > 0:
            return round(row["Ganancia_Num"], 2)
        return round(row["Mano_Obra"] * (row["Comision_Pct_Num"] / 100.0), 2)

    df_prod["Mano_Obra"] = df_prod.apply(calcular_mo, axis=1)
    df_prod["Ganancia"] = df_prod.apply(calcular_ganancia, axis=1)
    df_prod["Mecanico_Clean"] = df_prod["Mecanico"].apply(quitar_acentos_y_espacios)
else:
    df_prod["Mano_Obra"] = 0.0
    df_prod["Ganancia"] = 0.0
    df_prod["Mecanico_Clean"] = ""
    df_prod["Estado"] = "⏳ Pendiente"

if not df_vales.empty:
    df_vales["Monto_Num"] = df_vales["Monto"].apply(a_numero)
    col_tot_v = "Total" if "Total" in df_vales.columns else "Total_USD"
    df_vales["Total_Num"] = df_vales[col_tot_v].apply(a_numero)
    
    if "Estado" not in df_vales.columns:
        df_vales["Estado"] = "⏳ Pendiente"
    df_vales["Estado"] = df_vales["Estado"].apply(lambda x: x if str(x).strip() else "⏳ Pendiente")

    def calcular_vale(row):
        if row["Total_Num"] > 0:
            return round(row["Total_Num"], 2)
        return round(row["Monto_Num"], 2)

    df_vales["Total"] = df_vales.apply(calcular_vale, axis=1)
    df_vales["Mecanico_Clean"] = df_vales["Mecanico"].apply(quitar_acentos_y_espacios)
else:
    df_vales["Total"] = 0.0
    df_vales["Mecanico_Clean"] = ""
    df_vales["Estado"] = "⏳ Pendiente"

# ---------------------------------------------------------
# CONTROL DE ACCESO
# ---------------------------------------------------------
CLAVE_ADMIN = st.secrets.get("CLAVE_ADMIN", "1234")

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
tel_dueno = obtener_telefono_dueno()

if es_admin:
    st.sidebar.markdown("---")
    st.sidebar.title("⚙️ Configuración Taller")

    with st.sidebar.form("form_config"):
        tasa_input = st.number_input(
            "Tasa del Día (VES/USD):",
            value=tasa_actual,
            min_value=1.0, step=0.10, format="%.2f"
        )
        tel_input = st.text_input(
            "WhatsApp del Dueño (ej: 584121234567):",
            value=tel_dueno
        )
        btn_guardar_cfg = st.form_submit_button("💾 Guardar Configuración")

        if btn_guardar_cfg:
            tel_limpio = limpiar_telefono(tel_input)
            guardar_config_clave("Tasa_Dia", round(tasa_input, 2))
            guardar_config_clave("Telefono_Dueno", tel_limpio)
            
            st.session_state["tasa_cambio"] = tasa_input
            st.session_state["telefono_dueno"] = tel_limpio
            st.sidebar.success("✅ Configuración actualizada")
            st.rerun()

    st.sidebar.markdown("---")
    st.sidebar.title("👥 Gestión de Mecánicos")

    with st.sidebar.expander("➕ Registrar Nuevo Mecánico"):
        with st.form("form_add_mec", clear_on_submit=True):
            nuevo_nombre = st.text_input("Nombre y Apellido:")
            btn_add_mec = st.form_submit_button("➕ Agregar Mecánico")
            if btn_add_mec:
                exito, msg = agregar_mecanico(nuevo_nombre)
                if exito:
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)

    with st.sidebar.expander("🗑️ Eliminar Mecánico"):
        if lista_mecanicos:
            with st.form("form_del_mec", clear_on_submit=True):
                mec_eliminar = st.selectbox("Seleccionar para eliminar:", lista_mecanicos)
                btn_del_mec = st.form_submit_button("🗑️ Eliminar Mecánico")
                if btn_del_mec:
                    exito, msg = eliminar_mecanico(mec_eliminar)
                    if exito:
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)
        else:
            st.info("No hay mecánicos registrados.")

    st.sidebar.info(f"📌 **Tasa Activa del Día:** {obtener_tasa_actual():.2f} VES/USD\n\n📲 **WhatsApp Dueño:** +{obtener_telefono_dueno()}")

# ---------------------------------------------------------
# FUNCIONES AUXILIARES PARA CIERRES
# ---------------------------------------------------------
def procesar_liquidacion_mecanico(mecanico, gan_usd, vales_usd, pago_usd, gan_ves, vales_ves, pago_ves, tasa):
    m_norm = quitar_acentos_y_espacios(mecanico)
    col_est_prod = COLUMNAS_PROD.index("Estado") + 1
    col_est_vales = COLUMNAS_VALES.index("Estado") + 1
    
    celdas_prod_actualizar = []
    if not df_prod.empty:
        for idx, r in df_prod.iterrows():
            if r["Mecanico_Clean"] == m_norm and str(r["Estado"]).strip() != "🔒 Liquidado":
                row_sheet = idx + 2
                celdas_prod_actualizar.append(Cell(row_sheet, col_est_prod, "🔒 Liquidado"))
    if celdas_prod_actualizar:
        ws_prod.update_cells(celdas_prod_actualizar)

    celdas_vales_actualizar = []
    if not df_vales.empty:
        for idx, r in df_vales.iterrows():
            if r["Mecanico_Clean"] == m_norm and str(r["Estado"]).strip() != "🔒 Liquidado":
                row_sheet = idx + 2
                celdas_vales_actualizar.append(Cell(row_sheet, col_est_vales, "🔒 Liquidado"))
    if celdas_vales_actualizar:
        ws_vales.update_cells(celdas_vales_actualizar)
                
    id_cierre = f"C-{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"
    fecha_cierre = str(datetime.date.today())
    
    fila_cierre = [
        id_cierre,
        fecha_cierre,
        mecanico,
        str(round(gan_usd, 2)),
        str(round(vales_usd, 2)),
        str(round(pago_usd, 2)),
        str(round(gan_ves, 2)),
        str(round(vales_ves, 2)),
        str(round(pago_ves, 2)),
        str(round(tasa, 2))
    ]
    ws_cierres.append_row(fila_cierre, value_input_option="USER_ENTERED")

# ---------------------------------------------------------
# INTERFAZ PRINCIPAL
# ---------------------------------------------------------
st.title("🏍️ Control de Taller")

def mostrar_formulario_produccion(es_modo_admin=False):
    st.subheader("Registrar Trabajo Realizado")
    t_actual = obtener_tasa_actual()
    
    if "wa_url_exito" in st.session_state and st.session_state["wa_url_exito"]:
        st.success(f"✅ Trabajo registrado con éxito. ¡Envía el comprobante al dueño por WhatsApp!")
        st.link_button(
            "📲 CLICK AQUÍ PARA ENVIAR POR WHATSAPP AL DUEÑO",
            st.session_state["wa_url_exito"],
            type="primary",
            use_container_width=True
        )
        if st.button("❌ Cerrar mensaje de WhatsApp"):
            del st.session_state["wa_url_exito"]
            st.rerun()
        st.markdown("---")

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
            tasa_p = c_tasa.number_input("Tasa Referencial", value=t_actual)
            comision_pct = c_com.slider("% Comisión Mecánico", min_value=0, max_value=100, value=50)
        else:
            c_mon, c_monto = st.columns(2)
            moneda_p = c_mon.selectbox("Moneda de Cobro", ["USD", "VES"])
            monto_cobrado = c_monto.number_input("Monto Mano de Obra", min_value=0.0, step=5.0)
            tasa_p = t_actual
            comision_pct = 50
        
        btn_prod = st.form_submit_button("💾 Guardar Trabajo")
        
        if btn_prod:
            mano_obra = monto_cobrado
            ganancia = mano_obra * (comision_pct / 100.0)
            
            nueva_fila = [
                orden,
                str(fecha_p),
                mecanico_p,
                moto,
                trabajo,
                moneda_p,
                str(monto_cobrado),
                str(tasa_p),
                str(round(mano_obra, 2)),
                str(round(comision_pct, 2)),
                str(round(ganancia, 2)),
                "⏳ Pendiente"
            ]
            
            ws_prod.append_row(nueva_fila, value_input_option="USER_ENTERED")
            
            msg_wa = (
                f"🏍️ *NUEVO TRABAJO REGISTRADO*\n\n"
                f"📌 *Orden:* {orden}\n"
                f"👤 *Mecánico:* {mecanico_p}\n"
                f"🏍️ *Moto:* {moto}\n"
                f"🛠️ *Trabajo:* {trabajo}\n"
                f"💰 *Monto:* {monto_cobrado} {moneda_p}\n"
                f"📅 *Fecha:* {fecha_p}\n"
                f"⏳ *Estado:* Pendiente de aprobación"
            )
            msg_encoded = urllib.parse.quote(msg_wa)
            num_dueno = obtener_telefono_dueno()
            wa_url = f"https://api.whatsapp.com/send?phone={num_dueno}&text={msg_encoded}"
            
            st.session_state["wa_url_exito"] = wa_url
            st.rerun()

    if es_modo_admin and not df_prod.empty:
        st.markdown("---")
        st.subheader("🔍 Verificación Rápida de Trabajos (Dueño)")
        
        df_pendientes = df_prod[df_prod["Estado"] == "⏳ Pendiente"]
        
        if not df_pendientes.empty:
            st.warning(f"⚠️ Tienes **{len(df_pendientes)}** trabajo(s) pendiente(s) por verificar.")
            
            col_todo, _ = st.columns([1, 3])
            if col_todo.button("✅ Verificar TODOS los Pendientes"):
                col_estado_idx = COLUMNAS_PROD.index("Estado") + 1
                celdas_verificar = [
                    Cell(idx + 2, col_estado_idx, "✅ Verificado")
                    for idx in df_pendientes.index
                ]
                if celdas_verificar:
                    ws_prod.update_cells(celdas_verificar)
                st.success("✅ ¡Todos los trabajos han sido verificados!")
                st.rerun()
                
            st.markdown("##### Trabajos Por Aprobar:")
            for idx, row in df_pendientes.iterrows():
                with st.container():
                    col_info, col_act = st.columns([4, 1])
                    with col_info:
                        st.write(f"**Orden:** {row['Orden']} | **Fecha:** {row['Fecha']} | **Mecánico:** {row['Mecanico']}")
                        st.caption(f"🏍️ **Moto:** {row['Moto']} | 🛠️ **Trabajo:** {row['Trabajo']} | 💰 **Monto:** {row['Monto_Cobrado']} {row['Moneda']}")
                    with col_act:
                        if st.button("✅ Aprobar", key=f"v_btn_{idx}_{row['Orden']}"):
                            col_estado_idx = COLUMNAS_PROD.index("Estado") + 1
                            row_sheet = idx + 2
                            ws_prod.update_cell(row_sheet, col_estado_idx, "✅ Verificado")
                            st.success(f"Trabajo {row['Orden']} verificado.")
                            st.rerun()
                    st.markdown("---")
        else:
            st.success("🎉 ¡Todos los trabajos registrados están verificados!")

    st.markdown("---")
    st.subheader("📋 Registro Completo de Trabajos")
    
    if es_modo_admin:
        cols_mostrar = [c for c in COLUMNAS_PROD if c in df_prod.columns]
    else:
        cols_mostrar = ["Orden", "Fecha", "Mecanico", "Moto", "Trabajo", "Moneda", "Monto_Cobrado", "Estado"]
        
    st.dataframe(df_prod[cols_mostrar], use_container_width=True, hide_index=True)


if not es_admin:
    st.info("💡 Modo Trabajador: Registra tus trabajos diarios. Quedarán en revisión hasta que el dueño los verifique.")
    mostrar_formulario_produccion(es_modo_admin=False)

else:
    tab_dash, tab_prod, tab_vales, tab_liq, tab_hist_cierres = st.tabs([
        "📊 Dashboard", "🛠️ Producción", "💵 Vales", "🧮 Liquidación Semana Activa", "🔒 Historial Cierres"
    ])

    with tab_dash:
        df_prod_activa = df_prod[df_prod["Estado"] != "🔒 Liquidado"] if not df_prod.empty else pd.DataFrame()
        df_vales_activa = df_vales[df_vales["Estado"] != "🔒 Liquidado"] if not df_vales.empty else pd.DataFrame()

        # Separación USD y VES
        prod_usd = df_prod_activa[df_prod_activa["Moneda"] == "USD"] if not df_prod_activa.empty else pd.DataFrame()
        prod_ves = df_prod_activa[df_prod_activa["Moneda"] == "VES"] if not df_prod_activa.empty else pd.DataFrame()
        
        vales_usd = df_vales_activa[df_vales_activa["Moneda"] == "USD"] if not df_vales_activa.empty else pd.DataFrame()
        vales_ves = df_vales_activa[df_vales_activa["Moneda"] == "VES"] if not df_vales_activa.empty else pd.DataFrame()

        mo_usd = prod_usd["Mano_Obra"].sum() if not prod_usd.empty else 0.0
        com_usd = prod_usd["Ganancia"].sum() if not prod_usd.empty else 0.0
        val_usd = vales_usd["Total"].sum() if not vales_usd.empty else 0.0

        mo_ves = prod_ves["Mano_Obra"].sum() if not prod_ves.empty else 0.0
        com_ves = prod_ves["Ganancia"].sum() if not prod_ves.empty else 0.0
        val_ves = vales_ves["Total"].sum() if not vales_ves.empty else 0.0

        st.subheader("📊 Resumen de Semana Activa (Sin Liquidar)")
        
        st.markdown("#### 💵 Totales en Dólares (USD)")
        c1, c2, c3 = st.columns(3)
        c1.metric("Mano de Obra (USD)", f"${mo_usd:.2f}")
        c2.metric("Comisiones Mecánicos (USD)", f"${com_usd:.2f}")
        c3.metric("Vales Entregados (USD)", f"${val_usd:.2f}")

        st.markdown("#### 🇻🇪 Totales en Bolívares (VES)")
        c4, c5, c6 = st.columns(3)
        c4.metric("Mano de Obra (VES)", f"{mo_ves:,.2f} Bs")
        c5.metric("Comisiones Mecánicos (VES)", f"{com_ves:,.2f} Bs")
        c6.metric("Vales Entregados (VES)", f"{val_ves:,.2f} Bs")

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
            tasa_v = v7.number_input("Tasa Referencial", value=t_actual)
            forma_pago = st.selectbox("Forma Pago", ["Efectivo USD", "Efectivo VES", "Pago Móvil", "Transferencia"])
            
            btn_vale = st.form_submit_button("💵 Entregar Vale")
            
            if btn_vale:
                total_monto = monto
                nuevo_vale = [
                    num_vale,
                    str(fecha_v),
                    mecanico_v,
                    concepto,
                    str(monto),
                    moneda,
                    str(tasa_v),
                    str(round(total_monto, 2)),
                    forma_pago,
                    "⏳ Pendiente"
                ]
                ws_vales.append_row(nuevo_vale, value_input_option="USER_ENTERED")
                st.success("✅ Vale registrado en Google Sheets.")
                st.rerun()

        st.markdown("---")
        cols_mostrar_vales = [c for c in COLUMNAS_VALES if c in df_vales.columns]
        st.dataframe(df_vales[cols_mostrar_vales], use_container_width=True, hide_index=True)

    with tab_liq:
        st.subheader("🧮 Resumen de Liquidación Pendiente (Semana Activa)")
        
        df_prod_pend = df_prod[df_prod["Estado"] != "🔒 Liquidado"] if not df_prod.empty else pd.DataFrame()
        df_vales_pend = df_vales[df_vales["Estado"] != "🔒 Liquidado"] if not df_vales.empty else pd.DataFrame()
        
        liq_rows = []
        tasa_actual = obtener_tasa_actual()
        
        for m in lista_mecanicos:
            m_norm = quitar_acentos_y_espacios(m)
            
            # Producción
            if not df_prod_pend.empty and "Mecanico_Clean" in df_prod_pend.columns:
                df_m_prod = df_prod_pend[df_prod_pend["Mecanico_Clean"] == m_norm]
                gan_usd = df_m_prod[df_m_prod["Moneda"] == "USD"]["Ganancia"].sum()
                gan_ves = df_m_prod[df_m_prod["Moneda"] == "VES"]["Ganancia"].sum()
            else:
                gan_usd, gan_ves = 0.0, 0.0
                
            # Vales
            if not df_vales_pend.empty and "Mecanico_Clean" in df_vales_pend.columns:
                df_m_vales = df_vales_pend[df_vales_pend["Mecanico_Clean"] == m_norm]
                vales_usd = df_m_vales[df_m_vales["Moneda"] == "USD"]["Total"].sum()
                vales_ves = df_m_vales[df_m_vales["Moneda"] == "VES"]["Total"].sum()
            else:
                vales_usd, vales_ves = 0.0, 0.0
                
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
        
        tot_usd_pagar = df_liq["PAGO EN USD ($)"].sum() if not df_liq.empty else 0.0
        tot_ves_pagar = df_liq["PAGO EN VES (Bs)"].sum() if not df_liq.empty else 0.0
        
        m1, m2 = st.columns(2)
        m1.metric("💵 Balance Neto Pendiente en USD", f"${tot_usd_pagar:.2f}")
        m2.metric("🇻🇪 Balance Neto Pendiente en VES", f"{tot_ves_pagar:,.2f} Bs")
        
        st.markdown("---")
        st.subheader("📋 Tabla General de Cierre Semanal")
        st.dataframe(df_liq.rename(columns={"Mecanico": "Mecánico"}), use_container_width=True, hide_index=True)
        
        st.markdown("---")
        
        col_cierre_gen, _ = st.columns([2, 2])
        with col_cierre_gen:
            if st.button("🔒 PROCESAR CIERRE SEMANAL GENERAL (LIQUIDAR A TODOS)", type="primary", use_container_width=True):
                with st.spinner("Procesando cierre semanal y guardando historial..."):
                    for _, row_l in df_liq.iterrows():
                        m_nombre = row_l["Mecanico"]
                        procesar_liquidacion_mecanico(
                            mecanico=m_nombre,
                            gan_usd=row_l["Comisión USD ($)"],
                            vales_usd=row_l["Vales USD ($)"],
                            pago_usd=row_l["PAGO EN USD ($)"],
                            gan_ves=row_l["Comisión VES (Bs)"],
                            vales_ves=row_l["Vales VES (Bs)"],
                            pago_ves=row_l["PAGO EN VES (Bs)"],
                            tasa=tasa_actual
                        )
                st.balloons()
                st.success("🎉 ¡Cierre semanal general completado con éxito!")
                st.rerun()

        st.markdown("---")
        st.subheader("🧾 Liquidación Individual por Mecánico")
        
        if lista_mecanicos:
            mec_sel = st.selectbox("Seleccionar Mecánico para Liquidar:", lista_mecanicos)
            
            fila_mec = df_liq[df_liq["Mecanico"] == mec_sel]
            if not fila_mec.empty:
                p_usd = fila_mec["PAGO EN USD ($)"].values[0]
                p_ves = fila_mec["PAGO EN VES (Bs)"].values[0]
                c_usd = fila_mec["Comisión USD ($)"].values[0]
                v_usd = fila_mec["Vales USD ($)"].values[0]
                c_ves = fila_mec["Comisión VES (Bs)"].values[0]
                v_ves = fila_mec["Vales VES (Bs)"].values[0]
                
                c_rec1, c_rec2 = st.columns(2)
                
                with c_rec1:
                    if p_usd < 0:
                        st.error(f"### 🔴 Debe en USD: **${abs(p_usd):.2f} USD**")
                    else:
                        st.info(f"### 💵 Pago en USD: **${p_usd:.2f} USD**")
                    st.caption(f"Comisiones: ${c_usd:.2f} - Vales: ${v_usd:.2f}")
                    
                with c_rec2:
                    if p_ves < 0:
                        st.error(f"### 🔴 Debe en VES: **{abs(p_ves):,.2f} Bs**")
                    else:
                        st.success(f"### 🇻🇪 Pago en VES: **{p_ves:,.2f} Bs**")
                    st.caption(f"Comisiones: {c_ves:,.2f} Bs - Vales: {v_ves:,.2f} Bs")

                if st.button(f"🔒 LIQUIDAR Y CERRAR CUENTA DE {mec_sel.upper()}", type="secondary"):
                    with st.spinner(f"Cerrando cuenta de {mec_sel}..."):
                        procesar_liquidacion_mecanico(
                            mecanico=mec_sel,
                            gan_usd=c_usd,
                            vales_usd=v_usd,
                            pago_usd=p_usd,
                            gan_ves=c_ves,
                            vales_ves=v_ves,
                            pago_ves=p_ves,
                            tasa=tasa_actual
                        )
                    st.success(f"✅ Se ha completado la liquidación de {mec_sel}.")
                    st.rerun()

    with tab_hist_cierres:
        st.subheader("🔒 Historial de Cierres Semanales")
        
        if not df_cierres.empty:
            st.dataframe(df_cierres, use_container_width=True, hide_index=True)
        else:
            st.info("Aún no se han procesado cierres semanales.")
