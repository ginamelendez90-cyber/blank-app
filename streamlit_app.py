import streamlit as st
import pandas as pd
import datetime
import io

# Configuración inicial de la página
st.set_page_config(
    page_title="Control Taller de Motos",
    page_icon="🏍️",
    layout="wide"
)

# ---------------------------------------------------------
# ESTADOS DE SESIÓN (Persistencia de datos en la sesión)
# ---------------------------------------------------------
if "tasa_cambio" not in st.session_state:
    st.session_state.tasa_cambio = 40.80

if "mecanicos" not in st.session_state:
    st.session_state.mecanicos = ["Carlos Pérez", "Pedro Gómez", "Luis Rodríguez"]

if "produccion" not in st.session_state:
    st.session_state.produccion = pd.DataFrame([
        {
            "Orden": "#101", 
            "Fecha": datetime.date(2026, 7, 25), 
            "Mecanico": "Carlos Pérez", 
            "Moto": "Bera SBR 150", 
            "Trabajo": "Mantenimiento General", 
            "Mano_Obra_USD": 30.00, 
            "Comision_Pct": 50, 
            "Ganancia_USD": 15.00
        },
        {
            "Orden": "#102", 
            "Fecha": datetime.date(2026, 7, 26), 
            "Mecanico": "Pedro Gómez", 
            "Moto": "Empire Keeway 150", 
            "Trabajo": "Cambio de Anillos", 
            "Mano_Obra_USD": 60.00, 
            "Comision_Pct": 40, 
            "Ganancia_USD": 24.00
        }
    ])

if "vales" not in st.session_state:
    st.session_state.vales = pd.DataFrame([
        {
            "Vale": "V-01", 
            "Fecha": datetime.date(2026, 7, 25), 
            "Mecanico": "Carlos Pérez", 
            "Concepto": "Adelanto efectivo", 
            "Monto": 10.00, 
            "Moneda": "USD", 
            "Tasa": 40.20, 
            "Total_USD": 10.00, 
            "Forma_Pago": "Efectivo USD"
        },
        {
            "Vale": "V-02", 
            "Fecha": datetime.date(2026, 7, 27), 
            "Mecanico": "Pedro Gómez", 
            "Concepto": "Pago Móvil repuesto", 
            "Monto": 807.00, 
            "Moneda": "VES", 
            "Tasa": 40.35, 
            "Total_USD": 20.00, 
            "Forma_Pago": "Pago Móvil"
        }
    ])

# ---------------------------------------------------------
# BARRA LATERAL (CONFIGURACIÓN)
# ---------------------------------------------------------
st.sidebar.title("⚙️ Configuración Taller")

st.session_state.tasa_cambio = st.sidebar.number_input(
    "Tasa de Cambio del Día (VES / USD):",
    value=float(st.session_state.tasa_cambio),
    min_value=1.0,
    step=0.10,
    format="%.2f"
)

st.sidebar.markdown("---")
st.sidebar.subheader("👨‍🔧 Gestión de Mecánicos")
nuevo_mecanico = st.sidebar.text_input("Nombre del Nuevo Mecánico:")
if st.sidebar.button("➕ Agregar Mecánico"):
    if nuevo_mecanico and nuevo_mecanico not in st.session_state.mecanicos:
        st.session_state.mecanicos.append(nuevo_mecanico)
        st.sidebar.success(f"¡{nuevo_mecanico} agregado exitosamente!")

# ---------------------------------------------------------
# PANEL PRINCIPAL
# ---------------------------------------------------------
st.title("🏍️ Sistema de Control Financiero de Taller")
st.caption(f"Tasa de cambio activa: **1 USD = {st.session_state.tasa_cambio:.2f} VES**")

tab_dash, tab_prod, tab_vales, tab_liq = st.tabs([
    "📊 Dashboard", 
    "🛠️ Registro de Producción", 
    "💵 Vales y Adelantos", 
    "🧮 Cierre y Liquidación"
])

