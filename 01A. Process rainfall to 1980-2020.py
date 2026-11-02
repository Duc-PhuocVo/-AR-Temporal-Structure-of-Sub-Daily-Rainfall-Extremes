# -*- coding: utf-8 -*-
"""
Created on Wed Apr 23 12:27:36 2025

@author: nvo599
"""

import os
import pandas as pd
import matplotlib.pyplot as plt

# Input and output directories
input_dir = 'C:/Users/nvo599/OneDrive - The University of Auckland/00. PhD/Final_version/Rainfall data/TKI'
save_dir = 'C:/Users/nvo599/OneDrive - The University of Auckland/00. PhD/Final_version/Rainfall_1980_2020/TKI'

# Get list of files
files = os.listdir(input_dir)

# Loop through files
for f in files:
    input_file = os.path.join(input_dir, f)
    save_file = os.path.join(save_dir, f)
    
    df = pd.read_csv(input_file)
    cols = df.columns
    
    # Convert to datetime
    df['Date (NZST)'] = pd.to_datetime(df['Date (NZST)'])
    df['DateTime (UTC)'] = pd.to_datetime(df['Date (NZST)']) - pd.Timedelta(hours=12)
    
    # Rename and add columns
    df = df.rename(columns={'Rainfall (mm)': 'Rainfall [mm]'})
    df['Time_UTC'] = df['DateTime (UTC)']
    df['Year'] = df['DateTime (UTC)'].dt.year
    
    # Filter by year range
    df = df[(df['Year'] >= 1980) & (df['Year'] <= 2020)]
    
    # Save to file
    df.to_csv(save_file, index=False)