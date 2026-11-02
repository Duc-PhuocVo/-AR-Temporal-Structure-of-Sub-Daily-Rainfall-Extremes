# -*- coding: utf-8 -*-
"""
Created on Thu May  8 10:51:37 2025

@author: nvo599
"""

import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import numpy as np
import os

input_dir = 'C:/Users/nvo599/OneDrive - The University of Auckland/00. PhD/Final_version/AR_IVT_RA'
save_dir = 'C:/Users/nvo599/OneDrive - The University of Auckland/00. PhD/Final_version/Result'
output = []

minimum_rain = 0.2
threseshold = 0.95

region_name_map = {
    'AKL': 'Auckland',
    'NTL': 'Northland',
    'WKO': 'Waikato',
    'BOP': 'Bay of Plenty',
    'GIS': 'Gisborne',
    'TKI': 'Taranaki',
    'HKB': 'Hawkes Bay',
    'MWT': 'Manawatū-Whanganui',
    'WEL': 'Wellington',
    'NSN': 'Nelson',
    'MBH': 'Marlborough',
    'CAN': 'Canterbury',
    'OTA': 'Otago',
    'STL': 'Southland',
    # Add others as needed
}
#%%
sns.set(style='whitegrid')
plt.rcParams.update({
    'axes.titlesize': 20,
    'axes.labelsize': 16,
    'xtick.labelsize': 14,
    'ytick.labelsize': 14,
    'legend.fontsize': 14
})

folders = sorted([f for f in os.listdir(input_dir) if os.path.isdir(os.path.join(input_dir, f))])
num_regions = len(folders)
ncols = 4  # Each column = 1 type of plot
nrows = num_regions  # Each row = 1 region
fig, axs = plt.subplots(nrows, ncols, figsize=(ncols * 6, nrows * 3), constrained_layout=True)
axs = np.array(axs)  # in case of single row

