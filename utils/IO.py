import pandas as pd
import os

def extract_excel_to_dataframe(uploaded_file):
    # Usa la segunda fila (índice 1) como cabecera real
    dataframe = pd.read_excel(uploaded_file, header=1)
    return dataframe