# ---------------------------------------------------------
# TAB 1: DASHBOARD
# ---------------------------------------------------------
with tab_dash:
    st.subheader("Resumen Global del Taller")
    
    total_mo = st.session_state.produccion["Mano_Obra_USD"].sum() if not st.session_state.produccion.empty else 0.0
    total_com = st.session_state.produccion["Ganancia_USD"].sum() if not st.session_state.produccion.empty else 0.0
    total_val = st.session_state.vales["Total_USD"].sum() if not st.session_state.vales.empty else 0.0
    neto_pagar = total_com - total_val
    
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Facturado (M.O)", f"${total_mo:.2f}")
    c2.metric("Comisiones Ganadas", f"${total_com:.2f}")
    c3.metric("Vales Entregados", f"${total_val:.2f}", delta=f"-${total_val:.2f}", delta_color="inverse")
    c4.metric("Neto por Pagar en Nómina", f"${neto_pagar:.2f}")

    st.markdown("---")
    st.markdown("### 💡 Indicaciones")
    st.info("""
    * **Producción:** Registra las órdenes listadas y la comisión correspondiente por mano de obra.
    * **Vales:** Si entregas dinero en Bolívares (VES), la app calcula la equivalencia en USD automáticamente.
    * **Liquidación:** Revisa el saldo neto en dólares y bolívares listos para pagar al cierre de semana.
    """)

# ---------------------------------------------------------
# TAB 2: REGISTRO DE PRODUCCIÓN
# ---------------------------------------------------------
with tab_prod:
    st.subheader("Registrar Trabajo Realizado")
    
    with st.form("form_produccion", clear_on_submit=True):
        f1, f2, f3 = st.columns(3)
        orden = f1.text_input("N° Orden / Factura", value=f"#{len(st.session_state.produccion)+101}")
        fecha_p = f2.date_input("Fecha", datetime.date.today())
        mecanico_p = f3.selectbox("Mecánico", st.session_state.mecanicos)
        
        f4, f5, f6 = st.columns(3)
        moto = f4.text_input("Vehículo / Moto", placeholder="Ej: Bera SBR 150")
        trabajo = f5.text_input("Descripción del Trabajo", placeholder="Ej: Cambio de frenos y entonación")
        mano_obra = f6.number_input("Cobro Mano de Obra ($)", min_value=0.0, step=5.0, format="%.2f")
        
        comision_pct = st.slider("% Comisión para el Mecánico", min_value=0, max_value=100, value=50, step=5)
        
        btn_guardar_prod = st.form_submit_button("💾 Registra Trabajo")
        
        if btn_guardar_prod:
            ganancia = mano_obra * (comision_pct / 100.0)
            nueva_fila = {
                "Orden": orden,
                "Fecha": fecha_p,
                "Mecanico": mecanico_p,
                "Moto": moto,
                "Trabajo": trabajo,
                "Mano_Obra_USD": mano_obra,
                "Comision_Pct": comision_pct,
                "Ganancia_USD": ganancia
            }
            st.session_state.produccion = pd.concat([st.session_state.produccion, pd.DataFrame([nueva_fila])], ignore_index=True)
            st.success("✅ Trabajo guardado correctamente.")

    st.markdown("---")
    st.subheader("📋 Registro de Trabajos Acumulados")
    st.dataframe(st.session_state.produccion, use_container_width=True)

