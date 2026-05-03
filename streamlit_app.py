import streamlit as st
import pandas as pd

ID = "1-g3icRDMsZu_L2nNHMRSHoPAU7n6k5hbZANUyV9WwEw"
GID = "T539541529"

url = f"https://docs.google.com/spreadsheets/d/{ID}/export?format=csv&gid={GID}"

st.write(f"Probando conexión a: {url}")

try:
    df = pd.read_csv(url)
    st.success("✅ ¡CONECTADO! Los datos se leen bien.")
    st.dataframe(df.head())
except Exception as e:
    st.error(f"❌ Error de Google: {e}")
    st.info("Si el error dice 'HTTP Error 404', el ID o el GID están mal.")
    st.info("Si el error dice 'HTTP Error 403', es un problema de permisos de Compartir.")
