import streamlit as st
import re
from datetime import datetime
import urllib.parse

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Sport Predictor Pro", page_icon="📈")

if 'historial' not in st.session_state:
    st.session_state['historial'] = []

# --- FUNCIONES ---
def limpiar_tenis(): st.session_state["texto_tenis"] = ""
def limpiar_futbol(): st.session_state["texto_futbol"] = ""

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
            goles_juegos = [int(m[0]) + int(m[1]) for m in matches]
            if deporte == "Tenis":
                metrica = sum(26.5 if (int(m[0]) + int(m[1])) >= 3 else 18.5 for m in matches) / len(matches)
                p_o15, p_o25 = 0, 0
            else:
                metrica = sum(goles_juegos) / len(matches)
                p_o15 = (sum(1 for g in goles_juegos if g >= 2) / len(matches)) * 100
                p_o25 = (sum(1 for g in goles_juegos if g >= 3) / len(matches)) * 100
            resumen.append({"nombre": nombre, "win_rate": (victorias/len(matches))*100, "metrica": metrica, "p_o15": p_o15, "p_o25": p_o25})
    return resumen

# --- INTERFAZ ---
st.title("🏆 Sport Value Predictor")
tab1, tab2, tab3 = st.tabs(["🎾 Tenis", "⚽ Fútbol", "📜 Historial"])

with tab1:
    st.header("Análisis de Tenis")
    input_tenis = st.text_area("Pega datos de Tenis:", height=180, key="texto_tenis")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("🚀 ANALIZAR TENIS", use_container_width=True):
            stats = procesar_datos(input_tenis, "Tenis")
            if len(stats) >= 2:
                j1, j2 = stats[0], stats[1]
                ganador = j1 if j1['win_rate'] > j2['win_rate'] else j2
                sets = "2-1" if abs(j1['win_rate'] - j2['win_rate']) < 15 else "2-0"
                puntos = round(j1['metrica'] + 3.5 if sets == "2-1" else j1['metrica'] - 1.5, 1)
                res = f"🎾 {j1['nombre']} vs {j2['nombre']}: Gana {ganador['nombre']} ({sets}, {puntos}j)"
                st.success(res)
                st.session_state['historial'].insert(0, f"{datetime.now().strftime('%H:%M')} - {res}")
    with c2: st.button("🗑️ BORRAR TENIS", on_click=limpiar_tenis)

with tab2:
    st.header("Análisis de Fútbol")
    input_futbol = st.text_area("Pega datos de Fútbol:", height=180, key="texto_futbol")
    col_c1, col_c2 = st.columns(2)
    with col_c1:
        c_loc = st.number_input("Cuota Local", value=2.00)
        c_o15 = st.number_input("Cuota Over 1.5", value=1.30)
    with col_c2:
        c_vis = st.number_input("Cuota Visita", value=3.00)
        c_u15 = st.number_input("Cuota Under 1.5", value=3.50)

    if st.button("🔍 DETECTAR VALOR", use_container_width=True, type="primary"):
        stats = procesar_datos(input_futbol, "Futbol")
        if len(stats) >= 2:
            e1, e2 = stats[0], stats[1]
            p_l = (e1['win_rate'] + (100 - e2['win_rate'])) / 2
            p_o15 = (e1['p_o15'] + e2['p_o15']) / 2
            
            def mostrar_v(label, p_r, cuota):
                p_c = (1/cuota)*100
                diff = p_r - p_c
                st.write(f"**{label}** | Real: {round(p_r,1)}% vs Casa: {round(p_c,1)}%")
                if diff > 5: st.success(f"✅ VALOR (+{round(diff,1)}%)")
                elif diff < -5: st.error("❌ RIESGO")
                else: st.warning("⚠️ JUSTO")
            
            mostrar_v(f"Gana {e1['nombre']}", p_l, c_loc)
            mostrar_v("Over 1.5 Goles", p_o15, c_o15)
            st.session_state['historial'].insert(0, f"⚽ {e1['nombre']} vs {e2['nombre']} | O1.5: {round(p_o15,1)}%")
    st.button("🗑️ BORRAR FÚTBOL", on_click=limpiar_futbol)

with tab3:
    st.header("Historial y Envío")
    if st.session_state['historial']:
        texto_hist = "\n".join(st.session_state['historial'])
        st.text_area("Resumen:", value=texto_hist, height=250)
        
        # BOTÓN DE ENVÍO SEGURO (Abre Gmail directamente)
        sujeto = urllib.parse.quote("Mi Reporte de Apuestas")
        cuerpo = urllib.parse.quote(texto_hist)
        mail_url = f"https://mail.google.com/mail/?view=cm&fs=1&to=williamvg120@gmail.com&su={sujeto}&body={cuerpo}"
        
        st.markdown(f'''
            <a href="{mail_url}" target="_blank" style="text-decoration: none;">
                <div style="background-color: #ff4b4b; color: white; padding: 10px; text-align: center; border-radius: 5px; font-weight: bold;">
                    📩 ENVIAR REPORTE A GMAIL
                </div>
            </a>
            ''', unsafe_allow_supported_markup=True)
    else:
        st.write("Historial vacío.")
