import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="Control de Créditos y Cobros", page_icon="💰", layout="wide"
)

# Inicializar la base de datos simulada en la sesión
if "creditos" not in st.session_state:
    st.session_state.creditos = []

if "pagos" not in st.session_state:
    # DataFrame para llevar el registro detallado de cada cuota/día pagado
    st.session_state.pagos = pd.DataFrame(
        columns=[
            "ID_Credito",
            "Cuota_N",
            "Monto_Cuota",
            "Estado",
            "Metodo_Pago",
            "Fecha_Pago",
        ]
    )

st.title("📊 Sistema de Gestión de Cobros (Diarios y Semanales)")

menu = st.sidebar.selectbox(
    "Menú de Navegación",
    [
        "Registrar Nuevo Crédito",
        "Panel de Cobros y Pagos",
        "Historial y Créditos Cerrados",
    ],
)

# ---------------------------------------------------------
# 1. REGISTRAR NUEVO CRÉDITO
# ---------------------------------------------------------
if menu == "Registrar Nuevo Crédito":
    st.header("📝 Registrar Nuevo Crédito")

    # Verificar si hay créditos activos del cliente para avisar
    creditos_activos = [
        c for c in st.session_state.creditos if c["Estado"] == "Activo"
    ]
    if creditos_activos:
        st.warning(
            "⚠️ Hay un crédito activo actualmente. Recuerda cerrarlo si vas a otorgar uno nuevo al mismo cliente."
        )

    with st.form("form_credito"):
        nombre_cliente = st.text_input("Nombre del Cliente")
        monto_total = st.number_input(
            "Monto Total a Deber (con intereses)",
            min_value=0.0,
            step=10.0,
            format="%.2f",
        )

        modalidad = st.selectbox("Modalidad de Cobro", ["Diario", "Semanal"])

        if modalidad == "Diario":
            plazo_dias = st.selectbox("Plazo en Días", [24, 30])
            num_cuotas = plazo_dias
        else:
            num_cuotas = st.number_input(
                "Cantidad de Semanas", min_value=1, max_value=52, value=4
            )

        submit = st.form_submit_button("Crear Crédito")

        if submit:
            if nombre_cliente and monto_total > 0:
                id_credito = len(st.session_state.creditos) + 1
                monto_cuota = monto_total / num_cuotas

                # Guardar el crédito principal
                nuevo_credito = {
                    "ID": id_credito,
                    "Cliente": nombre_cliente,
                    "Monto_Total": monto_total,
                    "Modalidad": modalidad,
                    "Plazo": num_cuotas,
                    "Cuota_Valor": monto_cuota,
                    "Estado": "Activo",
                }
                st.session_state.creditos.append(nuevo_credito)

                # Generar las cuotas correspondientes en el registro de pagos
                nuevas_filas = []
                for i in range(1, int(num_cuotas) + 1):
                    nuevas_filas.append(
                        {
                            "ID_Credito": id_credito,
                            "Cuota_N": i,
                            "Monto_Cuota": monto_cuota,
                            "Estado": "Pendiente",
                            "Metodo_Pago": "N/A",
                            "Fecha_Pago": "N/A",
                        }
                    )

                df_nuevos_pagos = pd.DataFrame(nuevas_filas)
                st.session_state.pagos = pd.concat(
                    [st.session_state.pagos, df_nuevos_pagos], ignore_index=True
                )

                st.success(
                    f"✅ ¡Crédito #{id_credito} creado con éxito para {nombre_cliente}!"
                )
            else:
                st.error("Por favor completa todos los campos correctamente.")

