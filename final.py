import pandas as pd
from prophet import Prophet
from pathlib import Path
from prophet.plot import plot_plotly, plot_components_plotly
import numpy as np
import plotly.express as px
import scipy.signal as s
import os

finalDataFrame = pd.DataFrame()
file = Path("./vsi_podatki/m182.csv")  
# df = pd.read_csv(file,header=None)
df = pd.DataFrame()

# Ovrednoteni podatki:
# df.columns = ['0', 'ds', 'y', '3']

#Vsi podatki:
# df.columns = ['0', 'ds', 'y']

# df['ds'] = pd.to_datetime(df['ds'] + ' 2024', format='%d.%m %H:%M %Y')

anomaliesStatusArr = []
anomaliesValuesArr = []
originalValuesArr = []

total_interruptions = 0
total_duration_minutes = 0
total_sites_processed = 0

#Config data sliding window
window_size = 9
quantiles = []
q1AndQ3Diffrence = 0
calibrationFactor = 0.035
treshold = 0
length = 0
#Config data prophet
factor = 1.1 # kako strogo odstopanje mora bit

def findAnomaliesUsingSteepSlopes():
    global anomaliesValuesArr
    global originalValuesArr
    global anomaliesStatusArr
    global df
    global finalDataFrame
    global treshold
    global window_size
    global quantiles
    global q1AndQ3Diffrence
    global calibrationFactor
    global length
    global factor
    min_peaks = s.argrelmin(df['y'].values, order=1)[0]
    max_peaks = s.argrelmax(df['y'].values, order=1)[0]  

    y = df['y'].values
    results = []
    left_low = []
    right_low = []

    for peak_idx in max_peaks:
        peak_val = y[peak_idx]

        left_mins = min_peaks[min_peaks < peak_idx]
        right_mins = min_peaks[min_peaks > peak_idx]

        # Ensures there is actually a minimum to the left and right
        if len(left_mins) > 0 and len(right_mins) > 0:
            left_idx = left_mins[-1]
            right_idx = right_mins[0]
            left_low.append(left_idx)
            right_low.append(right_idx)

            left_slope = (peak_val - y[left_idx]) / (peak_idx - left_idx)
            right_slope = (peak_val - y[right_idx]) / (right_idx - peak_idx)
            
            avg_steepness = (left_slope + right_slope) / 2
            results.append(avg_steepness)

    df_steepness = pd.DataFrame()
    df_steepness['steep'] = results
    df_steepness['left'] = left_low
    df_steepness['right'] = right_low
    # Steepnes factor is set to 70%
    steepnesFactor = (df_steepness['steep'].mean() * 70) / 50
    filtered_df = df_steepness[df_steepness['steep'] > steepnesFactor]

    avg_all_steepness = filtered_df['steep'].mean()

    #Upper Bound is 50% of avg
    steep_upper_bound = (avg_all_steepness * 3) / 2
    # steep_upper_bound = (avg_all_steepness * 150) / 100
    for index, row in filtered_df.iterrows():
      if ( row['steep'] > steep_upper_bound):
           int_left = int(row['left'])
           int_right = int(row['right'])

           #print("Row: \n", row)
           
           diffrences = []
           for i in range(int_left + 1, int_right):
                curr = df["y"][i]
                prev = df["y"][i-1]
                #print(curr, ", ", prev)
                diffrences.append(abs(prev-curr))
        
           #print("\n")
           avgDiffrence = np.mean(diffrences)
           stdDiffrence = np.std(diffrences)

           #print("Diffrence: ", stdDiffrence)

           steepnesTreshold = avgDiffrence * stdDiffrence

           for i in range(int_left + 1, int_right):
                curr = df["y"][i]
                prev = df["y"][i-1]
                diff = abs(prev-curr)
                if diff > steepnesTreshold:
                    anomaliesStatusArr[int_left:int_right + 1] = "Yes"
                    anomaliesValuesArr[int_left:int_right + 1] = None

