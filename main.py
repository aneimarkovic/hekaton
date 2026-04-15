from fastapi import FastAPI, UploadFile, File, Response
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import io
from detect import get_anomaly_plot # Import from refactored final.py

app = FastAPI()

origins = [
    "http://localhost.tiangolo.com",
    "https://localhost.tiangolo.com",
    "http://localhost",
    "http://localhost:5173",
]

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