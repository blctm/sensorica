import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from io import BytesIO
from utils.IO import extract_excel_to_dataframe
from utils.calculos import metricas, extraer_fecha_desde_nombre

st.title("La app de Julio")


# -------------------------------
# Inicializar estado
# -------------------------------
if "uploaded_files" not in st.session_state:
    st.session_state["uploaded_files"] = []

if "all_summaries" not in st.session_state:
    st.session_state["all_summaries"] = []

if "all_dataframes" not in st.session_state:
    st.session_state["all_dataframes"] = []

if "last_uploaded" not in st.session_state:
    st.session_state["last_uploaded"] = None

# -------------------------------
# Subir archivos (sin procesar aún)
# -------------------------------
new_files = st.file_uploader("Sube uno o varios archivos .xlsx", type=["xlsx"], accept_multiple_files=True)

if new_files:
    for f in new_files:
        if f.name not in [file.name for file in st.session_state["uploaded_files"]]:
            st.session_state["uploaded_files"].append(f)

# # Mostrar archivos pendientes
# if st.session_state["uploaded_files"]:
#     st.info("📂 Archivos pendientes de procesar:")
#     for file in st.session_state["uploaded_files"]:
#         st.markdown(f"• {file.name}")

# -------------------------------
# 🔘 Botón para procesar archivos
# -------------------------------
if st.button("🔄 Procesar archivos"):
    for uploaded_file in st.session_state["uploaded_files"]:
        try:
            df = extract_excel_to_dataframe(uploaded_file)
            valores_a_eliminar = [-1000000, -999979]
            df = df.loc[:, ~df.isin(valores_a_eliminar).any()]
            df.columns = df.columns.str.strip()

            fecha_archivo = extraer_fecha_desde_nombre(uploaded_file.name)
            df["Fecha"] = fecha_archivo

            summary_df = metricas(df, filename=uploaded_file.name)

            nombres_previos = [s["Archivo"].iloc[0] for s in st.session_state["all_summaries"]]
            if uploaded_file.name not in nombres_previos:
                st.session_state["all_summaries"].append(summary_df.copy())
                st.session_state["all_dataframes"].append(df.copy())

                st.session_state["last_uploaded"] = {
                    "df": df.copy(),
                    "summary": summary_df.copy(),
                    "filename": uploaded_file.name
                }

        except Exception as e:
            st.error(f"❌ Error al procesar {uploaded_file.name}: {e}")

    # Vaciar lista de archivos pendientes tras procesarlos
    st.session_state["uploaded_files"] = []

# -------------------------------
# Mostrar último archivo procesado
# -------------------------------
if st.session_state.get("last_uploaded"):
    st.success(f"✅ ¡{st.session_state['last_uploaded']['filename']} procesado correctamente!")
    st.subheader("Primeras 5 filas del archivo más reciente")
    st.dataframe(st.session_state["last_uploaded"]["df"].head(5), use_container_width=True)

    st.subheader("Resumen de métricas del archivo más reciente")
    st.dataframe(st.session_state["last_uploaded"]["summary"], use_container_width=True)

# -------------------------------
# Mostrar y descargar resumen acumulado
# -------------------------------
if st.session_state["all_summaries"]:
    st.divider()
    st.subheader("📊 Resumen combinado de todos los archivos")
    resumen_total = pd.concat(st.session_state["all_summaries"], ignore_index=True)
    st.dataframe(resumen_total, use_container_width=True)

    # Descargar resumen
    resumen_excel = BytesIO()
    with pd.ExcelWriter(resumen_excel, engine="xlsxwriter") as writer:
        resumen_total.to_excel(writer, index=False, sheet_name="Resumen")
    resumen_excel.seek(0)

    st.download_button("📥 Descargar resumen combinado (Excel)", resumen_excel,
        file_name="resumen_completo.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    resumen_csv = resumen_total.to_csv(index=False).encode("utf-8")
    st.download_button("📥 Descargar resumen combinado (CSV)", resumen_csv,
        file_name="resumen_completo.csv", mime="text/csv"
    )

    # -------------------------------
    # 📈 Gráfica interactiva
    # -------------------------------
    st.subheader("📈 Visualización de series temporales")

    resumen_total["Fecha"] = pd.to_datetime(resumen_total["Fecha"], format="%d/%m/%Y")
    resumen_total = resumen_total.sort_values("Fecha")

    metricas_para_graficar = [
        "Deformación promedio",
        "Diferencia temperatura",
        "Humedad Sens. 0",
        "Humedad Sens. 1",
        "Humedad Sens. 2",
        "Humedad Sens. 3",
        "Humedad Sens. 4",
    ]

    opcion = st.selectbox(
        "Selecciona una métrica para visualizar (o 'Todas')",
        ["Todas"] + metricas_para_graficar
    )

    fig, ax = plt.subplots()
    if opcion == "Todas":
        for metrica in metricas_para_graficar:
            ax.plot(resumen_total["Fecha"], resumen_total[metrica], marker="o", label=metrica)
        ax.set_title("Todas las métricas en el tiempo")
        ax.legend()
    else:
        ax.plot(resumen_total["Fecha"], resumen_total[opcion], marker="o", color="tab:blue")
        ax.set_title(f"{opcion} en el tiempo")

    ax.set_xlabel("Fecha")
    ax.set_ylabel("Valor")
    ax.grid(True)
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%d/%m'))
    fig.autofmt_xdate()
    st.pyplot(fig)