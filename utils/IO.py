import pandas as pd
import os

def extract_excel_to_dataframe(uploaded_file):
    try:
        # Leer el archivo sin usar la primera fila como encabezado
        df = pd.read_excel(uploaded_file, header=None, skiprows=1)

        # Usar la segunda fila del archivo como encabezado
        new_header = df.iloc[0]  # La "segunda" fila (después de saltar una)
        df = df[1:]              # El resto de los datos
        df.columns = new_header

        # Convertir nombres de columna a string y limpiar
        df.columns = df.columns.map(str).str.strip()

        return df
    except Exception as e:
        raise ValueError(f"❌ No se pudo leer el archivo: {e}")