# ---------------------------------------------------------
# 2. PANEL DE COBROS Y PAGOS
# ---------------------------------------------------------
elif menu == "Panel de Cobros y Pagos":
    st.header("💵 Panel de Cobros Diarios y Semanales")

    creditos_activos = [
        c for c in st.session_state.creditos if c["Estado"] == "Activo"
    ]

    if not creditos_activos:
        st.info("No hay créditos activos en este momento. Crea uno nuevo.")
    else:
        # Seleccionar crédito activo
        opciones_credito = {
            f"Crédito #{c['ID']} - {c['Cliente']} (Debe: {c['Monto_Total']})": c[
                "ID"
            ]
            for c in creditos_activos
        }
        credito_seleccionado_str = st.selectbox(
            "Seleccione el Crédito a Gestionar", list(opciones_credito.keys())
        )
        id_activo = opciones_credito[credito_seleccionado_str]

        # Obtener datos del crédito
        credito_info = next(
            c for c in st.session_state.creditos if c["ID"] == id_activo
        )

        col1, col2, col3 = st.columns(3)
        col1.metric("Cliente", credito_info["Cliente"])
        col2.metric("Monto Total", f"${credito_info['Monto_Total']:.2f}")
        col3.metric(
            "Valor por Cuota", f"${credito_info['Cuota_Valor']:.2f}"
        )

        st.markdown("---")
        st.subheader("📋 Registro de Cuotas")

        # Filtrar pagos de este crédito
        df_pagos_credito = st.session_state.pagos[
            st.session_state.pagos["ID_Credito"] == id_activo
        ]

        # Mostrar tabla interactiva de pagos
        st.dataframe(df_pagos_credito, use_container_width=True)

        st.markdown("### Registrar un Pago o Abono")
        with st.form("form_registrar_pago"):
            # Filtrar solo cuotas pendientes
            cuotas_pendientes = df_pagos_credito[
                df_pagos_credito["Estado"] == "Pendiente"
            ]["Cuota_N"].tolist()

            if cuotas_pendientes:
                cuota_a_pagar = st.selectbox(
                    "Seleccione el número de cuota a abonar/pagar",
                    cuotas_pendientes,
                )
                metodo = st.selectbox(
                    "Método de Pago", ["Pago Móvil", "Efectivo", "Binance"]
                )
                fecha = st.date_input("Fecha del Pago")

                btn_pagar = st.form_submit_button("Registrar Pago")

                if btn_pagar:
                    # Actualizar el estado en el DataFrame global de pagos
                    idx = st.session_state.pagos[
                        (st.session_state.pagos["ID_Credito"] == id_activo)
                        & (st.session_state.pagos["Cuota_N"] == cuota_a_pagar)
                    ].index

                    st.session_state.pagos.loc[idx, "Estado"] = "Pagado"
                    st.session_state.pagos.loc[idx, "Metodo_Pago"] = metodo
                    st.session_state.pagos.loc[idx, "Fecha_Pago"] = str(fecha)

                    st.success(
                        f"✅ Cuota #{cuota_a_pagar} registrada como PAGADA vía {metodo}."
                    )
                    st.rerun()
            else:
                st.success(
                    "🎉 ¡Todas las cuotas de este crédito han sido pagadas!"
                )

        st.markdown("---")
        # Sección para cerrar el crédito
        st.subheader("🔒 Cerrar Crédito")
        pendientes_restantes = len(
            st.session_state.pagos[
                (st.session_state.pagos["ID_Credito"] == id_activo)
                & (st.session_state.pagos["Estado"] == "Pendiente")
            ]
        )

        if pendientes_restantes == 0:
            if st.button("Cerrar Crédito Finalizado"):
                for c in st.session_state.creditos:
                    if c["ID"] == id_activo:
                        c["Estado"] = "Cerrado"
                st.success(
                    "🔒 El crédito se ha cerrado correctamente. ¡Ya puedes abrir uno nuevo!"
                )
                st.rerun()
        else:
            st.warning(
                f"Aún quedan {pendientes_restantes} cuotas pendientes. Si deseas cerrarlo por fuerza mayor, haz clic abajo:"
            )
            if st.button("Forzar Cierre de Crédito"):
                for c in st.session_state.creditos:
                    if c["ID"] == id_activo:
                        c["Estado"] = "Cerrado"
                st.warning("⚠️ Crédito cerrado manualmente con deudas pendientes.")
                st.rerun()

# ---------------------------------------------------------
# 3. HISTORIAL Y CRÉDITOS CERRADOS
# ---------------------------------------------------------
elif menu == "Historial y Créditos Cerrados":
    st.header("📂 Historial de Créditos")

    if not st.session_state.creditos:
        st.info("No hay registros de créditos creados.")
    else:
        df_creditos = pd.DataFrame(st.session_state.creditos)
        st.dataframe(df_creditos, use_container_width=True)

        st.subheader("Detalle completo de todos los pagos registrados")
        st.dataframe(st.session_state.pagos, use_container_width=True)
