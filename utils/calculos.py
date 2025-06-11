import pandas as pd
import re
from datetime import datetime


def extraer_fecha_desde_nombre(nombre_archivo):
    match = re.search(r'(\d{4})_(\d{2})_(\d{2})', nombre_archivo)
    if match:
        año, mes, dia = match.groups()
        return f"{dia}/{mes}/{año}"
    return "Fecha desconocida"


def metricas(df, filename=""):
    # Limpiar nombres de columnas
    df.columns = df.columns.str.strip()

    fecha_str = extraer_fecha_desde_nombre(filename)

    # -------------------------------
    # Buscar columnas con patrones flexibles
    # -------------------------------
    deformacion_cols = [col for col in df.columns if "def" in col.lower()]
    temperatura_cols = [col for col in df.columns if "temp" in col.lower() or "cal" in col.lower()]
    humedad_cols = [col for col in df.columns if "hum" in col.lower()]

    if not deformacion_cols:
        raise ValueError(f"❌ No se encontraron columnas de deformación. Columnas disponibles: {list(df.columns)}")
    if not temperatura_cols:
        raise ValueError(f"❌ No se encontraron columnas de temperatura. Columnas disponibles: {list(df.columns)}")
    if not humedad_cols:
        raise ValueError(f"❌ No se encontraron columnas de humedad. Columnas disponibles: {list(df.columns)}")

    deformacion = df[deformacion_cols]
    temperatura = df[temperatura_cols]
    humedad = df[humedad_cols]

    # -------------------------------
    # Deformación promedio corregida
    # -------------------------------
    deformacion_sensi = deformacion.mean(skipna=True) * 1.2
    vdefor = deformacion_sensi.values.flatten().tolist()
    defo_prom = vdefor[0] if vdefor else None

    # -------------------------------
    # Temperatura (usar primera columna válida)
    # -------------------------------
    temp_series = temperatura.iloc[:, 0]
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
    }

    return pd.DataFrame(resumen)

