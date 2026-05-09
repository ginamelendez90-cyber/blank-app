import streamlit as st
import re
import urllib.parse

# --- CONFIGURACIÓN PROFESIONAL ---
st.set_page_config(page_title="Sport Predictor Pro V7.1", page_icon="🏆", layout="wide")

# --- ESTADO DE LA SESIÓN ---
if 'historial' not in st.session_state:
    st.session_state['historial'] = []

# --- MOTOR DE CÁLCULO CON PONDERACIÓN DE RECENCIA ---
def procesar_datos_v7(texto):
    # Separamos por bloques de equipo
    bloques = re.split(r'ÚLTIMOS PARTIDOS:', texto, flags=re.IGNORECASE)
    resumen = []
    
    for bloque in bloques:
        if not bloque.strip() or len(bloque) < 10: continue
        
        lineas = [l.strip() for l in bloque.strip().split('\n') if l.strip()]
        nombre = lineas[0]
        
        # Regex flexible para capturar marcadores y resultado (G/E/P)
        matches = re.findall(r'(\d)\s*[:\-\s]*\s*(\d)\s*([GEP])', bloque, flags=re.IGNORECASE)
        
        if matches:
            # Los 2 partidos más recientes tienen un 50% más de peso (Factor 1.5)
            pesos = [1.5 if i < 2 else 1.0 for i in range(len(matches))]
            total_peso = sum(pesos)
            
            # Cálculos Ponderados
            win_p = sum(pesos[i] for i, m in enumerate(matches) if m[2].upper() == 'G') / total_peso
            o15_p = sum(pesos[i] for i, m in enumerate(matches) if (int(m[0]) + int(m[1])) >= 2) / total_peso
            o25_p = sum(pesos[i] for i, m in enumerate(matches) if (int(m[0]) + int(m[1])) >= 3) / total_peso
            btts_p = sum(pesos[i] for i, m in enumerate(matches) if int(m[0]) > 0 and int(m[1]) > 0) / total_peso
            
            resumen.append({
                "nombre": nombre,
                "win": win_p * 100,
                "o15": o15_p * 100,
                "o25": o25_p * 100,
                "btts": btts_p * 100
            })
    return resumen

# --- INTERFAZ DE USUARIO ---
st.title("🚀 Sport Predictor Pro V7.1")
st.markdown("---")

col_input, col_cuotas = st.columns([2, 1])

with col_input:
    st.subheader("📋 Datos de 365Scores")
    data_f = st.text_area("Pega aquí el historial de ambos equipos:", height=250, placeholder="Copia desde 'ÚLTIMOS PARTIDOS'...")

with col_cuotas:
    st.subheader("💰 Cuotas del Mercado")
    c_loc = st.number_input("Cuota Local", value=2.0, step=0.01, format="%.2f")
    c_o15 = st.number_input("Cuota Over 1.5", value=1.30, step=0.01, format="%.2f")
    c_o25 = st.number_input("Cuota Over 2.5", value=1.85, step=0.01, format="%.2f")
    c_u25 = st.number_input("Cuota Under 2.5", value=1.90, step=0.01, format="%.2f")
    c_btts = st.number_input("Cuota BTTS", value=1.75, step=0.01, format="%.2f")

# --- ACCIÓN DE ANÁLISIS ---
if st.button("🔍 ANALIZAR VALOR CON RECENCIA", type="primary", use_container_width=True):
    stats = procesar_datos_v7(data_f)
    
    if len(stats) >= 2:
        e1, e2 = stats[0], stats[1]
        
        # Probabilidades Combinadas (Promedio ponderado de ambos equipos)
        p_win_l = (e1['win'] + (100 - e2['win'])) / 2
        p_o15 = (e1['o15'] + e2['o15']) / 2
        p_o25 = (e1['o25'] + e2['o25']) / 2
        p_u25 = 100 - p_o25
        p_btts = (e1['btts'] + e2['btts']) / 2
        
        st.success(f"### 📊 Pronóstico: {e1['nombre']} vs {e2['nombre']}")
        
        results_for_history = [f"⚽ {e1['nombre']} vs {e2['nombre']}"]

        def evaluar_valor(label, p_real, cuota):
            p_casa = (1 / cuota) * 100 if cuota > 0 else 100
            diff = p_real - p_casa
            
            if diff > 10: 
                color, tag, icon = "#00ff00", "VALOR ALTO", "✅"
            elif diff > 0: 
                color, tag, icon = "#ffa500", "VALOR MEDIO", "⚠️"
            else: 
                color, tag, icon = "#ff4b4b", "SIN VALOR", "❌"
            
            st.markdown(f"**{label}**: {icon} <span style='color:{color}; font-weight:bold;'>{tag}</span> (Real: {round(p_real,1)}% | Casa: {round(p_casa,1)}%)", unsafe_allow_html=True)
            return f"- {label}: {tag} ({round(p_real,1)}%)"

        results_for_history.append(evaluar_valor(f"Gana {e1['nombre']}", p_win_l, c_loc))
        results_for_history.append(evaluar_valor("Over 1.5", p_o15, c_o15))
        results_for_history.append(evaluar_valor("Over 2.5", p_o25, c_o25))
        results_for_history.append(evaluar_valor("Under 2.5", p_u25, c_u25))
        results_for_history.append(evaluar_valor("BTTS (Ambos Marcan)", p_btts, c_btts))
        
        # Guardar en Historial
        st.session_state['historial'].insert(0, "\n".join(results_for_history))
    else:
        st.error("Error: Asegúrate de haber pegado los datos de ambos equipos correctamente.")

# --- SECCIÓN DE HISTORIAL ---
if st.session_state['historial']:
    st.divider()
    st.subheader("📜 Historial de Análisis")
    full_history_text = "\n\n---\n\n".join(st.session_state['historial'])
    st.text_area("Reportes generados:", value=full_history_text, height=300)
    
    # Botón de envío a Gmail
    u_hist = urllib.parse.quote(full_history_text)
    mail_url = f"https://mail.google.com/mail/?view=cm&fs=1&to=williamvg120@gmail.com&su=Reporte_Apuestas_V7&body={u_hist}"
    st.markdown(f'<a href="{mail_url}" target="_blank" style="text-decoration:none;"><div style="background-color:#ff4b4b;color:white;padding:15px;text-align:center;border-radius:10px;font-weight:bold;font-size:18px;">📩 ENVIAR TODO A MI GMAIL</div></a>', unsafe_allow_html=True)
