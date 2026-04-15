from fastapi import FastAPI, UploadFile, File, Response
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import io
from detect import get_anomaly_plot # Import from refactored final.py

<<<<<<< HEAD
app = FastAPI()

origins = [
    "http://localhost.tiangolo.com",
    "https://localhost.tiangolo.com",
    "http://localhost",
    "http://localhost:5173",
]
=======
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
      

a = Path("./vsi_podatki/m198.csv")
#if a.exists():
#    print("File exists")
#else:
#    print("File does not exist")
>>>>>>> main

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/detect/postCsv")
async def post_csv(file: UploadFile = File(...)):
    # 1. Read CSV from request
    contents = await file.read()
    input_df = pd.read_csv(io.BytesIO(contents), header=None)
    
    # 2. Get the Plotly Figure from our logic
    fig = get_anomaly_plot(input_df)
    
    # 3. Convert Plotly figure to PNG bytes
    # Requires 'kaleido' package installed
    img_bytes = fig.to_image(format="png", engine="kaleido")
    
    # 4. Return the image as a response
    return Response(content=img_bytes, media_type="image/png")

@app.get("/")
def read_root():
    return {"status": "API is online. Use POST /detect/postCsv to get an anomaly graph."}

@app.get("/items/{item_id}")
def read_item(item_id: int, q: str | None = None):
    return {"item_id": item_id, "q": q}