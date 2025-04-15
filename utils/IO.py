import pandas as pd
import os

def extract_excel_to_dataframe(uploaded_file):
    dataframe = pd.read_excel(uploaded_file)
    return dataframe