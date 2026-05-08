import streamlit as st
import re
from datetime import datetime

st.set_page_config(page_title="Multi-Sport Value Predictor", page_icon="📈", layout="centered")

# --- INICIALIZACIÓN DE ESTADOS ---
if 'historial' not in st.session_state:
    st.session_state['historial'] = []

# --- FUNCIONES DE LIMPIEZA ---
def limpiar_tenis(): st.session_state["texto_tenis"] = ""
def limpiar_futbol(): st.session_state["texto_futbol"] = ""

# --- LÓGICA DE PROCESAMIENTO ---
def procesar_datos(texto, deporte):
    bloques = re.split(r'ÚLTIMOS PARTIDOS:', texto)
    resumen = []
    for bloque in bloques:
        if not bloque.strip(): continue
        lineas = [l.strip() for l in bloque.strip().split('\n') if l.strip()]
        if not lineas: continue
        nombre = lineas[0]
        matches = re.findall(r'(\d)\s+(\d)\s+([GEP])', bloque)
        if matches:
            victorias = sum(1 for m in matches if m[2] == 'G')
            goles_partido = [int(m[0]) + int(m[1]) for m in matches]
            
            if deporte == "Tenis":
                valor_metrica = sum(26.5 if (int(m[0]) + int(m[1])) >= 3 else 18.5 for m in matches) / len(matches)
                prob_over = 0 # No aplica para fútbol
            else:
                # Fútbol: Promedio de goles y % de partidos con Over 1.5
                valor_metrica = sum(goles_partido) / len(matches)
                prob_over = sum(1 for g in goles_partido if g >= 2) / len(matches)
                
            resumen.append({
                "nombre": nombre,
                "win_rate": victorias / len(matches),
                "metrica": valor_metrica,
                "prob_over_15": prob_over,
                "racha": f"{victorias}-{sum(1 for m in matches if m[2] == 'E')}-{sum(1 for m in matches if m[2] == 'P')}" if deporte == "Futbol" else f"{victorias}-{len(matches)-victorias}"
            })
    return resumen

# --- INTERFAZ ---
tab1, tab2, tab3 = st.tabs(["🎾 Tenis", "⚽ Fútbol", "📜 Historial"])

with tab1:
    st.header("Análisis de Tenis")
    data_tenis = st.text_area("Datos de Tenis:", height=150, key="texto_tenis")
    if st.button("🚀 ANALIZAR TENIS"):
        stats = procesar_datos(data_tenis, "Tenis")
        if len(stats) >= 2:
            j1, j2 = stats[0], stats[1]
            ganador = j1 if j1['win_rate'] > j2['win_rate'] else j2
            st.success(f"**Favorito:** {ganador['nombre']}")
            st.session_state['historial'].insert(0, {"msg": f"Tenis: {j1['nombre']} vs {j2['nombre']}"})

with tab2:
    st.header("Análisis de Fútbol + Cuotas")
    data_futbol = st.text_area("Datos de Fútbol:", height=150, key="texto_futbol")
    
    col_cuota1, col_cuota2 = st.columns(2)
    with col_cuota1:
        cuota_local = st.number_input("Cuota Local (Casa)", min_value=1.01, value=2.0, step=0.1)
    with col_cuota2:
        cuota_over15 = st.number_input("Cuota Over 1.5 (Casa)", min_value=1.01, value=1.5, step=0.1)

    c1, c2 = st.columns(2)
    with c1:
        if st.button("🚀 CALCULAR VALOR"):
            stats = procesar_datos(data_futbol, "Futbol")
            if len(stats) >= 2:
                e1, e2 = stats[0], stats[1]
                
                # Cálculo de Probabilidades Reales
                prob_ganador_real = ((e1['win_rate'] + (1 - e2['win_rate'])) / 2) * 100
                prob_over15_real = ((e1['prob_over_15'] + e2['prob_over_15']) / 2) * 100
                
                # Verificación de Valor (Probabilidad Real > 1/Cuota)
                valor_ganador = prob_ganador_real > (1/cuota_local * 100)
                valor_over = prob_over15_real > (1/cuota_over15 * 100)

                st.subheader("🎯 Veredicto de Fútbol")
                
                # Mostrar Gana Local
                st.write(f"**Gana {e1['nombre']}:** {round(prob_ganador_real, 1)}% de probabilidad.")
                if valor_ganador: st.success("✅ ¡HAY VALOR EN EL LOCAL!")
                else: st.error("❌ Cuota muy baja para el riesgo.")

                st.markdown("---")
                
                # Mostrar Over 1.5
                st.write(f"**Probabilidad Over 1.5:** {round(prob_over15_real, 1)}%")
                if valor_over: st.success("✅ ¡HAY VALOR EN EL OVER 1.5!")
                else: st.warning("⚠️ Probabilidad ajustada a la cuota.")

                st.session_state['historial'].insert(0, {"msg": f"Futbol: {e1['nombre']} vs {e2['nombre']} | Over 1.5: {round(prob_over15_real,1)}%"})

    with c2:
        st.button("🗑️ BORRAR FÚTBOL", on_click=limpiar_futbol)

with tab3:
    st.header("Historial")
    for h in st.session_state['historial']:
        st.write(h['msg'])
