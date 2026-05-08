import streamlit as st
import re
from datetime import datetime
import urllib.parse

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Sport Predictor Pro V4", page_icon="🏆", layout="centered")

# --- INICIALIZACIÓN DE ESTADOS (Persistencia de datos) ---
if 'historial' not in st.session_state:
    st.session_state['historial'] = []
if 'texto_tenis' not in st.session_state:
    st.session_state['texto_tenis'] = ""
if 'texto_futbol' not in st.session_state:
    st.session_state['texto_futbol'] = ""

# --- FUNCIONES DE LIMPIEZA ---
def limpiar_tenis():
    st.session_state["texto_tenis"] = ""

def limpiar_futbol():
    st.session_state["texto_futbol"] = ""

# --- LÓGICA DE PROCESAMIENTO ESTADÍSTICO ---
def procesar_datos(texto, deporte):
    bloques = re.split(r'ÚLTIMOS PARTIDOS:', texto)
    resumen = []
    for bloque in bloques:
        if not bloque.strip(): continue
        lineas = [l.strip() for l in bloque.strip().split('\n') if l.strip()]
        if not lineas: continue
        nombre = lineas[0]
        # Captura marcador y resultado G/P/E
        matches = re.findall(r'(\d)\s+(\d)\s+([GEP])', bloque)
        if matches:
            victorias = sum(1 for m in matches if m[2] == 'G')
            goles_juegos = [int(m[0]) + int(m[1]) for m in matches]
            
            if deporte == "Tenis":
                # Estimación de juegos basada en sets (2-0 vs 2-1)
                metrica = sum(26.5 if (int(m[0]) + int(m[1])) >= 3 else 18.5 for m in matches) / len(matches)
                p_o15, p_o25 = 0, 0
            else:
                # Métricas de fútbol
                metrica = sum(goles_juegos) / len(matches)
                p_o15 = (sum(1 for g in goles_juegos if g >= 2) / len(matches)) * 100
                p_o25 = (sum(1 for g in goles_juegos if g >= 3) / len(matches)) * 100
                
            resumen.append({
                "nombre": nombre,
                "win_rate": (victorias / len(matches)) * 100,
                "metrica": metrica,
                "p_o15": p_o15,
                "p_o25": p_o25
            })
    return resumen

# --- LÓGICA DE ANÁLISIS DE CONTEXTO (Noticias/Rachas) ---
def analizar_contexto(texto):
    ajuste = {"ganador": 0, "goles": 0, "notas": []}
    if not texto: return ajuste
    
    t = texto.lower()
    # Palabras clave para Under/Pocos Goles
    if any(w in t for w in ["menos de 2", "pocas anotaciones", "sin ver puerta", "under", "baja produccion"]):
        ajuste["goles"] -= 15
        ajuste["notas"].append("📉 Contexto: Tendencia UNDER detectada en noticias.")
    
    # Palabras clave para Over/Goleadores
    if any(w in t for w in ["más de 2", "ofensivo", "goleador", "over", "ambos marcan"]):
        ajuste["goles"] += 15
        ajuste["notas"].append("📈 Contexto: Tendencia OVER detectada en noticias.")
        
    # Alertas de Bajas/Historial
    if any(w in t for w in ["baja", "lesion", "expulsado", "ausencia"]):
        ajuste["notas"].append("⚠️ Alerta: El reporte menciona bajas o suspensiones.")
    if "historial" in t or "domina" in t:
        ajuste["notas"].append("📚 Contexto: El historial previo es un factor relevante aquí.")
        
    return ajuste

# --- INTERFAZ DE USUARIO ---
st.title("🏆 Sport Predictor Pro V4")
st.markdown("---")

tab1, tab2, tab3 = st.tabs(["🎾 Tenis", "⚽ Fútbol", "📜 Historial"])

