import streamlit as st
import pandas as pd

# Reemplaza con tu ID real
SHEET_ID = "https://docs.google.com/spreadsheets/d/1-g3icRDMsZu_L2nNHMRSHoPAU7n6k5hbZANUyV9WwEw/edit?usp=drivesdk" 

def cargar_usuarios():
    # Formato alternativo para evitar el error 404
    url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid=0"
    return pd.read_csv(url)

# --- PRUEBA DE CONEXIÓN ---
try:
    df = cargar_usuarios()
    st.success("✅ ¡Conectado con éxito!")
    st.write(df.head()) # Esto te mostrará si leyó bien los datos
except Exception as e:
    st.error(f"Sigue fallando: {e}")