# ---------------------------------------------------------
# TAB 3: VALES Y ADELANTOS
# ---------------------------------------------------------
with tab_vales:
    st.subheader("Registrar Entrega de Dinero / Vale")
    
    with st.form("form_vales", clear_on_submit=True):
        v1, v2, v3 = st.columns(3)
        num_vale = v1.text_input("N° Vale", value=f"V-0{len(st.session_state.vales)+1}")
        fecha_v = v2.date_input("Fecha de Vale", datetime.date.today())
        mecanico_v = v3.selectbox("Mecánico ", st.session_state.mecanicos, key="mec_vales")
        
        v4, v5, v6, v7 = st.columns(4)
        concepto = v4.text_input("Concepto / Motivo", placeholder="Ej: Pasajes / Adelanto")
        monto = v5.number_input("Monto Entregado", min_value=0.0, step=5.0, format="%.2f")
        moneda = v6.selectbox("Moneda Entregada", ["USD", "VES"])
        tasa_v = v7.number_input("Tasa Aplicada (VES/USD)", value=float(st.session_state.tasa_cambio), format="%.2f")
        
        forma_pago = st.selectbox("Forma de Entrega", ["Efectivo USD", "Efectivo VES", "Pago Móvil", "Zelle", "Transferencia"])
        
        btn_guardar_vale = st.form_submit_button("💵 Registrar Vale")
        
        if btn_guardar_vale:
            total_usd = monto if moneda == "USD" else (monto / tasa_v if tasa_v > 0 else 0.0)
            nuevo_vale = {
                "Vale": num_vale,
                "Fecha": fecha_v,
                "Mecanico": mecanico_v,
                "Concepto": concepto,
                "Monto": monto,
                "Moneda": moneda,
                "Tasa": tasa_v,
                "Total_USD": total_usd,
                "Forma_Pago": forma_pago
            }
            st.session_state.vales = pd.concat([st.session_state.vales, pd.DataFrame([nuevo_vale])], ignore_index=True)
            st.success("✅ Vale registrado correctamente.")

    st.markdown("---")
    st.subheader("📜 Historial de Vales")
    st.dataframe(st.session_state.vales, use_container_width=True)

# ---------------------------------------------------------
# TAB 4: LIQUIDACIÓN
# ---------------------------------------------------------
with tab_liq:
    st.subheader("🧮 Balance de Liquidación de Nómina")
    
    liq_rows = []
    for m in st.session_state.mecanicos:
        gen = st.session_state.produccion[st.session_state.produccion["Mecanico"] == m]["Ganancia_USD"].sum() if not st.session_state.produccion.empty else 0.0
        val = st.session_state.vales[st.session_state.vales["Mecanico"] == m]["Total_USD"].sum() if not st.session_state.vales.empty else 0.0
        neto = gen - val
        neto_ves = neto * st.session_state.tasa_cambio
        
        liq_rows.append({
            "Mecánico": m,
            "Ganancia Total ($)": gen,
            "Total Vales ($)": val,
            "Saldo Neto ($)": neto,
            "Tasa Cierre": st.session_state.tasa_cambio,
            "Saldo Neto (VES)": neto_ves
        })
    
    df_liq = pd.DataFrame(liq_rows)
    
    st.dataframe(
        df_liq.style.format({
            "Ganancia Total ($)": "${:.2f}",
            "Total Vales ($)": "${:.2f}",
            "Saldo Neto ($)": "${:.2f}",
            "Tasa Cierre": "{:.2f}",
            "Saldo Neto (VES)": "Bs. {:.2f}"
        }), 
        use_container_width=True
    )
    
    st.markdown("---")
    st.subheader("📊 Comparativo Producción vs. Vales")
    if not df_liq.empty:
        st.bar_chart(df_liq.set_index("Mecánico")[["Ganancia Total ($)", "Total Vales ($)"]])
        
    # Exportación a Excel
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        df_liq.to_excel(writer, sheet_name='LIQUIDACION', index=False)
        st.session_state.produccion.to_excel(writer, sheet_name='PRODUCCION', index=False)
        st.session_state.vales.to_excel(writer, sheet_name='VALES', index=False)
    
    st.download_button(
        label="📥 Descargar Liquidación Completa a Excel",
        data=buffer.getvalue(),
        file_name=f"Liquidacion_Taller_{datetime.date.today()}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
