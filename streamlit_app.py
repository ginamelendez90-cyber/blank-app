import streamlit as st
import pandas as pd
import soccerdata as sd

# Configuración de la interfaz en modo ancho
st.set_page_config(page_title="Football Sabermetrics Analytics", layout="wide", page_icon="⚽")

st.title("⚽ Sistema Predictivo de Fútbol Profesional (xG Model)")
st.markdown("---")

# --- CONTROLADORES DE FILTROS ---
st.sidebar.header("⚙️ Configuración del Modelo")

# Inicializamos el conector de SoccerData usando la fuente de Understat (incluye datos xG gratuitos)
@st.cache_data(ttl=3600) # Guardamos en caché por 1 hora para no saturar los servidores
def cargar_datos_futbol():
    try:
        # Extrae datos de las ligas top. Usaremos la Premier League como base
        understat = sd.Understat(leagues="ENG-Premier League", seasons=2025) 
        
        # Obtener el historial de partidos y resultados de la temporada
        cronograma = understat.read_schedule()
        return cronograma
    except Exception as e:
        st.error(f"Error al conectar con el servidor de datos: {e}")
        return pd.DataFrame()

# --- PROCESAMIENTO DE DATOS ---
df_partidos = cargar_datos_futbol()

if df_partidos.empty:
    st.warning("⚠️ No se pudieron recuperar los datos de la liga en este momento.")
else:
    # 1. Limpieza rápida: Filtrar solo los partidos que aún NO se han jugado (Pre-Partido)
    # Understat marca los partidos jugados con goles definidos. Filtramos los pendientes:
    partidos_pendientes = df_partidos[df_partidos['home_goals'].isna()]
    
    if partidos_pendientes.empty:
        st.info("⚽ Todos los partidos de la temporada actual ya se han jugado. Mostrando últimos encuentros para simulación:")
        partidos_pendientes = df_partidos.tail(10) # Respaldar con los últimos 10 si la temporada acabó
    
    # Crear la lista de selección para el usuario
    lista_opciones = []
    for idx, row in partidos_pendientes.iterrows():
        lista_opciones.append(f"{row['home_team']} vs {row['away_team']} (Fecha: {row['date'].strftime('%Y-%m-%d')})")
        
    partido_elegido = st.selectbox("🎯 Selecciona el próximo encuentro que deseas analizar:", lista_opciones)
    
    # Extraer los equipos del partido seleccionado
    match_idx = lista_opciones.index(partido_elegido)
    fila_partido = partidos_pendientes.iloc[match_idx]
    equipo_local = fila_partido['home_team']
    equipo_visitante = fila_partido['away_team']
    
    # =========================================================================
    # 📊 PESTAÑA ÚNICA: ESTUDIO PRE-PARTIDO
    # =========================================================================
    st.header(f"🏟️ Análisis de Confrontación: {equipo_local} vs {equipo_visitante}")
    
    # 2. CÁLCULO DE MÉTRICAS AVANZADAS (Métricas xG históricas de la temporada)
    # Calculamos los promedios de Goles Esperados (xG) anotados y concedidos
    # xG Home anotado
    xg_anotado_local = df_partidos[df_partidos['home_team'] == equipo_local]['home_xg'].mean()
    # xG Home recibido
    xg_concedido_local = df_partidos[df_partidos['home_team'] == equipo_local]['away_xg'].mean()
    
    # xG Away anotado
    xg_anotado_visita = df_partidos[df_partidos['away_team'] == equipo_visitante]['away_xg'].mean()
    # xG Away recibido
    xg_concedido_visita = df_partidos[df_partidos['away_team'] == equipo_visitante]['home_xg'].mean()
    
    # Promedio de xG general de toda la liga (Línea base)
    xg_promedio_liga = df_partidos['home_xg'].mean()
    
    # Rellenar con valores estándar si es el primer partido del torneo
    xg_anotado_local = xg_anotado_local if not pd.isna(xg_anotado_local) else 1.35
    xg_concedido_local = xg_concedido_local if not pd.isna(xg_concedido_local) else 1.20
    xg_anotado_visita = xg_anotado_visita if not pd.isna(xg_anotado_visita) else 1.15
    xg_concedido_visita = xg_concedido_visita if not pd.isna(xg_concedido_visita) else 1.40
    xg_promedio_liga = xg_promedio_liga if not pd.isna(xg_promedio_liga) else 1.25

    # 3. INTERFAZ VISUAL DE MÉTRICAS (Mano a Mano)
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
    st.header("🧮 4. Proyección de Goles del Partido")
    st.write("Cálculo predictivo cruzando la Fuerza Ofensiva de un equipo contra la Fuerza Defensiva del oponente.")
    
    # Algoritmo de Proyección de Goles Esperados para este partido específico:
    # Goles Proyectados = (xG de Ataque del Equipo / Promedio de la liga) * xG de Defensa del Rival
    goles_proyectados_local = (xg_anotado_local / xg_promedio_liga) * xg_concedido_visita
    goles_proyectados_visita = (xg_anotado_visita / xg_promedio_liga) * xg_concedido_local
    
    col_pred1, col_pred2 = st.columns(2)
    col_pred1.metric(f"Goles Proyectados para {equipo_local}", f"{goles_proyectados_local:.2f}")
    col_pred2.metric(f"Goles Proyectados para {equipo_visitante}", f"{goles_proyectados_visita:.2f}")
    
    # Diagnóstico final del Analista
    st.subheader("🎯 Diagnóstico del Modelo Predictivo")
    if goles_proyectados_local > goles_proyectados_visita + 0.4:
        st.success(f"🟢 **Alta probabilidad de Victoria Local**. El ataque de {equipo_local} supera con creces las carencias defensivas de {equipo_visitante}.")
    elif goles_proyectados_visita > goles_proyectados_local + 0.4:
        st.success(f"🔵 **Alta probabilidad de Victoria Visitante**. {equipo_visitante} tiene las métricas de peligro necesarias para asaltar el estadio local.")
    else:
        st.warning("🟡 **Tendencia al Empate o Partido Cerrado**. Las fuerzas están sumamente niveladas en las proyecciones analíticas.")
