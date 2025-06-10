import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from io import BytesIO
from utils.IO import extract_excel_to_dataframe
from utils.calculos import extraer_fecha_desde_nombre

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
# Subir archivos
# -------------------------------
new_files = st.file_uploader("Sube uno o varios archivos .xlsx", type=["xlsx"], accept_multiple_files=True)

if new_files:
    for f in new_files:
        if f.name not in [file.name for file in st.session_state["uploaded_files"]]:
            st.session_state["uploaded_files"].append(f)

# -------------------------------
# Función métrica mejorada
# -------------------------------
def metricas(df, filename=""):
    resumen = {}
    original_columns = df.columns.tolist()  # Guardar nombres originales

    # Identificar sensores por tipo
    columnas_def = [col for col in original_columns if "def" in col.lower()]
    columnas_temp = [col for col in original_columns if "temp" in col.lower()]
    columnas_hum = [col for col in original_columns if "hum" in col.lower()]

    # 1. Deformación: Promedio general
    if columnas_def:
        def_promedio = df[columnas_def].mean().mean()
        resumen["Deformación promedio"] = def_promedio
    else:
        resumen["Deformación promedio"] = None

    # 2. Temperatura: Valores originales + diferencia
    if columnas_temp:
        # Calcular promedio por cada sensor
        for col in columnas_temp:
            resumen[f"Temp {col}"] = df[col].mean()
        
        # Calcular diferencia entre sensores
        temp_means = df[columnas_temp].mean()
        resumen["Diferencia temperatura"] = temp_means.max() - temp_means.min()
    else:
        resumen["Diferencia temperatura"] = None

    # 3. Humedad: Valores originales con nombres específicos
    hum_count = 0
    for col in columnas_hum:
        # Usar nombres más descriptivos basados en posición común
        sensor_name = f"Humedad Sens. {hum_count+1}"
        resumen[sensor_name] = df[col].mean()
        hum_count += 1

    resumen["Archivo"] = filename
    resumen["Total Sensores Humedad"] = hum_count
    return pd.DataFrame([resumen])

# -------------------------------
# 🔘 Botón para procesar archivos
# -------------------------------
if st.button("🔄 Procesar archivos"):
    for uploaded_file in st.session_state["uploaded_files"]:
        try:
            df = extract_excel_to_dataframe(uploaded_file)
            
            # Limpieza de datos
            valores_a_eliminar = [-1000000, -999979]
            df = df.loc[:, ~df.isin(valores_a_eliminar).any()]
            df.columns = df.columns.str.strip()

            # Extraer fecha
            fecha_archivo = extraer_fecha_desde_nombre(uploaded_file.name)
            df["Fecha"] = fecha_archivo

            # Generar resumen
            summary_df = metricas(df, filename=uploaded_file.name)
            summary_df["Fecha"] = fecha_archivo

            # Almacenar resultados
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

    st.session_state["uploaded_files"] = []

# -------------------------------
# Mostrar último archivo procesado
# -------------------------------
if st.session_state.get("last_uploaded"):
    last = st.session_state["last_uploaded"]
    st.success(f"✅ ¡{last['filename']} procesado correctamente!")
    
    # Mostrar detalle de sensores
    st.subheader("Detectados en el archivo:")
    summary = last["summary"]
    
    # Contadores de sensores
    temp_cols = [c for c in summary.columns if c.startswith("Temp")]
    hum_cols = [c for c in summary.columns if c.startswith("Humedad")]
    
    col1, col2 = st.columns(2)
    col1.metric("Sensores de temperatura", len(temp_cols))
    col2.metric("Sensores de humedad", summary["Total Sensores Humedad"].iloc[0])
    
    # Mostrar datos
    with st.expander("📊 Ver primeras filas de datos"):
        st.dataframe(last["df"].head(5), use_container_width=True)
    
    with st.expander("📝 Ver resumen completo"):
        st.dataframe(summary, use_container_width=True)

# -------------------------------
# Mostrar y descargar resumen acumulado
# -------------------------------
if st.session_state["all_summaries"]:
    st.divider()
    st.subheader("📊 Resumen combinado de todos los archivos")
    resumen_total = pd.concat(st.session_state["all_summaries"], ignore_index=True)
    st.dataframe(resumen_total, use_container_width=True)

    # Botones de descarga
    resumen_excel = BytesIO()
    with pd.ExcelWriter(resumen_excel, engine="xlsxwriter") as writer:
        resumen_total.to_excel(writer, index=False, sheet_name="Resumen")
    resumen_excel.seek(0)

    st.download_button("📥 Descargar resumen combinado (Excel)", resumen_excel,
        file_name="resumen_completo.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    # Visualización de series temporales
    st.subheader("📈 Visualización de series temporales")
    
    if "Fecha" not in resumen_total.columns:
        st.error("❌ Falta columna 'Fecha' en el resumen")
    else:
        resumen_total["Fecha"] = pd.to_datetime(resumen_total["Fecha"])
        resumen_total = resumen_total.sort_values("Fecha")

        # Selección de métricas
        metric_options = [col for col in resumen_total.columns if col not in ["Archivo", "Fecha", "Total Sensores Humedad"]]
        selected_metrics = st.multiselect(
            "Selecciona métricas para visualizar",
            metric_options,
            default=["Deformación promedio", "Diferencia temperatura"]
        )

        if selected_metrics:
            fig, ax = plt.subplots(figsize=(10, 6))
            
            for metric in selected_metrics:
                ax.plot(
                    resumen_total["Fecha"], 
                    resumen_total[metric], 
                    marker="o", 
                    linestyle="-",
                    label=metric
                )
            
            ax.set_title("Evolución temporal de las métricas")
            ax.set_xlabel("Fecha")
            ax.set_ylabel("Valor")
            ax.grid(True, alpha=0.3)
            ax.legend()
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%d/%m/%Y'))
            fig.autofmt_xdate()
            st.pyplot(fig)
            
            # Mostrar tabla de datos del gráfico
            with st.expander("📋 Ver datos del gráfico"):
                st.dataframe(resumen_total[["Fecha"] + selected_metrics])
        else:
            st.warning("Selecciona al menos una métrica para visualizar")
