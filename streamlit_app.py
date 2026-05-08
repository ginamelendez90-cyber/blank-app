import streamlit as st
import re
import urllib.parse

st.set_page_config(page_title="Sport Predictor Pro V7", page_icon="🏆", layout="centered")

if 'historial' not in st.session_state: st.session_state['historial'] = []

def procesar_datos_v7(texto):
    bloques = re.split(r'ÚLTIMOS PARTIDOS:', texto, flags=re.IGNORECASE)
    resumen = []
    for bloque in bloques:
        if not bloque.strip() or len(bloque) < 10: continue
        lineas = [l.strip() for l in bloque.strip().split('\n') if l.strip()]
        nombre = lineas[0]
        matches = re.findall(r'(\d)\s*[:\-\s]*\s*(\d)\s*([GEP])', bloque, flags=re.IGNORECASE)
        
        if matches:
            # Ponderación: Los partidos más recientes (al principio de la lista) valen más
            pesos = [1.5 if i < 2 else 1.0 for i in range(len(matches))]
            total_peso = sum(pesos)
            
            win_ponderado = sum(pesos[i] for i, m in enumerate(matches) if m[2].upper() == 'G') / total_peso
            o15_ponderado = sum(pesos[i] for i, m in enumerate(matches) if (int(m[0])+int(m[1])) >= 2) / total_peso
            o25_ponderado = sum(pesos[i] for i, m in enumerate(matches) if (int(m[0])+int(m[1])) >= 3) / total_peso
            btts_ponderado = sum(pesos[i] for i, m in enumerate(matches) if int(m[0])>0 and int(m[1])>0) / total_peso
            
            resumen.append({
                "nombre": nombre,
                "win": win_ponderado * 100,
                "o15": o15_ponderado * 100,
                "o25": o25_ponderado * 100,
                "btts": btts_ponderado * 100
            })
    return resumen

st.title("🏆 Sport Predictor Pro V7")
data_f = st.text_area("Pega datos de 365Scores aquí:", height=150)

st.subheader("💰 Cuotas Actuales")
c1, c2, c3 = st.columns(3)
with c1:
    cl = st.number_input("Cuota Local", value=2.0)
    co15 = st.number_input("Cuota Over 1.5", value=1.3)
with c2:
    cv = st.number_input("Cuota Visita", value=3.0)
    co25 = st.number_input("Cuota Over 2.5", value=2.0)
with c3:
    cbtts = st.number_input("Cuota BTTS", value=1.9)
    cu25 = st.number_input("Cuota Under 2.5", value=1.8)

if st.button("🔍 ANALIZAR CON FILTRO DE RECENCIA", type="primary", use_container_width=True):
    stats = procesar_datos_v7(data_f)
    if len(stats) >= 2:
        e1, e2 = stats[0], stats[1]
        
        # Cálculo de Probabilidades Combinadas
        prob_gana_l = (e1['win'] + (100 - e2['win'])) / 2
        prob_o15 = (e1['o15'] + e2['o15']) / 2
        prob_o25 = (e1['o25'] + e2['o25']) / 2
        prob_btts = (e1['btts'] + e2['btts']) / 2
        
        st.subheader(f"📊 Pronóstico: {e1['nombre']} vs {e2['nombre']}")
        
        def mostrar_analisis(label, p_real, cuota):
            p_casa = (1/cuota)*100
            diff = p_real - p_casa
            if diff > 10: icon, color, txt = "✅", "green", "VALOR ALTO"
            elif diff > 0: icon, color, txt = "⚠️", "orange", "VALOR MEDIO"
            else: icon, color, txt = "❌", "red", "SIN VALOR"
            
            st.markdown(f"**{label}**: {icon} <span style='color:{color}'>{txt}</span> (Real: {round(p_real,1)}% | Cuota: {round(p_casa,1)}%)", unsafe_allow_html=True)
            return f"{label}: {txt} ({round(p_real,1)}%)"

        r1 = mostrar_analisis(f"Gana {e1['nombre']}", prob_gana_l, cl)
        r2 = mostrar_analisis("Over 1.5", prob_o15, co15)
        r3 = mostrar_analisis("Over 2.5", prob_o25, co25)
        r4 = mostrar_analisis("BTTS", prob_btts, cbtts)
        
        st.session_state['historial'].insert(0, f"⚽ {e1['nombre']} vs {e2['nombre']}\n{r1}\n{r2}\n{r3}\n{r4}")
    else:
        st.error("Pega los datos correctamente.")

if st.session_state['historial']:
    st.divider()
    st.subheader("📜 Historial")
    txt_h = "\n\n".join(st.session_state['historial'])
    st.text_area("Copia tu historial:", value=txt_h, height=150)
