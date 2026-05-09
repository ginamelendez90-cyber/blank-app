import streamlit as st
import re
import urllib.parse

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Sport Predictor Pro V7.1", page_icon="🏆", layout="wide")

# --- INICIALIZACIÓN DE ESTADOS ---
if 'historial' not in st.session_state:
    st.session_state['historial'] = []

# --- FUNCIONES DE LIMPIEZA ---
def limpiar_datos():
    st.session_state["texto_entrada"] = ""

# --- MOTOR DE CÁLCULO CON PONDERACIÓN (RECENCIA) ---
def procesar_datos_v7(texto):
    # Divide el texto por bloques de equipo ignorando mayúsculas/minúsculas
    bloques = re.split(r'ÚLTIMOS PARTIDOS:', texto, flags=re.IGNORECASE)
    resumen = []
    
    for bloque in bloques:
        if not bloque.strip() or len(bloque) < 10: continue
        
        lineas = [l.strip() for l in bloque.strip().split('\n') if l.strip()]
        if not lineas: continue
        nombre = lineas[0]
        
        # Regex flexible: detecta "2 1 G", "2-1 G", "2 - 1 G", "2:1 G"
        matches = re.findall(r'(\d)\s*[:\-\s]*\s*(\d)\s*([GEP])', bloque, flags=re.IGNORECASE)
        
        if matches:
            # PONDERACIÓN: Los 2 partidos más recientes valen 1.5x (Factor de Recencia)
            pesos = [1.5 if i < 2 else 1.0 for i in range(len(matches))]
            total_peso = sum(pesos)
            
            # Cálculos ponderados para evitar errores por resultados antiguos
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

col_in, col_cuo = st.columns([2, 1])

with col_in:
    st.subheader("📋 Datos de 365Scores")
    data_f = st.text_area("Pega el historial de ambos equipos:", height=250, key="texto_entrada", 
                          placeholder="Copia desde 'ÚLTIMOS PARTIDOS' de ambos equipos...")
    st.button("🗑️ Limpiar Entrada", on_click=limpiar_datos)

with col_cuo:
    st.subheader("💰 Cuotas (Sin Límites)")
    # Cuotas con formato decimal libre
    c_loc = st.number_input("Cuota Local", value=2.00, step=0.01, format="%.2f")
    c_o15 = st.number_input("Cuota Over 1.5", value=1.30, step=0.01, format="%.2f")
    c_o25 = st.number_input("Cuota Over 2.5", value=1.85, step=0.01, format="%.2f")
    c_u25 = st.number_input("Cuota Under 2.5", value=1.90, step=0.01, format="%.2f")
    c_btts = st.number_input("Cuota BTTS", value=1.75, step=0.01, format="%.2f")

# --- PROCESAMIENTO ---
if st.button("🔍 ANALIZAR VALOR REAL", type="primary", use_container_width=True):
    stats = procesar_datos_v7(data_f)
    
    if len(stats) >= 2:
        e1, e2 = stats[0], stats[1]
        
        # Probabilidades Combinadas
        p_win_l = (e1['win'] + (100 - e2['win'])) / 2
        p_o15 = (e1['o15'] + e2['o15']) / 2
        p_o25 = (e1['o25'] + e2['o25']) / 2
        p_u25 = 100 - p_o25
        p_btts = (e1['btts'] + e2['btts']) / 2
        
        st.success(f"### 🎯 Análisis: {e1['nombre']} vs {e2['nombre']}")
        
        historial_partido = [f"⚽ {e1['nombre']} vs {e2['nombre']}"]

        def evaluar(label, p_real, cuota):
            p_casa = (1 / cuota) * 100 if cuota > 0 else 100
            diff = p_real - p_casa
            
            # Filtro de valor estricto (10% para VALOR ALTO)
            if diff > 10: 
                color, tag, icon = "#00ff00", "VALOR ALTO", "✅"
            elif diff > 0: 
                color, tag, icon = "#ffa500", "VALOR MEDIO", "⚠️"
            else: 
                color, tag, icon = "#ff4b4b", "SIN VALOR", "❌"
            
            st.markdown(f"**{label}**: {icon} <span style='color:{color}; font-weight:bold;'>{tag}</span> (Real: {round(p_real,1)}% | Casa: {round(p_casa,1)}%)", unsafe_allow_html=True)
            return f"- {label}: {tag} ({round(p_real,1)}%)"

        historial_partido.append(evaluar(f"Gana {e1['nombre']}", p_win_l, c_loc))
        historial_partido.append(evaluar("Over 1.5", p_o15, c_o15))
        historial_partido.append(evaluar("Over 2.5", p_o25, c_o25))
        historial_partido.append(evaluar("Under 2.5", p_u25, c_u25))
        historial_partido.append(evaluar("BTTS (Ambos Marcan)", p_btts, c_btts))
        
        # Guardar en el historial detallado
        st.session_state['historial'].insert(0, "\n".join(historial_partido))
    else:
        st.error("No se detectaron datos suficientes. Asegúrate de copiar el historial de ambos equipos.")

# --- SECCIÓN DE HISTORIAL ---
if st.session_state['historial']:
    st.divider()
    st.subheader("📜 Historial de Análisis Detallado")
    texto_historial = "\n\n---\n\n".join(st.session_state['historial'])
    st.text_area("Copia tus resultados aquí:", value=texto_historial, height=300)
    
    # Botón de envío directo a Gmail
    u_hist = urllib.parse.quote(texto_historial)
    mail_url = f"https://mail.google.com/mail/?view=cm&fs=1&to=williamvg120@gmail.com&su=Reporte_Sport_Predictor&body={u_hist}"
    st.markdown(f'''
        <a href="{mail_url}" target="_blank" style="text-decoration:none;">
            <div style="background-color:#ff4b4b;color:white;padding:15px;text-align:center;border-radius:10px;font-weight:bold;font-size:16px;">
                📩 ENVIAR REPORTE COMPLETO A GMAIL
            </div>
        </a>
    ''', unsafe_allow_html=True)
