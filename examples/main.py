from contextlib import asynccontextmanager

import uvicorn
import valkey.asyncio as valkey
from fastapi import Depends, FastAPI, HTTPException, WebSocket, WebSocketDisconnect

from fastapi_limiter import FastAPILimiter
from fastapi_limiter.depends import RateLimiter, WebSocketRateLimiter


@asynccontextmanager
async def lifespan(_: FastAPI):
    valkey_connection = valkey.from_url("valkey://localhost:6379", encoding="utf8")
    await FastAPILimiter.init(valkey_connection)
    yield
    await FastAPILimiter.close()


app = FastAPI(lifespan=lifespan)


@app.get("/", dependencies=[Depends(RateLimiter(times=2, seconds=5))])
async def index_get():
    return {"msg": "Hello World"}


@app.post("/", dependencies=[Depends(RateLimiter(times=1, seconds=5))])
async def index_post():
    return {"msg": "Hello World"}


@app.get(
    "/multiple",
    dependencies=[
        Depends(RateLimiter(times=1, seconds=5)),
        Depends(RateLimiter(times=2, seconds=15)),
    ],
)
async def multiple():
    return {"msg": "Hello World"}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    ratelimit = WebSocketRateLimiter(times=1, seconds=5)
    try:
        while True:
            try:
                data = await websocket.receive_text()
                await ratelimit(websocket, context_key=data)  # NB: context_key is optional
                await websocket.send_text("Hello, world")
            except HTTPException:
                await websocket.send_text("Hello again")
    except WebSocketDisconnect:
        print("Client disconnected")
    finally:
        await websocket.close()


if __name__ == "__main__":
    uvicorn.run("main:app", debug=True, reload=True)
