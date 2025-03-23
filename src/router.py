from datetime import datetime, timedelta
import hashlib
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Path
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field
from redis.asyncio import Redis
from sqlalchemy import and_, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import exists

from database import get_async_session
from models import Link, Project
from schemas import ShortenRequest, UpdateUrlRequest, LinkInfoResponse, StatusResponse, SearchQuery, ShortResponse
from src.config import REDIS_HOST, REDIS_PORT


router = APIRouter(
    prefix="/links",
    tags=["Links"]
)

async def get_redis() -> Redis:
    return Redis.from_url(f"redis://{REDIS_HOST}:{REDIS_PORT}")

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
async def get_info(
    short_code: str = Path(..., min_length=3, max_length=64),
    session: AsyncSession = Depends(get_async_session),
    redis: Redis = Depends(get_redis)
):
    cached_url = await redis.get(f"redirect:{short_code}")
    if cached_url:
        return RedirectResponse(cached_url.decode(), status_code=307)

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

    if link.cnt_usage > 10:
        await redis.setex(
            f"redirect:{short_code}", 
            600,  
            link.url
        )

    return RedirectResponse(link.url, status_code=307)


@router.delete("/{short_code}", response_model=StatusResponse)
async def delete_short(
    short_code: str = Path(..., min_length=3, max_length=64),
    session: AsyncSession = Depends(get_async_session),
    redis: Redis = Depends(get_redis)  
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
    
    # Удаляем кэш
    await redis.delete(f"redirect:{short_code}")  
    await redis.delete(f"stats:{short_code}")    
    
    return StatusResponse(
        status="success",
        message="Link has been deleted"
    )


@router.put("/{short_code}", response_model=StatusResponse)
async def change_url(
    short_code: str,
    request_data: UpdateUrlRequest,
    session: AsyncSession = Depends(get_async_session),
    redis: Redis = Depends(get_redis)
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

    # Удаляем кэш
    await redis.delete(f"redirect:{short_code}")  
    await redis.delete(f"stats:{short_code}")  
    
    return StatusResponse(
        status="success",
        message="Url has been updated"
    )



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
async def get_link_info(
    short_code: str,
    session: AsyncSession = Depends(get_async_session),
    redis: Redis = Depends(get_redis)
):

    cache_key = f"stats:{short_code}"
    cached_data = await redis.get(cache_key)
    
    if cached_data:
        return LinkInfoResponse.parse_raw(cached_data)

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
            .where(Link.short == short_code)
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

        response = LinkInfoResponse(
            url=url,
            created_at=created_at,
            last_usage=last_usage,
            cnt_usage=cnt_usage,
            project_name=project_name,
            is_active=is_active
        )

        if cnt_usage > 10:
            await redis.setex(
                cache_key,
                600,
                response.json()
            )

        return response