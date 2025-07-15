from sqlalchemy import Column, String, Text, ForeignKey, DateTime, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime
import enum

from app.models.models import Base


class IssueStatus(str, enum.Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CLOSED = "closed"


class IssuePriority(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class IssueType(str, enum.Enum):
    BUG = "bug"
    FEATURE_REQUEST = "feature_request"
    IMPROVEMENT = "improvement"
    QUESTION = "question"
    OTHER = "other"


class Issue(Base):
    __tablename__ = "issues"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=True)
    
    # Basic issue information
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    type = Column(SQLEnum(IssueType), default=IssueType.BUG, nullable=False)
    status = Column(SQLEnum(IssueStatus), default=IssueStatus.OPEN, nullable=False)
    priority = Column(SQLEnum(IssuePriority), default=IssuePriority.MEDIUM, nullable=False)
    
    # Reporter information (can be anonymous)
    reporter_email = Column(String(255), nullable=True)
    reporter_name = Column(String(255), nullable=True)
    reporter_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    
    # Assignment and resolution
    assigned_to_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    resolved_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    resolution = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    resolved_at = Column(DateTime, nullable=True)
    
    # Relationships
    tenant = relationship("Tenant", backref="issues")
    reporter_user = relationship("User", foreign_keys=[reporter_user_id], backref="reported_issues")
    assigned_to = relationship("User", foreign_keys=[assigned_to_id], backref="assigned_issues")
    resolved_by = relationship("User", foreign_keys=[resolved_by_id], backref="resolved_issues")
    comments = relationship("IssueComment", back_populates="issue", cascade="all, delete-orphan", order_by="IssueComment.created_at")


class IssueComment(Base):
    __tablename__ = "issue_comments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    issue_id = Column(UUID(as_uuid=True), ForeignKey("issues.id"), nullable=False)
    
    # Comment content
    content = Column(Text, nullable=False)
    
    # Commenter information
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    author_name = Column(String(255), nullable=True)  # For anonymous comments
    author_email = Column(String(255), nullable=True)  # For anonymous comments
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    issue = relationship("Issue", back_populates="comments")
    user = relationship("User", backref="issue_comments")