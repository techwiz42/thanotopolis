from datetime import datetime
from typing import Optional, List
from uuid import UUID
from pydantic import BaseModel, EmailStr

from app.models.issues import IssueStatus, IssuePriority, IssueType


# Issue Comment Schemas
class IssueCommentBase(BaseModel):
    content: str


class IssueCommentCreate(IssueCommentBase):
    author_name: Optional[str] = None
    author_email: Optional[EmailStr] = None


class IssueCommentUpdate(BaseModel):
    content: Optional[str] = None


class IssueCommentInDB(IssueCommentBase):
    id: UUID
    issue_id: UUID
    user_id: Optional[UUID] = None
    author_name: Optional[str] = None
    author_email: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class IssueComment(IssueCommentInDB):
    pass


# Issue Schemas
class IssueBase(BaseModel):
    title: str
    description: str
    type: IssueType = IssueType.BUG
    priority: IssuePriority = IssuePriority.MEDIUM


class IssueCreate(IssueBase):
    reporter_email: Optional[EmailStr] = None
    reporter_name: Optional[str] = None


class IssueUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    type: Optional[IssueType] = None
    status: Optional[IssueStatus] = None
    priority: Optional[IssuePriority] = None
    assigned_to_id: Optional[UUID] = None
    resolution: Optional[str] = None


class IssueInDB(IssueBase):
    id: UUID
    tenant_id: Optional[UUID] = None
    status: IssueStatus
    reporter_email: Optional[str] = None
    reporter_name: Optional[str] = None
    reporter_user_id: Optional[UUID] = None
    assigned_to_id: Optional[UUID] = None
    resolved_by_id: Optional[UUID] = None
    resolution: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    resolved_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class Issue(IssueInDB):
    comments: List[IssueComment] = []


class IssueList(BaseModel):
    items: List[Issue]
    total: int
    page: int
    page_size: int