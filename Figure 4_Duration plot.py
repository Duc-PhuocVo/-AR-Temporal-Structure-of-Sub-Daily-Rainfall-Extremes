
# -*- coding: utf-8 -*-
"""
Created on Tue Mar 31 14:09:35 2026
@author: nvo599
"""

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import os

# ==============================
# Region mapping
# ==============================
region_name_map = { 
    'AKL': 'Auckland', 'NTL': 'Northland', 'WKO': 'Waikato',
    'BOP': 'Bay of Plenty', 'GIS': 'Gisborne', 'TKI': 'Taranaki',
    'HKB': 'Hawkes Bay', 'MWT': 'Manawatū-Whanganui', 'WEL': 'Wellington',
    'NSN': 'Nelson', 'MBH': 'Marlborough', 'CAN': 'Canterbury',
    'OTA': 'Otago', 'STL': 'Southland',
}

# ==============================
# Plot style
# ==============================
sns.set(style='whitegrid')
plt.rcParams.update({
    'axes.titlesize': 18,
    'axes.labelsize': 14,
    'xtick.labelsize': 12,
    'ytick.labelsize': 12,
    'legend.fontsize': 12
})

# ==============================
# Input & Setup
# ==============================
input_dir = ('C:/Users/nvo599/OneDrive - The University of Auckland/00. PhD/Final_version/'
             'Result/01_rainfall_events/2026_run')

region_folders = [f for f in os.listdir(input_dir) if os.path.isdir(os.path.join(input_dir, f))]

# ==========================================================
# NEW GRID: 5 Rows, 2 Columns with SHARED AXES
# ==========================================================
rows, cols = 5, 2
fig, axs = plt.subplots(rows, cols, figsize=(15, 22), sharex=True, sharey=True)
axs_flat = axs.flatten()

# Storage for global max density calculation
all_regional_dfs = {}

# First Pass: Load data and find global limits
for folder in region_folders:
    folder_path = os.path.join(input_dir, folder)
    duration_data = []
    for file in os.listdir(folder_path):
        if file.endswith('.csv'):
            print (file)
            df = pd.read_csv(os.path.join(folder_path, file))
            # Critical date fix
            df["Start Time"] = pd.to_datetime(df["Start Time"], errors="coerce")
            df["AR"] = df["AR"].fillna(0).astype(bool)
            df["P95"] = df["P95"].astype(bool)
            df["Duration"] = pd.to_numeric(df["Duration"], errors="coerce")
            df = df[(df["Duration"] > 0) & (df["Duration"] <= 170) & (df["P95"])]
            duration_data.append(df[["Duration", "AR"]])
    
    if duration_data:
        all_regional_dfs[folder] = pd.concat(duration_data, ignore_index=True)

#%% ==========================================================
# Second Pass: Plotting
# ==========================================================
for idx, (folder, combined_df) in enumerate(all_regional_dfs.items()):
    if idx >= rows * cols: break
    
    ax = axs_flat[idx]
    region_name = region_name_map.get(folder, folder)

    sns.histplot(
    data=combined_df, x="Duration", hue="AR",
    bins=30, kde=True, stat="density", common_norm=False,
    palette={True: "dodgerblue", False: "gray"}, ax=ax,
    alpha=0.4, legend=(idx == 0),
    )
    
    # Change legend labels
    # Customize the legend labels on the first subplot
    if idx == 0:
        legend = ax.get_legend()
        if legend:
            legend.set_title("")  # Remove legend title
            labels = ["Non AR", "AR"]  # Map to False, True
            for text, label in zip(legend.get_texts(), labels):
                text.set_text(label)
    
    # Labeling
    ax.set_title(f"{region_name}", fontweight='bold', fontsize=16)
    
    # Only show labels on the outer edges for a clean look
    if idx >= 8: ax.set_xlabel("Duration (hours)")
    if idx % 2 == 0: ax.set_ylabel("Density")

# Clean up
for i in range(len(all_regional_dfs), rows * cols):
    axs_flat[i].set_visible(False)

# Optional: Force a specific X-Limit if desired
plt.xlim(0, 120)

plt.tight_layout(rect=[0, 0.03, 1, 0.97])
# plt.suptitle("Comparative Duration Distributions (P95 Extremes)", fontsize=24, y=0.99)
plt.savefig('duration_shared_axes_5x2.png', dpi=300)
plt.show()