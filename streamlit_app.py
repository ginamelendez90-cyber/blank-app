import streamlit as st
import re
from datetime import datetime
import urllib.parse

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Sport Predictor Pro V4", page_icon="🏆", layout="centered")

if 'historial' not in st.session_state:
    st.session_state['historial'] = []

# --- FUNCIONES DE APOYO ---
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

def analizar_contexto(texto):
    ajuste = {"ganador": 0, "goles": 0, "notas": []}
    texto = texto.lower()
    
    # Lógica de Goles
    if any(word in texto for word in ["menos de 2.5", "pocas anotaciones", "sin ver puerta", "under"]):
        ajuste["goles"] -= 15
        ajuste["notas"].append("📉 Tendencia Under detectada en noticias.")
    if any(word in texto for word in ["más de 2.5", "ofensivo", "goleador", "over"]):
        ajuste["goles"] += 15
        ajuste["notas"].append("📈 Tendencia Over detectada en noticias.")
        
    # Lógica de Ganador
    if any(word in texto for word in ["bajas", "lesionados", "expulsado"]):
        ajuste["notas"].append("⚠️ Alerta de bajas/ausencias importantes.")
    if "dominio" in texto or "historial" in texto:
        ajuste["notas"].append("📚 Historial favorece al equipo analizado.")
        
    return ajuste

# --- INTERFAZ ---
st.title("🏆 Sport Predictor Pro V4")
tab1, tab2, tab3 = st.tabs(["🎾 Tenis", "⚽ Fútbol", "📜 Historial"])

with tab1:
    st.header("Análisis de Tenis")
    data_tenis = st.text_area("Pega datos de Tenis:", height=150, key="texto_tenis")
    if st.button("🚀 ANALIZAR TENIS", use_container_width=True):
        stats = procesar_datos(data_tenis, "Tenis")
        if len(stats) >= 2:
            j1, j2 = stats[0], stats[1]
            ganador = j1 if j1['win_rate'] > j2['win_rate'] else j2
            sets = "2-1" if abs(j1['win_rate'] - j2['win_rate']) < 15 else "2-0"
            puntos = round(j1['metrica'] + 3.5 if sets == "2-1" else j1['metrica'] - 1.5, 1)
            st.success(f"**Favorito:** {ganador['nombre']} | **Sets:** {sets} | **Juegos:** {puntos}")
            st.session_state['historial'].insert(0, f"🎾 {j1['nombre']} vs {j2['nombre']}: {ganador['nombre']}")
    st.button("🗑️ BORRAR TENIS", on_click=limpiar_tenis)

with tab2:
    st.header("Análisis de Fútbol + Contexto")
    data_futbol = st.text_area("1. Pega Datos 365Scores:", height=150, key="texto_futbol")
    contexto_txt = st.text_area("2. Pega Noticias/Contexto (Opcional):", height=100, placeholder="Ej: Bajas, historial de pocos goles...")
    
    st.subheader("💰 Cuotas")
    c1, c2 = st.columns(2)
    with c1:
        cloc = st.number_input("Cuota Local", value=2.0)
        co15 = st.number_input("Cuota Over 1.5", value=1.3)
    with c2:
        cvis = st.number_input("Cuota Visita", value=3.0)
        cu15 = st.number_input("Cuota Under 1.5", value=3.5)

    if st.button("🔍 DETECTAR VALOR CON CONTEXTO", use_container_width=True, type="primary"):
        stats = procesar_datos(data_futbol, "Futbol")
        ajustes = analizar_contexto(contexto_txt)
        
        if len(stats) >= 2:
            e1, e2 = stats[0], stats[1]
            p_l = ((e1['win_rate'] + (100 - e2['win_rate'])) / 2)
            p_o15 = ((e1['p_o15'] + e2['p_o15']) / 2) + ajustes["goles"] # Aplicamos el ajuste de contexto
            
            st.subheader("🎯 Veredicto Final")
            for nota in ajustes["notas"]: st.info(nota)

            def check_v(label, p_r, cuota):
                p_c = (1/cuota)*100
                diff = p_r - p_c
                st.write(f"**{label}** | Prob. Final: {round(p_r,1)}% vs Casa: {round(p_c,1)}%")
                if diff > 5: st.success(f"✅ VALOR (+{round(diff,1)}%)")
                elif diff < -5: st.error("❌ RIESGO")
                else: st.warning("⚠️ JUSTO")

            check_v(f"Gana {e1['nombre']}", p_l, cloc)
            check_v("Over 1.5 Goles", p_o15, co15)
            st.session_state['historial'].insert(0, f"⚽ {e1['nombre']} vs {e2['nombre']} - Valor detectado con contexto.")
    st.button("🗑️ BORRAR FÚTBOL", on_click=limpiar_futbol)

with tab3:
    st.header("Historial")
    if st.session_state['historial']:
        hist_txt = "\n".join(st.session_state['historial'])
        st.text_area("Historial:", value=hist_txt, height=200)
        sujeto = urllib.parse.quote("Reporte Deportivo")
        cuerpo = urllib.parse.quote(hist_txt)
        mail_url = f"https://mail.google.com/mail/?view=cm&fs=1&to=williamvg120@gmail.com&su={sujeto}&body={cuerpo}"
        st.markdown(f'<a href="{mail_url}" target="_blank" style="text-decoration:none;"><div style="background-color:#ff4b4b;color:white;padding:12px;text-align:center;border-radius:8px;font-weight:bold;">📩 ENVIAR A GMAIL</div></a>', unsafe_allow_html=True)