def findAnomaliesUsingRollingWindow():
    global anomaliesValuesArr, anomaliesStatusArr, df
    global window_size, length

    y = df['y'].values.astype(float).copy()
    n = len(y)

    zero_mask = (y == 0.0)
    anomaliesStatusArr[zero_mask] = "Yes"
    anomaliesValuesArr[zero_mask] = np.nan

    # Izračunaj globalni std samo iz ne-anomalnih vrednosti
    valid_vals = y[~np.isnan(y)]
    global_std = np.std(valid_vals)
    
    # Flat segment: lokalni std mora biti manjši od globalnega
    flat_threshold = global_std * 0.03 
    
    for i in range(n - window_size + 1):
        window = y[i:i + window_size]
        if np.std(window) < flat_threshold:
            anomaliesStatusArr[i:i + window_size] = "Yes"
            anomaliesValuesArr[i:i + window_size] = np.nan

def findAnomaliesUsingProphet():
    global anomaliesValuesArr
    global originalValuesArr
    global anomaliesStatusArr
    global df
    global finalDataFrame
    global treshold
    global window_size
    global quantiles
    global q1AndQ3Diffrence
    global calibrationFactor
    global length
    global factor

    df["y"] = anomaliesValuesArr
    xd = 0
    for x in df["y"]:
        if (not np.isnan(x)):
            xd += 1
    #print(xd)
    if (xd < 4): # vsaj 3 razlicne
        #print("not unique", df["y"] )
        df["anomaly"] = anomaliesStatusArr
        return df
    
    df["y"] = anomaliesValuesArr
    m = Prophet(changepoint_range=0.3, changepoint_prior_scale=0.5,interval_width=0.88)
    m.add_country_holidays(country_name='SI')
    # m.add_seasonality(name='hourly', period=0.04, fourier_order=20)
    m.fit(df)

    future_period = 10
    future_period_freq ='h'
    future = m.make_future_dataframe(periods=future_period, freq=future_period_freq)
    forecast = m.predict(future)
    forecast_df = forecast[['ds','yhat','yhat_upper','yhat_lower']]
    forecast_df['yhat'] = forecast_df['yhat'].astype(int)    
    forecasting_final = pd.merge(forecast_df, df, how='inner',
                                        left_on = 'ds', right_on = 'ds')

    forecasting_final['error'] = forecasting_final['y'] - forecasting_final['yhat']
    forecasting_final['uncertainty'] = forecasting_final['yhat_upper'] - forecasting_final['yhat_lower']
    forecasting_final["anomaly"] = anomaliesStatusArr
    for i in range(0,length + window_size):
      if(np.abs(forecasting_final['error'][i]) > factor*forecasting_final['uncertainty'][i]):
            forecasting_final.loc[i,"anomaly"] = "Yes"
    
    return forecasting_final

def sortFunc(e):
    return int(e[1:-4])


def calculate_site_metrics(df):
    """
    Identifies contiguous blocks of anomalies, calculates their count 
    and total duration for a single site (file).
    """
    # Ensure ds is datetime
    df['ds'] = pd.to_datetime(df['ds'])
    
    # Create a grouping ID for consecutive anomalies
    # This increments every time the 'anomalies' value changes
    df['group'] = (df['anomalies'] != df['anomalies'].shift()).cumsum()
    
    # Filter only the anomaly groups (where anomalies == 1)
    anomaly_groups = df[df['anomalies'] == 1].groupby('group')
    
    site_interruption_count = anomaly_groups.ngroups
    site_total_duration = pd.Timedelta(0)
    
    for _, group in anomaly_groups:
        if len(group) > 0:
            start_time = group['ds'].min()
            end_time = group['ds'].max()
            
            # Duration is end - start. 
            # Note: If there's only 1 point, duration is 0. 
            # Often, we add one sampling interval to represent the block properly.
            duration = end_time - start_time
            
            # If the sampling interval is known (e.g. 15 min), you might use:
            # duration += pd.Timedelta(minutes=15) 
            
            site_total_duration += duration
            
    return site_interruption_count, site_total_duration.total_seconds() / 60

