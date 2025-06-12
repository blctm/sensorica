import pandas as pd
import re
from datetime import datetime

def extraer_fecha_desde_nombre(nombre_archivo):
    match = re.search(r'(\d{4})_(\d{2})_(\d{2})', nombre_archivo)
    if match:
        año, mes, dia = match.groups()
        return f"{dia}/{mes}/{año}"
    return "Fecha desconocida"

def identificar_columnas(df):
    """
    Identifica las columnas usando los nombres originales con patrones específicos
    """
    columnas = df.columns.astype(str).str.strip()
    columnas_lower = columnas.str.lower()
    
    # Patrones específicos para los nombres originales
    patrones_deformacion = ['def']
    patrones_temperatura = ['temp', 'cal']
    patrones_humedad = ['hum']
    
    deformacion_cols = []
    temperatura_cols = []
    humedad_cols = []
    
    for i, col_lower in enumerate(columnas_lower):
        col_original = columnas[i]
        
        # Verificar deformación (ej: Demos_2_Def_1)
        if any(patron in col_lower for patron in patrones_deformacion) and 'temp' not in col_lower:
            deformacion_cols.append(col_original)
        
        # Verificar temperatura (ej: Demos_5_Temp_1_Cal)
        elif any(patron in col_lower for patron in patrones_temperatura):
            temperatura_cols.append(col_original)
        
        # Verificar humedad (ej: Demos_3_Hum_1)
        elif any(patron in col_lower for patron in patrones_humedad):
            humedad_cols.append(col_original)
    
    return deformacion_cols, temperatura_cols, humedad_cols

def buscar_columnas_por_contenido(df):
    """
    Si no se pueden identificar por nombre, analizar el contenido de las columnas
    """
    columnas_numericas = df.select_dtypes(include=[float, int]).columns
    
    deformacion_cols = []
    temperatura_cols = []
    humedad_cols = []
    
    for col in columnas_numericas:
        valores = df[col].dropna()
        if len(valores) == 0:
            continue
            
        mean_val = valores.mean()
        std_val = valores.std()
        min_val = valores.min()
        max_val = valores.max()
        
        # Heurísticas basadas en rangos típicos
        # Temperatura (normalmente entre -50 y 100°C)
        if -50 <= min_val <= 100 and -50 <= max_val <= 100:
            temperatura_cols.append(col)
        
        # Humedad (normalmente entre 0 y 100%)
        elif 0 <= min_val <= 100 and 0 <= max_val <= 100 and mean_val < 100:
            humedad_cols.append(col)
        
        # Deformación (puede tener valores muy variados)
        else:
            deformacion_cols.append(col)
    
    return deformacion_cols, temperatura_cols, humedad_cols

