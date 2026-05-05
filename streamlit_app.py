import streamlit as st
import pandas as pd
import numpy as np
import re
from scipy.stats import poisson
from datetime import datetime

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Radar V9.4 - Reset Ready", layout="wide")

if 'historial' not in st.session_state:
    st.session_state.historial = []

# Función de extracción
def extraer_todos_los_datos(texto):
    numeros = re.findall(r"\d+\.\d+|\d+", texto)
    return [float(n) for n in numeros]

# Función para limpiar todos los campos
def limpiar_todo():
    keys_to_reset = ['xg_l', 'xg_v', 'c_l', 'c_x', 'c_v', 'c_o', 'c_u', 'c_b', 'raw_input']
    for key in keys_to_reset:
        if key in st.session_state:
            del st.session_state[key]
    st.toast("Formulario reiniciado")

class EngineMonteCarlo:
    def simular_partido(self, l_xg, v_xg, h_adv, sims=10000):
        l_lamb = l_xg * (1 + h_adv)
        v_lamb = v_xg 
        goles_l = np.random.poisson(l_lamb, sims)
        goles_v = np.random.poisson(v_lamb, sims)
        resultados = pd.DataFrame({'L': goles_l, 'V': goles_v})
        
        p_1 = np.mean(resultados['L'] > resultados['V'])
        p_x = np.mean(resultados['L'] == resultados['V'])
        p_2 = np.mean(resultados['L'] < resultados['V'])
        p_o25 = np.mean((resultados['L'] + resultados['V']) > 2.5)
        p_btts = np.mean((resultados['L'] > 0) & (resultados['V'] > 0))
        marcador_top = resultados.groupby(['L', 'V']).size().idxmax()
        
        return {
            "p_1": p_1, "p_x": p_x, "p_2": p_2,
            "p_o25": p_o25, "p_btts": p_btts,
            "top_score": f"{marcador_top[0]} - {marcador_top[1]}"
        }

# --- INTERFAZ ---
st.title("🛰️ Radar de Valor V9.4")

with st.sidebar:
    st.header("📋 Importación")
    # Usamos session_state para el contenido del área de texto
    raw_data = st.text_area("Pega aquí los datos:", height=150, key="raw_input")
    
    col_btn1, col_btn2 = st.columns(2)
    
    if col_btn1.button("🪄 Rellenar"):
        val = extraer_todos_los_datos(raw_data)
        if len(val) >= 2: st.session_state['xg_l'] = val[0]; st.session_state['xg_v'] = val[1]
        if len(val) >= 5: st.session_state['c_l'] = val[2]; st.session_state['c_x'] = val[3]; st.session_state['c_v'] = val[4]
        if len(val) >= 8: st.session_state['c_o'] = val[5]; st.session_state['c_u'] = val[6]; st.session_state['c_b'] = val[7]
        st.rerun()

    # BOTÓN DE BORRAR
    if col_btn2.button("🗑️ Borrar Todo", on_click=limpiar_todo):
        st.rerun()

t1, t2, t3 = st.tabs(["📥 Datos", "🧪 Simulación", "📂 Historial"])

with t1:
    c1, c2 = st.columns(2)
    with c1:
        n_l = st.text_input("Local", "Equipo Local")
        # El value ahora busca en session_state, si no hay, pone 0.0
        xg_l = st.number_input("xG Local", value=st.session_state.get('xg_l', 0.0), format="%.2f")
        c_l = st.number_input("Cuota Local", value=st.session_state.get('c_l', 0.0), format="%.2f")
    with c2:
        n_v = st.text_input("Visitante", "Equipo Visitante")
        xg_v = st.number_input("xG Visitante", value=st.session_state.get('xg_v', 0.0), format="%.2f")
        c_v = st.number_input("Cuota Visita", value=st.session_state.get('c_v', 0.0), format="%.2f")
    
    st.divider()
    col_ext = st.columns(4)
    cx = col_ext[0].number_input("Cuota X", value=st.session_state.get('c_x', 0.0))
    co = col_ext[1].number_input("Cuota O2.5", value=st.session_state.get('c_o', 0.0))
    cu = col_ext[2].number_input("Cuota U2.5", value=st.session_state.get('c_u', 0.0))
    cb = col_ext[3].number_input("Cuota BTTS", value=st.session_state.get('c_b', 0.0))

with t2:
    if xg_l > 0 or xg_v > 0:
        if st.button("🎲 EJECUTAR MONTE CARLO", use_container_width=True):
            engine = EngineMonteCarlo()
            res = engine.simular_partido(xg_l, xg_v, 0.10)
            
            st.metric("Marcador Probable", res['top_score'])
            
            mercados = [
                (f"Victoria {n_l}", res['p_1'], c_l), ("Empate", res['p_x'], cx),
                (f"Victoria {n_v}", res['p_2'], c_v), ("Over 2.5", res['p_o25'], co),
                ("Under 2.5", 1-res['p_o25'], cu), ("Ambos Anotan", res['p_btts'], cb)
            ]
            
            filas, opciones = [], []
            for nombre, prob, cuota in mercados:
                ev = (prob * cuota) - 1 if cuota > 0 else -1
                filas.append({
                    "Mercado": nombre, "Prob. (%)": f"{prob:.1%}", 
                    "Cuota Justa": round(1/prob, 2) if prob > 0 else 0,
                    "EV (%)": f"{ev*100:.1f}%",
                    "Estado": "POSITIVO" if ev > 0 else "negativo"
                })
                opciones.append(f"{nombre} (@{cuota})")

            st.table(pd.DataFrame(filas).style.map(
                lambda x: 'background-color: #004d40; color: white' if x == "POSITIVO" else 'color: #757575',
                subset=['Estado']
            ))

            st.divider()
            sel1, sel2 = st.columns(2)
            j1 = sel1.selectbox("Apuesta 1:", ["Ninguna"] + opciones)
            j2 = sel2.selectbox("Apuesta 2:", ["Ninguna"] + opciones)
            
            if st.button("💾 GUARDAR"):
                st.session_state.historial.append({
                    "Fecha": datetime.now().strftime("%d/%m %H:%M"),
                    "Partido": f"{n_l} vs {n_v}", "Sim": res['top_score'], "J1": j1, "J2": j2
                })
                st.toast("Registrado")
    else:
        st.warning("Introduce datos de xG para habilitar la simulación.")

with t3:
    if st.session_state.historial:
        st.dataframe(pd.DataFrame(st.session_state.historial), use_container_width=True)
        if st.button("🗑️ Reset Historial"):
            st.session_state.historial = []; st.rerun()
