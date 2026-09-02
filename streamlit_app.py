import streamlit as st
import pandas as pd
from datetime import date

# Configuración
st.set_page_config(page_title="Control de Cobranza", layout="wide")
st.title("💸 Control Diario de Ruta")

# 1. Inicializar bases de datos en memoria (Session State)
if 'movimientos' not in st.session_state:
    st.session_state.movimientos = pd.DataFrame(
        columns=['Fecha', 'Tipo', 'Cliente_Concepto', 'Monto', 'Metodo']
    )
    
# Nueva base para clientes registrados
if 'clientes' not in st.session_state:
    st.session_state.clientes = [] # Inicia la lista vacía

# --- MENÚ LATERAL: DIRECTORIO DE CLIENTES ---
with st.sidebar:
    st.header("👥 Nuevo Cliente")
    st.write("Registra aquí los clientes para próximos créditos.")
    
    nuevo_cliente = st.text_input("Nombre completo")
    if st.button("Guardar Cliente"):
        if nuevo_cliente and nuevo_cliente not in st.session_state.clientes:
            st.session_state.clientes.append(nuevo_cliente)
            st.success(f"{nuevo_cliente} guardado.")
        elif nuevo_cliente in st.session_state.clientes:
            st.warning("El cliente ya existe en el directorio.")
            
    st.divider()
    st.subheader("Clientes Registrados")
    # Mostramos la lista actual para control visual
    if len(st.session_state.clientes) > 0:
        st.dataframe(pd.DataFrame(st.session_state.clientes, columns=["Nombre"]), hide_index=True)
    else:
        st.info("No hay clientes registrados aún.")

# --- 1. FORMULARIO DE INGRESO (Dinámico) ---
st.header("1. Registrar Movimiento")

col1, col2, col3, col4 = st.columns(4)

with col1:
    tipo = st.selectbox("Tipo", ["Cobro", "Préstamo", "Gasto"])

with col2:
    # La interfaz cambia dependiendo de lo que elijas en "Tipo"
    if tipo in ["Cobro", "Préstamo"]:
        if len(st.session_state.clientes) == 0:
            st.warning("Agrega clientes en el menú lateral 👈")
            cliente_concepto = None
        else:
            cliente_concepto = st.selectbox("Seleccionar Cliente", st.session_state.clientes)
    else:
        cliente_concepto = st.text_input("Concepto del Gasto (Ej. Gasolina, Comida)")

with col3:
    monto = st.number_input("Monto ($)", min_value=0.0, step=1.0)
    
with col4:
    metodo = st.selectbox("Método de Pago", ["Efectivo", "Transferencia", "Pago Móvil"])

if st.button("Registrar Operación", type="primary"):
    if cliente_concepto and monto > 0:
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
        st.success("✅ Operación guardada exitosamente.")
    else:
        st.error("Por favor completa el cliente/concepto y asegúrate de que el monto sea mayor a 0.")

# --- 2. DETALLE DE MOVIMIENTOS ---
st.header("2. Movimientos del Día")
st.dataframe(st.session_state.movimientos, use_container_width=True)

# --- 3. CUADRE DE CAJA ---
st.header("3. Cuadre de Caja Físico")
base_inicial = st.number_input("Efectivo de Salida (Base Inicial):", min_value=0.0, step=1.0)

# Cálculos automáticos
df = st.session_state.movimientos
df_efectivo = df[df['Metodo'] == 'Efectivo']

total_cobrado = df_efectivo[df_efectivo['Tipo'] == 'Cobro']['Monto'].sum()
total_prestamos = df_efectivo[df_efectivo['Tipo'] == 'Préstamo']['Monto'].sum()
total_gastos = df_efectivo[df_efectivo['Tipo'] == 'Gasto']['Monto'].sum()

efectivo_esperado = base_inicial + total_cobrado - total_prestamos - total_gastos

colA, colB, colC, colD, colE = st.columns(5)
colA.metric("Base", f"${base_inicial:.2f}")
colB.metric("Cobros (+)", f"${total_cobrado:.2f}")
colC.metric("Préstamos (-)", f"${total_prestamos:.2f}")
colD.metric("Gastos (-)", f"${total_gastos:.2f}")
colE.metric("EFECTIVO ESPERADO", f"${efectivo_esperado:.2f}")

# --- 4. EXPORTACIÓN PARA EXCEL ---
st.header("4. Reporte para Jefatura")
csv = df.to_csv(index=False).encode('utf-8')
st.download_button(
    label="📥 Descargar Reporte (CSV)",
    data=csv,
    file_name=f"reporte_cobranza_{date.today()}.csv",
    mime="text/csv",
)
