# -*- coding: utf-8 -*-
"""
Created on Thu Aug 13 11:14:44 2026

@author: nvo599
"""


import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from collections import defaultdict

plt.style.use('seaborn-v0_8')

# Region Name Mapping
region_name_map = { 
    'AKL': 'Auckland', 'NTL': 'Northland', 'WKO': 'Waikato',
    'BOP': 'Bay of Plenty', 'GIS': 'Gisborne', 'TKI': 'Taranaki',
    'HKB': 'Hawkes Bay', 'MWT': 'Manawatū-Whanganui', 'WEL': 'Wellington',
    'NSN': 'Nelson', 'MBH': 'Marlborough', 'CAN': 'Canterbury',
    'OTA': 'Otago', 'STL': 'Southland',
}

# Input paths
Rainfall_base_path = r"C:/Users/nvo599/OneDrive - The University of Auckland/00. PhD/Final_version/Result/00_rainfall_events_base/2026_run"
Event_base_path = r"C:/Users/nvo599/OneDrive - The University of Auckland/00. PhD/Final_version/Result/01_rainfall_events/2026_run"

# Parameters
duration_map = {'60-min': '1-Hour', '180-min': '3-Hour', '360-min': '6-Hour', '720-min': '12-Hour'}
duration_keys = list(duration_map.keys())
colors = ['blue', 'green', 'red', 'cyan']
months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
x = np.arange(12)

# Function: compute stats
def compute_stats(df):
    """Compute average monthly stats over years for each duration"""
    counts = defaultdict(lambda: np.zeros(12))
    totals = defaultdict(lambda: np.zeros(12))
    sums_for_mean = defaultdict(lambda: np.zeros(12))
    n_for_mean = defaultdict(lambda: np.zeros(12))

    # Extract year column for monthly grouping
    df['year'] = df['Start Time'].dt.year

    mean_counts = {}

    for dur in duration_keys:
        # Count number of events per month per year
        df_valid = df[df[dur] > 0]
        grouped = df_valid.groupby(['year', 'month']).size().unstack(fill_value=0)

        # Now average over years (row-wise mean)
        monthly_mean = grouped.mean(axis=0).reindex(range(1, 13), fill_value=0).values
        mean_counts[dur] = monthly_mean

        # For intensity and total rainfall
        for m in range(1, 13):
            monthly = df_valid[df_valid['month'] == m]
            idx = m - 1
            totals[dur][idx] = monthly[dur].sum()
            sums_for_mean[dur][idx] = monthly[dur].sum()
            n_for_mean[dur][idx] = len(monthly)

    # Calculate mean intensity and total per event
    mean_intensity = {}
    mean_total_rain = {}
    for dur in duration_keys:
        dur_hr = int(dur.split('-')[0]) / 60

        mean_intensity[dur] = np.divide(
            sums_for_mean[dur], n_for_mean[dur],
            out=np.zeros(12), where=n_for_mean[dur] != 0
        ) / dur_hr

        mean_total_rain[dur] = np.divide(
            totals[dur], n_for_mean[dur],
            out=np.zeros(12), where=n_for_mean[dur] != 0
        )

    return mean_counts, mean_intensity, mean_total_rain

# Prepare results container
region_results = []

# Read and process data
folder_names = [f for f in os.listdir(Rainfall_base_path) if os.path.isdir(os.path.join(Rainfall_base_path, f))]

