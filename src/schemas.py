from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

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

class LinkDeletedResponse(BaseModel):
    url: str
    short: str
    created_at: datetime
    last_usage: datetime | None
    cnt_usage: int = Field(..., ge=0)
    project_name: str | None


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
    
class ProjectStatsResponse(BaseModel):
    name: str
    started_at: datetime
    finished_at: datetime | None
    total_links: int = Field(..., ge=0)
    active_links: int = Field(..., ge=0)
    total_clicks: int = Field(..., ge=0)
    