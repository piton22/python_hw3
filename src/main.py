from fastapi import FastAPI
from router import router
from redis import asyncio as aioredis
from redis.asyncio import Redis
from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend
from src.config import REDIS_HOST, REDIS_PORT

import uvicorn


app = FastAPI()

@app.on_event("startup")
async def startup():
    redis = Redis.from_url(
        f"redis://{REDIS_HOST}:{REDIS_PORT}",
        encoding="utf-8",
        decode_responses=True
    )
    FastAPICache.init(RedisBackend(redis), prefix="fastapi-cache")
app.include_router(router)


if __name__ == "__main__":
    uvicorn.run("main:app", reload=True, host="0.0.0.0", log_level="info")