import streamlit as st
import re
import urllib.parse

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Sport Predictor Pro V7.5", page_icon="🏆", layout="wide")

# --- INICIALIZACIÓN DE ESTADOS ---
if 'historial' not in st.session_state:
    st.session_state['historial'] = []

def limpiar_datos():
    st.session_state["texto_entrada"] = ""

# --- MOTOR DE CÁLCULO CON PONDERACIÓN (RECENCIA) ---
def procesar_datos_v7(texto):
    bloques = re.split(r'ÚLTIMOS PARTIDOS:', texto, flags=re.IGNORECASE)
    resumen = []
    
    for bloque in bloques:
        if not bloque.strip() or len(bloque) < 10: continue
        
        lineas = [l.strip() for l in bloque.strip().split('\n') if l.strip()]
        if not lineas: continue
        nombre = lineas[0]
        
        # Regex para capturar goles y resultado
        matches = re.findall(r'(\d)\s*[:\-\s]*\s*(\d)\s*([GEP])', bloque, flags=re.IGNORECASE)
        
        if matches:
            # PONDERACIÓN DE RECENCIA (1.5x a los últimos 2 partidos)
            pesos = [1.5 if i < 2 else 1.0 for i in range(len(matches))]
            total_peso = sum(pesos)
            
            win_p = sum(pesos[i] for i, m in enumerate(matches) if m[2].upper() == 'G') / total_peso
            draw_p = sum(pesos[i] for i, m in enumerate(matches) if m[2].upper() == 'E') / total_peso
            o15_p = sum(pesos[i] for i, m in enumerate(matches) if (int(m[0]) + int(m[1])) >= 2) / total_peso
            o25_p = sum(pesos[i] for i, m in enumerate(matches) if (int(m[0]) + int(m[1])) >= 3) / total_peso
            btts_p = sum(pesos[i] for i, m in enumerate(matches) if int(m[0]) > 0 and int(m[1]) > 0) / total_peso
            
            resumen.append({
                "nombre": nombre,
                "win": win_p * 100,
                "draw": draw_p * 100,
                "o15": o15_p * 100,
                "o25": o25_p * 100,
                "btts": btts_p * 100
            })
    return resumen

# --- INTERFAZ ---
st.title("🏆 Sport Predictor Pro V7.5 (Full Control)")
st.markdown("---")

col_in, col_cuo = st.columns([1.8, 1.2])

with col_in:
    st.subheader("📋 Datos de 365Scores")
    data_f = st.text_area("Pega el historial de ambos equipos:", height=300, key="texto_entrada")
    st.button("🗑️ Limpiar Todo", on_click=limpiar_datos)

with col_cuo:
    st.subheader("💰 Todas las Cuotas")
    c1, c2 = st.columns(2)
    with c1:
        cl = st.number_input("Cuota Local (1)", value=2.00, format="%.2f")
        ce = st.number_input("Cuota Empate (X)", value=3.20, format="%.2f")
        cv = st.number_input("Cuota Visita (2)", value=2.80, format="%.2f")
    with c2:
        co15 = st.number_input("Cuota Over 1.5", value=1.30, format="%.2f")
        co25 = st.number_input("Cuota Over 2.5", value=1.85, format="%.2f")
        cbtts = st.number_input("Cuota BTTS", value=1.75, format="%.2f")
    
    cu25 = st.number_input("Cuota Under 2.5", value=1.90, format="%.2f")

# --- ANÁLISIS ---
if st.button("🔍 ANALIZAR VALOR TOTAL", type="primary", use_container_width=True):
    stats = procesar_datos_v7(data_f)
    
    if len(stats) >= 2:
        e1, e2 = stats[0], stats[1]
        
        # Probabilidades Combinadas (Local vs Visita)
        p_l = (e1['win'] + (100 - e2['win'] - e2['draw'])) / 2
        p_v = (e2['win'] + (100 - e1['win'] - e1['draw'])) / 2
        p_x = (e1['draw'] + e2['draw']) / 2
        
        p_o15 = (e1['o15'] + e2['o15']) / 2
        p_o25 = (e1['o25'] + e2['o25']) / 2
        p_btts = (e1['btts'] + e2['btts']) / 2
        
        st.success(f"### 🎯 {e1['nombre']} vs {e2['nombre']}")
        
        hist_partido = [f"⚽ {e1['nombre']} vs {e2['nombre']}"]

        def check(label, p_real, cuota):
            p_casa = (1 / cuota) * 100 if cuota > 0 else 100
            diff = p_real - p_casa
            if diff > 10: col, tag, ico = "#00ff00", "VALOR ALTO", "✅"
            elif diff > 0: col, tag, ico = "#ffa500", "VALOR MEDIO", "⚠️"
            else: col, tag, ico = "#ff4b4b", "SIN VALOR", "❌"
            
            st.markdown(f"**{label}**: {ico} <span style='color:{col}; font-weight:bold;'>{tag}</span> (Real: {round(p_real,1)}% | Cuota: {round(p_casa,1)}%)", unsafe_allow_html=True)
            return f"- {label}: {tag} ({round(p_real,1)}%)"

        # Resultados 1X2
        hist_partido.append(check(f"Gana {e1['nombre']} (Local)", p_l, cl))
        hist_partido.append(check("Empate (X)", p_x, ce))
        hist_partido.append(check(f"Gana {e2['nombre']} (Visita)", p_v, cv))
        
        # Goles
        hist_partido.append(check("Over 1.5", p_o15, co15))
        hist_partido.append(check("Over 2.5", p_o25, co25))
        hist_partido.append(check("Under 2.5", (100-p_o25), cu25))
        hist_partido.append(check("BTTS", p_btts, cbtts))
        
        st.session_state['historial'].insert(0, "\n".join(hist_partido))
    else:
        st.error("Faltan datos de uno de los equipos.")

# --- HISTORIAL ---
if st.session_state['historial']:
    st.divider()
    tx_h = "\n\n---\n\n".join(st.session_state['historial'])
    st.subheader("📜 Historial de Análisis")
    st.text_area("Resultados acumulados:", value=tx_h, height=300)
    
    u_h = urllib.parse.quote(tx_h)
    mail_url = f"https://mail.google.com/mail/?view=cm&fs=1&to=williamvg120@gmail.com&su=Reporte_V7.5&body={u_h}"
    st.markdown(f'<a href="{mail_url}" target="_blank" style="text-decoration:none;"><div style="background-color:#ff4b4b;color:white;padding:15px;text-align:center;border-radius:10px;font-weight:bold;">📩 ENVIAR REPORTE A GMAIL</div></a>', unsafe_allow_html=True)
