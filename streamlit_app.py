import streamlit as st
import re
import numpy as np
import urllib.parse

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Sport Predictor Monte Carlo V8.2", page_icon="🎲", layout="wide")

if 'historial' not in st.session_state:
    st.session_state['historial'] = []

def limpiar_datos():
    st.session_state["texto_entrada"] = ""

# --- MOTOR DE PROCESAMIENTO REVISADO ---
def extraer_stats(texto):
    # Dividimos por "ÚLTIMOS PARTIDOS"
    bloques = re.split(r'ÚLTIMOS PARTIDOS:', texto, flags=re.IGNORECASE)
    resumen = []
    
    for bloque in bloques:
        if not bloque.strip() or len(bloque) < 10: continue
        
        lineas = [l.strip() for l in bloque.strip().split('\n') if l.strip()]
        if not lineas: continue
        
        # El nombre suele ser la primera línea después de "ÚLTIMOS PARTIDOS"
        nombre = lineas[0]
        
        # Buscamos los resultados (Goles Favor, Goles Contra, Resultado)
        matches = re.findall(r'(\d)\s*[:\-\s]*\s*(\d)\s*([GEP])', bloque, flags=re.IGNORECASE)
        
        if matches:
            # Ponderación de recencia (más peso a los últimos 2 partidos)
            pesos = np.array([1.5 if i < 2 else 1.0 for i in range(len(matches))])
            goles_f = np.array([int(m[0]) for m in matches])
            goles_c = np.array([int(m[1]) for m in matches])
            
            # Calculamos promedio de goles a favor y en contra
            avg_f = np.average(goles_f, weights=pesos)
            avg_c = np.average(goles_c, weights=pesos)
            
            resumen.append({
                "nombre": nombre,
                "ataque": avg_f, 
                "defensa": avg_c,
                "win_h": sum(1 for m in matches if m[2].upper() == 'G') / len(matches)
            })
    return resumen

# --- SIMULADOR MONTE CARLO (CON LÓGICA DE LOCALÍA) ---
def simular_partido(e1, e2, factor_ajuste=1.0, n_sim=10000):
    # xG: Ataque de uno contra defensa del otro
    # e1 es Local, e2 es Visitante
    exp_g_e1 = ((e1['ataque'] + e2['defensa']) / 2) * factor_ajuste
    exp_g_e2 = ((e2['ataque'] + e1['defensa']) / 2) * factor_ajuste
    
    # Simulación de Poisson
    sim_e1 = np.random.poisson(exp_g_e1, n_sim)
    sim_e2 = np.random.poisson(exp_g_e2, n_sim)
    
    # Análisis de los 10,000 resultados
    w_e1 = np.sum(sim_e1 > sim_e2)
    w_e2 = np.sum(sim_e2 > sim_e1)
    empates = np.sum(sim_e1 == sim_e2)
    
    goles_totales = sim_e1 + sim_e2
    
    return {
        "p_e1": (w_e1 / n_sim) * 100,
        "p_e2": (w_e2 / n_sim) * 100,
        "p_x": (empates / n_sim) * 100,
        "p_o15": (np.sum(goles_totales >= 2) / n_sim) * 100,
        "p_o25": (np.sum(goles_totales >= 3) / n_sim) * 100,
        "p_btts": (np.sum((sim_e1 > 0) & (sim_e2 > 0)) / n_sim) * 100,
        "avg_g": np.mean(goles_totales)
    }

# --- INTERFAZ ---
st.title("🎲 Sport Predictor V8.2: Corrección de Localía")
st.info("Asegúrate de pegar PRIMERO el bloque del equipo LOCAL y SEGUNDO el del VISITANTE.")

col_a, col_b = st.columns([2, 1])

with col_a:
    data_f = st.text_area("Pega datos de 365Scores (Local arriba, Visita abajo):", height=250, key="texto_entrada")

with col_b:
    st.subheader("⚙️ Parámetros")
    contexto = st.text_input("Novedades (Bajas, clima, etc.):")
    ajuste = 0.85 if any(x in contexto.lower() for x in ["baja", "falta", "suplente", "lesion"]) else 1.0
    if ajuste < 1.0: st.warning("⚠️ Ajuste de goles activo.")

if st.button("🚀 INICIAR SIMULACIÓN 10,000 PARTIDOS", type="primary", use_container_width=True):
    stats = extraer_stats(data_f)
    
    if len(stats) >= 2:
        # El primer bloque detectado es el LOCAL, el segundo el VISITANTE
        local, visita = stats[0], stats[1]
        res = simular_partido(local, visita, factor_ajuste=ajuste)
        
        st.divider()
        st.header(f"🏟️ {local['nombre']} (L) vs {visita['nombre']} (V)")
        
        # Resultados Principales
        c1, c2, c3 = st.columns(3)
        c1.metric(f"Gana {local['nombre']}", f"{round(res['p_e1'], 1)}%")
        c2.metric("Empate", f"{round(res['p_x'], 1)}%")
        c3.metric(f"Gana {visita['nombre']}", f"{round(res['p_e2'], 1)}%")
        
        # Mercados de Goles
        st.subheader("🔥 Probabilidades de Mercado")
        g1, g2, g3, g4 = st.columns(4)
        g1.info(f"**Over 1.5:** {round(res['p_o15'], 1)}%")
        g2.info(f"**Over 2.5:** {round(res['p_o25'], 1)}%")
        g3.info(f"**BTTS:** {round(res['p_btts'], 1)}%")
        g4.info(f"**Goles Est.:** {round(res['avg_g'], 2)}")
        
        # Guardar en Historial con claridad de quién es quién
        rep = f"🎰 {local['nombre']} vs {visita['nombre']} | L:{round(res['p_e1'],1)}% X:{round(res['p_x'],1)}% V:{round(res['p_e2'],1)}%"
        st.session_state['historial'].insert(0, rep)
    else:
        st.error("Error: No se detectaron 2 bloques de 'ÚLTIMOS PARTIDOS'.")

# --- HISTORIAL ---
if st.session_state['historial']:
    st.divider()
    tx_h = "\n\n".join(st.session_state['historial'])
    st.text_area("Historial de Simulaciones:", value=tx_h, height=150)
    
    u_h = urllib.parse.quote(tx_h)
    mail_url = f"https://mail.google.com/mail/?view=cm&fs=1&to=williamvg120@gmail.com&su=Reporte_V8.2&body={u_h}"
    st.markdown(f'<a href="{mail_url}" target="_blank" style="text-decoration:none;"><div style="background-color:#ff4b4b;color:white;padding:12px;text-align:center;border-radius:10px;font-weight:bold;">📩 ENVIAR A GMAIL</div></a>', unsafe_allow_html=True)
