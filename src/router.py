from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, insert, and_, update, or_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import exists
from fastapi import HTTPException, status
from fastapi.responses import RedirectResponse 
import time
import hashlib
from datetime import datetime
from database import get_async_session
from models import Link, LinkUsage, Project
import uvicorn

from pydantic import BaseModel
from typing import Optional


class ShortenRequest(BaseModel):
    url: str
    custom_alias: Optional[str] = None
    expires_at: Optional[datetime] = None
    project: Optional[str] = None



router = APIRouter(
    prefix="/links",
    tags=["Links"]
)


# @router.post("/shorten")
# async def make_short_link(
#     url: str,
#     session: AsyncSession = Depends(get_async_session),
#     custom_alias: str = None,
#     expires_at: datetime = None,
#     project: str = None
# ):
@router.post("/shorten")
async def make_short_link(
    request: ShortenRequest,  # Принимаем данные из тела запроса
    session: AsyncSession = Depends(get_async_session)
):
    # Проверка кастомного алиаса
    if ShortenRequest.custom_alias:
        alias_exists = await session.scalar(
            select(exists().where(and_(Link.short == ShortenRequest.custom_alias, Link.deleted.is_(False)))))
        if alias_exists:
            raise HTTPException(409, "Alias already exists")
        short_url = f'/shrt/custom_alias'
    else:
        # Генерация уникального короткого кода
        max_attempts = 5

        for _ in range(max_attempts):
            hash_url = hashlib.sha256(ShortenRequest.url.encode()).hexdigest()
            short_hash = hash_url[:6]
            short_url = f'/shrt/{short_hash}'
            exists = await session.scalar(
                select(exists().where(and_(Link.short == short_url, Link.deleted.is_(False)))))
            if not exists:
                break
        raise HTTPException(500, "Failed to generate short URL")

    # Обработка проекта
    project_id = None
    if ShortenRequest.project:
        project_obj = await session.scalar(
            select(Project).where(Project.name == ShortenRequest.project))
        if not project_obj:
            project_obj = Project(name=ShortenRequest.project, started_at=datetime.utcnow())
            session.add(project_obj)
            await session.commit()
            await session.refresh(project_obj)
        project_id = project_obj.id

    # Создание ссылки
    new_link = Link(
        url=ShortenRequest.url,
        short=short_url,
        created_at=func.now(),
        expires_at=ShortenRequest.expires_at,
        project_id=project_id
    )
    session.add(new_link)
    await session.commit()
    await session.refresh(new_link)
    
    return {"short_url": short_url}


@router.get("/{short_code}")
async def get_info(
    short_code: str,
    session: AsyncSession = Depends(get_async_session)
):
    # Формируем запрос для получения данных ссылки
    stmt = select(
        Link.url
    ).where(
        and_(
            Link.short == short_code,
            Link.deleted.is_(False),
            or_(Link.expires_at > func.now(), Link.expires_at.is_(None))  
        )
    )

    result = await session.execute(stmt)
    original_url = result.scalar_one_or_none()

    if not original_url:
        raise HTTPException(404, "Short link not found or expired")

    return RedirectResponse(
        url=original_url, 
        status_code=307
    )


@router.delete("/{short_code}")
async def delete_short(
    short_code: str,
    session: AsyncSession = Depends(get_async_session)
):

    exists = await session.scalar(
        select(exists().where(
            and_(
                Link.short == short_code,
                Link.deleted.is_(False)
            )
        ))
    )
    
    if not exists:
        raise HTTPException(404, "Short link doesn't exist")

    stmt = (
        update(Link)
        .where(Link.short == short_code)
        .values(deleted=True)
        .execution_options(synchronize_session="fetch")
    )
    
    await session.execute(stmt)
    await session.commit()
    
    return {"status": "success", "message": "Link has been deleted"}


@router.put("/{short_code}")
async def change_url(
    url: str,
    short_code: str,
    session: AsyncSession = Depends(get_async_session)):

    exists = await session.scalar(
        select(exists().where(
            and_(
                Link.short == short_code,
                Link.deleted.is_(False)
            )
        ))
    )
    
    if not exists:
        raise HTTPException(404, "Short link doesn't exist")
    
    stmt = (
        update(Link)
        .where(Link.short == short_code)
        .values(url=url)
        .execution_options(synchronize_session="fetch")
    )
    
    await session.execute(stmt)
    await session.commit()
    
    return {"status": "success", "message": "Url has been updated"}

@router.get("/search?original_url={url}")
async def search_short(
    url: str,
    session: AsyncSession = Depends(get_async_session)):

    stmt = select(
        Link.short
    ).where(
        and_(
            Link.url == url,
            Link.deleted.is_(False),
            or_(Link.expires_at > func.now(), Link.expires_at.is_(None))  
        )
    )

    result = await session.execute(stmt)
    link_data = result.first()

    if not link_data:
        raise HTTPException(404, "Url not found or expired")

    short_url  = link_data[0]

    return {"short_url": short_url}

# if __name__ == "__main__":
#     uvicorn.run("main:app", reload=True, host="0.0.0.0", log_level="info")