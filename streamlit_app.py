import streamlit as st
import pandas as pd
import numpy as np
from scipy.stats import poisson
from datetime import datetime

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Radar de Valor V8.8 - Doble Selección", layout="wide")

if 'historial' not in st.session_state:
    st.session_state.historial = []

class EngineAnalitico:
    def calcular_probabilidades(self, l_data, v_data, h_adv):
        # Ajuste de localía (Home Advantage)
        l_lamb = (l_data['xg'] * (1 + h_adv) + v_data['xga']) / 2
        v_lamb = (v_data['xg'] + l_data['xga'] * (1 - h_adv)) / 2
        
        max_g = 10
        p_l = [poisson.pmf(i, l_lamb) for i in range(max_g)]
        p_v = [poisson.pmf(i, v_lamb) for i in range(max_g)]
        matriz = np.outer(p_l, p_v)
        
        return {
            "p_1": np.sum(np.tril(matriz, -1)),
            "p_x": np.sum(np.diag(matriz)),
            "p_2": 1 - np.sum(np.tril(matriz, -1)) - np.sum(np.diag(matriz)),
            "p_o25": 1 - sum(matriz[i, j] for i in range(3) for j in range(3-i)),
            "p_u25": sum(matriz[i, j] for i in range(3) for j in range(3-i)),
            "p_btts": 1 - (p_l[0] + p_v[0] - matriz[0, 0])
        }

# --- INTERFAZ ---
st.title("🛰️ Radar de Valor V8.8: Selección Doble")

t1, t2, t3 = st.tabs(["📥 Datos", "📊 Análisis y Doble Elección", "📂 Historial"])

with t1:
    c1, c2 = st.columns(2)
    with c1:
        n_l = st.text_input("Local", "Bournemouth")
        xg_l = st.number_input("xG Local", value=1.70)
        xga_l = st.number_input("xGA Local", value=1.10)
        c_l = st.number_input("Cuota Local", value=1.75)
    with c2:
        n_v = st.text_input("Visitante", "Crystal Palace")
        xg_v = st.number_input("xG Visitante", value=1.05)
        xga_v = st.number_input("xGA Visitante", value=1.60)
        c_v = st.number_input("Cuota Visita", value=4.50)
    
    st.divider()
    col_g = st.columns(4)
    c_x, c_o, c_u, c_b = col_g[0].number_input("Cuota X", 3.80), col_g[1].number_input("Cuota O2.5", 1.85), col_g[2].number_input("Cuota U2.5", 1.95), col_g[3].number_input("Cuota BTTS", 1.70)

with t2:
    engine = EngineAnalitico()
    res = engine.calcular_probabilidades({'xg': xg_l, 'xga': xga_l}, {'xg': xg_v, 'xga': xga_v}, 0.10)
    
    mercados = [
        (f"Victoria {n_l}", res['p_1'], c_l), ("Empate", res['p_x'], c_x),
        (f"Victoria {n_v}", res['p_2'], c_v), ("Over 2.5", res['p_o25'], c_o),
        ("Under 2.5", res['p_u25'], c_u), ("Ambos Anotan", res['p_btts'], c_b)
    ]
    
    filas, opciones = [], []
    for nombre, prob, cuota in mercados:
        ev = (prob * cuota) - 1
        filas.append({"Mercado": nombre, "Prob": f"{prob:.1%}", "CJ": round(1/prob, 2), "Estado": "POSITIVO" if ev > 0.05 else "negativo"})
        opciones.append(f"{nombre} (@{cuota})")

    st.table(pd.DataFrame(filas).style.map(lambda x: 'background-color: #1b5e20; color: white' if x == "POSITIVO" else 'color: #757575', subset=['Estado']))

    st.divider()
    st.subheader("🎯 Selecciona hasta 2 jugadas")
    col_a, col_b = st.columns(2)
    with col_a:
        j1 = st.selectbox("Jugada Principal:", ["Ninguna"] + opciones)
    with col_b:
        j2 = st.selectbox("Jugada Secundaria:", ["Ninguna"] + opciones)
    
    if st.button("💾 GUARDAR AMBAS EN HISTORIAL", use_container_width=True):
        if j1 != "Ninguna" or j2 != "Ninguna":
            st.session_state.historial.append({
                "Fecha": datetime.now().strftime("%d/%m %H:%M"),
                "Partido": f"{n_l} vs {n_v}",
                "Selección 1": j1,
                "Selección 2": j2,
                "Favorito Math": n_l if res['p_1'] > res['p_2'] else n_v
            })
            st.success("¡Jugadas registradas!")

with t3:
    if st.session_state.historial:
        st.dataframe(pd.DataFrame(st.session_state.historial), use_container_width=True)
        if st.button("🗑️ Limpiar Historial"):
            st.session_state.historial = []
            st.rerun()
    else:
        st.info("Historial vacío.")
