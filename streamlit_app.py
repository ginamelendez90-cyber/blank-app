import streamlit as st
import re
from datetime import datetime

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Sport Predictor Pro", page_icon="📈", layout="centered")

# --- INICIALIZACIÓN DE ESTADOS (Para no perder datos) ---
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
            goles_juegos = [int(m[0]) + int(m[1]) for m in matches]
            
            if deporte == "Tenis":
                metrica = sum(26.5 if (int(m[0]) + int(m[1])) >= 3 else 18.5 for m in matches) / len(matches)
                p_o15, p_o25 = 0, 0
            else:
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

# --- INTERFAZ PRINCIPAL ---
st.title("🏆 Sport Value Predictor")
tab1, tab2, tab3 = st.tabs(["🎾 Tenis", "⚽ Fútbol", "📜 Historial / Reporte"])

# --- PESTAÑA 1: TENIS ---
with tab1:
    st.header("Análisis de Tenis")
    input_tenis = st.text_area("Pega datos de Tenis:", height=180, key="texto_tenis")
    colt1, colt2 = st.columns(2)
    with colt1:
        if st.button("🚀 ANALIZAR TENIS", use_container_width=True):
            stats = procesar_datos(input_tenis, "Tenis")
            if len(stats) >= 2:
                j1, j2 = stats[0], stats[1]
                ganador = j1 if j1['win_rate'] > j2['win_rate'] else j2
                diff = abs(j1['win_rate'] - j2['win_rate'])
                sets = "2-1" if diff < 15 else "2-0"
                puntos = round(j1['metrica'] + 3.5 if sets == "2-1" else j1['metrica'] - 1.5, 1)
                
                st.success(f"**Ganador:** {ganador['nombre']} | **Sets:** {sets} | **Juegos:** {puntos}")
                st.session_state['historial'].insert(0, f"🎾 {datetime.now().strftime('%H:%M')} - {j1['nombre']} vs {j2['nombre']}: Gana {ganador['nombre']} ({puntos}j)")
    with colt2:
        st.button("🗑️ BORRAR TENIS", on_click=limpiar_tenis, use_container_width=True)

# --- PESTAÑA 2: FÚTBOL ---
with tab2:
    st.header("Fútbol: Probabilidad vs Casa")
    input_futbol = st.text_area("Pega datos de Fútbol:", height=180, key="texto_futbol")
    
    st.subheader("💰 Cuotas Actuales")
    c_l1, c_l2 = st.columns(2)
    with c_l1:
        c_loc = st.number_input("Cuota Local", value=2.00, step=0.01)
        c_o15 = st.number_input("Cuota Over 1.5", value=1.30, step=0.01)
        c_o25 = st.number_input("Cuota Over 2.5", value=1.90, step=0.01)
    with c_l2:
        c_vis = st.number_input("Cuota Visita", value=3.00, step=0.01)
        c_u15 = st.number_input("Cuota Under 1.5", value=3.50, step=0.01)
        c_u25 = st.number_input("Cuota Under 2.5", value=1.85, step=0.01)

    colf1, colf2 = st.columns(2)
    with colf1:
        if st.button("🔍 DETECTAR VALOR", use_container_width=True, type="primary"):
            stats = procesar_datos(input_futbol, "Futbol")
            if len(stats) >= 2:
                e1, e2 = stats[0], stats[1]
                # Lógica de probabilidad real vs casa
                p_real_l = (e1['win_rate'] + (100 - e2['win_rate'])) / 2
                p_real_o15 = (e1['p_o15'] + e2['p_o15']) / 2
                p_real_o25 = (e1['p_o25'] + e2['p_o25']) / 2
                
                def mostrar_v(label, p_r, cuota):
                    p_c = (1/cuota)*100
                    diff = p_r - p_c
                    st.write(f"**{label}** | Real: {round(p_r,1)}% vs Casa: {round(p_c,1)}%")
                    if diff > 5: st.success(f"✅ VALOR ENCONTRADO (+{round(diff,1)}%)")
                    elif diff < -5: st.error("❌ RIESGO: Casa paga muy poco")
                    else: st.warning("⚠️ Cuota Justa")

                mostrar_v(f"Gana {e1['nombre']}", p_real_l, c_loc)
                mostrar_v("Over 1.5 Goles", p_real_o15, c_o15)
                mostrar_v("Over 2.5 Goles", p_real_o25, c_o25)
                
                st.session_state['historial'].insert(0, f"⚽ {datetime.now().strftime('%H:%M')} - {e1['nombre']} vs {e2['nombre']} | O1.5: {round(p_real_o15,1)}%")
    with colf2:
        st.button("🗑️ BORRAR FÚTBOL", on_click=limpiar_futbol, use_container_width=True)

# --- PESTAÑA 3: HISTORIAL Y ENVÍO ---
with tab3:
    st.header("Historial de Análisis")
    if st.session_state['historial']:
        texto_historial = "\n".join(st.session_state['historial'])
        st.text_area("Copia tu historial:", value=texto_historial, height=200)
        
        st.markdown("---")
        st.write("📩 **Enviar reporte a williamvg120@gmail.com**")
        if st.button("📧 ENVIAR POR CORREO", use_container_width=True):
            # Aquí simulamos el envío para que no falle por falta de claves SMTP
            st.success(f"Reporte preparado para williamvg120@gmail.com")
            st.toast("Copia el texto de arriba para tu registro")
    else:
        st.write("No hay datos en esta sesión.")
