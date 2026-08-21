import streamlit as st
from google.cloud import bigquery
import pandas as pd
import plotly.express as px

# Configuración de la página
st.set_page_config(page_title="Football Analytics & Value Bets", layout="wide")

st.title("⚽ Dashboard Automatizado de Análisis de Fútbol")
st.markdown("Conectado en tiempo real con **Google Cloud BigQuery**.")

# 1. Configuración de la conexión a BigQuery usando los secretos de Streamlit
@st.cache_resource
def get_bigquery_client():
    # Streamlit lee automáticamente las credenciales desde st.secrets
    return bigquery.Client.from_service_account_info(st.secrets["gcp"])

client = get_bigquery_client()

# 2. Función para consultar datos (reemplaza 'tu_proyecto.tu_dataset.tu_tabla' por tus datos reales)
@st.cache_data(ttl=600) # Cache por 10 minutos
def load_data(query):
    query_job = client.query(query)
    return query_job.to_dataframe()

# Ejemplo de consulta SQL analítica
default_query = """
    SELECT 
        fecha, 
        liga, 
        local, 
        visitante, 
        cuota_local, 
        cuota_empate, 
        cuota_visitante
    FROM `tu_proyecto.futbol_dataset.partidos_recientes`
    ORDER BY fecha DESC
    LIMIT 100
"""

st.sidebar.header("Filtros de Análisis")
query_input = st.sidebar.text_area("Consulta SQL en BigQuery", value=default_query, height=150)

try:
    with st.spinner("Consultando BigQuery..."):
        df = load_data(query_input)
    
    st.success(f"¡Datos cargados con éxito! ({len(df)} registros encontrados)")
    
    # Mostrar tabla interactiva
    st.dataframe(df, use_container_width=True)
    
    # Ejemplo básico de métrica o gráfico automatizado
    if "liga" in df.columns:
        ligas_disponibles = df["liga"].unique()
        liga_seleccionada = st.selectbox("Filtrar por Liga", ligas_disponibles)
        df_filtrado = df[df["liga"] == liga_seleccionada]
        st.subheader(f partidos para {liga_seleccionada})
        st.dataframe(df_filtrado)

except Exception as e:
    st.error(f"Error al conectar con BigQuery o ejecutar la consulta: {e}")
