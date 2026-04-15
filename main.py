import pandas as pd
from prophet import Prophet
from pathlib import Path
from prophet.plot import plot_plotly, plot_components_plotly
import numpy as np
import plotly.express as px
import scipy.signal as s

window_size = 12      

file = Path("./vsi_podatki/m182.csv")
#if a.exists():
#    print("File exists")
#else:
#    print("File does not exist")

df = pd.read_csv(file,header=None)
# Ovrednoteni podatki:
# df.columns = ['0', 'ds', 'y', '3']

#Vsi podatki:
df.columns = ['0', 'ds', 'y']

df['ds'] = pd.to_datetime(df['ds'] + ' 2024', format='%d.%m %H:%M %Y')

m = Prophet(changepoint_range=0.8, changepoint_prior_scale=0.5)
m.add_seasonality(name='hourly', period=0.04, fourier_order=20)
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

quantiles = np.quantile(df['y'], [0,0.25,0.5,0.75,1])
q1AndQ3Diffrence = quantiles[3] - quantiles[1]
calibrationFactor = 0.025
treshold = q1AndQ3Diffrence * calibrationFactor

if(q1AndQ3Diffrence < 1):
  treshold = 1    


# Find steep slopes
min_peaks = s.argrelmin(forecasting_final['y'].values, order=1)[0]
max_peaks = s.argrelmax(forecasting_final['y'].values, order=1)[0]

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

# Steepnes factor is set to 70%
steepnesFactor = (df_steepness['steep'].mean() * 70) / 50
filtered_df = df_steepness[df_steepness['steep'] > steepnesFactor]

avg_all_steepness = filtered_df['steep'].mean()

#Upper Bound is 50% of avg
steep_upper_bound = (avg_all_steepness * 3) / 2

tempArray = np.array(['No' for _ in range(len(forecasting_final["y"]))])
for index, row in filtered_df.iterrows():
      if ( row['steep'] > steep_upper_bound):
           int_left = int(row['left'])
           int_right = int(row['right'])
           tempArray[int_left:int_right + 1] = "Yes"


# Find error using sliding window
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

# Find errors in prophet
forecasting_final["anomaly"] = tempArray
factor = 0.8 # kako strogo odstopanje mora bit
for i in range(0,length + window_size):
      if(np.abs(forecasting_final['error'][i]) > factor*forecasting_final['uncertainty'][i]):
            forecasting_final.loc[i,"anomaly"] = "Yes"



#Display results
color_discrete_map = {'Yes': 'rgb(255,12,0)', 'No': 'blue'}
fig = px.scatter(forecasting_final, x='ds', y='y', color='anomaly', title='Anomaly',
                 color_discrete_map=color_discrete_map)

#Display plot
#fig = m.plot(forecasting_final)
#fig.waitforbuttonpress()

#Display plot on web
# fig.show()