import pandas as pd
import os

def extract_excel_to_dataframe(uploaded_file):
    """
    Extrae datos de un archivo Excel con manejo robusto de diferentes estructuras
    """
    try:
        # Primero, intentar leer las primeras filas para inspeccionar la estructura
        df_inspect = pd.read_excel(uploaded_file, header=None, nrows=5)
        print(f"Primeras 5 filas del archivo:")
        print(df_inspect)
        
        # Buscar la fila que contiene los nombres de columnas reales
        header_row = None
        for i in range(len(df_inspect)):
            row_values = df_inspect.iloc[i].astype(str).str.lower()
            # Buscar palabras clave que indiquen que es la fila de encabezados
            keywords = ['def', 'temp', 'hum', 'cal', 'time', 'timestamp']
            if any(keyword in str(val).lower() for val in row_values for keyword in keywords):
                header_row = i
                break
        
        if header_row is not None:
            print(f"Encabezados encontrados en la fila {header_row}")
            # Leer el archivo usando la fila de encabezados detectada
            df = pd.read_excel(uploaded_file, header=header_row, skiprows=range(0, header_row))
        else:
            # Si no se encuentran encabezados, probar diferentes estrategias
            print("No se detectaron encabezados automáticamente. Probando estrategias alternativas...")
            
            # Estrategia 1: Leer sin encabezado y usar la primera fila como encabezado
            df = pd.read_excel(uploaded_file, header=None)
            
            # Verificar si la primera fila contiene nombres válidos de columnas
            first_row = df.iloc[0].astype(str)
            if any('def' in str(val).lower() or 'temp' in str(val).lower() or 'hum' in str(val).lower() 
                   for val in first_row):
                df.columns = first_row
                df = df[1:].reset_index(drop=True)
            else:
                # Estrategia 2: Buscar en las primeras filas
                for i in range(min(5, len(df))):
                    row_values = df.iloc[i].astype(str)
                    if any('def' in str(val).lower() or 'temp' in str(val).lower() or 'hum' in str(val).lower() 
                           for val in row_values):
                        df.columns = row_values
                        df = df[i+1:].reset_index(drop=True)
                        break
                else:
                    # Si no se encuentran patrones, usar encabezados genéricos
                    print("Usando encabezados genéricos...")
                    df.columns = [f'Column_{i}' for i in range(len(df.columns))]
        
        # Limpiar nombres de columnas
        df.columns = df.columns.astype(str).str.strip()
        
        # Remover filas completamente vacías
        df = df.dropna(how='all')
        
        # Convertir columnas numéricas
        for col in df.columns:
            if df[col].dtype == 'object':
                try:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
                except:
                    pass
        
        print(f"Columnas finales detectadas: {list(df.columns)}")
        print(f"Forma del DataFrame: {df.shape}")
        print(f"Primeras filas de datos:")
        print(df.head(3))
        
        return df.reset_index(drop=True)
        
    except Exception as e:
        raise ValueError(f"❌ No se pudo leer el archivo: {e}")
