import subprocess
import sys
import streamlit as st

# =========================================================================
# ⚙️ CARGADOR DINÁMICO DE DEPENDENCIAS (BLINDADO)
# =========================================================================
# Este bloque detecta si las librerías científicas están instaladas.
# Si faltan, invoca de manera forzada al instalador de Python antes de que
# la interfaz intente arrancar, evitando colapsos del servidor.
try:
    import soccerdata as sd
    from scipy.stats import poisson
except ModuleNotFoundError:
    with st.spinner("📦 Inicializando entorno analítico por primera vez... (Espere 30 segundos)"):
        # Descarga forzada y silenciosa de paquetes analíticos
        subprocess.check_call([sys.executable, "-m", "pip", "install", "soccerdata", "understat", "scipy", "pandas>=2.0.0"])
    st.success("✅ ¡Entorno configurado con éxito! Refrescando interfaz...")
    st.rerun()

# Una vez asegurado el entorno, realizamos las importaciones analíticas
import pandas as pd
import soccerdata as sd
from scipy.stats import poisson
from datetime import datetime

# Configuración de la interfaz en modo ancho
st.set_page_config(page_title="Football Analytics Pro", layout="wide", page_icon="⚽")

st.title("⚽ Sistema Predictivo de Fútbol Profesional (Modelo Poisson & xG)")
st.markdown("---")

# --- CONEXIÓN Y CARGA DE DATOS OPTIMIZADA ---
@st.cache_data(ttl=3600)
def cargar_datos_futbol():
    try:
        # Se conecta al módulo analítico de Understat para extraer métricas xG masivas
        understat = sd.Understat(leagues="ENG-Premier League", seasons=2026) 
        return understat.read_schedule()
    except Exception as e:
        st.error(f"Error al conectar con la base de datos de fútbol: {e}")
        return pd.DataFrame()

# --- PROCESAMIENTO ANALÍTICO ---
df_partidos = cargar_datos_futbol()

if df_partidos.empty:
    st.warning("⚠️ No se pudieron recuperar los datos de la liga en este momento. Intenta refrescar la página.")
