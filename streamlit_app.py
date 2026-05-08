import streamlit as st
import re
from datetime import datetime
import urllib.parse

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Sport Predictor Pro V5", page_icon="🏆", layout="centered")

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

# --- LÓGICA DE PROCESAMIENTO REFORZADA ---
def procesar_datos(texto, deporte):
    # Separamos por "ÚLTIMOS PARTIDOS" o por líneas que parecen nombres de equipos
    bloques = re.split(r'ÚLTIMOS PARTIDOS:', texto, flags=re.IGNORECASE)
    resumen = []
    
    for bloque in bloques:
        if not bloque.strip() or len(bloque) < 10: continue
        
        lineas = [l.strip() for l in bloque.strip().split('\n') if l.strip()]
        if not lineas: continue
        
        nombre = lineas[0]
        # Regex mejorado para capturar: Goles Local, Goles Visita y Resultado (G/E/P)
        # Busca patrones como "2 1 G" o "1 - 1 E"
        matches = re.findall(r'(\d)\s*[-]*\s*(\d)\s*([GEP])', bloque, flags=re.IGNORECASE)
        
        if matches:
            victorias = sum(1 for m in matches if m[2].upper() == 'G')
            goles_partido = [int(m[0]) + int(m[1]) for m in matches]
            btts_count = sum(1 for m in matches if int(m[0]) > 0 and int(m[1]) > 0)
            
            if deporte == "Tenis":
                # En tenis sumamos los sets para estimar juegos
                metrica = sum(26.5 if (int(m[0]) + int(m[1])) >= 3 else 18.5 for m in matches) / len(matches)
                p_o15, p_o25, p_btts = 0, 0, 0
            else:
                metrica = sum(goles_partido) / len(matches)
                p_o15 = (sum(1 for g in goles_partido if g >= 2) / len(matches)) * 100
                p_o25 = (sum(1 for g in goles_partido if g >= 3) / len(matches)) * 100
                p_btts = (btts_count / len(matches)) * 100
                
            resumen.append({
                "nombre": nombre,
                "win_rate": (victorias / len(matches)) * 100,
                "metrica": metrica,
                "p_o15": p_o15,
                "p_o25": p_o25,
                "p_btts": p_btts,
                "partidos_analizados": len(matches)
            })
    return resumen

def analizar_contexto(texto):
    ajuste = {"goles": 0, "notas": []}
    if not texto: return ajuste
    t = texto.lower()
    if any(w in t for w in ["menos de", "pocas anotaciones", "under", "baja produccion", "pocos goles"]):
        ajuste["goles"] -= 12
        ajuste["notas"].append("📉 Contexto: Tendencia UNDER detectada.")
    if any(w in t for w in ["más de", "over", "ambos marcan", "goleador", "muchos goles"]):
        ajuste["goles"] += 12
        ajuste["notas"].append("📈 Contexto: Tendencia OVER/BTTS detectada.")
    return ajuste

# --- INTERFAZ ---
st.title("🏆 Sport Predictor Pro V5")
tab1, tab2, tab3 = st.tabs(["🎾 Tenis", "⚽ Fútbol", "📜 Historial"])

with tab1:
    st.header("Tenis")
    input_tenis = st.text_area("Pega datos aquí:", height=150, key="texto_tenis")
    if st.button("🚀 ANALIZAR TENIS", use_container_width=True):
        if input_tenis:
            stats = procesar_datos(input_tenis, "Tenis")
            if len(stats) >= 2:
                j1, j2 = stats[0], stats[1]
                ganador = j1 if j1['win_rate'] > j2['win_rate'] else j2
                st.success(f"Favorito: {ganador['nombre']} (Basado en {ganador['partidos_analizados']} partidos)")
                st.session_state['historial'].insert(0, f"🎾 Tenis: {j1['nombre']} vs {j2['nombre']}")
            else:
                st.error("No se detectaron 2 jugadores. Asegúrate de copiar el historial completo de ambos.")
    st.button("🗑️ BORRAR", on_click=limpiar_tenis, key="c_t")

