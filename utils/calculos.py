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
    fecha_str = extraer_fecha_desde_nombre(filename)

    # -------------------------------
    # Extraer columnas
    # -------------------------------
    deformacion = df.filter(like='_Def')
    temperatura = df.filter(like="_Cal")
    humedad = df.filter(like="_Hum")

    if deformacion.empty:
        raise ValueError("❌ No se encontraron columnas de deformación ('_Def')")
    if temperatura.empty:
        raise ValueError("❌ No se encontraron columnas de temperatura ('_Cal')")
    if humedad.empty:
        raise ValueError("❌ No se encontraron columnas de humedad ('_Hum')")

    # -------------------------------
    # Deformación promedio corregida
    # -------------------------------
    deformacion_sensi = deformacion.mean(skipna=True) * 1.2
    vdefor = deformacion_sensi.values.flatten().tolist()
    defo_prom = vdefor[0] if vdefor else None

    # -------------------------------
    # Temperatura (buscar columna)
    # -------------------------------
    temp_cols = [col for col in temperatura.columns if "Temp_1_Cal" in col]
    if not temp_cols:
        raise ValueError("❌ No se encontró una columna de temperatura tipo 'Temp_1_Cal'")

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
            valores_humedad.append(None)  # Si no hay datos, poner None

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
