import streamlit as st
import pandas as pd
import numpy as np
from scipy.stats import poisson
from datetime import datetime

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Radar de Valor V8.7 - Control Manual", layout="wide")

# Inicializar historial en la sesión
if 'historial' not in st.session_state:
    st.session_state.historial = []

class EngineAnalitico:
    def calcular_probabilidades(self, l_data, v_data, h_adv):
        # Ajuste de localía estándar (10%)
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
st.title("🛰️ Radar de Valor V8.7: Selección de Apuesta")

t1, t2, t3 = st.tabs(["📥 Datos del Partido", "📊 Análisis y Selección", "📂 Mi Historial"])

with t1:
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Equipo Local")
        n_l = st.text_input("Nombre Local", "Bournemouth")
        xg_l = st.number_input("xG Local", value=1.70)
        xga_l = st.number_input("xGA Local", value=1.10)
        c_l = st.number_input("Cuota Local", value=1.75)
    with col2:
        st.subheader("Equipo Visitante")
        n_v = st.text_input("Nombre Visitante", "Crystal Palace")
        xg_v = st.number_input("xG Visitante", value=1.05)
        xga_v = st.number_input("xGA Visitante", value=1.60)
        c_v = st.number_input("Cuota Visita", value=4.50)
    
    st.divider()
    st.caption("Cuotas de Mercados Secundarios")
    col_g1, col_g2, col_g3, col_g4 = st.columns(4)
    c_x = col_g1.number_input("Cuota X", value=3.80)
    c_o = col_g2.number_input("Cuota O2.5", value=1.85)
    c_u = col_g3.number_input("Cuota U2.5", value=1.95)
    c_b = col_g4.number_input("Cuota BTTS", value=1.70)

with t2:
    engine = EngineAnalitico()
    res = engine.calcular_probabilidades({'xg': xg_l, 'xga': xga_l}, {'xg': xg_v, 'xga': xga_v}, 0.10)
    
    # Mostrar tabla de probabilidades para ayudar a decidir
    mercados = [
        (f"Victoria {n_l}", res['p_1'], c_l),
        ("Empate", res['p_x'], c_x),
        (f"Victoria {n_v}", res['p_2'], c_v),
        ("Over 2.5", res['p_o25'], c_o),
        ("Under 2.5", res['p_u25'], c_u),
        ("Ambos Anotan", res['p_btts'], c_b)
    ]
    
    filas = []
    opciones_seleccion = []
    for nombre, prob, cuota in mercados:
        cj = 1/prob
        ev = (prob * cuota) - 1
        estado = "POSITIVO" if ev > 0.05 else "negativo"
        filas.append({"Mercado": nombre, "Prob": f"{prob:.1%}", "CJ": round(cj, 2), "Estado": estado})
        opciones_seleccion.append(f"{nombre} (@{cuota})")

    st.table(pd.DataFrame(filas).style.map(
        lambda x: 'background-color: #1b5e20; color: white; font-weight: bold' if x == "POSITIVO" else 'color: #757575',
        subset=['Estado']
    ))

    st.divider()
    
    # SECCIÓN DE ELECCIÓN MANUAL
    st.subheader("🎯 ¿Qué resultado vas a jugar?")
    col_sel, col_btn = st.columns([3, 1])
    
    with col_sel:
        eleccion = st.selectbox("Selecciona tu jugada para el historial:", opciones_seleccion)
    
    with col_btn:
        st.write(" ") # Espaciador
        if st.button("💾 GUARDAR JUGADA", use_container_width=True):
            nuevo_registro = {
                "Fecha/Hora": datetime.now().strftime("%d/%m %H:%M"),
                "Partido": f"{n_l} vs {n_v}",
                "Mi Apuesta": eleccion,
                "Favorito Math": n_l if res['p_1'] > res['p_2'] else n_v,
                "Prob. (%)": f"{max(res['p_1'], res['p_2']):.1%}"
            }
            st.session_state.historial.append(nuevo_registro)
            st.success("¡Guardado!")

with t3:
    st.subheader("📂 Registro de Apuestas Seleccionadas")
    if st.session_state.historial:
        df_hist = pd.DataFrame(st.session_state.historial)
        st.dataframe(df_hist, use_container_width=True)
        
        if st.button("🗑️ Limpiar Todo"):
            st.session_state.historial = []
            st.rerun()
    else:
        st.info("Aún no has guardado ninguna jugada.")
