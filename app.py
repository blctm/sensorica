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
# 🔍 Botón de diagnóstico
# -------------------------------
if st.session_state["uploaded_files"]:
    if st.button("🔍 Diagnosticar columnas de archivos"):
        st.subheader("🔍 Diagnóstico de columnas")
        for uploaded_file in st.session_state["uploaded_files"]:
            try:
                df = extract_excel_to_dataframe(uploaded_file)
                df.columns = df.columns.str.strip()
                
                st.write(f"**📁 {uploaded_file.name}**")
                
                # Mostrar todas las columnas
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write("**Todas las columnas:**")
                    for i, col in enumerate(df.columns):
                        st.write(f"{i+1}. `{col}`")
                
                with col2:
                    # Clasificar columnas
                    deformacion_cols = [col for col in df.columns if any(x in col.lower() for x in ['def', 'defor'])]
                    temp_cols = [col for col in df.columns if any(x in col.lower() for x in ['temp', 'cal'])]
                    hum_cols = [col for col in df.columns if 'hum' in col.lower()]
                    
                    st.write("**Columnas clasificadas:**")
                    st.write(f"🔧 Deformación ({len(deformacion_cols)}): {deformacion_cols}")
                    st.write(f"🌡️ Temperatura ({len(temp_cols)}): {temp_cols}")
                    st.write(f"💧 Humedad ({len(hum_cols)}): {hum_cols}")
                
                st.divider()
                
            except Exception as e:
                st.error(f"❌ Error al diagnosticar {uploaded_file.name}: {e}")

# -------------------------------
# Función metricas adaptada (más flexible)
# -------------------------------
def metricas_flexible(df, filename=""):
    fecha_str = extraer_fecha_desde_nombre(filename)
    
    # -------------------------------
    # Extraer columnas con múltiples patrones
    # -------------------------------
    # Deformación: buscar varios patrones
    deformacion = df.filter(like='_Def')
    if deformacion.empty:
        deformacion = df.filter(like='def')
    if deformacion.empty:
        deformacion = df.filter(like='Def')
    if deformacion.empty:
        # Buscar por contenido en nombre de columna
        deformacion_cols = [col for col in df.columns if 'def' in col.lower()]
        if deformacion_cols:
            deformacion = df[deformacion_cols]
    
    # Temperatura: buscar varios patrones
    temperatura = df.filter(like="_Cal")
    if temperatura.empty:
        temperatura = df.filter(like="temp")
    if temperatura.empty:
        temperatura = df.filter(like="Temp")
    if temperatura.empty:
        temp_cols = [col for col in df.columns if 'temp' in col.lower()]
        if temp_cols:
            temperatura = df[temp_cols]
    
    # Humedad: buscar varios patrones
    humedad = df.filter(like="_Hum")
    if humedad.empty:
        humedad = df.filter(like="hum")
    if humedad.empty:
        humedad = df.filter(like="Hum")
    if humedad.empty:
        hum_cols = [col for col in df.columns if 'hum' in col.lower()]
        if hum_cols:
            humedad = df[hum_cols]
    
    # Validar que encontramos las columnas necesarias
    if deformacion.empty:
        raise ValueError(f"❌ No se encontraron columnas de deformación. Columnas disponibles: {list(df.columns)}")
    if temperatura.empty:
        raise ValueError(f"❌ No se encontraron columnas de temperatura. Columnas disponibles: {list(df.columns)}")
    if humedad.empty:
        raise ValueError(f"❌ No se encontraron columnas de humedad. Columnas disponibles: {list(df.columns)}")
    
    # -------------------------------
    # Deformación promedio corregida
    # -------------------------------
    deformacion_sensi = deformacion.mean(skipna=True) * 1.2
    vdefor = deformacion_sensi.values.flatten().tolist()
    defo_prom = vdefor[0] if vdefor else None
    
    # -------------------------------
    # Temperatura (buscar columna adecuada)
    # -------------------------------
    # Primero intentar encontrar columna específica "Temp_1_Cal"
    temp_cols = [col for col in temperatura.columns if "Temp_1_Cal" in col]
    if not temp_cols:
        # Si no existe, usar la primera columna de temperatura disponible
        temp_cols = temperatura.columns.tolist()
    
    if not temp_cols:
        raise ValueError("❌ No se encontró ninguna columna de temperatura válida")
    
    temp_series = temperatura[temp_cols[0]]
    if temp_series.isnull().all():
        raise ValueError("❌ La columna de temperatura está vacía")
    
    temp_0 = temp_series.iloc[0]
    temp_1 = temp_series.iloc[-1]
    diff_temp = temp_1 - temp_0
    
    # -------------------------------
    # Calcular humedad sensorial
    # -------------------------------
    vhumedad = humedad.mean(skipna=True).values.flatten().tolist()
    sensores = len(vhumedad)
    
    constantes = [
        (83.76, 27.95),
        (65.87, 20.33),
        (94.59, 14.46),
        (87.58, 10.23),
        (79.79, 14.82)
    ]
    
    valores_humedad = []
    for i in range(5):
        if i < sensores:
            C, D = constantes[i]
            hs = (vhumedad[i] * 1.2 - defo_prom - (C * diff_temp)) / D
            valores_humedad.append(hs)
        else:
            valores_humedad.append(None)
    
    # -------------------------------
    # Resumen
    # -------------------------------
    resumen = {
        "Fecha": [fecha_str],
        "Archivo": [filename],
        "Deformación promedio": [defo_prom],
        "Diferencia temperatura": [diff_temp],
        "Humedad Sens. 0": [valores_humedad[0]],
        "Humedad Sens. 1": [valores_humedad[1]],
        "Humedad Sens. 2": [valores_humedad[2]],
        "Humedad Sens. 3": [valores_humedad[3]],
        "Humedad Sens. 4": [valores_humedad[4]],
        "Columnas encontradas": [f"Def: {len(deformacion.columns)}, Temp: {len(temperatura.columns)}, Hum: {len(humedad.columns)}"]
    }
    
    return pd.DataFrame(resumen)

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

            # Generar resumen usando la función flexible
            summary_df = metricas_flexible(df, filename=uploaded_file.name)

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
