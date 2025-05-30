# backend/app/api/conversations.py
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import selectinload, joinedload
from typing import List, Optional
from uuid import UUID
import json

from app.db.database import get_db
from app.models.models import (
    Conversation, Message, User, Participant, 
    ConversationUser, ConversationAgent, ConversationParticipant,
    ConversationStatus, MessageType
)
from app.schemas.schemas import (
    ConversationCreate, ConversationResponse, ConversationListResponse,
    MessageCreate, MessageResponse, PaginationParams, PaginatedResponse,
    ConversationAgentAdd, ConversationParticipantAdd
)
from app.auth.auth import get_current_active_user, get_tenant_from_request

router = APIRouter(prefix="/api/conversations", tags=["conversations"])

@router.post("/", response_model=ConversationResponse)
async def create_conversation(
    conversation_data: ConversationCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new conversation."""
    # Create the conversation
    conversation = Conversation(
        tenant_id=current_user.tenant_id,
        title=conversation_data.title,
        description=conversation_data.description,
        created_by_user_id=current_user.id
    )
    db.add(conversation)
    await db.flush()  # Get the conversation ID
    
    # Add the creator as a participant
    creator_participant = ConversationUser(
        conversation_id=conversation.id,
        user_id=current_user.id
    )
    db.add(creator_participant)
    
    # Add requested users
    for user_id in conversation_data.user_ids:
        if user_id != current_user.id:  # Skip if already added
            # Verify user exists and is in same tenant
            user_result = await db.execute(
                select(User).where(
                    User.id == user_id,
                    User.tenant_id == current_user.tenant_id,
                    User.is_active == True
                )
            )
            user = user_result.scalar_one_or_none()
            if user:
                conv_user = ConversationUser(
                    conversation_id=conversation.id,
                    user_id=user_id
                )
                db.add(conv_user)
    
    # Add requested agents
    for agent_type in conversation_data.agent_types:
        conv_agent = ConversationAgent(
            conversation_id=conversation.id,
            agent_type=agent_type
        )
        db.add(conv_agent)
    
    # Add requested participants
    for participant_id in conversation_data.participant_ids:
        # Verify participant exists and is in same tenant
        participant_result = await db.execute(
            select(Participant).where(
                Participant.id == participant_id,
                Participant.tenant_id == current_user.tenant_id
            )
        )
        participant = participant_result.scalar_one_or_none()
        if participant:
            conv_participant = ConversationParticipant(
                conversation_id=conversation.id,
                participant_id=participant_id
            )
            db.add(conv_participant)
    
    await db.commit()
    await db.refresh(conversation)
    
    # Load relationships for response
    return await get_conversation_with_details(conversation.id, db)

@router.get("/", response_model=PaginatedResponse)
async def list_conversations(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[ConversationStatus] = None,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """List conversations the current user has access to."""
    # Base query - user must be part of the conversation
    query = (
        select(Conversation)
        .join(ConversationUser)
        .where(
            ConversationUser.user_id == current_user.id,
            ConversationUser.is_active == True,
            Conversation.tenant_id == current_user.tenant_id
        )
    )
    
    if status:
        query = query.where(Conversation.status == status)
    
    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0
    
    # Get paginated results
    query = query.order_by(Conversation.updated_at.desc().nullsfirst(), Conversation.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    
    result = await db.execute(query)
    conversations = result.scalars().all()
    
    # Convert to response format with additional info
    items = []
    for conv in conversations:
        # Get last message
        last_msg_query = (
            select(Message)
            .where(Message.conversation_id == conv.id)
            .order_by(Message.created_at.desc())
            .limit(1)
        )
        last_msg_result = await db.execute(last_msg_query)
        last_message = last_msg_result.scalar_one_or_none()
        
        # Get counts
        participant_count_query = select(func.count()).select_from(ConversationUser).where(
            ConversationUser.conversation_id == conv.id,
            ConversationUser.is_active == True
        )
        participant_count_result = await db.execute(participant_count_query)
        participant_count = participant_count_result.scalar() or 0
        
        message_count_query = select(func.count()).select_from(Message).where(
            Message.conversation_id == conv.id
        )
        message_count_result = await db.execute(message_count_query)
        message_count = message_count_result.scalar() or 0
        
        items.append(ConversationListResponse(
            id=conv.id,
            title=conv.title,
            description=conv.description,
            status=conv.status,
            created_at=conv.created_at,
            updated_at=conv.updated_at,
            last_message=MessageResponse.model_validate(last_message) if last_message else None,
            participant_count=participant_count,
            message_count=message_count
        ))
    
    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size
    )

@router.get("/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(
    conversation_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get conversation details."""
    # Verify user has access
    access_query = select(ConversationUser).where(
        ConversationUser.conversation_id == conversation_id,
        ConversationUser.user_id == current_user.id,
        ConversationUser.is_active == True
    )
    access_result = await db.execute(access_query)
    if not access_result.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="Access denied")
    
    return await get_conversation_with_details(conversation_id, db)