# --- PESTAÑA 1: TENIS ---
with tab1:
    st.header("Analizador de Tenis")
    input_tenis = st.text_area("Pega datos de 365Scores (Tenis):", height=150, key="texto_tenis")
    c_t1, c_t2 = st.columns(2)
    with c_t1:
        if st.button("🚀 ANALIZAR TENIS", use_container_width=True, type="primary"):
            stats = procesar_datos(input_tenis, "Tenis")
            if len(stats) >= 2:
                j1, j2 = stats[0], stats[1]
                ganador = j1 if j1['win_rate'] > j2['win_rate'] else j2
                diff = abs(j1['win_rate'] - j2['win_rate'])
                sets = "2-1" if diff < 15 else "2-0"
                puntos = round(j1['metrica'] + 3.5 if sets == "2-1" else j1['metrica'] - 1.5, 1)
                
                st.success(f"**Favorito:** {ganador['nombre']} | **Marcador:** {sets} | **Juegos Totales:** {puntos}")
                st.session_state['historial'].insert(0, f"🎾 {datetime.now().strftime('%H:%M')} - {j1['nombre']} vs {j2['nombre']}: Gana {ganador['nombre']} ({puntos}j)")
            else:
                st.error("Datos insuficientes para comparar jugadores.")
    with c_t2:
        st.button("🗑️ BORRAR", on_click=limpiar_tenis, use_container_width=True, key="clear_t")

# --- PESTAÑA 2: FÚTBOL ---
with tab2:
    st.header("Fútbol: Estadística + Contexto")
    data_futbol = st.text_area("1. Pega Datos 365Scores:", height=150, key="texto_futbol")
    contexto_input = st.text_area("2. Pega Noticias/Rachas (Contexto):", height=100, placeholder="Ej: Bajas, localía fuerte, historial de pocos goles...")
    
    st.subheader("💰 Cuotas de la Casa")
    f1, f2 = st.columns(2)
    with f1:
        c_loc = st.number_input("Cuota Local", value=2.00, step=0.01)
        c_o15 = st.number_input("Cuota Over 1.5", value=1.35, step=0.01)
    with f2:
        c_vis = st.number_input("Cuota Visitante", value=3.20, step=0.01)
        c_u15 = st.number_input("Cuota Under 1.5", value=3.40, step=0.01)

    if st.button("🔍 DETECTAR VALOR REAL", use_container_width=True, type="primary"):
        stats = procesar_datos(data_futbol, "Futbol")
        ajustes = analizar_contexto(contexto_input)
        
        if len(stats) >= 2:
            e1, e2 = stats[0], stats[1]
            # Probabilidad Base
            p_real_l = (e1['win_rate'] + (100 - e2['win_rate'])) / 2
            p_real_o15 = ((e1['p_o15'] + e2['p_o15']) / 2) + ajustes["goles"] # Ajuste por noticias
            
            st.subheader("🎯 Veredicto Inteligente")
            for nota in ajustes["notas"]: st.info(nota)

            def mostrar_v(label, p_r, cuota):
                p_c = (1/cuota)*100
                diff = p_r - p_c
                st.write(f"**{label}** | Real: {round(p_r,1)}% vs Casa: {round(p_c,1)}%")
                if diff > 6: st.success(f"✅ ¡VALOR ENCONTRADO! (+{round(diff,1)}%)")
                elif diff < -6: st.error("❌ RIESGO ALTO: La casa paga muy poco.")
                else: st.warning("⚠️ CUOTA JUSTA: No hay ventaja clara.")
                st.markdown("---")

            mostrar_v(f"Gana {e1['nombre']}", p_real_l, c_loc)
            mostrar_v("Over 1.5 Goles", p_real_o15, c_o15)
            
            st.session_state['historial'].insert(0, f"⚽ {datetime.now().strftime('%H:%M')} - {e1['nombre']} vs {e2['nombre']} | Valor detectado")
        else:
            st.error("Datos insuficientes para el análisis.")
            
    st.button("🗑️ BORRAR", on_click=limpiar_futbol, use_container_width=True, key="clear_f")

# --- PESTAÑA 3: HISTORIAL Y ENVÍO ---
with tab3:
    st.header("Historial de Análisis")
    if st.session_state['historial']:
        texto_historial = "\n".join(st.session_state['historial'])
        st.text_area("Copia tus resultados:", value=texto_historial, height=250)
        
        # Preparación de enlace a Gmail
        sujeto = urllib.parse.quote("Reporte de Apuestas Deportivas")
        cuerpo = urllib.parse.quote(texto_historial)
        mail_url = f"https://mail.google.com/mail/?view=cm&fs=1&to=williamvg120@gmail.com&su={sujeto}&body={cuerpo}"
        
        st.markdown(f'''
            <a href="{mail_url}" target="_blank" style="text-decoration: none;">
                <div style="background-color: #ff4b4b; color: white; padding: 12px; text-align: center; border-radius: 8px; font-weight: bold; margin-top: 20px; cursor: pointer;">
                    📩 ENVIAR REPORTE A GMAIL
                </div>
            </a>
            ''', unsafe_allow_html=True)
    else:
        st.write("No hay análisis registrados en esta sesión.")
