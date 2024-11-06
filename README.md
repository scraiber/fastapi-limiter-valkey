# fastapi-limiter-valkey

[![pypi](https://img.shields.io/pypi/v/fastapi-limiter-valkey.svg?style=flat)](https://pypi.python.org/pypi/fastapi-limiter-valkey)
[![license](https://img.shields.io/github/license/scraiber/fastapi-limiter-valkey)](https://github.com/scraiber/fastapi-limiter-valkey/blob/master/LICENCE)
[![workflows](https://github.com/scraiber/fastapi-limiter-valkey/workflows/pypi/badge.svg)](https://github.com/scraiber/fastapi-limiter-valkey/actions?query=workflow:pypi)
[![workflows](https://github.com/scraiber/fastapi-limiter-valkey/workflows/ci/badge.svg)](https://github.com/scraiber/fastapi-limiter-valkey/actions?query=workflow:ci)

## Introduction

FastAPI-Limiter-Valkey is a rate limiting tool for [fastapi](https://github.com/tiangolo/fastapi) routes with lua script.

It is a friendly fork from [FastAPI-Limiter](https://github.com/long2ice/fastapi-limiter) and adapted to use `Valkey`.

## Requirements

- [valkey](https://valkey.io/)

## Install

Just install from pypi

```shell script
> pip install fastapi-limiter-valkey
```

## Quick Start

FastAPI-Limiter-Valkey is simple to use, which just provide a dependency `RateLimiter`, the following example allow `2` times
request per `5` seconds in route `/`.

```py
import valkey.asyncio as valkey
import uvicorn
from contextlib import asynccontextmanager
from fastapi import Depends, FastAPI

from fastapi_limiter import FastAPILimiter
from fastapi_limiter.depends import RateLimiter

@asynccontextmanager
async def lifespan(_: FastAPI):
    valkey_connection = valkey.from_url("valkey://localhost:6379", encoding="utf8")
    await FastAPILimiter.init(valkey_connection)
    yield
    await FastAPILimiter.close()

app = FastAPI(lifespan=lifespan)

@app.get("/", dependencies=[Depends(RateLimiter(times=2, seconds=5))])
async def index():
    return {"msg": "Hello World"}


if __name__ == "__main__":
    uvicorn.run("main:app", debug=True, reload=True)
```

## Usage

There are some config in `FastAPILimiter.init`.

### valkey

The async `valkey` instance.

### prefix

Prefix of valkey key.

### identifier

Identifier of route limit, default is `ip`, you can override it such as `userid` and so on.

```py
async def default_identifier(request: Request):
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0]
    return request.client.host + ":" + request.scope["path"]
```

### callback

Callback when access is forbidden, default is raise `HTTPException` with `429` status code.

```py
async def default_callback(request: Request, response: Response, pexpire: int):
    """
    default callback when too many requests
    :param request:
    :param pexpire: The remaining milliseconds
    :param response:
    :return:
    """
    expire = ceil(pexpire / 1000)

    raise HTTPException(
        HTTP_429_TOO_MANY_REQUESTS, "Too Many Requests", headers={"Retry-After": str(expire)}
    )
```

## Multiple limiters

You can use multiple limiters in one route.

```py
@app.get(
    "/multiple",
    dependencies=[
        Depends(RateLimiter(times=1, seconds=5)),
        Depends(RateLimiter(times=2, seconds=15)),
    ],
)
async def multiple():
    return {"msg": "Hello World"}
```

Not that you should note the dependencies orders, keep lower of result of `seconds/times` at the first.

## Rate limiting within a websocket.

While the above examples work with rest requests, FastAPI also allows easy usage
of websockets, which require a slightly different approach.

Because websockets are likely to be long lived, you may want to rate limit in
response to data sent over the socket.

You can do this by rate limiting within the body of the websocket handler:

```py
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
```

## Lua script

The lua script used.

```lua
local key = KEYS[1]
local limit = tonumber(ARGV[1])
local expire_time = ARGV[2]

local current = tonumber(server.call('get', key) or "0")
if current > 0 then
    if current + 1 > limit then
        return server.call("PTTL", key)
    else
        server.call("INCR", key)
        return 0
    end
else
    server.call("SET", key, 1, "px", expire_time)
    return 0
end
```

## License

This project is licensed under the
[Apache-2.0](https://github.com/scraiber/fastapi-limiter-valkey/blob/master/LICENCE) License.
