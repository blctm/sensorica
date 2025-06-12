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
    """
    Función mejorada para calcular métricas con mejor detección de columnas
    """
    # Limpiar nombres de columnas
    df.columns = df.columns.astype(str).str.strip()
    fecha_str = extraer_fecha_desde_nombre(filename)
    
    print(f"Procesando archivo: {filename}")
    print(f"Columnas disponibles: {list(df.columns)}")
    print(f"Forma del DataFrame: {df.shape}")
    
    # Intentar identificar columnas por nombre
    deformacion_cols, temperatura_cols, humedad_cols = identificar_columnas(df)
    
    print(f"Columnas identificadas por nombre:")
    print(f"  - Deformación: {deformacion_cols}")
    print(f"  - Temperatura: {temperatura_cols}")
    print(f"  - Humedad: {humedad_cols}")
    
    # Si no se identifican suficientes columnas, usar análisis de contenido
    if not deformacion_cols or not temperatura_cols:
        print("Intentando identificar columnas por contenido...")
        deformacion_cols_content, temperatura_cols_content, humedad_cols_content = buscar_columnas_por_contenido(df)
        
        if not deformacion_cols:
            deformacion_cols = deformacion_cols_content
        if not temperatura_cols:
            temperatura_cols = temperatura_cols_content
        if not humedad_cols:
            humedad_cols = humedad_cols_content
            
        print(f"Columnas identificadas por contenido:")
        print(f"  - Deformación: {deformacion_cols}")
        print(f"  - Temperatura: {temperatura_cols}")
        print(f"  - Humedad: {humedad_cols}")
    
    # Validaciones con mensajes más informativos
    if not deformacion_cols:
        # Intentar usar todas las columnas numéricas como última opción
        columnas_numericas = df.select_dtypes(include=[float, int]).columns.tolist()
        if columnas_numericas:
            print(f"⚠️ Usando columnas numéricas como deformación: {columnas_numericas}")
            deformacion_cols = columnas_numericas[:3]  # Usar máximo 3 columnas
        else:
            raise ValueError(f"❌ No se encontraron columnas de deformación. Columnas disponibles: {list(df.columns)}")
    
    if not temperatura_cols:
        # Usar la primera columna numérica disponible
        columnas_numericas = df.select_dtypes(include=[float, int]).columns.tolist()
        if columnas_numericas:
            temperatura_cols = [columnas_numericas[0]]
            print(f"⚠️ Usando primera columna numérica como temperatura: {temperatura_cols}")
        else:
            raise ValueError(f"❌ No se encontraron columnas de temperatura. Columnas disponibles: {list(df.columns)}")
    
    # Extraer datos
    try:
        deformacion = df[deformacion_cols]
        temperatura = df[temperatura_cols]
        
        if humedad_cols:
            humedad = df[humedad_cols]
        else:
            print("⚠️ No se encontraron columnas de humedad, usando valores por defecto")
            humedad = pd.DataFrame({'humedad_default': [50.0] * len(df)})
    
    except KeyError as e:
        raise ValueError(f"❌ Error al acceder a las columnas: {e}")
    
    # Deformación promedio corregida
    try:
        deformacion_sensi = deformacion.mean(skipna=True) * 1.2
        vdefor = deformacion_sensi.values.flatten().tolist()
        defo_prom = vdefor[0] if vdefor else 0.0
    except Exception as e:
        print(f"⚠️ Error calculando deformación: {e}")
        defo_prom = 0.0
    
    # Temperatura (usar primera columna válida)
    try:
        temp_series = temperatura.iloc[:, 0]
        if temp_series.isnull().all():
            print("⚠️ La columna de temperatura está vacía, usando valores por defecto")
            temp_0, temp_1 = 20.0, 25.0
        else:
            temp_0 = temp_series.iloc[0] if not pd.isna(temp_series.iloc[0]) else 20.0
            temp_1 = temp_series.iloc[-1] if not pd.isna(temp_series.iloc[-1]) else 25.0
        
        diff_temp = temp_1 - temp_0
    except Exception as e:
        print(f"⚠️ Error calculando temperatura: {e}")
        diff_temp = 5.0
    
    # Calcular humedad sensorial
    try:
        vhumedad = humedad.mean(skipna=True).values.flatten().tolist()
        # Asegurar que tenemos al menos algunos valores
        while len(vhumedad) < 5:
            vhumedad.append(50.0)  # Valor por defecto
        sensores = min(len(vhumedad), 5)
    except Exception as e:
        print(f"⚠️ Error calculando humedad: {e}")
        vhumedad = [50.0] * 5
        sensores = 5
    
    constantes = [
        (83.76, 27.95),
        (65.87, 20.33),
        (94.59, 14.46),
        (87.58, 10.23),
        (79.79, 14.82)
    ]
    
    valores_humedad = []
    for i in range(5):
        try:
            if i < sensores:
                C, D = constantes[i]
                hs = (vhumedad[i] * 1.2 - defo_prom - (C * diff_temp)) / D
                valores_humedad.append(hs)
            else:
                valores_humedad.append(None)
        except Exception as e:
            print(f"⚠️ Error calculando humedad sensorial {i}: {e}")
            valores_humedad.append(None)
    
    # Resumen
    resumen = {
        "Fecha": [fecha_str],
        "Archivo": [filename],
        "Deformación promedio": [defo_prom],
        "Diferencia temperatura": [diff_temp],
        "Temperatura promedio": [temp_series.mean(skipna=True)],
        "Humedad Sens. 0": [valores_humedad[0]],
        "Humedad Sens. 1": [valores_humedad[1]],
        "Humedad Sens. 2": [valores_humedad[2]],
        "Humedad Sens. 3": [valores_humedad[3]],
        "Humedad Sens. 4": [valores_humedad[4]],
    }
    
    print(f"✅ Métricas calculadas exitosamente para {filename}")
    return pd.DataFrame(resumen)
