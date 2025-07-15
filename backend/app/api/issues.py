from typing import List, Optional
from uuid import UUID
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, status, Request
from sqlalchemy import select, func, or_, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.database import get_db
from app.auth.auth import get_current_user, get_current_active_user
from app.models import User, Issue, IssueComment, IssueStatus, IssuePriority, IssueType
from app.schemas.issues import (
    IssueCreate, IssueUpdate, Issue as IssueSchema, IssueList,
    IssueCommentCreate, IssueComment as IssueCommentSchema
)

router = APIRouter()


@router.post("/issues", response_model=IssueSchema)
async def create_issue(
    issue: IssueCreate,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new issue. Can be anonymous or authenticated.
    """
    # Try to get authenticated user
    current_user = None
    try:
        current_user = await get_current_user(request, db)
    except:
        # Allow anonymous issue creation
        pass
    
    db_issue = Issue(
        **issue.dict(),
        reporter_user_id=current_user.id if current_user else None,
        tenant_id=current_user.tenant_id if current_user else None
    )
    
    db.add(db_issue)
    await db.commit()
    await db.refresh(db_issue)
    
    # Load relationships
    result = await db.execute(
        select(Issue)
        .options(selectinload(Issue.comments))
        .where(Issue.id == db_issue.id)
    )
    return result.scalar_one()


@router.get("/issues", response_model=IssueList)
async def list_issues(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[IssueStatus] = None,
    priority: Optional[IssuePriority] = None,
    type: Optional[IssueType] = None,
    search: Optional[str] = None,
    assigned_to_me: bool = False,
    request: Request = None,
    db: AsyncSession = Depends(get_db)
):
    """
    List issues with filtering and pagination.
    Anonymous users can see all open issues.
    """
    # Base query
    query = select(Issue).options(selectinload(Issue.comments))
    
    # Try to get authenticated user
    current_user = None
    try:
        current_user = await get_current_user(request, db)
    except:
        pass
    
    # For authenticated users, show tenant-specific issues
    if current_user:
        query = query.where(Issue.tenant_id == current_user.tenant_id)
        
        if assigned_to_me:
            query = query.where(Issue.assigned_to_id == current_user.id)
    else:
        # Anonymous users see public issues only
        query = query.where(Issue.tenant_id.is_(None))
    
    # Apply filters
    if status:
        query = query.where(Issue.status == status)
    if priority:
        query = query.where(Issue.priority == priority)
    if type:
        query = query.where(Issue.type == type)
    
    if search:
        search_filter = or_(
            Issue.title.ilike(f"%{search}%"),
            Issue.description.ilike(f"%{search}%")
        )
        query = query.where(search_filter)
    
    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # Apply pagination
    query = query.order_by(Issue.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    
    result = await db.execute(query)
    issues = result.scalars().all()
    
    return IssueList(
        items=issues,
        total=total,
        page=page,
        page_size=page_size
    )


@router.get("/issues/{issue_id}", response_model=IssueSchema)
async def get_issue(
    issue_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Get a specific issue by ID.
    """
    result = await db.execute(
        select(Issue)
        .options(selectinload(Issue.comments))
        .where(Issue.id == issue_id)
    )
    issue = result.scalar_one_or_none()
    
    if not issue:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Issue not found"
        )
    
    return issue


@router.put("/issues/{issue_id}", response_model=IssueSchema)
async def update_issue(
    issue_id: UUID,
    issue_update: IssueUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Update an issue. Requires authentication.
    """
    result = await db.execute(
        select(Issue).where(Issue.id == issue_id)
    )
    issue = result.scalar_one_or_none()
    
    if not issue:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Issue not found"
        )
    
    # Get authenticated user (required for updates)
    current_user = await get_current_user(request, db)
    
    # Check permissions (must be admin or assigned to the issue)
    if current_user.role not in ["admin", "super_admin"] and issue.assigned_to_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this issue"
        )
    
    # Update fields
    update_data = issue_update.dict(exclude_unset=True)
    
    # Track resolution
    if update_data.get("status") == IssueStatus.RESOLVED and issue.status != IssueStatus.RESOLVED:
        update_data["resolved_at"] = datetime.utcnow()
        update_data["resolved_by_id"] = current_user.id
    
    for field, value in update_data.items():
        setattr(issue, field, value)
    
    issue.updated_at = datetime.utcnow()
    
    await db.commit()
    await db.refresh(issue)
    
    # Load relationships
    result = await db.execute(
        select(Issue)
        .options(selectinload(Issue.comments))
        .where(Issue.id == issue.id)
    )
    return result.scalar_one()


@router.post("/issues/{issue_id}/comments", response_model=IssueCommentSchema)
async def create_comment(
    issue_id: UUID,
    comment: IssueCommentCreate,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Add a comment to an issue. Can be anonymous or authenticated.
    """
    # Verify issue exists
    result = await db.execute(
        select(Issue).where(Issue.id == issue_id)
    )
    issue = result.scalar_one_or_none()
    
    if not issue:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Issue not found"
        )
    
    # Try to get authenticated user
    current_user = None
    try:
        current_user = await get_current_user(request, db)
    except:
        # Allow anonymous comments
        pass
    
    db_comment = IssueComment(
        issue_id=issue_id,
        content=comment.content,
        user_id=current_user.id if current_user else None,
        author_name=comment.author_name if not current_user else None,
        author_email=comment.author_email if not current_user else None
    )
    
    db.add(db_comment)
    await db.commit()
    await db.refresh(db_comment)
    
    return db_comment


@router.get("/issues/{issue_id}/comments", response_model=List[IssueCommentSchema])
async def list_comments(
    issue_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    List all comments for an issue.
    """
    result = await db.execute(
        select(IssueComment)
        .where(IssueComment.issue_id == issue_id)
        .order_by(IssueComment.created_at)
    )
    comments = result.scalars().all()
    
    return comments


@router.get("/issues/stats/summary")
async def get_issue_stats(
    request: Request = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Get issue statistics.
    """
    # Base query filter
    base_filter = []
    
    # Try to get authenticated user
    current_user = None
    try:
        current_user = await get_current_user(request, db)
    except:
        pass
    
    if current_user:
        base_filter.append(Issue.tenant_id == current_user.tenant_id)
    else:
        base_filter.append(Issue.tenant_id.is_(None))
    
    # Count by status
    status_stats = {}
    for status in IssueStatus:
        result = await db.execute(
            select(func.count(Issue.id))
            .where(and_(Issue.status == status, *base_filter))
        )
        status_stats[status.value] = result.scalar()
    
    # Count by priority
    priority_stats = {}
    for priority in IssuePriority:
        result = await db.execute(
            select(func.count(Issue.id))
            .where(and_(Issue.priority == priority, *base_filter))
        )
        priority_stats[priority.value] = result.scalar()
    
    # Count by type
    type_stats = {}
    for issue_type in IssueType:
        result = await db.execute(
            select(func.count(Issue.id))
            .where(and_(Issue.type == issue_type, *base_filter))
        )
        type_stats[issue_type.value] = result.scalar()
    
    # Recent issues
    result = await db.execute(
        select(Issue)
        .where(and_(*base_filter))
        .order_by(Issue.created_at.desc())
        .limit(5)
    )
    recent_issues = result.scalars().all()
    
    return {
        "by_status": status_stats,
        "by_priority": priority_stats,
        "by_type": type_stats,
        "recent_issues": [
            {
                "id": str(issue.id),
                "title": issue.title,
                "status": issue.status.value,
                "priority": issue.priority.value,
                "created_at": issue.created_at.isoformat()
            }
            for issue in recent_issues
        ]
    }