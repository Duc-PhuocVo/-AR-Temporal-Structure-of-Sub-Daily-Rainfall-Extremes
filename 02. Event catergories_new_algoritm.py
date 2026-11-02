# -*- coding: utf-8 -*-
"""
Created on Fri Jan 30 14:39:53 2026

@author: nvo599
"""

import pandas as pd
import numpy as np
import os

#%% Functional Fixes for Pandas 3.0

def clean_datetime_index(df):
    df = df.copy()
    # Explicitly tell pandas that days come first
    if not isinstance(df.index, pd.DatetimeIndex):
        df.index = pd.to_datetime(df.index, dayfirst=True, errors='coerce')
    
    # Drop rows where dates couldn't be parsed
    df = df[df.index.notna()]
    return df.sort_index()

def calculate_max_intensity(group, window_minutes):
    if group.empty:
        return np.nan
    # Rolling on a time-offset requires a DatetimeIndex
    return (
        group['Rainfall [mm]']
        .rolling(f'{window_minutes}min', min_periods=1)
        .sum()
        .max()
    )

def detect_events(df, ietd_minutes):
    df = df.copy()
    if not isinstance(df.index, pd.DatetimeIndex):
        df.index = pd.to_datetime(df.index, dayfirst=True, errors='coerce')
    
    df = df.loc[~df.index.isna()].copy()
    df['Rainfall [mm]'] = df['Rainfall [mm]'].fillna(0)

    # Use .loc to avoid Copy-on-Write warnings
    df_rain = df[df['Rainfall [mm]'] > 0].copy()
    if df_rain.empty:
        return df

    # time_diff calculation
    df_rain['time_diff'] = df_rain.index.to_series().diff().dt.total_seconds() / 60
    df_rain['new_event'] = (df_rain['time_diff'] >= ietd_minutes).astype(int)
    
    # Correcting first row assignment for Pandas 3.0
    df_rain.iloc[0, df_rain.columns.get_loc('new_event')] = 1
    df_rain['final_event'] = df_rain['new_event'].cumsum()

    # Join event IDs back to original dataframe
    df = df.join(df_rain[['final_event']], how='left')
    
    # Create start date map
    event_start_dates = df_rain.groupby('final_event').apply(
        lambda x: x.index.min(), include_groups=False
    )
    df['event_start_date'] = df['final_event'].map(event_start_dates)

    return df.dropna(subset=['final_event'])

def categorize_storms(events_df):
    events_df = events_df.copy()
    storm_categories = {}

    # include_groups=False is a requirement in modern Pandas groupby.apply
    for event_id, group in events_df.groupby('final_event'):
        if len(group) < 2: continue

        total_rainfall = group['Rainfall [mm]'].sum()
        if total_rainfall <= 0: continue

        group = group.sort_index()
        cum_rain = group['Rainfall [mm]'].cumsum() / total_rainfall * 100
        
        total_dur = (group.index[-1] - group.index[0]).total_seconds() / 60
        if total_dur == 0: continue
        
        cum_time = ((group.index - group.index[0]).total_seconds() / 60) / total_dur * 100

        # Interpolation logic
        r25 = np.interp(25, cum_time, cum_rain)
        r50 = np.interp(50, cum_time, cum_rain)
        r75 = np.interp(75, cum_time, cum_rain)
        r100 = np.interp(100, cum_time, cum_rain)

        # Logic for quartiles
        if r50 - r25 >= 40: q = 2
        elif r75 - r50 >= 40: q = 3
        elif r100 - r75 >= 40: q = 4
        elif r25 >= 40: q = 1
        else: q = 5
        storm_categories[event_id] = q

    events_df['storm_category'] = events_df['final_event'].map(storm_categories)
    return events_df, storm_categories

def compute_rainfall_metrics(df, duration, unique_events):
    df = df.copy().sort_index()
    sum_col = f"{duration}h_Rainfall_Sum"
    dur_mask_col = f"{duration}hmax_dur"

    # Initialize columns with 0 or NaN
    df[sum_col] = np.nan
    df[dur_mask_col] = 0

    for event_id in unique_events:
        mask = df['final_event'] == event_id
        event_group = df.loc[mask].copy()
        
        if event_group.empty: continue

        # Calculate rolling sum
        rolling_vals = event_group['Rainfall [mm]'].rolling(f"{duration}h", min_periods=1).sum()
        df.loc[mask, sum_col] = rolling_vals

        # Identify max window
        max_val = rolling_vals.max()
        if pd.isna(max_val): continue
        
        # End of the max rainfall period
        max_end_time = event_group.index[rolling_vals == max_val].min()
        max_start_time = max_end_time - pd.Timedelta(hours=duration)
        
        # Mark the duration window
        window_mask = (df.index > max_start_time) & (df.index <= max_end_time) & (df['final_event'] == event_id)
        df.loc[window_mask, dur_mask_col] = 1

    return df

#%% Main Processing Loop

