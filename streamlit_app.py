import streamlit as st
import re
from datetime import datetime

st.set_page_config(page_title="Predicador Pro Fútbol", page_icon="⚽", layout="centered")

if 'historial' not in st.session_state:
    st.session_state['historial'] = []

def limpiar_futbol(): st.session_state["texto_futbol"] = ""

def procesar_futbol(texto):
    bloques = re.split(r'ÚLTIMOS PARTIDOS:', texto)
    resumen = []
    for bloque in bloques:
        if not bloque.strip(): continue
        lineas = [l.strip() for l in bloque.strip().split('\n') if l.strip()]
        nombre = lineas[0]
        matches = re.findall(r'(\d)\s+(\d)\s+([GEP])', bloque)
        if matches:
            victorias = sum(1 for m in matches if m[2] == 'G')
            goles_partido = [int(m[0]) + int(m[1]) for m in matches]
            resumen.append({
                "nombre": nombre,
                "win_rate": victorias / len(matches),
                "avg_goles": sum(goles_partido) / len(matches),
                "p_over15": sum(1 for g in goles_partido if g >= 2) / len(matches),
                "p_over25": sum(1 for g in goles_partido if g >= 3) / len(matches)
            })
    return resumen

tab1, tab2 = st.tabs(["⚽ Análisis de Fútbol", "📜 Historial"])

with tab1:
    st.header("⚽ Fútbol: Análisis de Valor")
    data_futbol = st.text_area("Pega los datos de 365Scores aquí:", height=150, key="texto_futbol")
    
    st.subheader("💰 Cuotas de la Casa de Apuestas")
    col_c1, col_c2 = st.columns(2)
    with col_c1:
        c_local = st.number_input("Cuota Local", min_value=1.01, value=2.0)
        c_over15 = st.number_input("Cuota Over 1.5", min_value=1.01, value=1.3)
        c_over25 = st.number_input("Cuota Over 2.5", min_value=1.01, value=1.9)
    with col_c2:
        c_visita = st.number_input("Cuota Visitante", min_value=1.01, value=3.0)
        c_under15 = st.number_input("Cuota Under 1.5", min_value=1.01, value=3.5)
        c_under25 = st.number_input("Cuota Under 2.5", min_value=1.01, value=1.8)

    if st.button("🚀 CALCULAR VALOR TOTAL", use_container_width=True):
        stats = procesar_futbol(data_futbol)
        if len(stats) >= 2:
            e1, e2 = stats[0], stats[1]
            
            # Probabilidades Reales (Modelo Estadístico)
            p_local = (e1['win_rate'] + (1 - e2['win_rate'])) / 2
            p_visita = (e2['win_rate'] + (1 - e1['win_rate'])) / 2
            p_o15 = (e1['p_over15'] + e2['p_over15']) / 2
            p_o25 = (e1['p_over25'] + e2['p_over25']) / 2
            p_u25 = 1 - p_o25

            st.markdown("---")
            st.subheader("🎯 Veredicto de Probabilidades Reales")
            
            def check_valor(prob, cuota, etiqueta):
                prob_implied = (1 / cuota)
                if prob > prob_implied:
                    st.success(f"✅ **{etiqueta}**: {round(prob*100,1)}% (HAY VALOR)")
                else:
                    st.error(f"❌ **{etiqueta}**: {round(prob*100,1)}% (Sin Valor)")

            # Sección Ganador
            col_res1, col_res2 = st.columns(2)
            with col_res1: check_valor(p_local, c_local, f"Gana {e1['nombre']}")
            with col_res2: check_valor(p_visita, c_visita, f"Gana {e2['nombre']}")

            # Sección Goles
            st.markdown("### 📊 Mercado de Goles")
            g_col1, g_col2 = st.columns(2)
            with g_col1:
                check_valor(p_o15, c_over15, "Over 1.5")
                check_valor(p_o25, c_over25, "Over 2.5")
            with g_col2:
                check_valor((1-p_o15), c_under15, "Under 1.5")
                check_valor(p_u25, c_under25, "Under 2.5")

            # Guardar en Historial
            st.session_state['historial'].insert(0, f"⚽ {e1['nombre']} vs {e2['nombre']} - {datetime.now().strftime('%H:%M')}")
        else:
            st.error("Pega los datos de ambos equipos.")

    st.button("🗑️ BORRAR DATOS", on_click=limpiar_futbol)

with tab2:
    st.header("Historial")
    for h in st.session_state['historial']:
        st.write(h)
