import streamlit as st
import pandas as pd
import math

# Configuración de la interfaz en modo ancho
st.set_page_config(page_title="Football Poisson Analytics Pro", layout="wide", page_icon="⚽")

st.title("⚽ Sistema Predictivo de Fútbol Profesional (Modelo Estadístico de Poisson)")
st.markdown("---")

# =========================================================================
# 📊 BASE DE DATOS INTERNA: INDICADORES xG REALES DE LA PREMIER LEAGUE
# =========================================================================
# Cargamos los datos analíticos acumulados de los equipos para la simulación.
# xG_Anotado: Capacidad de generar peligro. xG_Concedido: Vulnerabilidad en defensa.
datos_equipos = {
    "Arsenal": {"xG_Anotado": 1.98, "xG_Concedido": 0.88},
    "Aston Villa": {"xG_Anotado": 1.54, "xG_Concedido": 1.34},
    "Bournemouth": {"xG_Anotado": 1.42, "xG_Concedido": 1.45},
    "Brentford": {"xG_Anotado": 1.31, "xG_Concedido": 1.58},
    "Brighton": {"xG_Anotado": 1.62, "xG_Concedido": 1.21},
    "Chelsea": {"xG_Anotado": 1.84, "xG_Concedido": 1.18},
    "Crystal Palace": {"xG_Anotado": 1.22, "xG_Concedido": 1.41},
    "Everton": {"xG_Anotado": 1.15, "xG_Concedido": 1.52},
    "Fulham": {"xG_Anotado": 1.38, "xG_Concedido": 1.29},
    "Ipswich": {"xG_Anotado": 1.02, "xG_Concedido": 1.78},
    "Leicester": {"xG_Anotado": 1.11, "xG_Concedido": 1.69},
    "Liverpool": {"xG_Anotado": 2.12, "xG_Concedido": 0.82},
    "Manchester City": {"xG_Anotado": 2.24, "xG_Concedido": 0.94},
    "Manchester United": {"xG_Anotado": 1.48, "xG_Concedido": 1.32},
    "Newcastle": {"xG_Anotado": 1.56, "xG_Concedido": 1.39},
    "Nottingham Forest": {"xG_Anotado": 1.28, "xG_Concedido": 1.24},
    "Southampton": {"xG_Anotado": 0.96, "xG_Concedido": 1.82},
    "Tottenham": {"xG_Anotado": 1.89, "xG_Concedido": 1.26},
    "West Ham": {"xG_Anotado": 1.34, "xG_Concedido": 1.48},
    "Wolves": {"xG_Anotado": 1.21, "xG_Concedido": 1.72}
}

# Constante de la línea base de la liga (Promedio general de xG por partido)
xG_PROMEDIO_LIGA = 1.38

# --- FUNCIÓN MATEMÁTICA DE POISSON NATIVA ---
# Implementación directa de la fórmula de Poisson sin librerías externas:
# P(x; k) = (e^-x * x^k) / k!
def calcular_poisson(goles_esperados, goles_exactos):
    if goles_esperados <= 0:
        return 0.0
    numerador = math.exp(-goles_esperados) * (goles_esperados ** goles_exactos)
    denominador = math.factorial(goles_exactos)
    return numerador / denominador

# --- CONTROLES DE LA INTERFAZ ---
lista_equipos = sorted(list(datos_equipos.keys()))

st.sidebar.header("⚙️ Configuración del Encuentro")
local = st.sidebar.selectbox("🏠 Selecciona el Equipo Local:", lista_equipos, index=0)
visitante = st.sidebar.selectbox("🚀 Selecciona el Equipo Visitante:", lista_equipos, index=11)

if local == visitante:
    st.error("⚠️ Por favor, selecciona dos equipos diferentes para poder realizar la simulación.")
else:
    st.header(f"🏟️ Estudio Analítico de Confrontación: {local} vs {visitante}")
    
    # Extraer métricas base de los equipos seleccionados
    stats_local = datos_equipos[local]
    stats_visita = datos_equipos[visitante]
    
    # Mostrar tarjetas analíticas de rendimiento
    c1, c2 = st.columns(2)
    with c1:
        st.subheader(f"Indicadores de {local}")
        st.metric("Peligro Ofensivo (xG Favor)", f"{stats_local['xG_Anotado']:.2f}")
        st.metric("Vulnerabilidad Defensiva (xG Contra)", f"{stats_local['xG_Concedido']:.2f}")
        
    with c2:
        st.subheader(f"Indicadores de {visitante}")
        st.metric("Peligro Ofensivo (xG Favor)", f"{stats_visita['xG_Anotado']:.2f}")
        st.metric("Vulnerabilidad Defensiva (xG Contra)", f"{stats_visita['xG_Concedido']:.2f}")
        
    st.markdown("---")
    st.header("🧮 Simulación Numérica del Partido")
    
    # Cruzar fuerzas ofensivas y defensivas según la teoría sabermétrica del fútbol
    # Goles Esperados Partido = (Ataque Equipo A / Promedio Liga) * Defensa Equipo B
    goles_proyectados_local = (stats_local['xG_Anotado'] / xG_PROMEDIO_LIGA) * stats_visita['xG_Concedido']
    goles_proyectados_visita = (stats_visita['xG_Anotado'] / xG_PROMEDIO_LIGA) * stats_local['xG_Concedido']
    
    # Ejecución de la Matriz Estadístca de Poisson
    prob_local = 0.0
    prob_empate = 0.0
    prob_visitante = 0.0
    
    for g_local in range(7):
        for g_visita in range(7):
            # Calcular probabilidad conjunta del marcador exacto
            p_marcador = calcular_poisson(goles_proyectados_local, g_local) * calcular_poisson(goles_proyectados_visita, g_visita)
            
            if g_local > g_visita:
                prob_local += p_marcador
            elif g_local < g_visita:
                prob_visitante += p_marcador
            else:
                prob_empate += p_marcador

    # Mostrar la expectativa de goles finales
    col_pred1, col_pred2 = st.columns(2)
    col_pred1.metric(f"Expectativa de Goles para {local}", f"{goles_proyectados_local:.2f}")
    col_pred2.metric(f"Expectativa de Goles para {visitante}", f"{goles_proyectados_visita:.2f}")
    
    # Desplegar los porcentajes probabilísticos finales
    st.markdown("### 🎯 Probabilidades Porcentuales del Resultado (Mercado 1X2)")
    col_p1, col_p2, col_p3 = st.columns(3)
    col_p1.metric(f"Victoria {local} (1)", f"{prob_local * 100:.2f}%")
    col_p2.metric("Empate (X)", f"{prob_empate * 100:.2f}%")
    col_p3.metric(f"Victoria {visitante} (2)", f"{prob_visitante * 100:.2f}%")
    
    # Conclusión descriptiva automática del modelo estadístico
    st.markdown("### 📋 Conclusión del Analista Pro")
    if prob_local > prob_visitante and prob_local > prob_empate:
        st.success(f"🟢 El modelo asigna la mayor probabilidad a la **Victoria de {local}** debido a su consistencia ofensiva y las ventajas relativas en el cruce de xG.")
    elif prob_visitante > prob_local and prob_visitante > prob_empate:
        st.info(f"🔵 El escenario más factible es una **Victoria de {visitante}**. Sus métricas de ataque superan los índices de resistencia defensiva del cuadro local.")
    else:
        st.warning("🟡 El partido presenta una fuerte tendencia estructural al **Empate**. Las fuerzas tácticas de ambos planteles se neutralizan numéricamente.")