rainfall_process = 'C:/Users/nvo599/OneDrive - The University of Auckland/00. PhD/Final_version/Result/00_rainfall_events_base'
output_dir = 'C:/Users/nvo599/OneDrive - The University of Auckland/00. PhD/Final_version/Result/01_rainfall_events'
base_path = r"C:/Users/nvo599/OneDrive - The University of Auckland/00. PhD/Final_version/AR_IVT_RA_clean/"

ietd_minutes = 6 * 60
min_duration = 60
min_rainfall = 0.5

intensity_windows = {
    '60-min': 60,
    '180-min': 180,
    '360-min': 360,
    '720-min': 720,
    '1440-min': 1440
}

folder_names = [
    name for name in os.listdir(base_path)
    if os.path.isdir(os.path.join(base_path, name))
]

for folder in folder_names:
    input_dir = os.path.join(base_path, folder)
    if not os.path.isdir(input_dir): continue
    files = [f for f in os.listdir(input_dir) if f.endswith('.csv')]

    for f in files:
        station = f.rsplit('_', 1)[0]
        file_path = os.path.join(input_dir, f)

        # Read CSV with explicit index processing
        input_df = pd.read_csv(file_path)
        if 'time' in input_df.columns:
            input_df['time'] = pd.to_datetime(input_df['time'], dayfirst=True, errors='coerce')
            input_df.set_index('time', inplace=True)
        
        input_df = clean_datetime_index(input_df)
        df = detect_events(input_df, ietd_minutes)

        if df.empty: continue

        # Filter events by duration and total rainfall
        event_stats = df.groupby('final_event').agg(
            total_rain=('Rainfall [mm]', 'sum'),
            start_time=('Rainfall [mm]', lambda x: x.index.min()),
            end_time=('Rainfall [mm]', lambda x: x.index.max())
        )
        event_stats['dur'] = (event_stats['end_time'] - event_stats['start_time']).dt.total_seconds() / 60
        
        valid_ids = event_stats[(event_stats['dur'] > min_duration) & (event_stats['total_rain'] > min_rainfall)].index
        df = df[df['final_event'].isin(valid_ids)].copy()

        if df.empty: continue

        # Intensity windows
        for label, minutes in intensity_windows.items():
            # Use include_groups=False for Pandas 3.0 compatibility
            intensities = df.groupby('final_event').apply(
                lambda x: calculate_max_intensity(x, minutes), include_groups=False
            )
            df[label] = df['final_event'].map(intensities)

        df, _ = categorize_storms(df)
        
        unique_events = df['final_event'].unique()
        for d in [3, 6, 12, 24]:
            df = compute_rainfall_metrics(df, d, unique_events)

        # Save processed data
        df.to_csv(os.path.join(rainfall_process, f))
        
        # This replaces the manual 'events_info' loop for better performance
        summary_df = df.groupby('final_event').agg(
            Start_Time=('Rainfall [mm]', lambda x: x.index.min()),
            End_Time=('Rainfall [mm]', lambda x: x.index.max()),
            Total_Rainfall_mm=('Rainfall [mm]', 'sum'),
            Category=('storm_category', 'first'),
            AR_percent=('AR', lambda x: x.mean() * 100),
            IVT_mean=('IVT', 'mean')
        ).reset_index()

        # Add the intensity window results
        for label in intensity_windows.keys():
            # Map the intensity values we already calculated in the main df
            intensity_map = df.groupby('final_event')[label].first()
            summary_df[label] = summary_df['final_event'].map(intensity_map)

        # Rename columns to match your original structure
        summary_df.columns = [
            'Event ID', 'Start Time', 'End Time', 
            'Total Rainfall [mm]', 'Category', 'AR_percent', 'IVT'
        ] + list(intensity_windows.keys())

        # Calculate Thresholds and Flags
        # Quantiles are calculated per station
        summary_df['P99'] = summary_df['Total Rainfall [mm]'] > summary_df['Total Rainfall [mm]'].quantile(0.99)
        summary_df['P95'] = summary_df['Total Rainfall [mm]'] > summary_df['Total Rainfall [mm]'].quantile(0.95)
        
        summary_df['50 mm'] = (summary_df['Total Rainfall [mm]'] > 50).astype(int)
        summary_df['100 mm'] = (summary_df['Total Rainfall [mm]'] > 100).astype(int)
        
        # AR occurrence flag (if mean AR coverage during event is >= 50%)
        summary_df['AR'] = (summary_df['AR_percent'] >= 50).astype(int)
        
        # Calculate Duration in Hours
        summary_df['Duration'] = (
            summary_df['End Time'] - summary_df['Start Time']
        ).dt.total_seconds() / 3600

        # Save the final summary file
        summary_output_path = os.path.join(output_dir, f"{station}.csv")
        summary_df.to_csv(summary_output_path, index=False)
        
        print(f'Successfully finished processing and summary for: {station}')

print("--- ALL STATIONS PROCESSED ---")