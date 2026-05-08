import streamlit as st
import re
from datetime import datetime

st.set_page_config(page_title="Football Value Finder", page_icon="⚽")

# --- LÓGICA MATEMÁTICA ---
def calcular_prob_implicita(cuota):
    return (1 / cuota) * 100

def procesar_futbol(texto):
    bloques = re.split(r'ÚLTIMOS PARTIDOS:', texto)
    resumen = []
    for bloque in bloques:
        if not bloque.strip(): continue
        lineas = [l.strip() for l in bloque.strip().split('\n') if l.strip()]
        nombre = lineas[0]
        matches = re.findall(r'(\d)\s+(\d)\s+([GEP])', bloque)
        if matches:
            vics = sum(1 for m in matches if m[2] == 'G')
            goles = [int(m[0]) + int(m[1]) for m in matches]
            resumen.append({
                "nombre": nombre,
                "win_rate": (vics / len(matches)) * 100,
                "p_o15": (sum(1 for g in goles if g >= 2) / len(matches)) * 100,
                "p_o25": (sum(1 for g in goles if g >= 3) / len(matches)) * 100
            })
    return resumen

# --- INTERFAZ ---
st.title("⚽ Comparador de Probabilidades")
data_futbol = st.text_area("Pega datos de 365Scores:", height=150, key="texto_futbol")

st.subheader("📊 Cuotas vs Probabilidad Real")
col_1, col_2 = st.columns(2)
with col_1:
    c_local = st.number_input("Cuota Local", value=2.0)
    c_over15 = st.number_input("Cuota Over 1.5", value=1.3)
    c_over25 = st.number_input("Cuota Over 2.5", value=1.9)
with col_2:
    c_visita = st.number_input("Cuota Visitante", value=3.0)
    c_under15 = st.number_input("Cuota Under 1.5", value=3.5)
    c_under25 = st.number_input("Cuota Under 2.5", value=1.8)

if st.button("🔍 DETECTAR VALOR", use_container_width=True):
    stats = procesar_futbol(data_futbol)
    if len(stats) >= 2:
        e1, e2 = stats[0], stats[1]
        
        # Probabilidades basadas en DATOS (Promedio de ambos equipos)
        prob_gana_l = (e1['win_rate'] + (100 - e2['win_rate'])) / 2
        prob_gana_v = (e2['win_rate'] + (100 - e1['win_rate'])) / 2
        prob_o15 = (e1['p_o15'] + e2['p_o15']) / 2
        prob_o25 = (e1['p_o25'] + e2['p_o25']) / 2
        
        def mostrar_analisis(titulo, p_real, cuota):
            p_casa = calcular_prob_implicita(cuota)
            diff = p_real - p_casa
            st.write(f"**{titulo}**")
            st.write(f"Real: {round(p_real,1)}% | Casa: {round(p_casa,1)}%")
            if diff > 5: # Si hay más de 5% de diferencia a nuestro favor
                st.success(f"✅ VALOR ENCONTRADO (+{round(diff,1)}%)")
            elif diff < -5:
                st.error(f"❌ RIESGO ALTO (Casa paga poco)")
            else:
                st.warning(f"⚠️ Cuota Justa")
            st.markdown("---")

        mostrar_analisis(f"Gana {e1['nombre']}", prob_gana_l, c_local)
        mostrar_analisis(f"Gana {e2['nombre']}", prob_gana_v, c_visita)
        mostrar_analisis("Over 1.5 Goles", prob_o15, c_over15)
        mostrar_analisis("Over 2.5 Goles", prob_o25, c_over25)
    else:
        st.error("Datos insuficientes.")

if st.button("🗑️ BORRAR"):
    st.session_state["texto_futbol"] = ""
    st.rerun()
