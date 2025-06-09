# backend/app/api/conversations.py
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import selectinload, joinedload
from typing import List, Optional
from uuid import UUID
import json
import uuid
import logging

from app.db.database import get_db
from app.models.models import (
    Conversation, Message, User, Participant, 
    ConversationUser, ConversationAgent, ConversationParticipant,
    ConversationStatus, MessageType
)
from app.schemas.schemas import (
    ConversationCreate, ConversationResponse, ConversationListResponse, ConversationUpdate,
    MessageCreate, MessageResponse, PaginationParams, PaginatedResponse,
    ConversationAgentAdd, ConversationParticipantAdd
)
from app.auth.auth import get_current_active_user, get_tenant_from_request

# Set up logger
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/conversations", tags=["conversations"])

async def generate_conversation_title_with_emails(
    conversation_id: UUID, 
    db: AsyncSession,
    creator_user: User
) -> str:
    """
    Generate a conversation title in format: <username> - <date & time> - <list of participant emails>
    
    Args:
        conversation_id: The UUID of the conversation
        db: Database session
        creator_user: The user who created the conversation
    
    Returns:
        A formatted title: <username> - <date & time> - <list of participant emails>
    """
    from datetime import datetime
    import pytz
    
    try:
        # Get creator username (prefer username, fallback to email)
        username = creator_user.username or creator_user.email
        
        # Get current date and time in Pacific timezone
        pacific_tz = pytz.timezone('America/Los_Angeles')
        now = datetime.now(pacific_tz)
        date_time_str = now.strftime("%b %d, %Y %I:%M %p")
        
        # Get all user participants (excluding creator to avoid duplication)
        user_emails_query = (
            select(User.email)
            .join(ConversationUser, User.id == ConversationUser.user_id)
            .where(
                ConversationUser.conversation_id == conversation_id,
                ConversationUser.is_active == True,
                User.id != creator_user.id  # Exclude creator
            )
        )
        user_emails_result = await db.execute(user_emails_query)
        user_emails = [email for email in user_emails_result.scalars().all()]
        
        # Get all email participants
        participant_emails_query = (
            select(Participant.identifier)
            .join(ConversationParticipant, Participant.id == ConversationParticipant.participant_id)
            .where(
                ConversationParticipant.conversation_id == conversation_id,
                ConversationParticipant.is_active == True,
                Participant.participant_type == "email"
            )
        )
        participant_emails_result = await db.execute(participant_emails_query)
        participant_emails = [email for email in participant_emails_result.scalars().all()]
        
        
        # Combine all participant emails (excluding creator)
        all_participant_emails = []
        seen_emails = set()
        
        # Add user emails
        for email in user_emails:
            if email and email not in seen_emails:
                all_participant_emails.append(email)
                seen_emails.add(email)
        
        # Add participant emails
        for email in participant_emails:
            if email and email not in seen_emails:
                all_participant_emails.append(email)
                seen_emails.add(email)
        
        # Format participant list - show first email and "et al." if multiple
        if not all_participant_emails:
            participant_list = "no participants"
        elif len(all_participant_emails) == 1:
            participant_list = all_participant_emails[0]
        else:
            participant_list = f"{all_participant_emails[0]} et al."
        
        # Generate final title: <username> - <participants> - <date & time>
        title = f"{username} - {participant_list} - {date_time_str}"
        
        return title
    
    except Exception as e:
        logger.error(f"Error generating conversation title with emails: {str(e)}")
        # Fallback title format with Pacific timezone
        from datetime import datetime
        import pytz
        pacific_tz = pytz.timezone('America/Los_Angeles')
        now = datetime.now(pacific_tz)
        date_time_str = now.strftime("%b %d, %Y %I:%M %p")
        username = getattr(creator_user, 'username', None) or getattr(creator_user, 'email', 'User')
        return f"{username} - New Conversation - {date_time_str}"

