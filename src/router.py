from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, insert, and_, update, or_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import exists
from fastapi import HTTPException, status, Path
from fastapi.responses import RedirectResponse 
import hashlib
from datetime import datetime, timedelta, timezone
from database import get_async_session
# from models import Link, LinkUsage, Project
from models import Link, Project
from pydantic import BaseModel, Field, constr
from typing import Optional
from fastapi_cache.decorator import cache
from fastapi_cache import FastAPICache
from redis import asyncio as aioredis
# from fastapi_cache.backends.redis import RedisCacheBackend
from src.config import REDIS_HOST, REDIS_PORT


class ShortenRequest(BaseModel):
    url: str = Field(..., example="https://example.com")
    custom_alias: Optional[str] = Field(
        None,
        min_length=3,
        max_length=32,
        example="hse"
    )
    expires_at: Optional[datetime] = Field(
        None,
        example="2024-01-01T00:00:00"
    )
    project: Optional[str] = Field(
        None,
        max_length=50,
        example="marketing"
    )

class UpdateUrlRequest(BaseModel):
    url: str


class LinkInfoResponse(BaseModel):
    url: str
    created_at: datetime
    last_usage: datetime | None
    cnt_usage: int = Field(..., ge=0)
    project_name: str | None
    is_active: bool


class StatusResponse(BaseModel):
    status: str
    message: str

class SearchQuery(BaseModel):
    original_url: str = Field(
        ...,
        min_length=3,
        max_length=2048,
        example="https://example.com/page"
    )
class ShortResponse(BaseModel):
    short_code: str = Field(..., 
                          example="abc123",
                          min_length=3,
                          max_length=64)
    


def get_cache_key(short_code: str):
    return f"link:{short_code}"

def get_stats_cache_key(short_code: str):
    return f"stats:{short_code}"

router = APIRouter(
    prefix="/links",
    tags=["Links"]
)

@router.post("/shorten", response_model = ShortResponse)
async def make_short_link(
    request: ShortenRequest, 
    session: AsyncSession = Depends(get_async_session)
):
    normalized_url = request.url.strip().rstrip("/").lower()
    # Проверка кастомного алиаса
    if request.custom_alias:
        short_url = request.custom_alias
        async with session.begin():
            alias_exists = await session.scalar(
                select(Link).where(
                    and_(
                        Link.short == short_url,
                        Link.deleted.is_(False)
                ))
            )
        if alias_exists:
            raise HTTPException(409, "Alias already exists")
    
    else:
        # Генерация короткого кода
        for _ in range(5):
            short_hash = hashlib.sha256(request.url.encode()).hexdigest()[:6]
            short_url = short_hash
            async with session.begin():
                exists = await session.scalar(
                    select(Link).where(
                        and_(
                            Link.short == short_url,
                            Link.deleted.is_(False)
                    )
                ))
                if not exists:
                    break
        else:
            raise HTTPException(500, "Failed to generate short URL")

    # Обработка проекта
    project_id = None
    if request.project:
        async with session.begin():
            project_obj = await session.scalar(
                select(Project).where(Project.name == request.project))
            
            if not project_obj:
                project_obj = Project(
                    name=request.project,
                    started_at=datetime.utcnow() + timedelta(hours=3) 
                )
                session.add(project_obj)
                await session.flush()
            
            project_id = project_obj.id

    # Создание ссылки
    async with session.begin():
        new_link = Link(
            url=normalized_url,
            short=short_url,
            created_at=datetime.utcnow() + timedelta(hours=3) ,
            expires_at=request.expires_at,
            project_id=project_id
        )
        session.add(new_link)
        await session.flush()
        await session.refresh(new_link)
    
    return ShortResponse(short_code=short_url)



@router.get("/{short_code}", response_class=RedirectResponse)
@cache(
    expire=300,
    namespace="redirects",
    key_builder=lambda *args, **kwargs: get_cache_key(kwargs['short_code']),
    unless=lambda response: response.cnt_usage <= 10
)
async def get_info(
    short_code: str = Path(..., min_length=3, max_length=64),
    session: AsyncSession = Depends(get_async_session)
):
    redis = aioredis.from_url(f"redis://{REDIS_HOST}:{REDIS_PORT}")

    link = await session.scalar(
        select(Link)
        .where(
            and_(
                Link.short == short_code,
                Link.deleted.is_(False),
                or_(
                    Link.expires_at > (datetime.utcnow() + timedelta(hours=3)),
                    Link.expires_at.is_(None)
                )
            )
        )
    )

    if not link:
        raise HTTPException(status_code=404, detail="Short link not found or expired")

    await redis.hincrby(f"link_stats:{short_code}", "hits", 1)
    await redis.hset(f"link_stats:{short_code}", "last_used", (datetime.utcnow() + timedelta(hours=3)).isoformat())
    await redis.expire(f"link_stats:{short_code}", 3600)

    return RedirectResponse(link.url, status_code=307)


