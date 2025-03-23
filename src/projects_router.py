from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import and_, or_, select, func
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_async_session
from models import Link, Project
from schemas import ProjectStatsResponse

projects_router = APIRouter(
    prefix="/projects",
    tags=["Projects"]
)

@projects_router.get("/{project_name}/stats", response_model=ProjectStatsResponse)
async def get_project_stats(
    project_name: str,
    session: AsyncSession = Depends(get_async_session)
):

    project = await session.scalar(
        select(Project)
        .where(Project.name == project_name)
    )
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    current_time = datetime.utcnow() + timedelta(hours=3)

    total_links = await session.scalar(
        select(func.count(Link.id))
        .where(Link.project_id == project.id)
    )

    total_clicks = await session.scalar(
        select(func.coalesce(func.sum(Link.cnt_usage), 0))
        .where(Link.project_id == project.id)
    )

    active_links = await session.scalar(
        select(func.count(Link.id))
        .where(
            and_(
                Link.project_id == project.id,
                Link.deleted.is_(False),
                or_(
                    Link.expires_at > current_time,
                    Link.expires_at.is_(None)
            )
        )
    ))

    return ProjectStatsResponse(
        name=project.name,
        started_at=project.started_at,
        finished_at=project.finished_at,
        total_links=total_links,
        active_links=active_links,
        total_clicks=total_clicks
    )