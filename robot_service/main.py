import os, json, asyncio, uuid, time, logging
from typing import List

import httpx, zmq, zmq.asyncio
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from prometheus_client import Counter, Histogram, start_http_server

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

PHOS_URL   = os.getenv("PHOS_URL", "http://phosphobot")
MODEL_ID   = os.getenv("MODEL_ID")
TARGET_POSE = json.loads(os.getenv("TARGET_POSE", "[0,0,0,0,0,0]"))
TOL        = float(os.getenv("TOL", "0.03"))

# Validate required environment variables
if not MODEL_ID:
    logger.error("MODEL_ID environment variable is required")
    raise ValueError("MODEL_ID environment variable is required")

REQS_TOTAL = Counter("robot_requests_total", "Robot dispense requests")
REQ_LAT    = Histogram("robot_request_latency_seconds", "Robot latency")

# --- FastAPI -----------------------------------------------------------------
app = FastAPI(title="Robot Service", version="0.1")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class DispenseRequest(BaseModel):
    mix_id: int
    run_id: int
    colour: str = Field(pattern="^(red|green|blue)$")
    volume_ml: float = Field(gt=0.0, le=50.0)

class ErrorResponse(BaseModel):
    error: str
    detail: str
    cmd_id: str | None = None

class DispenseStatus(BaseModel):
    status: str
    predicted_squeeze_sec: float | None = None
    created_at: float = Field(default_factory=time.time)

# in-memory store; replace w/ DB table in prod
TASKS: dict[str, DispenseStatus] = {}
TASK_CLEANUP_INTERVAL = 300  # 5 minutes
MAX_TASK_AGE = 3600  # 1 hour


def pose_close(q: List[float]) -> bool:
    return all(abs(a-b) < TOL for a, b in zip(q, TARGET_POSE))


async def zmq_state_listener():
    ctx = zmq.asyncio.Context.instance()
    sub = ctx.socket(zmq.SUB)
    sub.connect("tcp://phosphobot:5555")   # state topic
    sub.setsockopt_string(zmq.SUBSCRIBE, "state")
    while True:
        try:
            _topic, raw = await sub.recv_multipart()
            msg = json.loads(raw)
            
            # Validate message structure
            if "joints" not in msg:
                logger.warning("Received message without 'joints' field")
                continue
                
            if pose_close(msg["joints"]):
                # broadcast event to any waiting CSR tasks
                async with POSE_WAITERS_LOCK:
                    completed_waiters = []
                    for fut in list(POSE_WAITERS):
                        if not fut.done():
                            fut.set_result(msg)
                            completed_waiters.append(fut)
                    # Clean up completed waiters
                    for fut in completed_waiters:
                        POSE_WAITERS.discard(fut)
            
            async with TASKS_LOCK:
                for tid, st in TASKS.items():
                    if st.status == "running" and msg.get("status") == "success":
                        st.status = "success"
        except json.JSONDecodeError as e:
            logger.error(f"Failed to decode ZMQ message: {e}")
        except Exception as e:
            logger.error(f"Error in ZMQ listener: {e}")
        await asyncio.sleep(0.0)

async def cleanup_old_tasks():
    """Periodically clean up old completed tasks"""
    while True:
        await asyncio.sleep(TASK_CLEANUP_INTERVAL)
        current_time = time.time()
        
        async with TASKS_LOCK:
            expired_tasks = [
                tid for tid, task in TASKS.items()
                if current_time - task.created_at > MAX_TASK_AGE
            ]
            for tid in expired_tasks:
                del TASKS[tid]
        
        # Also clean up any done futures in POSE_WAITERS
        async with POSE_WAITERS_LOCK:
            done_waiters = [fut for fut in POSE_WAITERS if fut.done()]
            for fut in done_waiters:
                POSE_WAITERS.discard(fut)

POSE_WAITERS: set[asyncio.Future] = set()
POSE_WAITERS_LOCK = asyncio.Lock()
TASKS_LOCK = asyncio.Lock()
asyncio.create_task(zmq_state_listener())
asyncio.create_task(cleanup_old_tasks())
start_http_server(9001)     # Prometheus

# --------------------------------------------------------------------------- #
@app.post("/robot/dispense")
@REQ_LAT.time()
async def dispense(req: DispenseRequest):
    REQS_TOTAL.inc()
    tid = str(uuid.uuid4())
    prompt = f"Dispense {req.volume_ml} ml from the {req.colour} bottle"
    
    try:
        async with TASKS_LOCK:
            TASKS[tid] = DispenseStatus(status="running")

        async with httpx.AsyncClient(timeout=60.0) as client:
            phos_resp = await client.post(f"{PHOS_URL}/inference",
                                          json={"model": MODEL_ID, "prompt": prompt})
            if phos_resp.status_code != 200:
                async with TASKS_LOCK:
                    TASKS[tid].status = "failed"
                logger.error(f"Phosphobot error: {phos_resp.status_code}")
                raise HTTPException(502, f"Phosphobot error: {phos_resp.status_code}")

            squeeze = phos_resp.json().get("predicted_squeeze_sec")
            async with TASKS_LOCK:
                TASKS[tid].predicted_squeeze_sec = squeeze

        async with TASKS_LOCK:
            return {"cmd_id": tid, **TASKS[tid].model_dump()}
    except httpx.TimeoutException:
        async with TASKS_LOCK:
            TASKS[tid].status = "failed"
        logger.error(f"Timeout calling Phosphobot for task {tid}")
        raise HTTPException(504, "Timeout calling Phosphobot")
    except Exception as e:
        async with TASKS_LOCK:
            TASKS[tid].status = "failed"
        logger.error(f"Unexpected error in dispense {tid}: {e}")
        raise HTTPException(500, f"Internal error: {str(e)}")


@app.get("/robot/{cmd_id}/status")
async def status(cmd_id: str):
    async with TASKS_LOCK:
        st = TASKS.get(cmd_id)
        if not st:
            raise HTTPException(404, f"Task {cmd_id} not found")
        return st.model_dump()


@app.get("/robot/{cmd_id}/pose-snapshot")
async def pose_snapshot(cmd_id: str, cam: str = "top_cam"):
    """
    Blocks until pose reached, then returns a presigned S3 URL provided
    by Vision-Bridge (polls kv-store every 100 ms).
    """
    fut = asyncio.get_event_loop().create_future()
    async with POSE_WAITERS_LOCK:
        POSE_WAITERS.add(fut)
    
    try:
        await asyncio.wait_for(fut, timeout=30.0)  # 30 second timeout
    except asyncio.TimeoutError:
        async with POSE_WAITERS_LOCK:
            POSE_WAITERS.discard(fut)
        raise HTTPException(408, "Timeout waiting for target pose")
    finally:
        async with POSE_WAITERS_LOCK:
            POSE_WAITERS.discard(fut)

    # ask Vision-Bridge to capture
    try:
        async with httpx.AsyncClient(timeout=30.0) as cl:
            vb = await cl.post("http://vision-bridge:8000/snapshot",
                               json={"cmd_id": cmd_id, "cam_id": cam})
            if vb.status_code != 200:
                logger.error(f"Vision bridge error: {vb.status_code}")
                raise HTTPException(502, f"Vision bridge error: {vb.status_code}")
            return vb.json()
    except httpx.TimeoutException:
        logger.error("Timeout calling vision bridge")
        raise HTTPException(504, "Timeout calling vision bridge")
    except Exception as e:
        logger.error(f"Error calling vision bridge: {e}")
        raise HTTPException(500, f"Vision bridge error: {str(e)}")
