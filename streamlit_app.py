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

# --- LÓGICA DE PROCESAMIENTO REFORZADA (A prueba de fallos) ---
def procesar_datos(texto, deporte):
    # Divide el texto ignorando mayúsculas/minúsculas
    bloques = re.split(r'ÚLTIMOS PARTIDOS:', texto, flags=re.IGNORECASE)
    resumen = []
    
    for bloque in bloques:
        if not bloque.strip() or len(bloque) < 10: continue
        
        lineas = [l.strip() for l in bloque.strip().split('\n') if l.strip()]
        if not lineas: continue
        
        nombre = lineas[0]
        # Regex Ultra-Flexible: Detecta "2 1 G", "2-1 G", "2 - 1 G", "2:1 G"
        matches = re.findall(r'(\d)\s*[:\-\s]*\s*(\d)\s*([GEP])', bloque, flags=re.IGNORECASE)
        
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
                "metrica_tenis": sum(26.5 if (int(m[0]) + int(m[1])) >= 3 else 18.5 for m in matches) / len(matches) if deporte == "Tenis" else 0,
                "cant": len(matches)
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
        else:
            st.error("No se detectaron 2 jugadores. Revisa el texto pegado.")
    st.button("🗑️ BORRAR", on_click=limpiar_tenis, key="b_c_t")

with tab2:
    st.header("Fútbol: Valor Total")
    data_f = st.text_area("1. Datos 365Scores:", height=150, key="texto_futbol")
    ctx_f = st.text_area("2. Contexto (Opcional):", height=80, key="contexto_f_input")
    
    st.subheader("💰 Cuotas")
    c1, c2, c3 = st.columns(3)
    with c1:
        cl = st.number_input("Cuota Local", value=2.0, format="%.2f")
        cv = st.number_input("Cuota Visita", value=3.0, format="%.2f")
    with c2:
        co15 = st.number_input("Cuota O1.5", value=1.3, format="%.2f")
        cu15 = st.number_input("Cuota U1.5", value=3.5, format="%.2f")
    with c3:
        co25 = st.number_input("Cuota O2.5", value=2.0, format="%.2f")
        cu25 = st.number_input("Cuota U2.5", value=1.8, format="%.2f")
    cbtts = st.number_input("Cuota BTTS", value=1.9, format="%.2f")

    if st.button("🔍 ANALIZAR VALOR", use_container_width=True, type="primary"):
        stats = procesar_datos(data_f, "Futbol")
        aj = analizar_contexto(ctx_f)
        
        if len(stats) >= 2:
            e1, e2 = stats[0], stats[1]
            p_l = (e1['win_rate'] + (100 - e2['win_rate'])) / 2
            p_o15 = ((e1['p_o15'] + e2['p_o15']) / 2) + aj["goles"]
            p_o25 = ((e1['p_o25'] + e2['p_o25']) / 2) + aj["goles"]
            p_btts = ((e1['p_btts'] + e2['p_btts']) / 2) + (aj["goles"]/2)
            
            st.subheader(f"🎯 Análisis: {e1['nombre']} vs {e2['nombre']}")
            for n in aj["notas"]: st.info(n)

            rep_data = []
            def check_v(label, p_r, cuota):
                p_c = (1 / cuota if cuota > 0 else 1) * 100
                diff = p_r - p_c
                status = "✅ VALOR" if diff > 5 else "❌ RIESGO" if diff < -5 else "⚠️ JUSTO"
                st.write(f"**{label}**: {status} (Real: {round(p_r,1)}% | Casa: {round(p_c,1)}%)")
                return f"- {label}: {status} ({round(p_r,1)}%)"

            rep_data.append(check_v(f"Gana {e1['nombre']}", p_l, cl))
            rep_data.append(check_v("Over 1.5", p_o15, co15))
            rep_data.append(check_v("Over 2.5", p_o25, co25))
            rep_data.append(check_v("Under 2.5", (100-p_o25), cu25))
            rep_data.append(check_v("BTTS (Ambos Marcan)", p_btts, cbtts))
            
            # Guardar reporte completo
            full_rep = f"⚽ {e1['nombre']} vs {e2['nombre']}\n" + "\n".join(rep_data)
            st.session_state['historial'].insert(0, full_rep)
        else:
            st.error("No se detectaron 2 equipos. Asegúrate de incluir 'ÚLTIMOS PARTIDOS' en el texto.")

    st.button("🗑️ BORRAR", on_click=limpiar_futbol, key="b_c_f")

with tab3:
    st.header("Historial Detallado")
    if st.session_state['historial']:
        txt_h = "\n\n---\n\n".join(st.session_state['historial'])
        st.text_area("Reportes Guardados:", value=txt_h, height=350)
        u_hist = urllib.parse.quote(txt_h)
        mail_url = f"https://mail.google.com/mail/?view=cm&fs=1&to=williamvg120@gmail.com&su=Reporte_Apuestas&body={u_hist}"
        st.markdown(f'<a href="{mail_url}" target="_blank" style="text-decoration:none;"><div style="background-color:#ff4b4b;color:white;padding:12px;text-align:center;border-radius:8px;font-weight:bold;">📩 ENVIAR REPORTE COMPLETO</div></a>', unsafe_allow_html=True)
    else:
        st.write("Aún no hay análisis en el historial.")
