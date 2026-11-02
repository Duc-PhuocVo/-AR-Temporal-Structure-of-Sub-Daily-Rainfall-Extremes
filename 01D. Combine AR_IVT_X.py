# -*- coding: utf-8 -*-
"""
Created on Sat Apr 19 15:03:58 2025

@author: nvo599
"""

import pandas as pd
import os
import numpy as np

# Function to load matching files from a directory
def load_matching_files(directory, keyword):
    dfs = []
    for fname in os.listdir(directory):
        if keyword in fname and fname.endswith('.csv'):
            fpath = os.path.join(directory, fname)
            df = pd.read_csv(fpath, parse_dates=['time'], 
            dayfirst=True)
            df['source_file'] = fname  # Optional: track source
            # print (df)
            dfs.append(df)
    return dfs

# Directory paths
final_dir = 'C:/Users/nvo599/OneDrive - The University of Auckland/00. PhD/Final_version'
AR_dir = os.path.join(final_dir, 'AR')
rainfall_dir = os.path.join(final_dir, 'Rainfall_1990_2020_CSV/WKO')
IVT_dir = os.path.join(final_dir,'IVT')
save_dir = os.path.join(final_dir,'AR_IVT_RA_clean')

# Process rainfall files
files = os.listdir(rainfall_dir)
os.chdir(rainfall_dir)

for rf in files:
    keyword = rf.split('_')[0]
    df = pd.read_csv(
        rf, 
        parse_dates=['Time_UTC'], 
        dayfirst=True
        )
    cols = df.columns

#     # Ensure datetime and index
#     # df['Time_UTC'] = pd.to_datetime(df['Time_UTC'], format="%d/%m/%Y %H:%M:%S")
#     cols = df.columns

    # Fill missing rainfall values (optional)
    df.fillna(0, inplace=True)

    # Resample to 1H frequency (sum of rainfall)
    df_hourly = df[['Rainfall [mm]', 'Time_UTC']]
    df_hourly = df_hourly.rename(columns={'Time_UTC': 'time'})
    df_hourly['time'] = pd.to_datetime(df_hourly['time'])

    # Load matching AR and IVT files
    ar_dfs = load_matching_files(AR_dir, keyword)
    ivt_dfs = load_matching_files(IVT_dir, keyword)

    # Concatenate AR dataframes
    df_ar = pd.concat(ar_dfs, ignore_index=True) if ar_dfs else pd.DataFrame()
    if not df_ar.empty:
        df_ar['time'] = pd.to_datetime(df_ar['time'])
    # Concatenate IVT dataframes
    df_ivt = pd.concat(ivt_dfs, ignore_index=True) if ivt_dfs else pd.DataFrame()
    if not df_ivt.empty:
        df_ivt['time'] = pd.to_datetime(df_ivt['time'])

    # Parse datetime
    if not df_ar.empty:
        df_ar['time'] = pd.to_datetime(df_ar['time'])
    
        # Create AR flag if any of ar1-ar4 == 1
        df_ar['AR'] = np.where(
            (df_ar['ar1'] == 1) | (df_ar['ar2'] == 1) | (df_ar['ar3'] == 1) | (df_ar['ar4'] == 1),
            1, 0
        )
    
        df_ar = df_ar[['time', 'AR']]
    
    if not df_ivt.empty:
        df_ivt['time'] = pd.to_datetime(df_ivt['time'])
    
        # Compute row-wise mean of IVT columns
        ivt_columns = ['IVT1', 'IVT2', 'IVT3', 'IVT4']
        existing_ivt_cols = [col for col in ivt_columns if col in df_ivt.columns]
    
        if existing_ivt_cols:
            df_ivt['IVT'] = df_ivt[existing_ivt_cols].mean(axis=1)
            df_ivt = df_ivt[['time', 'IVT']]
        else:
            print("Warning: None of the expected IVT columns found.")
            df_ivt = pd.DataFrame(columns=['time', 'IVT'])

    # Merge AR and IVT if both are available
    df_combined = df_hourly.copy()
    if not df_ar.empty:
        df_combined = pd.merge(df_combined, df_ar, on='time', how='left')
    if not df_ivt.empty:
        df_combined = pd.merge(df_combined, df_ivt, on='time', how='left')

    # Optional: Save combined data
    combined_output = os.path.join(save_dir, f"{keyword}_combined_AR_IVT_Rain.csv")
    df_combined.to_csv(combined_output, index=False)
    print(f"Saved combined data to: {combined_output}")

# Final print
print("Processing complete.")