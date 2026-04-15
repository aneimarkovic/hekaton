import pandas as pd
from prophet import Prophet
from pathlib import Path
from prophet.plot import plot_plotly, plot_components_plotly
import numpy as np
import plotly.express as px
import scipy.signal as s

window_size = 12
abs_factor = 1.5    
calibration_factor = 3.5


def detectAnomaly(row):
      # Potrebno izracunati brke za posamezni window
      
      #upperBound = povp + sorgoNum
      #lowerBound = popv - sorgoNum
      # upperBound = row['mean'] + row["treshold"]
      # lowerBound = row['mean'] - row["treshold"]
      # print("UpperBound: " + str(upperBound))
      # print("LowerBound: " + str(lowerBound))
      print("Upper bound: " + str(row['upperBound']))
      print("Lower bound: " + str(row['lowerBound']))

      delta = row['upperBound'] - row['lowerBound']
      print("DELTA: " + str(delta))
      print("Row: " + str(row["y"]))

      if(np.isnan(row['upperBound'])):
            # Rolling window se ni tako dalec
            return "No"

      quantileAnomaly = False

      if(row['y'] > row['upperBound']) or row['y'] < row['lowerBound']:
            print("Found anomaly")
            quantileAnomaly = True

      # absAnomaly = np.abs(row['error']) > (abs_factor * row['uncertainty'])

      # if(absAnomaly or quantileAnomaly):
      if(True):
            return "Yes"
      else:
            return "No"
      

a = Path("./vsi_podatki/m182.csv")
#if a.exists():
#    print("File exists")
#else:
#    print("File does not exist")

df = pd.read_csv(a,header=None)
#print(df)
df.columns = ['0', 'ds', 'y']
df['ds'] = pd.to_datetime(df['ds'] + ' 2024', format='%d.%m %H:%M %Y') #doda datum kr drugace panda ne dela
#print(df.head())
m = Prophet(changepoint_range=0.8, changepoint_prior_scale=0.5)
m.add_seasonality(name='hourly', period=0.04, fourier_order=20)
m.fit(df)

future_period = 10
future_period_freq ='h'
future = m.make_future_dataframe(periods=future_period, freq=future_period_freq)
forecast = m.predict(future)
#print(forecast[['ds', 'yhat', 'yhat_lower', 'yhat_upper']].tail())

forecast_df = forecast[['ds','yhat','yhat_upper','yhat_lower']]
forecast_df
forecast_df['yhat'] = forecast_df['yhat'].astype(int)    
forecasting_final = pd.merge(forecast_df, df, how='inner',
                                     left_on = 'ds', right_on = 'ds')

forecasting_final['error'] = forecasting_final['y'] - forecasting_final['yhat']
forecasting_final['uncertainty'] = forecasting_final['yhat_upper'] - forecasting_final['yhat_lower']

# forecasting_final['anomaly'] = forecasting_final.apply(lambda x: 'Yes' 
#       if(np.abs(x['error']) >  factor*x['uncertainty']) else 'No', axis = 1)

# Calculate sorgoNum aka treshold

brki = np.quantile(df['y'], [0,0.25,0.5,0.75,1])
low_high_AVG = brki[3] - brki[1]

cb_fac = 0.025

treshold = low_high_AVG * cb_fac
# print(low_high_AVG)

if(low_high_AVG < 1):
  treshold = 1    

print("Treshold: " + str(treshold))

forecasting_final["mean"] = forecasting_final['y'].rolling(window=window_size).mean()
# forecasting_final["q1"] = forecasting_final['y'].rolling(window=window_size).quantile(0.25)
# forecasting_final["q3"] = forecasting_final['y'].rolling(window=window_size).quantile(0.75)
# low_high_AVG = forecasting_final["q3"] - forecasting_final["q1"]
# forecasting_final["treshold"] = low_high_AVG * calibration_factor 
forecasting_final["upperBound"] = forecasting_final["mean"] + treshold
forecasting_final["lowerBound"] = forecasting_final["mean"] - treshold

# forecasting_final['anomaly'] = forecasting_final.apply(detectAnomaly, axis=1)

# print(forecasting_final["y"][0])
# print(len(forecasting_final["y"]) - window_size)ž

min_peaks = s.argrelmin(forecasting_final['y'].values, order=1)[0]
max_peaks = s.argrelmax(forecasting_final['y'].values, order=1)[0]
print("Min_peaks", min_peaks)
print("Max_peaks", max_peaks)


y = forecasting_final['y'].values
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
print("AVG_steepnes_before_filter", df_steepness['steep'].mean())
filtered_df = df_steepness[df_steepness['steep'] > (df_steepness['steep'].mean() * 70) / 50]

avg_all_steepness = filtered_df['steep'].mean()
print(filtered_df)
print("all average steepness", avg_all_steepness)

steep_upper_bound = (avg_all_steepness * 3) / 2
#steep_lower_bound = (avg_all_steepness * 1) / 2
print("steep_upper_bound", steep_upper_bound)
#print("steep_lower_bound", steep_lower_bound)

tempArray = np.array(['No' for _ in range(len(forecasting_final["y"]))])
for index, row in filtered_df.iterrows():
      #print("left", row['left'])
      #print("right", row['right'])
      if ( row['steep'] > steep_upper_bound):
           print("steep_anomaly", row)
           int_left = int(row['left'])
           int_right = int(row['right'])
           tempArray[int_left:int_right + 1] = "Yes"



length = len(forecasting_final["y"]) - window_size
for i in range(0, length + 1):
      mean = forecasting_final["y"][i:i+window_size].mean()
      upperBound = mean + treshold
      lowerBound = mean - treshold

      anomaly = True

      for j in range(i, i+window_size):
            if (forecasting_final["y"][j] < lowerBound) or (forecasting_final["y"][j] > upperBound):
                  anomaly = False


      

      # print(forecasting_final['anomaly'])
      
      if anomaly:
            tempArray[i:i+window_size] = "Yes"

forecasting_final["anomaly"] = tempArray

#forecasting_final.loc[forecasting_final.index[min_peaks], 'anomaly'] = 'MinPeak'
#forecasting_final.loc[forecasting_final.index[max_peaks], 'anomaly'] = 'MaxPeak'

color_discrete_map = {'Yes': 'rgb(255,12,0)', 'No': 'blue'}
fig = px.scatter(forecasting_final, x='ds', y='y', color='anomaly', title='Anomaly',
                 color_discrete_map=color_discrete_map)

#fig = m.plot(forecasting_final)
#fig.waitforbuttonpress()
fig.show()