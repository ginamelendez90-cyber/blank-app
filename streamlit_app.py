import streamlit as st
import pandas as pd
import numpy as np
from scipy.stats import poisson
from datetime import datetime

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Radar de Valor V8.9 - Sin Límites", layout="wide")

if 'historial' not in st.session_state:
    st.session_state.historial = []

class EngineAnalitico:
    def calcular_probabilidades(self, l_data, v_data, h_adv):
        # Ajuste de localía
        l_lamb = (l_data['xg'] * (1 + h_adv) + v_data['xga']) / 2
        v_lamb = (v_data['xg'] + l_data['xga'] * (1 - h_adv)) / 2
        
        max_g = 10
        p_l = [poisson.pmf(i, l_lamb) for i in range(max_g)]
        p_v = [poisson.pmf(i, v_lamb) for i in range(max_g)]
        matriz = np.outer(p_l, p_v)
        
        # Probabilidades base
        p_1 = np.sum(np.tril(matriz, -1))
        p_x = np.sum(np.diag(matriz))
        p_2 = 1 - p_1 - p_x
        p_o25 = 1 - sum(matriz[i, j] for i in range(3) for j in range(3-i))
        p_u25 = 1 - p_o25
        p_btts = 1 - (p_l[0] + p_v[0] - matriz[0, 0])
        
        return {
            "p_1": p_1, "p_x": p_x, "p_2": p_2,
            "p_o25": p_o25, "p_u25": p_u25, "p_btts": p_btts
        }

# --- INTERFAZ ---
st.title("🛰️ Radar de Valor V8.9: Modo Sin Restricciones")

t1, t2, t3 = st.tabs(["📥 Datos del Evento", "📊 Análisis y Doble Elección", "📂 Historial"])

with t1:
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Equipo Local")
        n_l = st.text_input("Nombre Local", "Equipo A")
        xg_l = st.number_input("xG Local", value=1.50, step=0.01, format="%.2f")
        xga_l = st.number_input("xGA Local", value=1.00, step=0.01, format="%.2f")
        c_l = st.number_input("Cuota Local", value=1.50, step=0.01, format="%.2f")
    with c2:
        st.subheader("Equipo Visitante")
        n_v = st.text_input("Nombre Visitante", "Equipo B")
        xg_v = st.number_input("xG Visitante", value=1.10, step=0.01, format="%.2f")
        xga_v = st.number_input("xGA Visitante", value=1.40, step=0.01, format="%.2f")
        c_v = st.number_input("Cuota Visita", value=3.00, step=0.01, format="%.2f")
    
    st.divider()
    st.caption("Cuotas Adicionales")
    col_ext = st.columns(4)
    c_x = col_ext[0].number_input("Cuota X", value=3.50)
    c_o = col_ext[1].number_input("Cuota O2.5", value=1.80)
    c_u = col_ext[2].number_input("Cuota U2.5", value=1.80)
    c_b = col_ext[3].number_input("Cuota BTTS", value=1.70)

with t2:
    engine = EngineAnalitico()
    # Mantenemos un 10% de ventaja local por realismo, pero puedes bajarlo a 0 si quieres.
    res = engine.calcular_probabilidades({'xg': xg_l, 'xga': xga_l}, {'xg': xg_v, 'xga': xga_v}, 0.10)
    
    mercados = [
        (f"Victoria {n_l}", res['p_1'], c_l), ("Empate", res['p_x'], c_x),
        (f"Victoria {n_v}", res['p_2'], c_v), ("Over 2.5", res['p_o25'], c_o),
        ("Under 2.5", res['p_u25'], c_u), ("Ambos Anotan", res['p_btts'], c_b)
    ]
    
    filas, opciones = [], []
    for nombre, prob, cuota in mercados:
        # ELIMINADO EL LÍMITE: Cualquier EV > 0 es positivo
        ev = (prob * cuota) - 1
        filas.append({
            "Mercado": nombre, 
            "Prob. Real": f"{prob:.1%}", 
            "Cuota Justa": round(1/prob, 2), 
            "EV (%)": f"{ev*100:.1f}%",
            "Estado": "POSITIVO" if ev > 0 else "negativo" # Ahora detecta cualquier ventaja
        })
        opciones.append(f"{nombre} (@{cuota})")

    st.table(pd.DataFrame(filas).style.map(
        lambda x: 'background-color: #004d40; color: white' if x == "POSITIVO" else 'color: #757575', 
        subset=['Estado']
    ))

    st.divider()
    st.subheader("🎯 Registra tus Jugadas")
    sel1, sel2 = st.columns(2)
    j1 = sel1.selectbox("Jugada 1:", ["Ninguna"] + opciones)
    j2 = sel2.selectbox("Jugada 2:", ["Ninguna"] + opciones)
    
    if st.button("💾 GUARDAR EN HISTORIAL", use_container_width=True):
        if j1 != "Ninguna" or j2 != "Ninguna":
            st.session_state.historial.append({
                "Fecha": datetime.now().strftime("%d/%m %H:%M"),
                "Partido": f"{n_l} vs {n_v}",
                "J1": j1, "J2": j2,
                "Fav Math": n_l if res['p_1'] > res['p_2'] else n_v
            })
            st.toast("Guardado correctamente")

with t3:
    if st.session_state.historial:
        st.dataframe(pd.DataFrame(st.session_state.historial), use_container_width=True)
        if st.button("🗑️ Vaciar Historial"):
            st.session_state.historial = []
            st.rerun()
    else:
        st.info("No hay jugadas guardadas.")
