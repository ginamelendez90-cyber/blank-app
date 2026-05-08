import streamlit as st
import re
from datetime import datetime
import urllib.parse

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Sport Predictor Pro V6", page_icon="🏆", layout="centered")

# --- INICIALIZACIÓN DE ESTADOS ---
if 'historial' not in st.session_state:
    st.session_state['historial'] = []
if 'texto_tenis' not in st.session_state:
    st.session_state['texto_tenis'] = ""
if 'texto_futbol' not in st.session_state:
    st.session_state['texto_futbol'] = ""

# --- FUNCIONES DE LIMPIEZA ---
def limpiar_tenis(): st.session_state["texto_tenis"] = ""
def limpiar_futbol(): st.session_state["texto_futbol"] = ""

# --- LÓGICA DE PROCESAMIENTO ---
def procesar_datos(texto, deporte):
    bloques = re.split(r'ÚLTIMOS PARTIDOS:', texto, flags=re.IGNORECASE)
    resumen = []
    for bloque in bloques:
        if not bloque.strip() or len(bloque) < 10: continue
        lineas = [l.strip() for l in bloque.strip().split('\n') if l.strip()]
        if not lineas: continue
        nombre = lineas[0]
        matches = re.findall(r'(\d)\s*[-]*\s*(\d)\s*([GEP])', bloque, flags=re.IGNORECASE)
        if matches:
            victorias = sum(1 for m in matches if m[2].upper() == 'G')
            goles_partido = [int(m[0]) + int(m[1]) for m in matches]
            btts_count = sum(1 for m in matches if int(m[0]) > 0 and int(m[1]) > 0)
            
            resumen.append({
                "nombre": nombre,
                "win_rate": (victorias / len(matches)) * 100,
                "p_o15": (sum(1 for g in goles_partido if g >= 2) / len(matches)) * 100,
                "p_o25": (sum(1 for g in goles_partido if g >= 3) / len(matches)) * 100,
                "p_btts": (btts_count / len(matches)) * 100,
                "metrica_tenis": sum(26.5 if (int(m[0]) + int(m[1])) >= 3 else 18.5 for m in matches) / len(matches) if deporte == "Tenis" else 0
            })
    return resumen

def analizar_contexto(texto):
    ajuste = {"goles": 0, "notas": []}
    if not texto: return ajuste
    t = texto.lower()
    if any(w in t for w in ["menos de", "under", "baja produccion", "pocos goles"]):
        ajuste["goles"] -= 12
        ajuste["notas"].append("📉 Contexto: Tendencia UNDER.")
    if any(w in t for w in ["más de", "over", "ambos marcan", "muchos goles"]):
        ajuste["goles"] += 12
        ajuste["notas"].append("📈 Contexto: Tendencia OVER/BTTS.")
    return ajuste

# --- INTERFAZ ---
st.title("🏆 Sport Predictor Pro V6")
tab1, tab2, tab3 = st.tabs(["🎾 Tenis", "⚽ Fútbol", "📜 Historial Detallado"])

with tab1:
    st.header("Tenis")
    data_t = st.text_area("Pega datos Tenis:", height=150, key="texto_tenis")
    if st.button("🚀 ANALIZAR TENIS", use_container_width=True):
        stats = procesar_datos(data_t, "Tenis")
        if len(stats) >= 2:
            j1, j2 = stats[0], stats[1]
            ganador = j1 if j1['win_rate'] > j2['win_rate'] else j2
            res = f"Favorito: {ganador['nombre']} | Juegos Est.: {round(j1['metrica_tenis'],1)}"
            st.success(res)
            st.session_state['historial'].insert(0, f"🎾 {j1['nombre']} vs {j2['nombre']} -> {res}")
    st.button("🗑️ BORRAR", on_click=limpiar_tenis, key="btn_clear_t")

with tab2:
    st.header("Fútbol: Análisis de Valor")
    data_f = st.text_area("1. Datos 365Scores:", height=150, key="texto_futbol")
    contexto_f = st.text_area("2. Contexto:", height=80, key="ctx_f")
    
    st.subheader("💰 Cuotas (Sin límites)")
    c1, c2, c3 = st.columns(3)
    with c1:
        # Eliminados los límites de min/max para total libertad
        cl = st.number_input("Cuota Local", value=2.0, format="%.2f")
        cv = st.number_input("Cuota Visita", value=3.0, format="%.2f")
    with c2:
        co15 = st.number_input("Cuota O1.5", value=1.3, format="%.2f")
        cu15 = st.number_input("Cuota U1.5", value=3.5, format="%.2f")
    with c3:
        co25 = st.number_input("Cuota O2.5", value=2.0, format="%.2f")
        cu25 = st.number_input("Cuota U2.5", value=1.8, format="%.2f")
    
    cbtts = st.number_input("Cuota BTTS", value=1.9, format="%.2f")

    if st.button("🔍 ANALIZAR VALOR TOTAL", use_container_width=True, type="primary"):
        stats = procesar_datos(data_f, "Futbol")
        aj = analizar_contexto(contexto_f)
        if len(stats) >= 2:
            e1, e2 = stats[0], stats[1]
            p_l = (e1['win_rate'] + (100 - e2['win_rate'])) / 2
            p_o15 = ((e1['p_o15'] + e2['p_o15']) / 2) + aj["goles"]
            p_o25 = ((e1['p_o25'] + e2['p_o25']) / 2) + aj["goles"]
            p_btts = ((e1['p_btts'] + e2['p_btts']) / 2) + (aj["goles"]/2)
            
            res_partido = f"⚽ {e1['nombre']} vs {e2['nombre']}\n"
            
            def check_val(label, p_r, cuota):
                # Protección básica contra división por cero si la cuota es 0
                cu
