from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, insert, and_, update, or_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import exists
from fastapi import HTTPException, status, Path
from fastapi.responses import RedirectResponse 
import hashlib
from datetime import datetime, timedelta
from database import get_async_session
from models import Link, LinkUsage, Project

from pydantic import BaseModel, Field, constr

from typing import Optional


class ShortenRequest(BaseModel):
    url: str = Field(..., example="https://example.com")
    custom_alias: Optional[str] = Field(
        None,
        min_length=4,
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



router = APIRouter(
    prefix="/links",
    tags=["Links"]
)

@router.post("/shorten", response_model = ShortResponse)
async def make_short_link(
    request: ShortenRequest, 
    session: AsyncSession = Depends(get_async_session)
):
    # Проверка кастомного алиаса
    if request.custom_alias:
        short_url = fr'/shrt/{request.custom_alias}'
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
            short_url = fr'/shrt/{short_hash}'
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
                    started_at=datetime.utcnow()
                )
                session.add(project_obj)
                await session.flush()
            
            project_id = project_obj.id

    # Создание ссылки
    async with session.begin():
        new_link = Link(
            url=request.url,
            short=short_url,
            created_at=datetime.utcnow() + timedelta(hours=3) ,
            expires_at=request.expires_at,
            project_id=project_id
        )
        session.add(new_link)
        await session.flush()
        await session.refresh(new_link)
    
    return ShortResponse(short_code=short_url)



@router.get("/{short_code}")
async def get_info(
    short_code: str = Path(..., 
                         min_length=3,
                         max_length=64),
    session: AsyncSession = Depends(get_async_session)
):
    short_code_clean = short_code.lstrip('/')
    short_code_norm = (
        f"/{short_code_clean}" 
        if short_code_clean.startswith('shrt/') 
        else f"/shrt/{short_code_clean}"
    )

    try:
        # Начать транзакцию
        async with session.begin():
            # Запрос и блокировка строки для обновления
            result = await session.execute(
                select(Link)
                .where(
                    and_(
                        Link.short == short_code_norm,
                        Link.deleted.is_(False),
                        or_(
                            Link.expires_at > (datetime.utcnow() + timedelta(hours=3)),
                            Link.expires_at.is_(None)
                        )
                    )
                )
                .with_for_update()
            )
            link = result.scalar()
            
            if not link:
                raise HTTPException(404, "Short link not found or expired")

            usage = LinkUsage(
                link_id=link.id,
                dt=(datetime.utcnow() + timedelta(hours=3)))
            session.add(usage)

            link.cnt_usage += 1
            link.last_usage = datetime.utcnow() + timedelta(hours=3)

    except Exception as e:
        await session.rollback()
        print(f"Error: {e}")
        raise HTTPException(500, "Internal server error")

    return RedirectResponse(link.url, status_code=307)



@router.delete("/{short_code}", response_model=StatusResponse)
async def delete_short(
    short_code: str = Path(..., 
                         min_length=3,
                         max_length=64),
    session: AsyncSession = Depends(get_async_session)
):

    short_code_clean = short_code.lstrip('/')
    
    if short_code_clean.startswith('shrt/'):
        short_code_norm = fr'/{short_code_clean}'
    else:
        short_code_norm = fr'/shrt/{short_code_clean}'
    
    exists_query = await session.scalar(
        select(1).where(
            and_(
                Link.short == short_code_norm,
                Link.deleted.is_(False)
        ))
    )
    
    if not exists_query:
        raise HTTPException(404, "Short link doesn't exist")
    
    await session.execute(
        update(Link)
        .where(Link.short == short_code_norm)
        .values(deleted=True)
    )
    await session.commit()
    
    return StatusResponse(status="success",
                          message= "Link has been deleted")


@router.put("/{short_code}", response_model=StatusResponse)
async def change_url(
    short_code: str,
    request_data: UpdateUrlRequest,
    session: AsyncSession = Depends(get_async_session)
    ):
    short_code_clean = short_code.lstrip('/')

    if short_code_clean.startswith('shrt/'):
        short_code_norm = fr'/{short_code_clean}'
    else:
        short_code_norm = fr'/shrt/{short_code_clean}'

    code_exists = await session.scalar(
        select(exists().where(
            and_(
                Link.short == short_code_norm,
                Link.deleted.is_(False)
        )))
    )
    
    if not code_exists:
        raise HTTPException(404, "Short link doesn't exist")
    
    stmt = (
        update(Link)
        .where(Link.short == short_code_norm)
        .values(url=request_data.url)
        .execution_options(synchronize_session="fetch")
    )
    
    await session.execute(stmt)
    await session.commit()
    
    return StatusResponse(status="success",
                          message= "Url has been updated")


@router.get("/search", response_model=ShortResponse)
async def search_short(
    query: SearchQuery = Depends(),
    session: AsyncSession = Depends(get_async_session)
):
    normalized_url = query.original_url.strip().rstrip("/").lower()

    stmt = select(
        Link.short
    ).where(
        and_(
            func.lower(func.replace(Link.url, '//', '/')).istartswith(normalized_url),
            Link.deleted.is_(False),
            or_(Link.expires_at > (datetime.utcnow() + timedelta(hours=3)), Link.expires_at.is_(None))
        )
    )

    result = await session.execute(stmt)
    link_data = result.scalar_one_or_none()

    if not link_data:
        raise HTTPException(404, "Short link not found or expired")

    return ShortResponse(short_code=link_data)



@router.get("/{short_code}/stats", response_model=LinkInfoResponse)
async def get_link_info(
    short_code: str,
    session: AsyncSession = Depends(get_async_session)
):
    short_code_clean = short_code.lstrip('/')
    short_code_norm = (
        f"/{short_code_clean}" 
        if short_code_clean.startswith('shrt/') 
        else f"/shrt/{short_code_clean}"
    )

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
                    Link.short == short_code_norm,
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