@router.delete("/{short_code}", response_model=StatusResponse)
async def delete_short(
    short_code: str = Path(..., 
                         min_length=3,
                         max_length=64),
    session: AsyncSession = Depends(get_async_session)
):
    
    exists_query = await session.scalar(
        select(1).where(
            and_(
                Link.short == short_code,
                Link.deleted.is_(False)
        ))
    )
    
    if not exists_query:
        raise HTTPException(404, "Short link doesn't exist")
    
    await session.execute(
        update(Link)
        .where(Link.short == short_code)
        .values(deleted=True)
    )
    await session.commit()
    redis_cache = FastAPICache.get_cache_backend()
    await redis_cache.delete(get_cache_key(short_code))
    await redis_cache.delete(get_stats_cache_key(short_code))
    
    return StatusResponse(status="success",
                          message= "Link has been deleted")


@router.put("/{short_code}", response_model=StatusResponse)
async def change_url(
    short_code: str,
    request_data: UpdateUrlRequest,
    session: AsyncSession = Depends(get_async_session)
    ):
    normalized_url = request_data.url.strip().rstrip("/").lower()

    code_exists = await session.scalar(
        select(exists().where(
            and_(
                Link.short == short_code,
                Link.deleted.is_(False)
        )))
    )
    
    if not code_exists:
        raise HTTPException(404, "Short link doesn't exist")
    
    stmt = (
        update(Link)
        .where(Link.short == short_code)
        .values(url=normalized_url)
        .execution_options(synchronize_session="fetch")
    )
    
    await session.execute(stmt)
    await session.commit()

    redis_cache = FastAPICache.get_cache_backend()
    await redis_cache.delete(get_cache_key(short_code))
    await redis_cache.delete(get_stats_cache_key(short_code))
    
    return StatusResponse(status="success",
                          message= "Url has been updated")


@router.get("/search", response_model=ShortResponse)
async def search_short(
    query: SearchQuery = Depends(),
    session: AsyncSession = Depends(get_async_session)
):
    normalized_url = query.original_url.strip().rstrip("/").lower()

    stmt = (
        select(Link.short)
        .where(
            and_(
                Link.url == normalized_url,
                Link.deleted.is_(False),
                or_(
                    Link.expires_at > (datetime.utcnow() + timedelta(hours=3)),
                    Link.expires_at.is_(None)
                )
            )
        )
        .limit(1)
    )

    result = await session.execute(stmt)
    short_code = result.scalar_one_or_none()

    if not short_code:
        raise HTTPException(
            status_code=404,
            detail={"message": "Short link not found or expired"}
        )

    return ShortResponse(short_code=short_code)



@router.get("/{short_code}/stats", response_model=LinkInfoResponse)
@cache(
    expire=600,
    namespace="stats",
    key_builder=lambda *args, **kwargs: get_stats_cache_key(kwargs['short_code']),
    unless=lambda response: response.cnt_usage <= 10
)
async def get_link_info(
    short_code: str,
    session: AsyncSession = Depends(get_async_session)
):


    async with session.begin():
        result = await session.execute(
            select(
                Link.url,
                Link.created_at,
                Link.last_usage,
                Link.cnt_usage,
                Project.name,
                Link.deleted,
                Link.expires_at
            )
            .outerjoin(Project, Link.project_id == Project.id)
            .where(
                    Link.short == short_code,
            )
        )
        
        row = result.first()
        if not row:
            raise HTTPException(status_code=404, detail="Link not found")


        (url, created_at, last_usage, cnt_usage, 
         project_name, deleted, expires_at) = row


        is_active = not deleted and (
            expires_at is None or 
            expires_at > (datetime.utcnow() + timedelta(hours=3))
        )

        return LinkInfoResponse(
            url=url,
            created_at=created_at,
            last_usage=last_usage,
            cnt_usage=cnt_usage,
            project_name=project_name,
            is_active=is_active
        )