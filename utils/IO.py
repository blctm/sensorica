import pandas as pd
import os

def extract_excel_to_dataframe(uploaded_file):
    try:
        # Leer desde la segunda fila (fila 1) como cabecera
        df = pd.read_excel(uploaded_file, header=1)

        # Asegurar que todos los nombres de columnas son strings y limpiarlos
        df.columns = df.columns.map(str).str.strip()

        return df
    except Exception as e:
        raise ValueError(f"❌ No se pudo leer el archivo: {e}")
