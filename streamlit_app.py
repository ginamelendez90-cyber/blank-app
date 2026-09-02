import streamlit as st
import pandas as pd
from datetime import date

# Configuración de la página
st.set_page_config(page_title="Control de Cobranza Diario", layout="wide")
st.title("💸 Control Diario de Ruta")

# Inicializar el DataFrame en el session state para no perder los datos al recargar
if 'movimientos' not in st.session_state:
    st.session_state.movimientos = pd.DataFrame(
        columns=['Fecha', 'Tipo', 'Cliente_Concepto', 'Monto', 'Metodo']
    )

# --- 1. FORMULARIO DE INGRESO ---
st.header("1. Registrar Movimiento")
with st.form("registro_form", clear_on_submit=True):
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        tipo = st.selectbox("Tipo", ["Cobro", "Préstamo", "Gasto"])
    with col2:
        cliente_concepto = st.text_input("Cliente o Concepto")
    with col3:
        monto = st.number_input("Monto ($)", min_value=0.0, step=1.0)
    with col4:
        metodo = st.selectbox("Método de Pago", ["Efectivo", "Transferencia", "Pago Móvil"])

    submit = st.form_submit_button("Guardar Registro")

    if submit and cliente_concepto and monto > 0:
        nuevo_registro = pd.DataFrame({
            'Fecha': [date.today().strftime("%Y-%m-%d")],
            'Tipo': [tipo],
            'Cliente_Concepto': [cliente_concepto],
            'Monto': [monto],
            'Metodo': [metodo]
        })
        st.session_state.movimientos = pd.concat(
            [st.session_state.movimientos, nuevo_registro], 
            ignore_index=True
        )
        st.success("✅ Registro guardado exitosamente.")

# --- 2. DETALLE DE MOVIMIENTOS ---
st.header("2. Movimientos del Día")
st.dataframe(st.session_state.movimientos, use_container_width=True)

# --- 3. CUADRE DE CAJA (MÉTRICAS) ---
st.header("3. Cuadre de Caja Físico")
base_inicial = st.number_input("Efectivo de Salida (Base Inicial):", min_value=0.0, step=1.0)

# Cálculos: Filtramos el DataFrame para calcular solo lo que entra y sale en EFECTIVO
df = st.session_state.movimientos
df_efectivo = df[df['Metodo'] == 'Efectivo']

total_cobrado = df_efectivo[df_efectivo['Tipo'] == 'Cobro']['Monto'].sum()
total_prestamos = df_efectivo[df_efectivo['Tipo'] == 'Préstamo']['Monto'].sum()
total_gastos = df_efectivo[df_efectivo['Tipo'] == 'Gasto']['Monto'].sum()

efectivo_esperado = base_inicial + total_cobrado - total_prestamos - total_gastos

# Mostrar tarjetas de métricas
colA, colB, colC, colD, colE = st.columns(5)
colA.metric("Base", f"${base_inicial:.2f}")
colB.metric("Cobros (+)", f"${total_cobrado:.2f}")
colC.metric("Préstamos (-)", f"${total_prestamos:.2f}")
colD.metric("Gastos (-)", f"${total_gastos:.2f}")
colE.metric("EFECTIVO ESPERADO", f"${efectivo_esperado:.2f}")

# --- 4. EXPORTACIÓN PARA EXCEL ---
st.header("4. Reporte para Jefatura")
st.write("Genera el archivo CSV. Tu jefe puede abrirlo directamente en Excel sin tener que formatear nada.")

# Convertir el DataFrame actual a CSV
csv = df.to_csv(index=False).encode('utf-8')
st.download_button(
    label="📥 Descargar Reporte (CSV)",
    data=csv,
    file_name=f"reporte_cobranza_{date.today()}.csv",
    mime="text/csv",
)