def iterate():
    global anomaliesValuesArr
    global originalValuesArr
    global anomaliesStatusArr
    global df
    global finalDataFrame
    global treshold
    global window_size
    global quantiles
    global q1AndQ3Diffrence
    global calibrationFactor
    global length
    global factor
    global total_interruptions 
    global total_duration_minutes 
    global total_sites_processed 
    
    directory = os.fsencode("./ovrednoteni_podatki").decode("utf-8")
    lst = os.listdir(directory)
    lst.sort(key=sortFunc)
    for file in lst[0:3]:
        filename = os.fsdecode(file)
        #print("File ", filename)
        if filename.endswith(".csv"): 
                df = pd.read_csv(os.path.join(directory, filename),header=None)
                df.columns = ['0', 'ds', 'y', '3']

                tempTimestampCol = df['ds']
                
                df['ds'] = pd.to_datetime(df['ds'] + ' 2024', format='%d.%m %H:%M %Y')
                anomaliesStatusArr = np.array(['No' for _ in range(len(df["y"]))])
                anomaliesValuesArr = df["y"]
                originalValuesArr = df["y"]

                quantiles = np.quantile(df['y'], [0,0.25,0.5,0.75,1])
                q1AndQ3Diffrence = quantiles[3] - quantiles[1]
                treshold = q1AndQ3Diffrence * calibrationFactor
                if treshold < 1.0:
                    treshold = 1
                length = len(df["y"]) - window_size
                # print("Length ",length)
                findAnomaliesUsingRollingWindow()
                findAnomaliesUsingSteepSlopes()
                finalDataFrame = findAnomaliesUsingProphet()
                # print(finalDataFrame)
                anomaliesArr = []
                # print(finalDataFrame["anomaly"])
                #finalDataFrame["anomaly"] = finalDataFrame["anomaly"].replace("Ye", "Yes")
                for i in range(0, len(finalDataFrame["anomaly"])):
                    if (finalDataFrame["anomaly"][i] == "Yes"):
                        anomaliesArr.append(1)
                    else:
                        anomaliesArr.append(0)
                        # print(len())
                # print("Anomalies arr ", len(anomaliesArr))
                df["anomalies"] = anomaliesArr
                
                # Calculate SAIFI/SAIDI components for THIS site
                site_count, site_dur = calculate_site_metrics(df)
                total_interruptions += site_count
                total_duration_minutes += site_dur
                total_sites_processed += 1
                
                print(f"Site {filename}: Interruptions: {site_count}, Duration: {site_dur:.2f} min")
                
                # print("Df anomalies ", len(df["anomalies"]))
                df["ds"] = tempTimestampCol
                df["y"] = originalValuesArr
                #print(df)
                df = df.drop(columns=["group"])
                df.to_csv('rezultati.csv', mode='a', header = None, index=False)
                finalDataFrame["y"] = originalValuesArr
                #Display results
                color_discrete_map = {'Yes': 'rgb(255,12,0)', 'No': 'blue'}
                #fig = px.scatter(finalDataFrame, x='ds', y='y', color='anomaly', title='Anomaly',
                #    color_discrete_map=color_discrete_map)
                #fig.show()
        else:
                continue 
        
    if total_sites_processed > 0:
        saifi = total_interruptions / total_sites_processed
        saidi = total_duration_minutes / total_sites_processed
        
        print("\n" + "="*30)
        print("FINAL RELIABILITY INDICES")
        print("="*30)
        print(f"Total Sites Processed: {total_sites_processed}")
        print(f"Total Interruption Events: {total_interruptions}")
        print(f"Total Duration: {total_duration_minutes:.2f} minutes")
        print(f"SAIFI: {saifi:.4f} (Avg interruptions per customer)")
        print(f"SAIDI: {saidi:.4f} (Avg duration per customer in minutes)")
        print("="*30)

if __name__ == "__main__":
    iterate()
#     findAnomaliesUsingRollingWindow()
#     findAnomaliesUsingSteepSlopes()
#     finalDataFrame = findAnomaliesUsingProphet()

#     finalDataFrame["y"] = originalValuesArr
#     #Display results
#     color_discrete_map = {'Yes': 'rgb(255,12,0)', 'No': 'blue'}
#     fig = px.scatter(finalDataFrame, x='ds', y='y', color='anomaly', title='Anomaly',
#                     color_discrete_map=color_discrete_map)

#     # #Display plot
#     # fig = m.plot(forecasting_final)
#     # fig.waitforbuttonpress()

#     #Display plot on web
#     fig.show()