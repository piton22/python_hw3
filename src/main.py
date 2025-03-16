from fastapi import FastAPI
# from collections.abc import AsyncIterator
# from contextlib import asynccontextmanager
from router import router
# from redis import asyncio as aioredis
# from fastapi_cache import FastAPICache
# from fastapi_cache.backends.redis import RedisBackend

import uvicorn


app = FastAPI()


app.include_router(router)


if __name__ == "__main__":
    uvicorn.run("main:app", reload=True, host="0.0.0.0", log_level="info")