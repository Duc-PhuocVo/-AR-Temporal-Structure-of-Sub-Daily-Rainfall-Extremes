import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import os

# Region code to full name mapping
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

# Plot styling
sns.set(style='whitegrid')
plt.rcParams.update({
    'axes.titlesize': 20,
    'axes.labelsize': 16,
    'xtick.labelsize': 14,
    'ytick.labelsize': 14,
    'legend.fontsize': 14
})

# Input directory
input_dir = ('C:/Users/nvo599/OneDrive - The University of Auckland/00. PhD/Final_version/'
'Result/01_rainfall_events/2026_run')
region_folders = [f for f in os.listdir(input_dir) if os.path.isdir(os.path.join(input_dir, f))]
n_regions = len(region_folders)

# Set up figure
fig, axs = plt.subplots(n_regions, 2, figsize=(14, 3 * n_regions), squeeze=False)

# Plot loop
for idx, folder in enumerate(region_folders):
    folder_path = os.path.join(input_dir, folder)
    all_data, p95_raw, p99_raw = [], [], []

    for file in os.listdir(folder_path):
        if file.endswith('.csv'):
            file_path = os.path.join(folder_path, file)
            df = pd.read_csv(file_path)

            df["Start Time"] = pd.to_datetime(df["Start Time"], errors='coerce')
            df["Year"] = df["Start Time"].dt.year
            df["Month"] = df["Start Time"].dt.month
            df["AR"] = df["AR"].fillna(0).astype(bool)
            df["P95"] = df["P95"].astype(bool)
            df["P99"] = df["P99"].astype(bool)

            grouped = df.groupby(["Year", "Month"])
            rain_total = grouped["Total Rainfall [mm]"].sum()
            rain_ar = df[df["AR"]].groupby(["Year", "Month"])["Total Rainfall [mm]"].sum()
            p95_total = grouped["P95"].sum()
            p95_ar = df[df["AR"] & df["P95"]].groupby(["Year", "Month"])["P95"].count()

            monthly_df = pd.DataFrame({
                "Rainfall_Total": rain_total,
                "Rainfall_AR": rain_ar,
                "P95_Total": p95_total,
                "P95_AR": p95_ar
            }).fillna(0)

            monthly_df["AR_Rainfall_%"] = (monthly_df["Rainfall_AR"] / monthly_df["Rainfall_Total"]) * 100
            monthly_df = monthly_df.reset_index()
            all_data.append(monthly_df)

            p95_raw.append(df[df["P95"]][["Year", "Month", "AR"]])
            p99_raw.append(df[df["P99"]][["Year", "Month", "AR"]])

    if not all_data:
        continue

    combined_df = pd.concat(all_data, ignore_index=True)
    p95_df = pd.concat(p95_raw, ignore_index=True)
    p99_df = pd.concat(p99_raw, ignore_index=True)

    # Group P95 and P99 for bar plot
    p95_group = p95_df.groupby('Month')['AR'].agg(Total='count', AR_True='sum').reset_index()
    p95_group['Metric'] = 'P95'
    p95_group['AR_Contribution (%)'] = (p95_group['AR_True'] / p95_group['Total']) * 100

    p99_group = p99_df.groupby('Month')['AR'].agg(Total='count', AR_True='sum').reset_index()
    p99_group['Metric'] = 'P99'
    p99_group['AR_Contribution (%)'] = (p99_group['AR_True'] / p99_group['Total']) * 100

    bar_data = pd.concat([p95_group, p99_group], ignore_index=True)

    # Plot 1: Boxplot
    ax1 = axs[idx, 0]
    sns.boxplot(data=combined_df, x='Month', y='AR_Rainfall_%', ax=ax1, color='skyblue')
    if idx == 0:
        ax1.set_title('AR Contribution to Rainfall')
    if idx == n_regions - 1:
        ax1.set_xlabel('Month')
    else:
        ax1.set_xlabel('')
        ax1.set_xticklabels([])
    ax1.set_ylabel('AR %')
    ax1.grid(True)

    # Plot 2: Barplot
    ax2 = axs[idx, 1]
    sns.barplot(data=bar_data, x='Month', y='AR_Contribution (%)', hue='Metric', ax=ax2, palette='Blues')
    if idx == 0:
        ax2.set_title('AR Contribution to P95/P99 Events')
    if idx == n_regions - 1:
        ax2.set_xlabel('Month')
    else:
        ax2.set_xlabel('')
        ax2.set_xticklabels([])
    ax2.set_ylabel('AR %')
    ax2.set_ylim(0, 100)
    ax2.grid(axis='y')
    if idx == 0:
        ax2.legend(title="Event Type")
    else:
        ax2.legend().remove()

    # Region label on left of the row
    region_name = region_name_map.get(folder, folder)
    fig.text(0.01, 1 - ((idx + 0.5) / n_regions), region_name, va='center', ha='left', fontsize=16, rotation='vertical')

# Final layout
plt.tight_layout(rect=[0.05, 0, 1, 0.97])
plt.suptitle('Rainfall Event Summary by Region', fontsize=22)
plt.savefig('figure1_ARcontribution')
plt.show()
