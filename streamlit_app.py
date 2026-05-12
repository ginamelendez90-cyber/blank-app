import streamlit as st
import re
import numpy as np
import urllib.parse

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Sport Predictor Monte Carlo", page_icon="🎲", layout="wide")

if 'historial' not in st.session_state:
    st.session_state['historial'] = []

def limpiar_datos():
    st.session_state["texto_entrada"] = ""

# --- MOTOR DE PROCESAMIENTO ---
def extraer_stats(texto):
    bloques = re.split(r'ÚLTIMOS PARTIDOS:', texto, flags=re.IGNORECASE)
    resumen = []
    for bloque in bloques:
        if not bloque.strip() or len(bloque) < 10: continue
        lineas = [l.strip() for l in bloque.strip().split('\n') if l.strip()]
        nombre = lineas[0]
        matches = re.findall(r'(\d)\s*[:\-\s]*\s*(\d)\s*([GEP])', bloque, flags=re.IGNORECASE)
        
        if matches:
            # Ponderación de recencia
            pesos = np.array([1.5 if i < 2 else 1.0 for i in range(len(matches))])
            goles_f = np.array([int(m[0]) for m in matches])
            goles_c = np.array([int(m[1]) for m in matches])
            
            # Promedios ponderados (Ataque y Defensa)
            avg_f = np.average(goles_f, weights=pesos)
            avg_c = np.average(goles_c, weights=pesos)
            
            resumen.append({
                "nombre": nombre,
                "ataque": avg_f,
                "defensa": avg_c,
                "btts_hist": sum(1 for m in matches if int(m[0]) > 0 and int(m[1]) > 0) / len(matches)
            })
    return resumen

# --- SIMULADOR MONTE CARLO (10,000 PARTIDOS) ---
def simular_partido(e1, e2, n_sim=10000):
    # Estimación de goles esperados (xG) para el partido
    # El ataque de uno contra la defensa del otro
    exp_goles_e1 = (e1['ataque'] + e2['defensa']) / 2
    exp_goles_e2 = (e2['ataque'] + e1['defensa']) / 2
    
    # Generar 10,000 resultados basados en Distribución de Poisson
    sim_e1 = np.random.poisson(exp_goles_e1, n_sim)
    sim_e2 = np.random.poisson(exp_goles_e2, n_sim)
    
    # Análisis de resultados simulados
    wins_e1 = np.sum(sim_e1 > sim_e2)
    wins_e2 = np.sum(sim_e2 > sim_e1)
    empates = np.sum(sim_e1 == sim_e2)
    
    goles_totales = sim_e1 + sim_e2
    o15 = np.sum(goles_totales >= 2)
    o25 = np.sum(goles_totales >= 3)
    btts = np.sum((sim_e1 > 0) & (sim_e2 > 0))
    
    return {
        "p_e1": (wins_e1 / n_sim) * 100,
        "p_e2": (wins_e2 / n_sim) * 100,
        "p_x": (empates / n_sim) * 100,
        "p_o15": (o15 / n_sim) * 100,
        "p_o25": (o25 / n_sim) * 100,
        "p_btts": (btts / n_sim) * 100,
        "avg_goles": np.mean(goles_totales)
    }

# --- INTERFAZ ---
st.title("🎲 Sport Predictor V8: Monte Carlo Simulation")
st.info("Este motor simula 10,000 variaciones del partido usando Distribución de Poisson para dar un veredicto matemático final.")

data_f = st.text_area("Pega datos de 365Scores:", height=250, key="texto_entrada")

col_b1, col_b2 = st.columns([1, 5])
with col_b1:
    btn = st.button("🚀 SIMULAR 10,000 PARTIDOS", type="primary")
with col_b2:
    st.button("🗑️ Limpiar", on_click=limpiar_datos)

if btn:
    stats = extraer_stats(data_f)
    if len(stats) >= 2:
        e1, e2 = stats[0], stats[1]
        res = simular_partido(e1, e2)
        
        st.divider()
        st.subheader(f"🏟️ Veredicto Final: {e1['nombre']} vs {e2['nombre']}")
        
        # Visualización de Probabilidades
        c1, c2, c3, c4 = st.columns(4)
        c1.metric(f"Gana {e1['nombre']}", f"{round(res['p_e1'], 1)}%")
        c2.metric("Empate", f"{round(res['p_x'], 1)}%")
        c3.metric(f"Gana {e2['nombre']}", f"{round(res['p_e2'], 1)}%")
        c4.metric("Promedio Goles", f"{round(res['avg_goles'], 2)}")
        
        st.markdown("#### Probabilidades de Mercado (Simuladas)")
        g1, g2, g3 = st.columns(3)
        g1.info(f"**Over 1.5:** {round(res['p_o15'], 1)}%")
        g2.info(f"**Over 2.5:** {round(res['p_o25'], 1)}%")
        g3.info(f"**BTTS:** {round(res['p_btts'], 1)}%")
        
        # Historial
        rep = (f"🎰 Simulación 10k: {e1['nombre']} vs {e2['nombre']}\n"
               f"Resultado: L:{round(res['p_e1'],1)}% X:{round(res['p_x'],1)}% V:{round(res['p_e2'],1)}%\n"
               f"Goles: O2.5:{round(res['p_o25'],1)}% | BTTS:{round(res['p_btts'],1)}%")
        st.session_state['historial'].insert(0, rep)
    else:
        st.error("Error al procesar datos. Asegúrate de incluir el historial de ambos equipos.")

# --- HISTORIAL ---
if st.session_state['historial']:
    st.divider()
    tx_h = "\n\n---\n\n".join(st.session_state['historial'])
    st.text_area("Historial de Simulaciones:", value=tx_h, height=200)
    u_h = urllib.parse.quote(tx_h)
    mail_url = f"https://mail.google.com/mail/?view=cm&fs=1&to=williamvg120@gmail.com&su=Reporte_MonteCarlo&body={u_h}"
    st.markdown(f'<a href="{mail_url}" target="_blank" style="text-decoration:none;"><div style="background-color:#ff4b4b;color:white;padding:12px;text-align:center;border-radius:10px;font-weight:bold;">📩 ENVIAR REPORTE A GMAIL</div></a>', unsafe_allow_html=True)
