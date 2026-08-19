import streamlit as st
import pandas as pd

# 1. Configuración de la página para aprovechar el ancho del monitor
st.set_page_config(page_title="Gestión de Cartera", layout="wide")

st.title("📊 Cartera de Créditos Activos")

# 2. Función con caché para leer y cruzar los datos
@st.cache_data
def cargar_cartera_activa():
    # Leer el archivo
    df_clientes = pd.read_excel('cartera_prestamos.xlsx', sheet_name='Clientes')
    df_prestamos = pd.read_excel('cartera_prestamos.xlsx', sheet_name='Prestamos')
    df_recaudos = pd.read_excel('cartera_prestamos.xlsx', sheet_name='Recaudos')
    
    # Agrupar pagos y cruzar
    pagos_totales = df_recaudos.groupby('ID_Prestamo')['Monto_Recibido'].sum().reset_index()
    pagos_totales.rename(columns={'Monto_Recibido': 'Total_Pagado'}, inplace=True)
    
    df_cartera = pd.merge(df_prestamos, pagos_totales, on='ID_Prestamo', how='left')
    df_cartera['Total_Pagado'] = df_cartera['Total_Pagado'].fillna(0)
    df_cartera['Saldo_Pendiente'] = df_cartera['Total_Deuda'] - df_cartera['Total_Pagado']
    
    # Filtrar solo activos (Saldo mayor a 0)
    cartera_activa = df_cartera[df_cartera['Saldo_Pendiente'] > 0].copy()
    
    # Unir con datos del cliente
    reporte = pd.merge(
        cartera_activa, 
        df_clientes[['ID_Cliente', 'Nombre_Completo', 'Telefono', 'Zona_Ruta']], 
        on='ID_Cliente', 
        how='left'
    )
    return reporte

# 3. Construcción de la Interfaz
try:
    # Llamamos a la función cacheada
    df_activos = cargar_cartera_activa()
    
    # --- BARRA LATERAL (FILTROS) ---
    st.sidebar.header("Filtros de Búsqueda")
    
    # Extraer las zonas únicas dinámicamente y agregar "Todas" al inicio
    lista_zonas = ["Todas"] + list(df_activos['Zona_Ruta'].dropna().unique())
    zona_seleccionada = st.sidebar.selectbox("Filtrar por Zona / Ruta", lista_zonas)
    
    # Lógica del filtro
    if zona_seleccionada != "Todas":
        df_filtrado = df_activos[df_activos['Zona_Ruta'] == zona_seleccionada]
    else:
        df_filtrado = df_activos
        
    # --- MÉTRICAS DE CABECERA ---
    # Mostramos el capital total en la calle y la cantidad de clientes a cobrar
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Total Clientes Activos", len(df_filtrado))
    with col2:
        saldo_total = df_filtrado['Saldo_Pendiente'].sum()
        st.metric("Capital en la Calle (Saldo)", f"${saldo_total:,.2f}")
        
    # --- TABLA DE DATOS INTERACTIVA ---
    st.subheader(f"Ruta de cobro: {zona_seleccionada}")
    
    # Seleccionamos solo las columnas relevantes para la tabla
    columnas_mostrar = [
        'ID_Prestamo', 'Nombre_Completo', 'Telefono', 
        'Zona_Ruta', 'Modalidad', 'Valor_Cuota', 'Saldo_Pendiente'
    ]
    
    # Renderizamos la tabla nativa de Streamlit (permite ordenar las columnas con un clic)
    st.dataframe(
        df_filtrado[columnas_mostrar],
        use_container_width=True,
        hide_index=True
    )

except FileNotFoundError:
    st.error("No se encontró 'cartera_prestamos.xlsx'. Verifica que esté en la misma carpeta que el script.")
