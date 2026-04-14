import pandas as pd
from prophet import Prophet
from pathlib import Path
from prophet.plot import plot_plotly, plot_components_plotly
import numpy as np
import plotly.express as px

a = Path("hekaton/ovrednoteni_podatki/m21.csv")
#if a.exists():
#    print("File exists")
#else:
#    print("File does not exist")

df = pd.read_csv(a,header=None)
#print(df)
df.columns = ['0', 'ds', 'y', '3']
df['ds'] = pd.to_datetime(df['ds'] + ' 2024', format='%d.%m %H:%M %Y') #doda datum kr drugace panda ne dela


brki = np.quantile(df['y'], [0,0.25,0.5,0.75,1])
low_high_AVG = brki[3] - brki[1]
cb_fac = 0.1

sorgo_num = low_high_AVG * cb_fac
print("Brki: ", brki)
print("Šorgotovo število: ", sorgo_num)

#print(df.head())
m = Prophet(changepoint_range=0.8, changepoint_prior_scale=0.95)
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
#Merging two dataset to have the actual and prediction values
forecasting_final = pd.merge(forecast_df, df, how='inner',
                                     left_on = 'ds', right_on = 'ds')

# We calculate the prediction error here and uncertainty 
forecasting_final['error'] = forecasting_final['y'] - forecasting_final['yhat']
forecasting_final['uncertainty'] = forecasting_final['yhat_upper'] - forecasting_final['yhat_lower']

# We this factor we can identify the outlier or anomaly. 
# This factor can be customized based on the data
factor = 0.5
forecasting_final['anomaly'] = forecasting_final.apply(lambda x: 'Yes' 
      if(np.abs(x['error']) >  factor*x['uncertainty']) else 'No', axis = 1)

color_discrete_map = {'Yes': 'rgb(255,12,0)', 'No': 'blue'}
fig = px.scatter(forecasting_final, x='ds', y='y', color='anomaly', title='Anomaly',
                 color_discrete_map=color_discrete_map)

#fig = m.plot(forecasting_final)
#fig.show()
#fig.waitforbuttonpress()