for region_idx, folder in enumerate(folders):
    folder_path = os.path.join(input_dir, folder)
    region_data = []

    for file in os.listdir(folder_path):
        if file.endswith('.csv'):
            file_path = os.path.join(folder_path, file)
            df = pd.read_csv(file_path)
            station = file.split('.')[0]

            if 'Rainfall [mm]' not in df.columns or 'AR' not in df.columns:
                continue

            # df['time'] = pd.to_datetime(df['time'])
            # df = df.sort_values('time').reset_index(drop=True)
            
            df['time'] = pd.to_datetime(
            df['time'],
            format='mixed',
            dayfirst=True,
            errors='coerce'
            )
            df = df.dropna(subset=['time'])
            df = df.sort_values('time').reset_index(drop=True)
            
            p95 = df[df['Rainfall [mm]'] > minimum_rain]['Rainfall [mm]'].quantile(threseshold)
            df['p95'] = df['Rainfall [mm]'] >= p95
            df_p95 = df[df['p95']].dropna(subset=['AR']).copy()
            if df_p95.empty:
                continue

            df_p95['event_group'] = (df_p95['time'].diff() != pd.Timedelta(hours=1)).cumsum()
            
            new_rows = []
            for group_id, group_df in df_p95.groupby('event_group'):
                group_df = group_df.sort_values('time').reset_index(drop=True)
                new_rows.append({
                    'duration_hr': len(group_df),  # Number of hours in the event
                    'total_rainfall': group_df['Rainfall [mm]'].sum(),
                    'max_intensity': group_df['Rainfall [mm]'].max(),
                    'max_IVT': group_df['IVT'].max(),
                    'AR_present': group_df['AR'].max(),
                    'station': station
                })

            grouped = pd.DataFrame(new_rows)
            if not grouped.empty:
                grouped['avg_intensity'] = grouped['total_rainfall'] / grouped['duration_hr']
                grouped['duration_hr'] = grouped['duration_hr'].astype(int)
                region_data.append(grouped)

    if not region_data:
        continue

    region_df = pd.concat(region_data, ignore_index=True)
    region_df = region_df[region_df['duration_hr'] <= 12]  # ✅ Only durations ≤ 12 hours
    filtered = region_df.copy()


    # Plot 1: Duration distribution
    duration_dist = (
        filtered.groupby(['duration_hr', 'AR_present'])
        .size()
        .reset_index(name='count')
    )
    duration_dist['percent'] = duration_dist.groupby('AR_present')['count'].transform(lambda x: 100 * x / x.sum())
    pivot_df = duration_dist.pivot(index='duration_hr', columns='AR_present', values='percent').fillna(0)

    if 0 in pivot_df.columns and 1 in pivot_df.columns:
        pivot_df.columns = ['Non-AR', 'AR']
    elif 1 in pivot_df.columns:
        pivot_df.columns = ['AR']
    elif 0 in pivot_df.columns:
        pivot_df.columns = ['Non-AR']

    x = np.arange(len(pivot_df))
    bar_width = 0.4
    ax = axs[region_idx, 0]
    if 'AR' in pivot_df.columns:
        ax.bar(x - bar_width/2, pivot_df['AR'], width=bar_width, label='AR', color='blue')
    if 'Non-AR' in pivot_df.columns:
        ax.bar(x + bar_width/2, pivot_df['Non-AR'], width=bar_width, label='Non-AR', color='green')
    ax.plot(x, 100 / (pivot_df.index), 'k--', label='1/n')
    
    # -------------------------------------------------------------
    # LOG SCALE UPDATES FOR COLUMN 1
    # -------------------------------------------------------------
    ax.set_yscale('log')
    
    # Set lower bound so zero-percentage bars don't cause rendering artifacts
    # Adjust 0.1 to 0.01 if you have smaller non-zero percentages to display
    ax.set_ylim(bottom=0.1, top=100) 
    # -------------------------------------------------------------

    ax.set_xticks(x)
    ax.set_xticklabels(pivot_df.index if region_idx == nrows - 1 else [])
    if region_idx == 0:
        ax.set_title("% Events by Duration")
    if region_idx == nrows - 1:
        ax.set_xlabel("Duration (hr)")

    region_full_name = region_name_map.get(folder, folder)
    ax.set_ylabel(region_full_name, fontsize=16, weight='bold')
    if region_idx == 0:
        ax.legend()        

    # ax.set_ylabel(folder if ax == axs[region_idx, 0] else "")
    
    region_full_name = region_name_map.get(folder, folder)
    ax.set_ylabel(region_full_name , fontsize=16, weight='bold')
    if region_idx == 0:
        ax.legend()

    # Plot 2: Avg Intensity
    ax = axs[region_idx, 1]
    sns.lineplot(data=filtered, x='duration_hr', y='avg_intensity', hue='AR_present',
                 ax=ax, palette={1: 'blue', 0: 'green'}, marker='o', legend=False)
    if region_idx == 0:
        ax.set_title("Avg Intensity")
    if region_idx == nrows - 1:
        ax.set_xlabel("Duration (hr)")
    else:
        ax.set_xlabel("")
    ax.set_ylabel("")

    # Plot 3: Total Rainfall
    ax = axs[region_idx, 2]
    sns.lineplot(data=filtered, x='duration_hr', y='total_rainfall', hue='AR_present',
                 ax=ax, palette={1: 'blue', 0: 'green'}, marker='o', legend=False)
    if region_idx == 0:
        ax.set_title("Total Rainfall")
    if region_idx == nrows - 1:
        ax.set_xlabel("Duration (hr)")
    else:
        ax.set_xlabel("")
    ax.set_ylabel("")

    # Plot 4: Max Intensity
    ax = axs[region_idx, 3]
    sns.lineplot(data=filtered, x='duration_hr', y='max_intensity', hue='AR_present',
                 ax=ax, palette={1: 'blue', 0: 'green'}, marker='o', legend=False)
    if region_idx == 0:
        ax.set_title("Max Intensity")
    if region_idx == nrows - 1:
        ax.set_xlabel("Duration (hr)")
    else:
        ax.set_xlabel("")
    ax.set_ylabel("")

plt.suptitle("Rainfall Event Characteristics by Region", fontsize=18)
plt.tight_layout(rect=[0, 0, 1, 0.97])
plt.show()