else:
    # 1. Filtrar los partidos que aún no tienen goles registrados (Pre-Partido)
    partidos_pendientes = df_partidos[df_partidos['home_goals'].isna()]
    
    if partidos_pendientes.empty:
        st.info("⚽ No hay encuentros pendientes inmediatos. Mostrando los últimos de la temporada para simulación:")
        partidos_pendientes = df_partidos.tail(10)
    
    # Crear la lista de selección interactiva
    lista_opciones = []
    for idx, row in partidos_pendientes.iterrows():
        fecha_str = row['date'].strftime('%Y-%m-%d') if pd.notna(row['date']) else "Fecha por confirmar"
        lista_opciones.append(f"{row['home_team']} vs {row['away_team']} ({fecha_str})")
        
    partido_elegido = st.selectbox("🎯 Selecciona el próximo encuentro que deseas analizar con el modelo:", lista_opciones)
    
    # Extraer los equipos del partido seleccionado
    match_idx = lista_opciones.index(partido_elegido)
    fila_partido = partidos_pendientes.iloc[match_idx]
    equipo_local = fila_partido['home_team']
    equipo_visitante = fila_partido['away_team']
    
    st.markdown("---")
    st.header(f"🏟️ Estudio de Confrontación: {equipo_local} vs {equipo_visitante}")
    
    # =========================================================================
    # 📊 BLOQUE 1: EXTRACCIÓN DE MÉTRICAS SOBERMÉTRICAS (xG)
    # =========================================================================
    xg_anotado_local = df_partidos[df_partidos['home_team'] == equipo_local]['home_xg'].mean()
    xg_concedido_local = df_partidos[df_partidos['home_team'] == equipo_local]['away_xg'].mean()
    
    xg_anotado_visita = df_partidos[df_partidos['away_team'] == equipo_visitante]['away_xg'].mean()
    xg_concedido_visita = df_partidos[df_partidos['away_team'] == equipo_visitante]['home_xg'].mean()
    
    # Línea base de la liga
    xg_promedio_liga = df_partidos['home_xg'].mean()
    
    # Asignar valores por defecto seguros en caso de valores nulos (Comienzos de torneo)
    xg_anotado_local = xg_anotado_local if not pd.isna(xg_anotado_local) else 1.35
    xg_concedido_local = xg_concedido_local if not pd.isna(xg_concedido_local) else 1.20
    xg_anotado_visita = xg_anotado_visita if not pd.isna(xg_anotado_visita) else 1.15
    xg_concedido_visita = xg_concedido_visita if not pd.isna(xg_concedido_visita) else 1.40
    xg_promedio_liga = xg_promedio_liga if not pd.isna(xg_promedio_liga) else 1.25

    # Visualización en columnas métricas
    c1, c2 = st.columns(2)
    with c1:
        st.subheader(f"🏠 Indicadores de {equipo_local} (Local)")
        st.metric("Peligro Ofensivo (xG Favor Promedio)", f"{xg_anotado_local:.2f}")
        st.metric("Vulnerabilidad Defensiva (xG Contra Promedio)", f"{xg_concedido_local:.2f}")
        
    with c2:
        st.subheader(f"🚀 Indicadores de {equipo_visitante} (Visitante)")
        st.metric("Peligro Ofensivo (xG Favor Promedio)", f"{xg_anotado_visita:.2f}")
        st.metric("Vulnerabilidad Defensiva (xG Contra Promedio)", f"{xg_concedido_visita:.2f}")
        
    st.markdown("---")
    
    # =========================================================================
    # 🧮 BLOQUE 2: MOTOR DE PROYECCIÓN Y DISTRIBUCIÓN DE POISSON
    # =========================================================================
    st.header("🧮 Modelo Matemático Predictivo Avanzado")
    
    goles_proyectados_local = (xg_anotado_local / xg_promedio_liga) * xg_concedido_visita
    goles_proyectados_visita = (xg_anotado_visita / xg_promedio_liga) * xg_concedido_local
    
    prob_local = 0.0
    prob_empate = 0.0
    prob_visitante = 0.0
    
    for g_local in range(7):
        for g_visita in range(7):
            p_marcador = poisson.pmf(g_local, goles_proyectados_local) * poisson.pmf(g_visita, goles_proyectados_visita)
            
            if g_local > g_visita:
                prob_local += p_marcador
            elif g_local < g_visita:
                prob_visitante += p_marcador
            else:
                prob_empate += p_marcador

    # Mostrar la proyección de goles
    col_pred1, col_pred2 = st.columns(2)
    col_pred1.metric(f"Goles Proyectados para {equipo_local}", f"{goles_proyectados_local:.2f}")
    col_pred2.metric(f"Goles Proyectados para {equipo_visitante}", f"{goles_proyectados_visita:.2f}")
    
    # Porcentajes probabilísticos
    st.markdown("### 🎯 Probabilidades Porcentuales del Resultado Final")
    col_p1, col_p2, col_p3 = st.columns(3)
    col_p1.metric(f"Victoria {equipo_local}", f"{prob_local * 100:.2f}%")
    col_p2.metric("Empate", f"{prob_empate * 100:.2f}%")
    col_p3.metric(f"Victoria {equipo_visitante}", f"{prob_visitante * 100:.2f}%")
    
    # Conclusión
    st.markdown("### 📋 Conclusión del Analista")
    if prob_local > prob_visitante and prob_local > prob_empate:
        st.success(f"🟢 El modelo asigna la mayor probabilidad a la **Victoria de {equipo_local}** debido a la consistencia en su generación de xG en casa.")
    elif prob_visitante > prob_local and prob_visitante > prob_empate:
        st.info(f"🔵 El escenario más factible es una **Victoria de {equipo_visitante}**. Sus métricas de ataque superan la resistencia defensiva del cuadro local.")
    else:
        st.warning("🟡 El partido presenta una fuerte tendencia al **Empate**. Las fuerzas tácticas y las probabilidades numéricas se encuentran neutralizadas.")
