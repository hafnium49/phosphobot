import os, uuid, io, datetime
from fastapi import FastAPI, HTTPException, UploadFile, File
from pydantic import BaseModel
import httpx, boto3
import numpy as np, cv2
from colour_checker_detection import detect_colour_checkers_segmentation
from prometheus_client import Counter, start_http_server

PHOS_URL = os.getenv("PHOS_URL", "http://phosphobot")
BUCKET   = os.getenv("BUCKET", "snapshots")
s3 = boto3.client("s3",
        endpoint_url=os.getenv("S3_ENDPOINT"),
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"))

SNAP_OK  = Counter("cam_snapshot_ok_total", "Snapshots succeeded")
SNAP_ERR = Counter("cam_snapshot_err_total", "Snapshots failed")
start_http_server(9003)

# ------------------------- FastAPI ----------------------------------------
app = FastAPI(title="Vision-Bridge")

class SnapReq(BaseModel):
    cmd_id: str
    cam_id: str = "top_cam"

@app.post("/snapshot")
async def snapshot(req: SnapReq):
    ts   = datetime.datetime.utcnow().isoformat(timespec="seconds")
    key  = f"{req.cmd_id}/{req.cam_id}_{ts}.jpg"
    url  = f"{PHOS_URL}/camera/snapshot/{req.cam_id}?format=jpeg"

    async with httpx.AsyncClient() as cl:
        r = await cl.get(url, timeout=10.0)
        if r.status_code != 200:
            SNAP_ERR.inc()
            raise HTTPException(502, "Camera error")
        data = io.BytesIO(r.content)
        s3.upload_fileobj(data, BUCKET, key,
                          ExtraArgs={"ContentType": "image/jpeg"})
    SNAP_OK.inc()
    presigned = s3.generate_presigned_url("get_object",
        Params={"Bucket": BUCKET, "Key": key}, ExpiresIn=86400)
    return {"url": presigned}


@app.post("/color-checker")
async def color_checker(file: UploadFile = File(...)):
    """Detect colour checkers in the uploaded image."""
    data = await file.read()
    arr = np.frombuffer(data, np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        raise HTTPException(400, "Invalid image")

    results = detect_colour_checkers_segmentation(img, additional_data=True)
    dets = []
    for r in results:
        dets.append({
            "quadrilateral": r.quadrilateral.tolist(),
            "swatch_colours": r.swatch_colours.tolist(),
        })
    return {"detections": dets}
