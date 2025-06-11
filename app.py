import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from io import BytesIO
from utils.IO import extract_excel_to_dataframe
from utils.calculos import extraer_fecha_desde_nombre, metricas

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

            # Generar resumen usando las métricas avanzadas de calculos.py
            summary_df = metricas(df, filename=uploaded_file.name)

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

        except ValueError as ve:
            st.error(f"❌ Error de validación en {uploaded_file.name}: {ve}")
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
    st.subheader("📊 Métricas calculadas:")
    summary = last["summary"]
    
    # Mostrar métricas principales
    col1, col2, col3 = st.columns(3)
    
    defo_val = summary["Deformación promedio"].iloc[0]
    temp_diff = summary["Diferencia temperatura"].iloc[0]
    
    col1.metric("Deformación promedio (corregida)", f"{defo_val:.4f}" if defo_val else "N/A")
    col2.metric("Diferencia temperatura", f"{temp_diff:.2f}°" if temp_diff else "N/A")
    
    # Contar sensores de humedad activos
    humedad_cols = [c for c in summary.columns if c.startswith("Humedad Sens.")]
    sensores_activos = sum(1 for col in humedad_cols if pd.notna(summary[col].iloc[0]))
    col3.metric("Sensores humedad activos", sensores_activos)
    
    # Mostrar valores de humedad sensorial
    st.subheader("🌡️ Humedad sensorial calibrada:")
    hum_cols = [f"Humedad Sens. {i}" for i in range(5)]
    hum_data = []
    
    for i, col in enumerate(hum_cols):
        if col in summary.columns:
            valor = summary[col].iloc[0]
            if pd.notna(valor):
                hum_data.append({"Sensor": f"Sensor {i}", "Humedad Sensorial": f"{valor:.4f}"})
    
    if hum_data:
        st.dataframe(pd.DataFrame(hum_data), use_container_width=True, hide_index=True)
    
    # Mostrar datos originales
    with st.expander("📊 Ver primeras filas de datos originales"):
        st.dataframe(last["df"].head(10), use_container_width=True)
    
    with st.expander("📝 Ver resumen completo con todas las métricas"):
        st.dataframe(summary, use_container_width=True)

# -------------------------------
# Mostrar y descargar resumen acumulado
# -------------------------------
if st.session_state["all_summaries"]:
    st.divider()
    st.subheader("📊 Resumen combinado de todos los archivos")
    resumen_total = pd.concat(st.session_state["all_summaries"], ignore_index=True)
    
    # Mostrar estadísticas generales
    col1, col2, col3 = st.columns(3)
    col1.metric("Total archivos procesados", len(resumen_total))
    
    # Promedios generales
    defo_mean = resumen_total["Deformación promedio"].mean()
    temp_mean = resumen_total["Diferencia temperatura"].mean()
    col2.metric("Deformación promedio general", f"{defo_mean:.4f}")
    col3.metric("Diferencia temp. promedio", f"{temp_mean:.2f}°")
    
    st.dataframe(resumen_total, use_container_width=True)

    # Botones de descarga
    resumen_excel = BytesIO()
    with pd.ExcelWriter(resumen_excel, engine="xlsxwriter") as writer:
        resumen_total.to_excel(writer, index=False, sheet_name="Resumen_Avanzado")
    resumen_excel.seek(0)

    st.download_button("📥 Descargar resumen combinado (Excel)", resumen_excel,
        file_name="resumen_metricas_avanzadas.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    # Visualización de series temporales
    st.subheader("📈 Visualización de series temporales")
    
    if "Fecha" not in resumen_total.columns:
        st.error("❌ Falta columna 'Fecha' en el resumen")
    else:
        # Convertir fecha al formato datetime
        try:
            resumen_total["Fecha_dt"] = pd.to_datetime(resumen_total["Fecha"], format="%d/%m/%Y")
            resumen_total = resumen_total.sort_values("Fecha_dt")
        except:
            st.error("❌ Error al convertir fechas. Verifica el formato DD/MM/YYYY")

        # Selección de métricas
        metric_options = [col for col in resumen_total.columns 
                         if col not in ["Archivo", "Fecha", "Fecha_dt"] and pd.notna(resumen_total[col]).any()]
        
        selected_metrics = st.multiselect(
            "Selecciona métricas para visualizar",
            metric_options,
            default=["Deformación promedio", "Diferencia temperatura"][:len(metric_options)]
        )

        if selected_metrics:
            # Crear gráficos separados para mejor visualización
            fig, axes = plt.subplots(len(selected_metrics), 1, figsize=(12, 4*len(selected_metrics)))
            if len(selected_metrics) == 1:
                axes = [axes]
            
            for i, metric in enumerate(selected_metrics):
                # Filtrar valores no nulos
                mask = pd.notna(resumen_total[metric])
                fechas_filtradas = resumen_total.loc[mask, "Fecha_dt"]
                valores_filtrados = resumen_total.loc[mask, metric]
                
                if len(valores_filtrados) > 0:
                    axes[i].plot(fechas_filtradas, valores_filtrados, 
                               marker="o", linestyle="-", linewidth=2, markersize=6)
                    axes[i].set_title(f"Evolución de {metric}")
                    axes[i].set_ylabel("Valor")
                    axes[i].grid(True, alpha=0.3)
                    axes[i].xaxis.set_major_formatter(mdates.DateFormatter('%d/%m/%Y'))
                    
                    # Mostrar valores en los puntos si hay pocos datos
                    if len(valores_filtrados) <= 10:
                        for x, y in zip(fechas_filtradas, valores_filtrados):
                            axes[i].annotate(f'{y:.3f}', (x, y), 
                                           textcoords="offset points", xytext=(0,10), ha='center')
            
            plt.tight_layout()
            fig.autofmt_xdate()
            st.pyplot(fig)
            
            # Mostrar tabla de datos del gráfico
            with st.expander("📋 Ver datos del gráfico"):
                cols_to_show = ["Fecha"] + selected_metrics
                st.dataframe(resumen_total[cols_to_show].dropna(subset=selected_metrics, how='all'))
        else:
            st.warning("Selecciona al menos una métrica para visualizar")

# -------------------------------
# Información sobre las métricas
# -------------------------------
with st.expander("ℹ️ Información sobre las métricas calculadas"):
    st.markdown("""
    ### 🧮 Métricas avanzadas aplicadas:
    
    **1. Deformación promedio corregida:**
    - Se filtran columnas con "_Def"
    - Se aplica factor de corrección: `promedio × 1.2`
    
    **2. Diferencia de temperatura:**
    - Se busca columna "Temp_1_Cal"
    - Se calcula: `temperatura_final - temperatura_inicial`
    
    **3. Humedad sensorial calibrada:**
    - Se filtran columnas con "_Hum"
    - Se aplica fórmula de calibración por sensor:
    - `HS = (humedad × 1.2 - deformación - (C × diff_temp)) / D`
    - Donde C y D son constantes específicas por sensor
    
    **Constantes de calibración por sensor:**
    - Sensor 0: C=83.76, D=27.95
    - Sensor 1: C=65.87, D=20.33  
    - Sensor 2: C=94.59, D=14.46
    - Sensor 3: C=87.58, D=10.23
    - Sensor 4: C=79.79, D=14.82
    """)
