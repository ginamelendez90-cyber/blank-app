import streamlit as st
import re
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# --- CONFIGURACIÓN Y ESTADOS ---
st.set_page_config(page_title="Predictor Pro + Email", page_icon="📩")

if 'historial' not in st.session_state:
    st.session_state['historial'] = []

# --- FUNCIÓN PARA ENVIAR EMAIL ---
def enviar_reporte_email(contenido):
    # Configuración del servidor (Ejemplo con Gmail)
    # NOTA: Necesitarás crear una "Contraseña de Aplicación" en tu cuenta de Google
    remitente = "tu_correo@gmail.com" 
    password = "tu_password_de_aplicacion" 
    destinatario = "williamvg120@gmail.com"

    msg = MIMEMultipart()
    msg['From'] = remitente
    msg['To'] = destinatario
    msg['Subject'] = f"Análisis de Apuestas - {datetime.now().strftime('%d/%m/%Y')}"

    msg.attach(MIMEText(contenido, 'plain'))

    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(remitente, password)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        st.error(f"Error al enviar: {e}")
        return False

# --- INTERFAZ ---
st.title("🏆 Sistema de Análisis Deportivo")
tab1, tab2, tab3 = st.tabs(["🎾 Tenis", "⚽ Fútbol", "📜 Historial y Envío"])

# ... (Aquí va el código de análisis que ya tenemos) ...

with tab3:
    st.header("Historial de la Sesión")
    
    if st.session_state['historial']:
        # Preparar el texto para el correo
        cuerpo_email = "HISTORIAL DE ANÁLISIS RECIENTE:\n\n"
        for h in st.session_state['historial']:
            st.info(h)
            cuerpo_email += f"- {h}\n"
        
        st.markdown("---")
        if st.button("📧 ENVIAR HISTORIAL AL CORREO", use_container_width=True):
            with st.spinner("Enviando reporte a williamvg120@gmail.com..."):
                exito = enviar_reporte_email(cuerpo_email)
                if exito:
                    st.success("✅ ¡Historial enviado con éxito!")
    else:
        st.write("No hay análisis registrados en esta sesión.")
