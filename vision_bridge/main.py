import os, uuid, io, datetime, logging
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import httpx, boto3
import numpy as np, cv2
from colour_checker_detection import detect_colour_checkers_segmentation
from prometheus_client import Counter, start_http_server

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

PHOS_URL = os.getenv("PHOS_URL", "http://phosphobot")
BUCKET   = os.getenv("BUCKET", "snapshots")

# Validate required environment variables
required_env_vars = ["S3_ENDPOINT", "AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY"]
for var in required_env_vars:
    if not os.getenv(var):
        logger.error(f"{var} environment variable is required")
        raise ValueError(f"{var} environment variable is required")

s3 = boto3.client("s3",
        endpoint_url=os.getenv("S3_ENDPOINT"),
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"))

SNAP_OK  = Counter("cam_snapshot_ok_total", "Snapshots succeeded")
SNAP_ERR = Counter("cam_snapshot_err_total", "Snapshots failed")
start_http_server(9003)

# ------------------------- FastAPI ----------------------------------------
app = FastAPI(title="Vision-Bridge")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class SnapReq(BaseModel):
    cmd_id: str
    cam_id: str = "top_cam"

@app.post("/snapshot")
async def snapshot(req: SnapReq):
    ts   = datetime.datetime.utcnow().isoformat(timespec="seconds")
    key  = f"{req.cmd_id}/{req.cam_id}_{ts}.jpg"
    url  = f"{PHOS_URL}/camera/snapshot/{req.cam_id}?format=jpeg"

    try:
        async with httpx.AsyncClient(timeout=10.0) as cl:
            r = await cl.get(url)
            if r.status_code != 200:
                SNAP_ERR.inc()
                logger.error(f"Camera error: {r.status_code}")
                raise HTTPException(502, f"Camera error: {r.status_code}")
            
            data = io.BytesIO(r.content)
            s3.upload_fileobj(data, BUCKET, key,
                              ExtraArgs={"ContentType": "image/jpeg"})
        
        SNAP_OK.inc()
        presigned = s3.generate_presigned_url("get_object",
            Params={"Bucket": BUCKET, "Key": key}, ExpiresIn=86400)
        return {"url": presigned}
    except httpx.TimeoutException:
        SNAP_ERR.inc()
        logger.error("Timeout calling camera")
        raise HTTPException(504, "Timeout calling camera")
    except Exception as e:
        SNAP_ERR.inc()
        logger.error(f"Error taking snapshot: {e}")
        raise HTTPException(500, f"Snapshot error: {str(e)}")


@app.post("/color-checker")
async def color_checker(file: UploadFile = File(...)):
    """Detect colour checkers in the uploaded image."""
    try:
        data = await file.read()
        arr = np.frombuffer(data, np.uint8)
        img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if img is None:
            raise HTTPException(400, "Invalid image format")

        results = detect_colour_checkers_segmentation(img, additional_data=True)
        dets = []
        for r in results:
            dets.append({
                "quadrilateral": r.quadrilateral.tolist(),
                "swatch_colours": r.swatch_colours.tolist(),
            })
        return {"detections": dets}
    except Exception as e:
        logger.error(f"Error in color checker detection: {e}")
        raise HTTPException(500, f"Color checker detection error: {str(e)}")
