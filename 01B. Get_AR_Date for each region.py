# -*- coding: utf-8 -*-
"""
Created on Fri Aug 21 22:02:24 2020

@author: ted

This code aims to have a check of data downloaded before further 
actions
"""
import xarray as xr
import pandas as pd
import numpy as np
import os
import matplotlib.pyplot as plt

def find_nearest(array, value):
    array = np.asarray(array)
    idx = (np.abs(array - value)).argmin()
    return idx

dirname = 'G:/04. Ted Paper/Ted/ar_project_reanalysis_data/Tier2ARdata_and_rainfallData'
ARfilepath = os.path.join(dirname, 'ERA5\ARdata')
csv_path = os.path.join('C:/Users/nvo599/OneDrive - The University of Auckland/00. PhD/Final_version/Metafile')
save_path = os.path.join('C:/Users/nvo599/OneDrive - The University of Auckland/00. PhD/Final_version/AR')
os.chdir(ARfilepath)

ArFileName = []
for  year in range(1980,2020):
    ArFileName += ['ERA5.ar_tag.GuanWaliser_v2.1hr.%04d%02d%02d-%04d%02d%02d.nc' % (year, 1, 1, year, 12, 31)]
f = xr.open_mfdataset(ArFileName, chunks = {'time': 'auto', 'lon': 'auto', 'lat': 'auto'},combine='nested', concat_dim = 'time')
AR = f.ar_binary_tag

os.chdir(csv_path)
Station_file = pd.read_csv('GIS.csv')
Station_list = Station_file['Agent']

os.chdir(save_path)
for s in Station_list:
    row_loc = list(Station_file.loc[Station_file.Agent == s].index)[0]
    
    x1 = int(Station_file['AR_x1'][row_loc])
    x2 = int(Station_file['AR_x2'][row_loc])
    y1 = int(Station_file['AR_y1'][row_loc])
    y2 = int(Station_file['AR_y2'][row_loc])
    
    AR1 = AR[:,y1,x1]
    AR2 = AR[:,y1,x2]
    AR3 = AR[:,y2,x1]
    AR4 = AR[:,y2,x2]
    
    AR_df1 = AR1.to_dataframe()
    AR_df2 = AR2.to_dataframe()
    AR_df3 = AR3.to_dataframe()
    AR_df4 = AR4.to_dataframe()
    
    AR_df1.rename(columns = {'lat':'lat1', 'lon': 'lon1', 'ar_binary_tag': 'ar1'}, inplace = True)
    AR_df2.rename(columns = {'lat':'lat2', 'lon': 'lon2', 'ar_binary_tag': 'ar2'}, inplace = True)
    AR_df3.rename(columns = {'lat':'lat3', 'lon': 'lon3', 'ar_binary_tag': 'ar3'}, inplace = True)
    AR_df4.rename(columns = {'lat':'lat4', 'lon': 'lon4', 'ar_binary_tag': 'ar4'}, inplace = True)
    
    df = pd.concat([AR_df1, AR_df2, AR_df3, AR_df4], axis=1)
    df['Date'] = df.index
    df['year']=df.Date.dt.year.astype('Int64')
    df['month']=df.Date.dt.month.astype('Int64')
    df['day']=df.Date.dt.day.astype('Int64')
    df['hour']=df.Date.dt.hour.astype('Int64')
    df.to_csv(str(s) + '_AR_date_tag_ear5.csv')