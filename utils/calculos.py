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
    Identifica las columnas de deformación, temperatura y humedad de forma más robusta
    """
    columnas = df.columns.astype(str).str.strip().str.lower()
    
    # Patrones más amplios para identificar columnas
    patrones_deformacion = ['def', 'deform', 'strain', 'displacement']
    patrones_temperatura = ['temp', 'temperature', 'cal', 'celsius']
    patrones_humedad = ['hum', 'humidity', 'moisture', 'rh']
    
    deformacion_cols = []
    temperatura_cols = []
    humedad_cols = []
    
    for i, col in enumerate(columnas):
        col_original = df.columns[i]
        
        # Verificar deformación
        if any(patron in col for patron in patrones_deformacion):
            deformacion_cols.append(col_original)
        
        # Verificar temperatura
        elif any(patron in col for patron in patrones_temperatura):
            temperatura_cols.append(col_original)
        
        # Verificar humedad
        elif any(patron in col for patron in patrones_humedad):
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

    deformacion_cols, temperatura_cols, humedad_cols = identificar_columnas(df)

    if not deformacion_cols or not temperatura_cols:
        deformacion_cols, temperatura_cols, humedad_cols = buscar_columnas_por_contenido(df)

    if not deformacion_cols:
        deformacion_cols = df.select_dtypes(include=[float, int]).columns.tolist()[:3]

    if not temperatura_cols:
        temperatura_cols = df.select_dtypes(include=[float, int]).columns.tolist()[:1]

    deformacion = df[deformacion_cols]
    temperatura = df[temperatura_cols]

    if humedad_cols:
        humedad = df[humedad_cols]
    else:
        humedad = pd.DataFrame({'humedad_default': [50.0] * len(df)})

    deformacion_sensi = deformacion.mean(skipna=True) * 1.2
    defo_prom = deformacion_sensi.iloc[0] if not deformacion_sensi.empty else 0.0

    # Filtrar explícitamente temperaturas anómalas
    temperatura = temperatura.apply(pd.to_numeric, errors='coerce')
    temperatura_filtrada = temperatura[(temperatura >= -50) & (temperatura <= 100)]

    temp_col_filtrada = temperatura_filtrada.iloc[:, 0].dropna()
    if not temp_col_filtrada.empty:
        temp_0 = temp_col_filtrada.iloc[0]
        temp_1 = temp_col_filtrada.iloc[-1]
        diff_temp = temp_1 - temp_0
    else:
        diff_temp = 0

    temp_promedio = temperatura_filtrada.mean(skipna=True)

    vhumedad = humedad.mean(skipna=True).values.flatten().tolist()
    while len(vhumedad) < 5:
        vhumedad.append(50.0)

    constantes = [(83.76, 27.95), (65.87, 20.33), (94.59, 14.46), (87.58, 10.23), (79.79, 14.82)]

    valores_humedad = []
    for i in range(5):
        C, D = constantes[i]
        hs = (vhumedad[i] * 1.2 - defo_prom - (C * temp_promedio.iloc[0])) / D if not temp_promedio.empty else 0
        valores_humedad.append(hs)

    resumen = {
        "Fecha": [fecha_str],
        "Archivo": [filename],
        "Deformación promedio": [defo_prom],
        "Diferencia temperatura": [diff_temp],
        "Temperatura promedio": [temp_promedio.mean()],
        "Humedad Sens. 0": [valores_humedad[0]],
        "Humedad Sens. 1": [valores_humedad[1]],
        "Humedad Sens. 2": [valores_humedad[2]],
        "Humedad Sens. 3": [valores_humedad[3]],
        "Humedad Sens. 4": [valores_humedad[4]],
    }

    return pd.DataFrame(resumen)