@router.post("/", response_model=ConversationResponse)
async def create_conversation(
    conversation_data: ConversationCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new conversation."""
    try:
        logger.info(f"Creating conversation for user {current_user.id}")
        
        # Create the conversation
        conversation = Conversation(
            tenant_id=current_user.tenant_id,
            title=conversation_data.title,
            description=conversation_data.description,
            created_by_user_id=current_user.id
        )
        db.add(conversation)
        await db.flush()  # Get the conversation ID
        
        logger.info(f"Created conversation {conversation.id}")
        
        # Add the creator as a participant
        creator_participant = ConversationUser(
            conversation_id=conversation.id,
            user_id=current_user.id,
            is_active=True
        )
        db.add(creator_participant)
        
        # Add requested users (with safe defaults)
        user_ids = getattr(conversation_data, 'user_ids', None) or []
        for user_id in user_ids:
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
                        user_id=user_id,
                        is_active=True
                    )
                    db.add(conv_user)
                    logger.info(f"Added user {user_id} to conversation {conversation.id}")
        
        # Add requested agents (with safe defaults)
        agent_types = getattr(conversation_data, 'agent_types', None) or []
        for agent_type in agent_types:
            conv_agent = ConversationAgent(
                conversation_id=conversation.id,
                agent_type=agent_type,
                is_active=True
            )
            db.add(conv_agent)
            logger.info(f"Added agent {agent_type} to conversation {conversation.id}")
        
        # Add requested participants (with safe defaults)
        participant_ids = getattr(conversation_data, 'participant_ids', None) or []
        for participant_id in participant_ids:
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
                    participant_id=participant_id,
                    is_active=True
                )
                db.add(conv_participant)
                logger.info(f"Added participant {participant_id} to conversation {conversation.id}")
        
        # Add participants by email address (create them if they don't exist)
        participant_emails = getattr(conversation_data, 'participant_emails', None) or []
        for email in participant_emails:
            if email and email.strip():
                email = email.strip()
                # Check if participant already exists
                existing_participant_result = await db.execute(
                    select(Participant).where(
                        Participant.identifier == email,
                        Participant.tenant_id == current_user.tenant_id,
                        Participant.participant_type == "email"
                    )
                )
                existing_participant = existing_participant_result.scalar_one_or_none()
                
                if not existing_participant:
                    # Create new participant
                    new_participant = Participant(
                        tenant_id=current_user.tenant_id,
                        participant_type="email",
                        identifier=email,
                        name=email.split('@')[0]  # Use part before @ as name
                    )
                    db.add(new_participant)
                    await db.flush()  # Get the ID
                    participant_to_add = new_participant
                    logger.info(f"Created new participant {email} for conversation {conversation.id}")
                else:
                    participant_to_add = existing_participant
                    logger.info(f"Using existing participant {email} for conversation {conversation.id}")
                
                # Add participant to conversation
                conv_participant = ConversationParticipant(
                    conversation_id=conversation.id,
                    participant_id=participant_to_add.id,
                    is_active=True
                )
                db.add(conv_participant)
                logger.info(f"Added email participant {email} to conversation {conversation.id}")
        
        # Generate title with participant emails if no title was provided
        if not conversation.title:
            generated_title = await generate_conversation_title_with_emails(
                conversation.id, 
                db, 
                creator_user=current_user
            )
            conversation.title = generated_title
            
        # Commit all changes
        await db.commit()
        await db.refresh(conversation)
        
        logger.info(f"Successfully saved conversation {conversation.id} to database")
        
        # Load relationships for response
        result = await get_conversation_with_details(conversation.id, db)
        return result
        
    except Exception as e:
        logger.error(f"Error creating conversation: {str(e)}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create conversation: {str(e)}"
        )

@router.get("/", response_model=List[ConversationListResponse])
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
        .join(ConversationUser, Conversation.id == ConversationUser.conversation_id)
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
        
        # Prepare the last message with proper sender type and metadata
        last_message_response = None
        if last_message:
            sender_type = "system"
            if last_message.user_id:
                sender_type = "user"
            elif last_message.agent_type:
                sender_type = "agent"
            elif last_message.participant_id:
                sender_type = "participant"
                
            metadata = last_message.message_metadata or {}
                
            last_message_response = MessageResponse(
                id=last_message.id,
                conversation_id=last_message.conversation_id,
                message_type=last_message.message_type,
                content=last_message.content,
                user_id=last_message.user_id,
                agent_type=last_message.agent_type,
                participant_id=last_message.participant_id,
                metadata=metadata,
                created_at=last_message.created_at,
                updated_at=last_message.updated_at,
                sender_name=None,
                sender_type=sender_type
            )
        
        # Use a more descriptive title for empty conversations
        if not conv.title and message_count == 0:
            conv_title = "New Conversation"
        elif not conv.title:
            conv_title = f"Conversation with {message_count} messages"
        else:
            conv_title = conv.title

        # Log conversation details to help with debugging
        logger.info(f"Conversation {conv.id}: {conv_title} - {message_count} messages")
        
        items.append(ConversationListResponse(
            id=conv.id,
            title=conv_title,
            description=conv.description,
            status=conv.status,
            created_at=conv.created_at,
            updated_at=conv.updated_at,
            last_message=last_message_response,
            participant_count=participant_count,
            message_count=message_count
        ))
    
    # Sort conversations by update time (most recent first), with a secondary sort by message count
    items.sort(key=lambda x: (-(x.updated_at.timestamp() if x.updated_at else 0), -x.message_count))
    
    return items

@router.get("/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(
    conversation_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get conversation details."""
    # Check if conversation exists
    conv_query = select(Conversation).where(Conversation.id == conversation_id)
    conv_result = await db.execute(conv_query)
    conversation = conv_result.scalar_one_or_none()
    
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
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
    
    # Process with agent if mention exists
    agent_type = None
    agent_response = None
    mention = getattr(message_data, 'mention', None)
    
    if mention:
        agent_type = mention
        agent_response = await process_conversation(conversation_id, message.id, agent_type, db)
    else:
        # Default to ASSISTANT agent if no specific mention
        agent_type = "ASSISTANT"
        agent_response = await process_conversation(conversation_id, message.id, agent_type, db)
    
    # Create agent response message
    if agent_response:
        response_agent_type, response_content = agent_response
        
        # Ensure we have a valid agent type
        if not response_agent_type:
            response_agent_type = agent_type or "ASSISTANT"
        
        # Create the message in the database
        agent_message = Message(
            conversation_id=conversation_id,
            agent_type=response_agent_type,
            content=response_content,
            message_type=MessageType.TEXT,
            # Store metadata directly in additional_data with all necessary fields
            additional_data=json.dumps({
                "agent_type": response_agent_type,
                "message_type": "agent",
                "sender_type": "agent"  # This is crucial for proper identification
            })
        )
        db.add(agent_message)
        await db.commit()
        await db.refresh(agent_message)
        
        # Return agent message instead of user message
        # Include additional metadata for proper agent styling
        agent_metadata = {
            "agent_type": response_agent_type,
            "message_type": "agent", 
            "sender_type": "agent"
        }
        
        return MessageResponse(
            id=agent_message.id,
            conversation_id=agent_message.conversation_id,
            message_type=agent_message.message_type,
            content=agent_message.content,
            user_id=None,
            agent_type=response_agent_type,  # Use the response_agent_type directly instead of the message field
            participant_id=None,
            metadata=agent_metadata,
            created_at=agent_message.created_at,
            updated_at=agent_message.updated_at,
            sender_name=response_agent_type,
            sender_type="agent"
        )
    
    # Return formatted response (fallback if no agent response)
    return MessageResponse(
        id=message.id,
        conversation_id=message.conversation_id,
        message_type=message.message_type,
        content=message.content,
        user_id=message.user_id,
        agent_type=message.agent_type,
        participant_id=message.participant_id,
        metadata=message.message_metadata,
        created_at=message.created_at,
        updated_at=message.updated_at,
        sender_name=f"{current_user.first_name} {current_user.last_name}".strip() or current_user.username,
        sender_type="user"
    )

@router.get("/{conversation_id}/messages", response_model=List[MessageResponse])
async def get_messages(
    conversation_id: UUID,
    skip: int = Query(0, ge=0),
    limit: Optional[int] = Query(None, ge=1),
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
    
    # Get messages with sender info
    query = (
        select(Message)
        .options(
            selectinload(Message.user),
            selectinload(Message.participant)
        )
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at)  # Order by creation time (oldest first)
        .offset(skip)
    )
    
    # Only apply limit if one is specified
    if limit is not None:
        query = query.limit(limit)
    
    result = await db.execute(query)
    messages = result.scalars().all()
    
    # Format messages
    items = []
    for msg in messages:
        sender_name = None
        sender_type = None
        
        # Get existing metadata first to check for agent messages in metadata
        existing_metadata = msg.message_metadata or {}
        
        # Check for agent message via agent_type field or metadata
        if msg.agent_type or (isinstance(existing_metadata, dict) and 
                             (existing_metadata.get("sender_type") == "agent" or 
                              existing_metadata.get("agent_type"))):
            # This is an agent message - ensure all agent fields are set
            sender_type = "agent"
            # Get agent_type from message field or metadata
            agent_type = msg.agent_type or existing_metadata.get("agent_type", "ASSISTANT")
            sender_name = agent_type
            
            # Always include required agent metadata fields
            metadata_dict = {
                "agent_type": agent_type,
                "message_type": "agent",
                "sender_type": "agent"
            }
            
            # Merge with our required fields, ensuring our fields take precedence
            if isinstance(existing_metadata, dict):
                merged_metadata = existing_metadata.copy()
                merged_metadata.update(metadata_dict)
            else:
                merged_metadata = metadata_dict
                
            # Store updated metadata in additional_data
            msg.additional_data = json.dumps(merged_metadata)
        elif msg.user_id:
            sender_type = "user"
            if msg.user:
                sender_name = f"{msg.user.first_name} {msg.user.last_name}".strip() or msg.user.username
                
            # Ensure user messages have sender_type in metadata
            existing_metadata = msg.message_metadata or {}
            if isinstance(existing_metadata, dict):
                if "sender_type" not in existing_metadata:
                    existing_metadata["sender_type"] = "user"
                    msg.additional_data = json.dumps(existing_metadata)
            else:
                msg.additional_data = json.dumps({"sender_type": "user"})
        elif msg.participant_id:
            sender_type = "participant"
            if msg.participant:
                sender_name = msg.participant.name or msg.participant.identifier
                
            # Ensure participant messages have sender_type in metadata
            existing_metadata = msg.message_metadata or {}
            if isinstance(existing_metadata, dict):
                if "sender_type" not in existing_metadata:
                    existing_metadata["sender_type"] = "participant"
                    msg.additional_data = json.dumps(existing_metadata)
            else:
                msg.additional_data = json.dumps({"sender_type": "participant"})
        else:
            sender_type = "system"
            sender_name = "System"
            
            # Ensure system messages have sender_type in metadata
            existing_metadata = msg.message_metadata or {}
            if isinstance(existing_metadata, dict):
                if "sender_type" not in existing_metadata:
                    existing_metadata["sender_type"] = "system"
                    msg.additional_data = json.dumps(existing_metadata)
            else:
                msg.additional_data = json.dumps({"sender_type": "system"})
        
        items.append(MessageResponse(
            id=msg.id,
            conversation_id=msg.conversation_id,
            message_type=msg.message_type,
            content=msg.content,
            user_id=msg.user_id,
            agent_type=msg.agent_type,
            participant_id=msg.participant_id,
            metadata=msg.message_metadata,
            created_at=msg.created_at,
            updated_at=msg.updated_at,
            sender_name=sender_name,
            sender_type=sender_type
        ))
    
    return items

# Process conversation - implementation for handling agent requests
async def process_conversation(conversation_id: UUID, message_id: UUID, agent_type: str, db: AsyncSession):
    """
    Process a conversation with an agent.
    This is a placeholder implementation that returns predefined responses based on agent type.
    In a real implementation, this would integrate with actual agent services.
    """
    # Simple mock implementation for tests
    if agent_type == "WEB_SEARCH":
        return (agent_type, "Search results...")
    elif agent_type == "MODERATOR":
        return (agent_type, "Content moderated successfully.")
    else:
        return ("ASSISTANT", "This is the agent response")

@router.patch("/{conversation_id}", response_model=ConversationResponse)
async def update_conversation(
    conversation_id: UUID,
    update_data: ConversationUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Update conversation details."""
    # Verify user has access
    access_query = select(ConversationUser).where(
        ConversationUser.conversation_id == conversation_id,
        ConversationUser.user_id == current_user.id,
        ConversationUser.is_active == True
    )
    access_result = await db.execute(access_query)
    if not access_result.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Get conversation
    query = select(Conversation).where(Conversation.id == conversation_id)
    result = await db.execute(query)
    conversation = result.scalar_one_or_none()
    
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    # Update fields
    if update_data.title is not None:
        conversation.title = update_data.title
    if update_data.description is not None:
        conversation.description = update_data.description
    if update_data.status is not None:
        conversation.status = update_data.status
    
    conversation.updated_at = func.now()
    await db.commit()
    await db.refresh(conversation)
    
    return await get_conversation_with_details(conversation_id, db)

@router.delete("/{conversation_id}", response_model=dict)
async def delete_conversation(
    conversation_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete a conversation."""
    # Verify user has access
    access_query = select(ConversationUser).where(
        ConversationUser.conversation_id == conversation_id,
        ConversationUser.user_id == current_user.id,
        ConversationUser.is_active == True
    )
    access_result = await db.execute(access_query)
    if not access_result.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Get conversation
    query = select(Conversation).where(Conversation.id == conversation_id)
    result = await db.execute(query)
    conversation = result.scalar_one_or_none()
    
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    # Delete the conversation
    await db.delete(conversation)
    await db.commit()
    
    return {"status": "success", "message": "Conversation deleted successfully"}

@router.get("/{conversation_id}/messages/{message_id}", response_model=MessageResponse)
async def get_message(
    conversation_id: UUID,
    message_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get a specific message by ID."""
    # Verify user has access to the conversation
    access_query = select(ConversationUser).where(
        ConversationUser.conversation_id == conversation_id,
        ConversationUser.user_id == current_user.id,
        ConversationUser.is_active == True
    )
    access_result = await db.execute(access_query)
    if not access_result.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Get the message
    query = (
        select(Message)
        .options(
            selectinload(Message.user),
            selectinload(Message.participant)
        )
        .where(
            Message.id == message_id,
            Message.conversation_id == conversation_id
        )
    )
    result = await db.execute(query)
    message = result.scalar_one_or_none()
    
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")
    
    # Format sender info
    sender_name = None
    sender_type = None
    
    # Get existing metadata to check for agent message signals
    existing_metadata = message.message_metadata or {}
    
    # Check for agent message via agent_type field or metadata
    if message.agent_type or (isinstance(existing_metadata, dict) and 
                             (existing_metadata.get("sender_type") == "agent" or 
                              existing_metadata.get("agent_type"))):
        # This is an agent message - ensure all agent fields are set
        sender_type = "agent"
        # Get agent_type from message field or metadata
        agent_type = message.agent_type or existing_metadata.get("agent_type", "ASSISTANT")
        sender_name = agent_type
        
        # Ensure agent messages have proper metadata
        if not message.message_metadata:
            message.message_metadata = {
                "agent_type": agent_type,
                "message_type": "agent",
                "sender_type": "agent"
            }
        elif isinstance(message.message_metadata, dict):
            # Ensure all required agent fields are set
            message.message_metadata.update({
                "agent_type": agent_type,
                "message_type": "agent",
                "sender_type": "agent"
            })
    elif message.user_id:
        sender_type = "user"
        if message.user:
            sender_name = f"{message.user.first_name} {message.user.last_name}".strip() or message.user.username
        # Add user-specific metadata if needed
        if not message.message_metadata:
            message.message_metadata = {
                "sender_type": "user"
            }
        elif isinstance(message.message_metadata, dict) and "sender_type" not in message.message_metadata:
            message.message_metadata["sender_type"] = "user"
    elif message.participant_id:
        sender_type = "participant"
        if message.participant:
            sender_name = message.participant.name or message.participant.identifier
    else:
        sender_type = "system"
        sender_name = "System"
        
        # Ensure system messages have sender_type in metadata
        if not message.message_metadata:
            message.message_metadata = {"sender_type": "system"}
        elif isinstance(message.message_metadata, dict) and "sender_type" not in message.message_metadata:
            message.message_metadata["sender_type"] = "system"
    
    # Construct the response - make sure agent_type is properly set for agent messages
    if sender_type == "agent":
        agent_type = message.agent_type or message.message_metadata.get("agent_type", "ASSISTANT")
    else:
        agent_type = message.agent_type
        
    return MessageResponse(
        id=message.id,
        conversation_id=message.conversation_id,
        message_type=message.message_type,
        content=message.content,
        user_id=message.user_id,
        agent_type=agent_type,
        participant_id=message.participant_id,
        metadata=message.message_metadata,
        created_at=message.created_at,
        updated_at=message.updated_at,
        sender_name=sender_name,
        sender_type=sender_type
    )

@router.delete("/{conversation_id}/messages/{message_id}", response_model=dict)
async def delete_message(
    conversation_id: UUID,
    message_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete a specific message."""
    # Verify user has access to the conversation
    access_query = select(ConversationUser).where(
        ConversationUser.conversation_id == conversation_id,
        ConversationUser.user_id == current_user.id,
        ConversationUser.is_active == True
    )
    access_result = await db.execute(access_query)
    if not access_result.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Get the message
    query = select(Message).where(
        Message.id == message_id,
        Message.conversation_id == conversation_id
    )
    result = await db.execute(query)
    message = result.scalar_one_or_none()
    
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")
    
    # Delete the message
    await db.delete(message)
    await db.commit()
    
    return {"status": "success", "message": "Message deleted successfully"}

@router.delete("/{conversation_id}/messages", response_model=dict)
async def clear_messages(
    conversation_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Clear all messages in a conversation."""
    # Verify user has access to the conversation
    access_query = select(ConversationUser).where(
        ConversationUser.conversation_id == conversation_id,
        ConversationUser.user_id == current_user.id,
        ConversationUser.is_active == True
    )
    access_result = await db.execute(access_query)
    if not access_result.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Delete all messages
    delete_query = Message.__table__.delete().where(Message.conversation_id == conversation_id)
    await db.execute(delete_query)
    await db.commit()
    
    return {"status": "success", "message": "All messages cleared successfully"}

@router.post("/{conversation_id}/agents")
async def add_agent(
    conversation_id: UUID,
    agent_data: ConversationAgentAdd,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Add an agent to a conversation."""
    # Verify user has access to the conversation
    access_query = select(ConversationUser).where(
        ConversationUser.conversation_id == conversation_id,
        ConversationUser.user_id == current_user.id,
        ConversationUser.is_active == True
    )
    access_result = await db.execute(access_query)
    if not access_result.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Check if agent already exists in conversation
    agent_query = select(ConversationAgent).where(
        ConversationAgent.conversation_id == conversation_id,
        ConversationAgent.agent_type == agent_data.agent_type
    )
    agent_result = await db.execute(agent_query)
    existing_agent = agent_result.scalar_one_or_none()
    
    if existing_agent:
        # Update existing agent
        existing_agent.is_active = True
        if agent_data.configuration:
            existing_agent.configuration = json.dumps(agent_data.configuration)
        agent_id = existing_agent.id
    else:
        # Create new agent
        agent = ConversationAgent(
            id=uuid.uuid4(),
            conversation_id=conversation_id,
            agent_type=agent_data.agent_type,
            configuration=json.dumps(agent_data.configuration) if agent_data.configuration else None
        )
        db.add(agent)
        agent_id = agent.id
    
    await db.commit()
    
    return {
        "id": str(agent_id),
        "agent_type": agent_data.agent_type,
        "configuration": agent_data.configuration
    }

@router.get("/{conversation_id}/agents", response_model=List[dict])
async def get_agents(
    conversation_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all agents in a conversation."""
    # Verify user has access to the conversation
    access_query = select(ConversationUser).where(
        ConversationUser.conversation_id == conversation_id,
        ConversationUser.user_id == current_user.id,
        ConversationUser.is_active == True
    )
    access_result = await db.execute(access_query)
    if not access_result.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Get all agents
    query = select(ConversationAgent).where(
        ConversationAgent.conversation_id == conversation_id,
        ConversationAgent.is_active == True
    )
    result = await db.execute(query)
    agents = result.scalars().all()
    
    return [
        {
            "id": agent.id,
            "agent_type": agent.agent_type,
            "configuration": json.loads(agent.configuration) if agent.configuration else None,
            "added_at": agent.added_at
        }
        for agent in agents
    ]

@router.delete("/{conversation_id}/agents/{agent_id}", response_model=dict)
async def remove_agent(
    conversation_id: UUID,
    agent_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Remove an agent from a conversation."""
    # Verify user has access to the conversation
    access_query = select(ConversationUser).where(
        ConversationUser.conversation_id == conversation_id,
        ConversationUser.user_id == current_user.id,
        ConversationUser.is_active == True
    )
    access_result = await db.execute(access_query)
    if not access_result.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Get the agent
    query = select(ConversationAgent).where(
        ConversationAgent.id == agent_id,
        ConversationAgent.conversation_id == conversation_id
    )
    result = await db.execute(query)
    agent = result.scalar_one_or_none()
    
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    # Delete the agent
    await db.delete(agent)
    await db.commit()
    
    return {"status": "success", "message": "Agent removed successfully"}

@router.get("/search", response_model=List[ConversationListResponse])
async def search_conversations(
    q: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Search for conversations by query."""
    # Base query - user must be part of the conversation
    query = (
        select(Conversation)
        .join(ConversationUser, Conversation.id == ConversationUser.conversation_id)
        .where(
            ConversationUser.user_id == current_user.id,
            ConversationUser.is_active == True,
            Conversation.tenant_id == current_user.tenant_id
        )
    )
    
    # Add search filter if q is provided
    if q:
        query = query.where(
            or_(
                Conversation.title.ilike(f"%{q}%"),
                Conversation.description.ilike(f"%{q}%")
            )
        )
    
    result = await db.execute(query)
    conversations = result.scalars().all()
    
    # Convert to response format - we need to manually query for counts because 
    # we can't rely on ORM relationships in this case
    result_list = []
    for conv in conversations:
        # Get message count 
        message_count_query = select(func.count()).select_from(Message).where(
            Message.conversation_id == conv.id
        )
        message_count_result = await db.execute(message_count_query)
        message_count = message_count_result.scalar() or 0
        
        # Get participant count
        participant_count_query = select(func.count()).select_from(ConversationUser).where(
            ConversationUser.conversation_id == conv.id,
            ConversationUser.is_active == True
        )
        participant_count_result = await db.execute(participant_count_query)
        participant_count = participant_count_result.scalar() or 0
        
        result_list.append(
            ConversationListResponse(
                id=conv.id,
                title=conv.title,
                description=conv.description,
                status=conv.status,
                created_at=conv.created_at,
                updated_at=conv.updated_at,
                participant_count=participant_count,
                message_count=message_count,
                last_message=None  # We'll handle this separately
            )
        )
    
    # Sort conversations by update time (most recent first), with a secondary sort by message count
    result_list.sort(key=lambda x: (-(x.updated_at.timestamp() if x.updated_at else 0), -x.message_count))
    
    return result_list

@router.get("/{conversation_id}/export", response_model=dict)
async def export_conversation(
    conversation_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Export conversation history."""
    # Verify user has access
    access_query = select(ConversationUser).where(
        ConversationUser.conversation_id == conversation_id,
        ConversationUser.user_id == current_user.id,
        ConversationUser.is_active == True
    )
    access_result = await db.execute(access_query)
    if not access_result.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Get conversation
    query = select(Conversation).where(Conversation.id == conversation_id)
    result = await db.execute(query)
    conversation = result.scalar_one_or_none()
    
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    # Get all messages
    messages_query = (
        select(Message)
        .options(
            selectinload(Message.user),
            selectinload(Message.participant)
        )
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at)
    )
    messages_result = await db.execute(messages_query)
    messages = messages_result.scalars().all()
    
    # Format messages
    formatted_messages = []
    for message in messages:
        sender_name = None
        sender_type = None
        
        # Get metadata from additional_data
        metadata = {}
        if message.additional_data:
            if isinstance(message.additional_data, str):
                try:
                    metadata = json.loads(message.additional_data)
                except:
                    metadata = {}
        
        if message.user_id:
            sender_type = "user"
            if message.user:
                sender_name = f"{message.user.first_name} {message.user.last_name}".strip() or message.user.username
            # Ensure metadata includes sender_type
            if "sender_type" not in metadata:
                metadata["sender_type"] = "user"
        elif message.agent_type:
            sender_type = "agent"
            sender_name = message.agent_type
            # Ensure metadata includes sender_type and agent_type
            if "sender_type" not in metadata:
                metadata["sender_type"] = "agent"
            if "agent_type" not in metadata:
                metadata["agent_type"] = message.agent_type
        elif message.participant_id:
            sender_type = "participant"
            if message.participant:
                sender_name = message.participant.name or message.participant.identifier
            # Ensure metadata includes sender_type
            if "sender_type" not in metadata:
                metadata["sender_type"] = "participant"
        else:
            sender_type = "system"
            sender_name = "System"
            # Ensure metadata includes sender_type
            if "sender_type" not in metadata:
                metadata["sender_type"] = "system"
        
        formatted_messages.append({
            "id": str(message.id),
            "content": message.content,
            "sender_name": sender_name,
            "sender_type": sender_type,
            "created_at": message.created_at.isoformat(),
            "metadata": metadata
        })
    
    return {
        "thread_id": str(conversation.id),
        "title": conversation.title,
        "description": conversation.description,
        "created_at": conversation.created_at.isoformat(),
        "messages": formatted_messages
    }

@router.get("/{conversation_id}/stats", response_model=dict)
async def get_conversation_stats(
    conversation_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get conversation statistics."""
    # Verify user has access
    access_query = select(ConversationUser).where(
        ConversationUser.conversation_id == conversation_id,
        ConversationUser.user_id == current_user.id,
        ConversationUser.is_active == True
    )
    access_result = await db.execute(access_query)
    if not access_result.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Get conversation
    query = select(Conversation).where(Conversation.id == conversation_id)
    result = await db.execute(query)
    conversation = result.scalar_one_or_none()
    
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    # Count messages
    message_count_query = select(func.count()).select_from(Message).where(
        Message.conversation_id == conversation_id
    )
    message_count_result = await db.execute(message_count_query)
    message_count = message_count_result.scalar() or 0
    
    # Get last message timestamp
    last_message_query = (
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.desc())
        .limit(1)
    )
    last_message_result = await db.execute(last_message_query)
    last_message = last_message_result.scalar_one_or_none()
    last_message_at = last_message.created_at if last_message else None
    
    # Get unique agent types used
    agents_query = (
        select(Message.agent_type)
        .where(
            Message.conversation_id == conversation_id,
            Message.agent_type.isnot(None)
        )
        .group_by(Message.agent_type)
    )
    agents_result = await db.execute(agents_query)
    agents_used = [a for a in agents_result.scalars().all() if a]
    
    return {
        "message_count": message_count,
        "created_at": conversation.created_at,
        "last_message_at": last_message_at,
        "agents_used": agents_used,
        "status": conversation.status,
        "title": conversation.title
    }

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
    
    # Get all messages in chronological order
    messages_query = (
        select(Message)
        .options(
            selectinload(Message.user),
            selectinload(Message.participant)
        )
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at)  # Order by creation time (oldest first)
    )
    messages_result = await db.execute(messages_query)
    messages = messages_result.scalars().all()
    
    # Format each message with sender info
    formatted_messages = []
    for msg in messages:
        sender_name = None
        sender_type = None
        
        # Get existing metadata first to check for agent messages in metadata
        existing_metadata = msg.message_metadata or {}
        
        # Check for agent message via agent_type field or metadata
        if msg.agent_type or (isinstance(existing_metadata, dict) and 
                             (existing_metadata.get("sender_type") == "agent" or 
                              existing_metadata.get("agent_type"))):
            # This is an agent message - ensure all agent fields are set
            sender_type = "agent"
            # Get agent_type from message field or metadata
            agent_type = msg.agent_type or existing_metadata.get("agent_type", "ASSISTANT")
            sender_name = agent_type
            
            # Always include required agent metadata fields
            metadata_dict = {
                "agent_type": agent_type,
                "message_type": "agent",
                "sender_type": "agent"
            }
            
            # Merge with our required fields, ensuring our fields take precedence
            if isinstance(existing_metadata, dict):
                merged_metadata = existing_metadata.copy()
                merged_metadata.update(metadata_dict)
            else:
                merged_metadata = metadata_dict
                
            # Store updated metadata in additional_data
            msg.additional_data = json.dumps(merged_metadata)
        elif msg.user_id:
            sender_type = "user"
            if msg.user:
                sender_name = f"{msg.user.first_name} {msg.user.last_name}".strip() or msg.user.username
                
            # Ensure user messages have sender_type in metadata
            existing_metadata = msg.message_metadata or {}
            if isinstance(existing_metadata, dict):
                if "sender_type" not in existing_metadata:
                    existing_metadata["sender_type"] = "user"
                    msg.additional_data = json.dumps(existing_metadata)
            else:
                msg.additional_data = json.dumps({"sender_type": "user"})
        elif msg.participant_id:
            sender_type = "participant"
            if msg.participant:
                sender_name = msg.participant.name or msg.participant.identifier
                
            # Ensure participant messages have sender_type in metadata
            existing_metadata = msg.message_metadata or {}
            if isinstance(existing_metadata, dict):
                if "sender_type" not in existing_metadata:
                    existing_metadata["sender_type"] = "participant"
                    msg.additional_data = json.dumps(existing_metadata)
            else:
                msg.additional_data = json.dumps({"sender_type": "participant"})
        else:
            sender_type = "system"
            sender_name = "System"
        
        # For agent messages, make sure we use the correct agent_type
        if sender_type == "agent":
            response_agent_type = msg.agent_type or existing_metadata.get("agent_type", "ASSISTANT")
        else:
            response_agent_type = msg.agent_type
            
        formatted_messages.append(MessageResponse(
            id=msg.id,
            conversation_id=msg.conversation_id,
            message_type=msg.message_type,
            content=msg.content,
            user_id=msg.user_id,
            agent_type=response_agent_type,
            participant_id=msg.participant_id,
            metadata=msg.message_metadata,
            created_at=msg.created_at,
            updated_at=msg.updated_at,
            sender_name=sender_name,
            sender_type=sender_type
        ))
    
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
        recent_messages=formatted_messages,  # All messages in chronological order
        owner_id=conversation.created_by_user_id  # For backward compatibility
    )