@router.post("/{conversation_id}/messages", response_model=MessageResponse)
async def send_message(
    conversation_id: UUID,
    message_data: MessageCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Send a message to a conversation."""
    # Verify user has access
    access_query = select(ConversationUser).where(
        ConversationUser.conversation_id == conversation_id,
        ConversationUser.user_id == current_user.id,
        ConversationUser.is_active == True
    )
    access_result = await db.execute(access_query)
    if not access_result.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Create message
    message = Message(
        conversation_id=conversation_id,
        user_id=current_user.id,
        content=message_data.content,
        message_type=message_data.message_type,
        metadata=json.dumps(message_data.metadata) if message_data.metadata else None
    )
    db.add(message)
    
    # Update conversation timestamp
    conv_query = select(Conversation).where(Conversation.id == conversation_id)
    conv_result = await db.execute(conv_query)
    conversation = conv_result.scalar_one()
    conversation.updated_at = func.now()
    
    await db.commit()
    await db.refresh(message)
    
    # Return formatted response
    return MessageResponse(
        id=message.id,
        conversation_id=message.conversation_id,
        message_type=message.message_type,
        content=message.content,
        user_id=message.user_id,
        agent_type=message.agent_type,
        participant_id=message.participant_id,
        metadata=json.loads(message.metadata) if message.metadata else None,
        created_at=message.created_at,
        updated_at=message.updated_at,
        sender_name=f"{current_user.first_name} {current_user.last_name}".strip() or current_user.username,
        sender_type="user"
    )

@router.get("/{conversation_id}/messages", response_model=PaginatedResponse)
async def get_messages(
    conversation_id: UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get messages from a conversation."""
    # Verify user has access
    access_query = select(ConversationUser).where(
        ConversationUser.conversation_id == conversation_id,
        ConversationUser.user_id == current_user.id,
        ConversationUser.is_active == True
    )
    access_result = await db.execute(access_query)
    if not access_result.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Count total messages
    count_query = select(func.count()).select_from(Message).where(
        Message.conversation_id == conversation_id
    )
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0
    
    # Get messages with sender info
    query = (
        select(Message)
        .options(
            selectinload(Message.user),
            selectinload(Message.participant)
        )
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    
    result = await db.execute(query)
    messages = result.scalars().all()
    
    # Format messages
    items = []
    for msg in reversed(messages):  # Reverse to show oldest first
        sender_name = None
        sender_type = None
        
        if msg.user_id:
            sender_type = "user"
            if msg.user:
                sender_name = f"{msg.user.first_name} {msg.user.last_name}".strip() or msg.user.username
        elif msg.agent_type:
            sender_type = "agent"
            sender_name = msg.agent_type
        elif msg.participant_id:
            sender_type = "participant"
            if msg.participant:
                sender_name = msg.participant.name or msg.participant.identifier
        else:
            sender_type = "system"
            sender_name = "System"
        
        items.append(MessageResponse(
            id=msg.id,
            conversation_id=msg.conversation_id,
            message_type=msg.message_type,
            content=msg.content,
            user_id=msg.user_id,
            agent_type=msg.agent_type,
            participant_id=msg.participant_id,
            metadata=json.loads(msg.metadata) if msg.metadata else None,
            created_at=msg.created_at,
            updated_at=msg.updated_at,
            sender_name=sender_name,
            sender_type=sender_type
        ))
    
    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size
    )

# Helper function
async def get_conversation_with_details(conversation_id: UUID, db: AsyncSession) -> ConversationResponse:
    """Get conversation with all related data."""
    query = (
        select(Conversation)
        .options(
            selectinload(Conversation.users).selectinload(ConversationUser.user),
            selectinload(Conversation.agents),
            selectinload(Conversation.participants).selectinload(ConversationParticipant.participant)
        )
        .where(Conversation.id == conversation_id)
    )
    
    result = await db.execute(query)
    conversation = result.scalar_one_or_none()
    
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    # Get recent messages
    recent_messages_query = (
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.desc())
        .limit(10)
    )
    recent_messages_result = await db.execute(recent_messages_query)
    recent_messages = recent_messages_result.scalars().all()
    
    # Format response
    users = [cu.user for cu in conversation.users if cu.user and cu.is_active]
    agents = [
        {
            "agent_type": ca.agent_type,
            "added_at": ca.added_at,
            "is_active": ca.is_active,
            "configuration": json.loads(ca.configuration) if ca.configuration else None
        }
        for ca in conversation.agents
    ]
    participants = [
        cp.participant 
        for cp in conversation.participants 
        if cp.participant and cp.is_active
    ]
    
    return ConversationResponse(
        id=conversation.id,
        tenant_id=conversation.tenant_id,
        title=conversation.title,
        description=conversation.description,
        status=conversation.status,
        created_by_user_id=conversation.created_by_user_id,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
        users=users,
        agents=agents,
        participants=participants,
        recent_messages=list(reversed(recent_messages))  # Show oldest first
    )
