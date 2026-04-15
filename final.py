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

#Config data sliding window
window_size = 12
quantiles = []
q1AndQ3Diffrence = 0
calibrationFactor = 0.025
treshold = 0
length = 0
#Config data prophet
factor = 1 # kako strogo odstopanje mora bit

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
    for index, row in filtered_df.iterrows():
      if ( row['steep'] > steep_upper_bound):
           int_left = int(row['left'])
           int_right = int(row['right'])
           anomaliesStatusArr[int_left:int_right + 1] = "Yes"
           anomaliesValuesArr[int_left:int_right + 1] = None

def findAnomaliesUsingRollingWindow():
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
    for i in range(0, length + 1):
      mean = df['y'][i:i+window_size].mean()
      upperBound = mean + treshold
      lowerBound = mean - treshold

      anomaly = True

      for j in range(i, i+window_size):
            if (df["y"][j] < lowerBound) or (df["y"][j] > upperBound):
                  anomaly = False

      if (df["y"][i] == 0.0):
        anomaliesValuesArr[i] = None
        anomaliesStatusArr[i] = "Yes"

      if anomaly:
        anomaliesStatusArr[i:i+window_size] = "Yes"
        anomaliesValuesArr[i:i+window_size] = None

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
    m = Prophet(changepoint_range=0.3, changepoint_prior_scale=0.5,interval_width=0.87)
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
    directory = os.fsencode("./vsi_podatki").decode("utf-8")
    lst = os.listdir(directory)
    lst.sort(key=sortFunc)
    for file in lst[:2]:
        filename = os.fsdecode(file)
        print("File ", filename)
        if filename.endswith(".csv"): 
                df = pd.read_csv(os.path.join(directory, filename),header=None)
                df.columns = ['0', 'ds', 'y']

                tempTimestampCol = df['ds']
                
                df['ds'] = pd.to_datetime(df['ds'] + ' 2024', format='%d.%m %H:%M %Y')
                anomaliesStatusArr = np.array(['No' for _ in range(len(df["y"]))])
                anomaliesValuesArr = df["y"]
                originalValuesArr = df["y"]

                quantiles = np.quantile(df['y'], [0,0.25,0.5,0.75,1])
                q1AndQ3Diffrence = quantiles[3] - quantiles[1]
                treshold = q1AndQ3Diffrence * calibrationFactor
                length = len(df["y"]) - window_size
                # print("Length ",length)
                findAnomaliesUsingRollingWindow()
                findAnomaliesUsingSteepSlopes()
                finalDataFrame = findAnomaliesUsingProphet()

                # print(finalDataFrame)
                anomaliesArr = []
                # print(finalDataFrame["anomaly"])
                finalDataFrame["anomaly"] = finalDataFrame["anomaly"].replace("Ye", "Yes")
                for i in range(0, len(finalDataFrame["anomaly"])):
                    if (finalDataFrame["anomaly"][i] == "Yes"):
                        anomaliesArr.append(1)
                    else:
                        anomaliesArr.append(0)
                        # print(len())
                # print("Anomalies arr ", len(anomaliesArr))
                df["anomalies"] = anomaliesArr
                # print("Df anomalies ", len(df["anomalies"]))
                df["ds"] = tempTimestampCol
                df["y"] = originalValuesArr
                # print(df)
                df.to_csv('rezultati.csv', mode='a', header = None, index=False)
                finalDataFrame["y"] = originalValuesArr
                #Display results
                color_discrete_map = {'Yes': 'rgb(255,12,0)', 'No': 'blue'}
                fig = px.scatter(finalDataFrame, x='ds', y='y', color='anomaly', title='Anomaly',
                    color_discrete_map=color_discrete_map)
                fig.show()
        else:
                continue 

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