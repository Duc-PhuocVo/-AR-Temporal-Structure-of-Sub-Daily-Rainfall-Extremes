# -*- coding: utf-8 -*-
"""
Created on Mon Apr  6 13:50:00 2026
Updated for 3-panel AR Dominance Plot (Single Column) and Regional Duration Table
@author: nvo599
"""

import os
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import cartopy.crs as ccrs
import cartopy.feature as cfeature
import cartopy.io.shapereader as shpreader

# --- Setup ---
plt.style.use('seaborn-v0_8')
input_dir = 'C:/Users/nvo599/OneDrive - The University of Auckland/00. PhD/Final_version/Metafile'
data_dir = r'C:/Users/nvo599/OneDrive - The University of Auckland/00. PhD/Final_version/Result/01_rainfall_events/2026_run'
shapefile_path = r'G:/00. PhD/00. Fundamental data/NZ region/nz_region_interserted_wgs2.shp' 

# Define durations for the table calculation
durations_map = {'3h': '180-min', '6h': '360-min', '12h': '720-min', '24h': '1440-min'}

# --- Processing Functions ---
def get_stats_for_duration(dfs, col_name, ar_key='AR'):
    """Helper to calculate Fraction and Amplification for a specific duration."""
    # 1. AR Fraction of Extremes (P95 of that duration)
    thresh = dfs[col_name].quantile(0.95)
    extremes = dfs[dfs[col_name] >= thresh]
    f_ar = (extremes[extremes[ar_key] == 1][col_name].sum() / extremes[col_name].sum()) * 100 if extremes[col_name].sum() > 0 else 0
    
    # 2. Amplification Ratio (Q95 AR / Q95 non-AR)
    q95_ar = dfs[dfs[ar_key] == 1][col_name].quantile(0.95)
    q95_non = dfs[dfs[ar_key] == 0][col_name].quantile(0.95)
    amp = q95_ar / q95_non if q95_non > 0 else 1
    
    return f_ar, amp

def calculate_plot_metrics(dfs):
    """Calculates the 3 specific metrics for the SPATIAL PLOT."""
    ar_key = 'AR'
    if ar_key not in dfs.columns: return None

    # (a) AR Fraction - P95 Total Rainfall
    t_p95 = dfs['Total Rainfall [mm]'].quantile(0.95)
    ext = dfs[dfs['Total Rainfall [mm]'] >= t_p95]
    f_ar = (ext[ext[ar_key] == 1]['Total Rainfall [mm]'].sum() / ext['Total Rainfall [mm]'].sum()) * 100 if ext['Total Rainfall [mm]'].sum() > 0 else 0

    # (b) Amplification - 6hr (360-min)
    q95_ar = dfs[dfs[ar_key] == 1]['360-min'].quantile(0.95)
    q95_non = dfs[dfs[ar_key] == 0]['360-min'].quantile(0.95)
    amp = q95_ar / q95_non if q95_non > 0 else 1

    # (c) Persistence Excess - Prob(Duration >= 6h)
    p_ar = (dfs[(dfs[ar_key] == 1) & (dfs['Duration'] >= 6)].shape[0] / dfs[dfs[ar_key] == 1].shape[0]) if not dfs[dfs[ar_key] == 1].empty else 0
    p_non = (dfs[(dfs[ar_key] == 0) & (dfs['Duration'] >= 6)].shape[0] / dfs[dfs[ar_key] == 0].shape[0]) if not dfs[dfs[ar_key] == 0].empty else 0
    delta_p = (p_ar - p_non) * 100 

    return f_ar, amp, delta_p

# --- Data Collection ---
result_list = []
table_list = []

for region in os.listdir(data_dir):
    region_path = os.path.join(data_dir, region)
    if not os.path.isdir(region_path): continue
    
    station_meta_file = os.path.join(input_dir, region + '.csv')
    if not os.path.exists(station_meta_file): continue
    
    station_meta = pd.read_csv(station_meta_file)
    files = os.listdir(region_path)
    
    for _, row in station_meta.iterrows():
        matched = [f for f in files if str(row['Agent']) in f]
        if matched:
            dfs = pd.read_csv(os.path.join(region_path, matched[0]))
            
            # 1. Collect Map Data
            m = calculate_plot_metrics(dfs)
            if m:
                result_list.append({
                    'Lat': row['Lat'], 'Lon': row['Lon'],
                    'f_ar': m[0], 'amp': m[1], 'delta_p': m[2]
                })
                
                # 2. Collect Table Data (Regional Comparison)
                table_row = {'Region': region, 'Agent': row['Agent']}
                for label, col in durations_map.items():
                    f, a = get_stats_for_duration(dfs, col)
                    table_row[f'f_ar_{label}'] = f
                    table_row[f'amp_{label}'] = a
                table_list.append(table_row)

result = pd.DataFrame(result_list)
table_df = pd.DataFrame(table_list)

# --- Save Regional Summary Table ---
regional_summary = table_df.groupby('Region').mean(numeric_only=True).drop(columns=['Agent'])
regional_summary.to_csv('Regional_Duration_Comparison.csv')
print("Regional duration comparison table saved to CSV.")

#%% --- Plotting ---
fig, axs = plt.subplots(1, 3, figsize=(14, 8.5), subplot_kw={'projection': ccrs.PlateCarree()})

panel_labels = ['(a)', '(b)', '(c)']
col_names = ['f_ar', 'amp', 'delta_p']
cmaps = ['Blues', 'Reds', 'RdYlGn']

for i, ax in enumerate(axs):
    ax.set_extent([172, 179, -41.7, -34], crs=ccrs.PlateCarree())
    ax.add_feature(cfeature.COASTLINE.with_scale('10m'), linewidth=0.8)
    ax.add_feature(cfeature.LAND, facecolor='#f9f9f9')
    
    if os.path.exists(shapefile_path):
        reader = shpreader.Reader(shapefile_path)
        ax.add_feature(cfeature.ShapelyFeature(reader.geometries(), ccrs.PlateCarree(), 
                       facecolor='none', edgecolor='gray', linewidth=0.5, alpha=0.5))

    sc = ax.scatter(result['Lon'], result['Lat'], c=result[col_names[i]], 
                    cmap=cmaps[i], s=80, edgecolor='k', linewidth=0.5, transform=ccrs.PlateCarree())
    
    cb = plt.colorbar(sc, ax=ax, orientation='horizontal', shrink=0.8, pad=0.05)
    cb.ax.tick_params(labelsize=9)
    
    # Add (a), (b), (c) in top-right of each panel with a translucent white background box
    ax.text(0.95, 0.95, panel_labels[i], transform=ax.transAxes,
            fontsize=13, fontweight='bold', va='top', ha='right',
            bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.85, edgecolor='none'))

plt.tight_layout()
plt.savefig('AR_Dominance_A4_Portrait.pdf', dpi=300, bbox_inches='tight')
plt.show()