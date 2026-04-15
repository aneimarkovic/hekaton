import pandas as pd
from prophet import Prophet
import numpy as np
import scipy.signal as s
import plotly.express as px
import io

def get_anomaly_plot(df_input: pd.DataFrame):
    # --- Configuration/Setup ---
    df = df_input.copy()
    df.columns = ['0', 'ds', 'y']
    original_y = df['y'].copy()
    df['ds'] = pd.to_datetime(df['ds'] + ' 2024', format='%d.%m %H:%M %Y')
    
    anomaliesStatusArr = np.array(['No' for _ in range(len(df["y"]))])
    anomaliesValuesArr = df["y"].values.astype(float).copy()
    window_size = 9
    factor = 1.1

    # --- 1. Rolling Window Logic (Flat lines & Zeros) ---
    y_vals = df['y'].values.astype(float)
    zero_mask = (y_vals == 0.0)
    anomaliesStatusArr[zero_mask] = "Yes"
    anomaliesValuesArr[zero_mask] = np.nan
    
    valid_vals = y_vals[~np.isnan(y_vals)]
    if len(valid_vals) > 0:
        global_std = np.std(valid_vals)
        flat_threshold = global_std * 0.03 
        for i in range(len(y_vals) - window_size + 1):
            window = y_vals[i:i + window_size]
            if np.std(window) < flat_threshold:
                anomaliesStatusArr[i:i + window_size] = "Yes"
                anomaliesValuesArr[i:i + window_size] = np.nan

    # --- 2. Steep Slopes Logic ---
    min_peaks = s.argrelmin(y_vals, order=1)[0]
    max_peaks = s.argrelmax(y_vals, order=1)[0]  
    results, left_low, right_low = [], [], []

    for peak_idx in max_peaks:
        peak_val = y_vals[peak_idx]
        left_mins = min_peaks[min_peaks < peak_idx]
        right_mins = min_peaks[min_peaks > peak_idx]
        if len(left_mins) > 0 and len(right_mins) > 0:
            l_idx, r_idx = left_mins[-1], right_mins[0]
            left_low.append(l_idx); right_low.append(r_idx)
            avg_steepness = ((peak_val - y_vals[l_idx]) / (peak_idx - l_idx) + (y_vals[r_idx] - peak_val) / (r_idx - peak_idx)) / 2
            results.append(avg_steepness)

    if results:
        df_steep = pd.DataFrame({'steep': results, 'left': left_low, 'right': right_low})
        avg_all = df_steep['steep'].mean()
        steep_upper_bound = (avg_all * 3) / 2
        for _, row in df_steep[df_steep['steep'] > steep_upper_bound].iterrows():
            l, r = int(row['left']), int(row['right'])
            anomaliesStatusArr[l:r + 1] = "Yes"
            anomaliesValuesArr[l:r + 1] = np.nan

    # --- 3. Prophet Logic ---
    df_prophet = pd.DataFrame({'ds': df['ds'], 'y': anomaliesValuesArr})
    if df_prophet['y'].notna().sum() > 4:
        m = Prophet(changepoint_range=0.3, changepoint_prior_scale=0.5, interval_width=0.88)
        m.add_country_holidays(country_name='SI')
        m.fit(df_prophet)
        
        forecast = m.predict(df_prophet[['ds']])
        res = pd.merge(forecast[['ds', 'yhat', 'yhat_upper', 'yhat_lower']], df_prophet, on='ds')
        res['error'] = res['y'] - res['yhat']
        res['uncertainty'] = res['yhat_upper'] - res['yhat_lower']
        
        for i in range(len(res)):
            if np.abs(res.loc[i, 'error']) > factor * res.loc[i, 'uncertainty']:
                anomaliesStatusArr[i] = "Yes"

    # --- 4. Plotting ---
    df['anomaly'] = anomaliesStatusArr
    df['y'] = original_y # Reset to original for visualization
    
    color_discrete_map = {'Yes': 'rgb(255,12,0)', 'No': 'blue'}
    fig = px.scatter(df, x='ds', y='y', color='anomaly', 
                     title='Anomaly Detection Results',
                     color_discrete_map=color_discrete_map)
    
    return fig