def metricas(df, filename=""):
    df.columns = df.columns.astype(str).str.strip()
    fecha_str = extraer_fecha_desde_nombre(filename)

    # Primero intentar identificar por nombres originales
    deformacion_cols, temperatura_cols, humedad_cols = identificar_columnas(df)

    # Solo usar identificación por contenido como respaldo si no se encuentran columnas
    if not deformacion_cols and not temperatura_cols and not humedad_cols:
        deformacion_cols, temperatura_cols, humedad_cols = buscar_columnas_por_contenido(df)

    # Respaldos finales si aún no se encuentran columnas
    if not deformacion_cols:
        # Buscar columnas que contengan 'def' o tomar las primeras numéricas
        posibles_def = [col for col in df.columns if 'def' in col.lower()]
        deformacion_cols = posibles_def if posibles_def else df.select_dtypes(include=[float, int]).columns.tolist()[:1]

    if not temperatura_cols:
        # Buscar columnas que contengan 'temp' o 'cal'
        posibles_temp = [col for col in df.columns if any(x in col.lower() for x in ['temp', 'cal'])]
        temperatura_cols = posibles_temp if posibles_temp else df.select_dtypes(include=[float, int]).columns.tolist()[:1]

    if not humedad_cols:
        # Buscar columnas que contengan 'hum'
        posibles_hum = [col for col in df.columns if 'hum' in col.lower()]
        humedad_cols = posibles_hum if posibles_hum else []

    # Extraer datos usando nombres originales
    deformacion = df[deformacion_cols] if deformacion_cols else pd.DataFrame()
    temperatura = df[temperatura_cols] if temperatura_cols else pd.DataFrame()
    
    if humedad_cols:
        humedad = df[humedad_cols]
    else:
        humedad = pd.DataFrame({'humedad_default': [50.0] * len(df)})

    # Calcular deformación promedio
    if not deformacion.empty:
        deformacion_sensi = deformacion.mean(skipna=True) * 1.2
        defo_prom = deformacion_sensi.iloc[0] if not deformacion_sensi.empty else 0.0
    else:
        defo_prom = 0.0

    # Aplicar filtros consistentes para temperatura
    if not temperatura.empty:
        temperatura = temperatura.apply(pd.to_numeric, errors='coerce')
        temperatura_filtrada = temperatura[(temperatura >= -50) & (temperatura <= 100)]

        temp_col_filtrada = temperatura_filtrada.iloc[:, 0].dropna()
        if not temp_col_filtrada.empty:
            temp_0 = temp_col_filtrada.iloc[0]
            temp_1 = temp_col_filtrada.iloc[-1]
            diff_temp = temp_1 - temp_0
        else:
            diff_temp = 0

        # Calcular promedio solo con valores filtrados
        temp_promedio = temperatura_filtrada.mean(skipna=True)
        temp_promedio_valor = temp_promedio.iloc[0] if not temp_promedio.empty else 0
    else:
        diff_temp = 0
        temp_promedio_valor = 0

    # Aplicar filtros consistentes para humedad
    humedad = humedad.apply(pd.to_numeric, errors='coerce')
    humedad_filtrada = humedad[(humedad >= 0) & (humedad <= 1000)]  # Ampliado para μm/m
    
    # Calcular promedio solo con valores filtrados
    vhumedad_filtrada = humedad_filtrada.mean(skipna=True).values.flatten().tolist()
    
    # Si no hay suficientes valores de humedad filtrados, completar con valores por defecto
    while len(vhumedad_filtrada) < 5:
        vhumedad_filtrada.append(200.0)  # Valor más apropiado para μm/m

    constantes = [(83.76, 27.95), (65.87, 20.33), (94.59, 14.46), (87.58, 10.23), (79.79, 14.82)]

    valores_humedad = []
    for i in range(5):
        C, D = constantes[i]
        hs = (vhumedad_filtrada[i] * 1.2 - defo_prom - (C * temp_promedio_valor)) / D
        valores_humedad.append(hs)

    # Crear nombres para el resumen usando los nombres originales de las columnas
    defo_nombre = deformacion_cols[0] if deformacion_cols else "Deformación"
    temp_nombres = temperatura_cols if temperatura_cols else ["Temperatura"]
    hum_nombres = humedad_cols[:5] if len(humedad_cols) >= 5 else humedad_cols + [f"Humedad_{i}" for i in range(len(humedad_cols), 5)]
    
    resumen = {
        "Fecha": [fecha_str],
        "Archivo": [filename],
        f"{defo_nombre} promedio": [defo_prom],
        f"Diferencia {temp_nombres[0] if temp_nombres else 'Temperatura'}": [diff_temp],
        f"{temp_nombres[0] if temp_nombres else 'Temperatura'} promedio": [temp_promedio_valor],
        f"{hum_nombres[0]} Sens.": [valores_humedad[0]],
        f"{hum_nombres[1]} Sens.": [valores_humedad[1]],
        f"{hum_nombres[2]} Sens.": [valores_humedad[2]],
        f"{hum_nombres[3]} Sens.": [valores_humedad[3]],
        f"{hum_nombres[4]} Sens.": [valores_humedad[4]],
    }
def obtener_valor_resumen(df_resumen, tipo_columna):
    """
    Función auxiliar para obtener valores del resumen de forma flexible
    """
    if tipo_columna == "deformacion":
        for col in df_resumen.columns:
            if "deformación" in col.lower() or "def" in col.lower():
                return df_resumen[col].iloc[0]
    elif tipo_columna == "temperatura":
        for col in df_resumen.columns:
            if "temperatura" in col.lower() and "promedio" in col.lower():
                return df_resumen[col].iloc[0]
    # ... etc
    return None
    return pd.DataFrame(resumen)