for folder in folder_names:
    print(f" Processing region: {folder}")
    input_dir = os.path.join(Rainfall_base_path, folder)
    event_dir = os.path.join(Event_base_path, folder)

    if not os.path.exists(event_dir):
        print(f" Event directory not found for folder: {folder}")
        continue

    event_files = os.listdir(event_dir)
    ar_df_list = []
    nonar_df_list = []

    for file in os.listdir(input_dir):
        station = file.rsplit('_', 4)[0]
        matched_file = next((ef for ef in event_files if station in ef), None)
        if not matched_file:
            continue

        try:
            df = pd.read_csv(os.path.join(event_dir, matched_file))
            
            # Convert 'Start Time' safely to datetime
            df['Start Time'] = pd.to_datetime(df['Start Time'], errors='coerce')
            df = df.dropna(subset=['Start Time'])
            
        except Exception as e:
            print(f"   ❌ Error reading {matched_file}: {e}")
            continue

        df = df[df['Start Time'] >= '1990-01-01']
        df['month'] = df['Start Time'].dt.month
        
        if 'AR' not in df.columns:
            continue

        # --- SELECT ONLY P95 EVENTS ---
        if 'P95' in df.columns:
            df = df[df['P95'].astype(str).str.upper().isin(['TRUE', '1'])]
        
        if df.empty:
            continue

        ar_df_list.append(df[df['AR'] == 1])
        nonar_df_list.append(df[df['AR'] == 0])

    ar_df = pd.concat(ar_df_list, ignore_index=True) if ar_df_list else pd.DataFrame()
    nonar_df = pd.concat(nonar_df_list, ignore_index=True) if nonar_df_list else pd.DataFrame()
    if ar_df.empty and nonar_df.empty:
        continue

    ar_stats = compute_stats(ar_df)
    nonar_stats = compute_stats(nonar_df)

    region_results.append((folder, ar_stats, nonar_stats))

#%% Plotting
n_regions = len(region_results)
fig, axs = plt.subplots(n_regions, 3, figsize=(18, 3 * n_regions), sharex=True, sharey='col')
if n_regions == 1:
    axs = np.expand_dims(axs, axis=0)

column_titles = ["(a) Event Count", "(b) Mean Intensity (mm/hr)", "(c) Mean Total Rainfall"]

for row_idx, (region_code, ar_data, nonar_data) in enumerate(region_results):
    ar_counts, ar_means, ar_totals = ar_data
    nonar_counts, nonar_means, nonar_totals = nonar_data

    # Map folder region code to full region name
    full_region_name = region_name_map.get(region_code, region_code)

    # Add full region label
    axs[row_idx, 0].text(-0.18, 0.5, full_region_name, fontsize=15, va='center', ha='right',
                         transform=axs[row_idx, 0].transAxes, rotation=90)

    for col_idx in range(3):
        ax = axs[row_idx, col_idx]
        ax.set_xticks(x)
        ax.set_xticklabels(months, fontsize=13)
        ax.tick_params(axis='y', labelsize=14)
        if row_idx == 0:
            ax.set_title(column_titles[col_idx], fontsize=16)

    # === Panel (a): One line for event count ===
    ax = axs[row_idx, 0]
    dur_key = '60-min'  # event counts across durations are identical
    ax.plot(x, nonar_counts[dur_key], label="Non-AR", color='black', linewidth=2)
    ax.plot(x, ar_counts[dur_key], linestyle='--', label="AR", color='black', linewidth=2)
    ax.set_ylabel("No. of Events", fontsize=14)

    # === Panel (b): Mean Intensity (all durations) ===
    ax = axs[row_idx, 1]
    for dur, color in zip(duration_keys, colors):
        ax.plot(x, nonar_means[dur], label=duration_map[dur], color=color, linewidth=2)
        ax.plot(x, ar_means[dur], linestyle='--', color=color, linewidth=2)
    ax.set_ylabel("Intensity (mm/hr)", fontsize=14)

    # === Panel (c): Mean Total Rainfall (all durations) ===
    ax = axs[row_idx, 2]
    for dur, color in zip(duration_keys, colors):
        ax.plot(x, nonar_totals[dur], label=duration_map[dur], color=color, linewidth=2)
        ax.plot(x, ar_totals[dur], linestyle='--', color=color, linewidth=2)
    ax.set_ylabel("Rainfall (mm)", fontsize=14)

    # Add legend only in first row, third column
    if row_idx == 0:
        ax.legend(
            title="Solid: Non-AR\nDashed: AR\nLine Color: Duration",
            fontsize=12, title_fontsize=12,
            loc='upper right'
        )

plt.tight_layout(rect=[0, 0, 1, 0.96])
plt.show()