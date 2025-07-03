import os, json, asyncio, uuid
from typing import List

import httpx, zmq, zmq.asyncio
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from prometheus_client import Counter, Histogram, start_http_server

PHOS_URL   = os.getenv("PHOS_URL", "http://phosphobot")
MODEL_ID   = os.getenv("MODEL_ID")
TARGET_POSE = json.loads(os.getenv("TARGET_POSE", "[0,0,0,0,0,0]"))
TOL        = float(os.getenv("TOL", "0.03"))

REQS_TOTAL = Counter("robot_requests_total", "Robot dispense requests")
REQ_LAT    = Histogram("robot_request_latency_seconds", "Robot latency")

# --- FastAPI -----------------------------------------------------------------
app = FastAPI(title="Robot Service", version="0.1")

class DispenseRequest(BaseModel):
    mix_id: int
    run_id: int
    colour: str = Field(pattern="^(red|green|blue)$")
    volume_ml: float = Field(gt=0.0, le=50.0)

class DispenseStatus(BaseModel):
    status: str
    predicted_squeeze_sec: float | None = None

# in-memory store; replace w/ DB table in prod
TASKS: dict[str, DispenseStatus] = {}


def pose_close(q: List[float]) -> bool:
    return all(abs(a-b) < TOL for a, b in zip(q, TARGET_POSE))


async def zmq_state_listener():
    ctx = zmq.asyncio.Context.instance()
    sub = ctx.socket(zmq.SUB)
    sub.connect("tcp://phosphobot:5555")   # state topic
    sub.setsockopt_string(zmq.SUBSCRIBE, "state")
    while True:
        _topic, raw = await sub.recv_multipart()
        msg = json.loads(raw)
        if pose_close(msg["joints"]):
            # broadcast event to any waiting CSR tasks
            for fut in list(POSE_WAITERS):
                if not fut.done():
                    fut.set_result(msg)
        for tid, st in TASKS.items():
            if st.status == "running" and msg.get("status") == "success":
                st.status = "success"
        await asyncio.sleep(0.0)

POSE_WAITERS: set[asyncio.Future] = set()
asyncio.create_task(zmq_state_listener())
start_http_server(9001)     # Prometheus

# --------------------------------------------------------------------------- #
@app.post("/robot/dispense")
@REQ_LAT.time()
async def dispense(req: DispenseRequest):
    REQS_TOTAL.inc()
    tid = str(uuid.uuid4())
    prompt = f"Dispense {req.volume_ml} ml from the {req.colour} bottle"
    TASKS[tid] = DispenseStatus(status="running")

    async with httpx.AsyncClient(timeout=60.0) as client:
        phos_resp = await client.post(f"{PHOS_URL}/inference",
                                      json={"model": MODEL_ID, "prompt": prompt})
        if phos_resp.status_code != 200:
            raise HTTPException(502, "Phosphobot error")

        squeeze = phos_resp.json().get("predicted_squeeze_sec")
        TASKS[tid].predicted_squeeze_sec = squeeze

    return {"cmd_id": tid, **TASKS[tid].model_dump()}


@app.get("/robot/{cmd_id}/status")
async def status(cmd_id: str):
    st = TASKS.get(cmd_id)
    if not st:
        raise HTTPException(404)
    return st.model_dump()


@app.get("/robot/{cmd_id}/pose-snapshot")
async def pose_snapshot(cmd_id: str, cam: str = "top_cam"):
    """
    Blocks until pose reached, then returns a presigned S3 URL provided
    by Vision-Bridge (polls kv-store every 100 ms).
    """
    fut = asyncio.get_event_loop().create_future()
    POSE_WAITERS.add(fut)
    await fut            # wait until pose reached

    # ask Vision-Bridge to capture
    async with httpx.AsyncClient(timeout=30.0) as cl:
        vb = await cl.post("http://vision-bridge:9002/snapshot",
                           json={"cmd_id": cmd_id, "cam_id": cam})
        return vb.json()