with tab2:
    st.header("Fútbol: Análisis de Valor")
    data_f = st.text_area("1. Datos 365Scores:", height=150, key="texto_futbol")
    contexto_f = st.text_area("2. Contexto/Noticias:", height=80, key="contexto_f")
    
    st.subheader("💰 Cuotas")
    col1, col2, col3 = st.columns(3)
    with col1:
        c_loc = st.number_input("Cuota Local", value=2.0, step=0.01)
        c_vis = st.number_input("Cuota Visita", value=3.0, step=0.01)
    with col2:
        c_o15 = st.number_input("Cuota Over 1.5", value=1.3, step=0.01)
        c_u15 = st.number_input("Cuota Under 1.5", value=3.5, step=0.01)
    with col3:
        c_o25 = st.number_input("Cuota Over 2.5", value=2.0, step=0.01)
        c_u25 = st.number_input("Cuota Under 2.5", value=1.8, step=0.01)
    
    c_btts = st.number_input("Cuota BTTS (Ambos Marcan)", value=1.9, step=0.01)

    if st.button("🔍 ANALIZAR VALOR TOTAL", use_container_width=True, type="primary"):
        if data_f:
            stats = procesar_datos(data_f, "Futbol")
            aj = analizar_contexto(contexto_f)
            if len(stats) >= 2:
                e1, e2 = stats[0], stats[1]
                p_l = (e1['win_rate'] + (100 - e2['win_rate'])) / 2
                p_o15 = ((e1['p_o15'] + e2['p_o15']) / 2) + aj["goles"]
                p_o25 = ((e1['p_o25'] + e2['p_o25']) / 2) + aj["goles"]
                p_btts = ((e1['p_btts'] + e2['p_btts']) / 2) + (aj["goles"] / 2)
                
                st.subheader("🎯 Resultados")
                for n in aj["notas"]: st.info(n)

                def check(label, p_r, cuota):
                    p_c = (1/max(cuota, 1.01))*100
                    diff = p_r - p_c
                    st.write(f"**{label}** | Real: {round(p_r,1)}% vs Casa: {round(p_c,1)}%")
                    if diff > 5: st.success(f"✅ VALOR (+{round(diff,1)}%)")
                    elif diff < -5: st.error("❌ RIESGO (Casa paga poco)")
                    else: st.warning("⚠️ JUSTO")

                check(f"Gana {e1['nombre']}", p_l, c_loc)
                check("Over 1.5", p_o15, c_o15)
                check("Under 1.5", (100-p_o15), c_u15)
                check("Over 2.5", p_o25, c_o25)
                check("Under 2.5", (100-p_o25), c_u25)
                check("BTTS (Ambos Marcan)", p_btts, c_btts)
                
                st.session_state['historial'].insert(0, f"⚽ {e1['nombre']} vs {e2['nombre']}")
            else:
                st.error("No se detectaron 2 equipos. Verifica que el texto incluya 'ÚLTIMOS PARTIDOS' para ambos.")
        else:
            st.warning("Pega los datos antes de analizar.")
            
    st.button("🗑️ BORRAR", on_click=limpiar_futbol, key="c_f")

with tab3:
    st.header("Historial")
    if st.session_state['historial']:
        txt_h = "\n".join(st.session_state['historial'])
        st.text_area("Historial:", value=txt_h, height=200)
        mail_url = f"https://mail.google.com/mail/?view=cm&fs=1&to=williamvg120@gmail.com&su=Reporte&body={urllib.parse.quote(txt_h)}"
        st.markdown(f'<a href="{mail_url}" target="_blank" style="text-decoration:none;"><div style="background-color:#ff4b4b;color:white;padding:12px;text-align:center;border-radius:8px;font-weight:bold;">📩 ENVIAR A GMAIL</div></a>', unsafe_allow_html=True)
