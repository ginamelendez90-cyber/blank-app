import streamlit as st
import pandas as pd
import numpy as np
from scipy.stats import poisson

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Radar de Valor V8.6 - Historial", layout="wide")

# Inicializar el historial en la sesión si no existe
if 'historial' not in st.session_state:
    st.session_state.historial = []

class EngineAnalitico:
    def calcular_probabilidades(self, l_data, v_data, h_adv):
        l_lamb = (l_data['xg'] * (1 + h_adv) + v_data['xga']) / 2
        v_lamb = (v_data['xg'] + l_data['xga'] * (1 - h_adv)) / 2
        
        max_g = 10
        p_l = [poisson.pmf(i, l_lamb) for i in range(max_g)]
        p_v = [poisson.pmf(i, v_lamb) for i in range(max_g)]
        matriz = np.outer(p_l, p_v)
        
        p_1 = np.sum(np.tril(matriz, -1))
        p_x = np.sum(np.diag(matriz))
        p_2 = 1 - p_1 - p_x
        p_u25 = sum(matriz[i, j] for i in range(3) for j in range(3-i))
        p_o25 = 1 - p_u25
        p_btts = 1 - (p_l[0] + p_v[0] - matriz[0, 0])
        
        return {
            "p_1": p_1, "p_x": p_x, "p_2": p_2,
            "p_o25": p_o25, "p_u25": p_u25, "p_btts": p_btts
        }

# --- INTERFAZ ---
st.title("🎯 Radar de Valor V8.6 + Historial de Guardado")

t1, t2, t3 = st.tabs(["📥 Entrada de Datos", "📊 Análisis Actual", "📂 Historial Guardado"])

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
    col_g1, col_g2, col_g3, col_g4 = st.columns(4)
    c_x = col_g1.number_input("Cuota X", value=3.80)
    c_o = col_g2.number_input("Cuota O2.5", value=1.85)
    c_u = col_g3.number_input("Cuota U2.5", value=1.95)
    c_b = col_g4.number_input("Cuota BTTS", value=1.70)

with t2:
    if st.button("🚀 CALCULAR Y GUARDAR", use_container_width=True):
        engine = EngineAnalitico()
        res = engine.calcular_probabilidades({'xg': xg_l, 'xga': xga_l}, {'xg': xg_v, 'xga': xga_v}, 0.10)
        
        # Procesar resultados para la tabla
        mercados = [
            (f"Victoria {n_l}", res['p_1'], c_l),
            ("Empate", res['p_x'], c_x),
            (f"Victoria {n_v}", res['p_2'], c_v),
            ("Over 2.5", res['p_o25'], c_o),
            ("Under 2.5", res['p_u25'], c_u),
            ("Ambos Anotan", res['p_btts'], c_b)
        ]

        filas = []
        for nombre, prob, cuota in mercados:
            cj = 1/prob
            ev = (prob * cuota) - 1
            diag = "POSITIVO" if ev > 0.05 else "negativo"
            filas.append({"Mercado": nombre, "Prob": f"{prob:.1%}", "CJ": round(cj, 2), "Estado": diag})
        
        # Mostrar tabla actual
        df_actual = pd.DataFrame(filas)
        st.table(df_actual.style.map(
            lambda x: 'background-color: #1b5e20; color: white; font-weight: bold' if x == "POSITIVO" else 'color: #757575',
            subset=['Estado']
        ))

        # GUARDAR EN EL HISTORIAL
        # Solo guardamos los que dieron "POSITIVO" para limpiar el historial
        positivos = [f"{m[0]} (@{m[2]})" for m in mercados if (m[1] * m[2]) - 1 > 0.05]
        
        nuevo_registro = {
            "Evento": f"{n_l} vs {n_v}",
            "Favorito": n_l if res['p_1'] > res['p_2'] else n_v,
            "Opciones Positivas": ", ".join(positivos) if positivos else "Ninguna",
            "Goles Est.": round( (1.70+1.05)/2 + (1.10+1.60)/2, 2) # Ejemplo rápido de proyección
        }
        st.session_state.historial.append(nuevo_registro)
        st.success("Análisis guardado en el historial.")

with t3:
    st.subheader("Historial de la Sesión")
    if st.session_state.historial:
        df_hist = pd.DataFrame(st.session_state.historial)
        st.dataframe(df_hist, use_container_width=True)
        
        if st.button("🗑️ Borrar Historial"):
            st.session_state.historial = []
            st.rerun()
    else:
        st.write("No hay análisis guardados aún.")
