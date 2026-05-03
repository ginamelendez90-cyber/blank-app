import streamlit as st
import pandas as pd
import numpy as np
from scipy.stats import poisson

# --- CONFIGURACIÓN DE INTERFAZ ---
st.set_page_config(page_title="Radar de Valor V8.4 - Lógica Pro", layout="wide")

class EngineLogicaPro:
    def calcular_analisis(self, local_data, visita_data, cuotas, home_adv):
        # 1. APLICACIÓN DE FACTOR DE LOCALÍA (Lógica Deportiva)
        # El local suele rendir un poco más que su promedio general
        xg_local_adj = local_data['xg'] * (1 + home_adv)
        xga_local_adj = local_data['xga'] * (1 - home_adv)
        
        # 2. AJUSTE DE FUERZAS CRUZADAS
        lambda_l = (xg_local_adj + visita_data['xga']) / 2
        lambda_v = (visita_data['xg'] + xga_local_adj) / 2
        
        # 3. MATRIZ DE POISSON
        max_g = 10
        p_l = [poisson.pmf(i, lambda_l) for i in range(max_g)]
        p_v = [poisson.pmf(i, lambda_v) for i in range(max_g)]
        matriz = np.outer(p_l, p_v)
        
        # Probabilidades Matemáticas
        p_x = np.sum(np.diag(matriz)) 
        p_1 = np.sum(np.tril(matriz, -1))
        p_2 = 1 - p_1 - p_x
        
        # Mercados de Goles
        p_u25 = sum(matriz[i, j] for i in range(3) for j in range(3-i))
        p_o25 = 1 - p_u25
        p_btts = 1 - (p_l[0] + p_v[0] - matriz[0, 0])

        # 4. CÁLCULO DE VALOR (EV) - (P * Cuota) - 1
        def get_ev(p, c): return (p * c) - 1 if c > 0 else -1
        
        # 5. DETERMINAR FAVORITO POR PROBABILIDAD
        probs = {local_data['nombre']: p_1, "Empate": p_x, visita_data['nombre']: p_2}
        ganador_logico = max(probs, key=probs.get)

        return {
            "p_1": p_1, "p_x": p_x, "p_2": p_2, "p_o25": p_o25, "p_u25": p_u25, "p_btts": p_btts,
            "cj_l": 1/p_1, "cj_x": 1/p_x, "cj_v": 1/p_2, "cj_o25": 1/p_o25, "cj_u25": 1/p_u25, "cj_btts": 1/p_btts,
            "ev_l": get_ev(p_1, cuotas['L']), "ev_x": get_ev(p_x, cuotas['X']), "ev_v": get_ev(p_2, cuotas['V']),
            "ev_o25": get_ev(p_o25, cuotas['O25']), "ev_u25": get_ev(p_u25, cuotas['U25']), "ev_btts": get_ev(p_btts, cuotas['BTTS']),
            "ganador_logico": ganador_logico
        }

# --- INTERFAZ ---
st.title("🛰️ Radar de Valor V8.4: Lógica de Localía")
st.markdown("---")

t1, t2 = st.tabs(["📊 Datos de Entrada", "💰 Resultados Coherentes"])

with t1:
    col_cfg1, col_cfg2 = st.columns([2, 1])
    with col_cfg1:
        st.info("Ingresa los datos de xG y xGA que ves en la imagen de 365Scores.")
    with col_cfg2:
        h_adv = st.slider("Ventaja Localía (%)", 0, 20, 10) / 100

    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Casa (Local)")
        n_l = st.text_input("Equipo Local", "Bournemouth")
        xg_l = st.number_input("xG (Esperados) L", value=1.75) # Valor más alto para el favorito
        xga_l = st.number_input("xGA (Recibidos) L", value=1.20)
    with c2:
        st.subheader("Fuera (Visitante)")
        n_v = st.text_input("Equipo Visitante", "Crystal Palace")
        xg_v = st.number_input("xG (Esperados) V", value=1.10)
        xga_v = st.number_input("xGA (Recibidos) V", value=1.65)

with t2:
    st.subheader("Cuotas Reales de la Casa")
    c_in1, c_in2, c_in3 = st.columns(3)
    cl = c_in1.number_input(f"Cuota {n_l}", value=1.70) # Cuota lógica para un favorito
    cx = c_in2.number_input("Cuota Empate", value=3.90)
    cv = c_in3.number_input(f"Cuota {n_v}", value=4.25)
    
    st.markdown("**Goles y BTTS**")
    c_g1, c_g2, c_g3 = st.columns(3)
    co = c_g1.number_input("Cuota Over 2.5", value=1.85)
    cu = c_g2.number_input("Cuota Under 2.5", value=2.00)
    cb = c_g3.number_input("Cuota BTTS (SI)", value=1.75)

    if st.button("🚀 GENERAR ANÁLISIS LÓGICO", use_container_width=True):
        engine = EngineLogicaPro()
        res = engine.calcular_analisis(
            {'nombre': n_l, 'xg': xg_l, 'xga': xga_l},
            {'nombre': n_v, 'xg': xg_v, 'xga': xga_v},
            {'L': cl, 'X': cx, 'V': cv, 'O25': co, 'U25': cu, 'BTTS': cb},
            h_adv
        )

        # TABLA DE RESULTADOS
        st.subheader("📋 Diagnóstico de Valor")
        def tag(ev): return "POSITIVO" if ev > 0.05 else "negativo"
        
        df_data = {
            "Mercado": [n_l, "Empate", n_v, "Over 2.5", "Under 2.5", "Ambos Anotan"],
            "Prob. Real": [f"{res['p_1']:.1%}", f"{res['p_x']:.1%}", f"{res['p_2']:.1%}", f"{res['p_o25']:.1%}", f"{res['p_u25']:.1%}", f"{res['p_btts']:.1%}"],
            "Cuota Justa": [res['cj_l'], res['cj_x'], res['cj_v'], res['cj_o25'], res['cj_u25'], res['cj_btts']],
            "Diagnóstico": [tag(res['ev_l']), tag(res['ev_x']), tag(res['ev_v']), tag(res['ev_o25']), tag(res['ev_u25']), tag(res['ev_btts'])]
        }
        
        st.table(pd.DataFrame(df_data).style.format({"Cuota Justa": "{:.2f}"}).map(
            lambda x: 'background-color: #1b5e20; color: white; font-weight: bold' if x == "POSITIVO" else 'color: #757575',
            subset=['Diagnóstico']
        ))

        # VEREDICTO FINAL COHERENTE
        st.divider()
        st.success(f"🏆 **Favorito Lógico:** {res['ganador_logico']} ({max(res['p_1'], res['p_x'], res['p_2']):.1%})")
        st.info(f"💡 **Explicación:** El Bournemouth es favorito porque su xG (ajustado por localía) es superior al xG del Palace y choca contra una defensa visitante más débil.")
