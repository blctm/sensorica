import pandas as pd
import os

def extract_excel_to_dataframe(uploaded_file):
    try:
        # Leer todo sin encabezado, saltando la primera fila
        df = pd.read_excel(uploaded_file, header=None, skiprows=1)

        # La nueva cabecera está en la primera fila del resultado
        new_header = df.iloc[0]
        df = df[1:]  # El resto son datos

        df.columns = new_header  # Aplicar la nueva cabecera
        df.columns = df.columns.map(str).str.strip()  # Asegurar que son strings

        return df.reset_index(drop=True)

    except Exception as e:
        raise ValueError(f"❌ No se pudo leer el archivo: {e}")
