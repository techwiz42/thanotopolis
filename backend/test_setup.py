# backend/test_setup.py
"""
Test script to verify the conversation system setup.
Run with: python -m asyncio test_setup.py
"""
import asyncio
from sqlalchemy import select
from app.db.database import get_db_context, init_db, check_db_connection
from app.models.models import (
    Tenant, User, Conversation, Message, Participant,
    ConversationUser, ConversationAgent, ParticipantType, MessageType
)
from app.auth.auth import AuthService
import uuid


async def test_database_setup():
    """Test the database setup and create some sample data."""
    print("Testing database connection...")
    if not await check_db_connection():
        print("❌ Database connection failed!")
        return
    print("✅ Database connection successful!")
    
    print("\nInitializing database tables...")
    await init_db()
    print("✅ Database tables created!")
    
    async with get_db_context() as db:
        # Create a test tenant
        print("\nCreating test tenant...")
        tenant = Tenant(
            name="Test Organization",
            subdomain="test",
            access_code="TEST123"
        )
        db.add(tenant)
        await db.commit()
        await db.refresh(tenant)
        print(f"✅ Created tenant: {tenant.name} (subdomain: {tenant.subdomain})")
        
        # Create a test user
        print("\nCreating test user...")
        user = User(
            email="test@example.com",
            username="testuser",
            hashed_password=AuthService.get_password_hash("password123"),
            first_name="Test",
            last_name="User",
            tenant_id=tenant.id,
            is_active=True,
            is_verified=True
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        print(f"✅ Created user: {user.email}")
        
        # Create a participant
        print("\nCreating test participant...")
        participant = Participant(
            tenant_id=tenant.id,
            participant_type=ParticipantType.PHONE,
            identifier="+1234567890",
            name="John Doe"
        )
        db.add(participant)
        await db.commit()
        await db.refresh(participant)
        print(f"✅ Created participant: {participant.name} ({participant.identifier})")
        
        # Create a conversation
        print("\nCreating test conversation...")
        conversation = Conversation(
            tenant_id=tenant.id,
            title="Test Conversation",
            description="A test conversation with user, agent, and participant",
            created_by_user_id=user.id
        )
        db.add(conversation)
        await db.commit()
        await db.refresh(conversation)
        print(f"✅ Created conversation: {conversation.title}")
        
        # Add participants to conversation
        print("\nAdding participants to conversation...")
        
        # Add user
        conv_user = ConversationUser(
            conversation_id=conversation.id,
            user_id=user.id
        )
        db.add(conv_user)
        
        # Add agent
        conv_agent = ConversationAgent(
            conversation_id=conversation.id,
            agent_type="MODERATOR",
            configuration='{"temperature": 0.7}'
        )
        db.add(conv_agent)
        
        # Add participant
        conv_participant = ConversationParticipant(
            conversation_id=conversation.id,
            participant_id=participant.id
        )
        db.add(conv_participant)
        
        await db.commit()
        print("✅ Added user, agent, and participant to conversation")
        
        # Create some messages
        print("\nCreating test messages...")
        
        # User message
        msg1 = Message(
            conversation_id=conversation.id,
            user_id=user.id,
            content="Hello, I need help with my account.",
            message_type=MessageType.TEXT
        )
        db.add(msg1)
        
        # Agent message
        msg2 = Message(
            conversation_id=conversation.id,
            agent_type="MODERATOR",
            content="Hello! I'd be happy to help you with your account. What specific issue are you experiencing?",
            message_type=MessageType.TEXT
        )
        db.add(msg2)
        
        # Participant join message
        msg3 = Message(
            conversation_id=conversation.id,
            content=f"{participant.name} joined the conversation",
            message_type=MessageType.PARTICIPANT_JOIN,
            metadata=f'{{"participant_id": "{participant.id}"}}'
        )
        db.add(msg3)
        
        # Participant message
        msg4 = Message(
            conversation_id=conversation.id,
            participant_id=participant.id,
            content="I'm also having similar issues.",
            message_type=MessageType.TEXT
        )
        db.add(msg4)
        
        await db.commit()
        print("✅ Created 4 test messages")
        
        # Query and display the conversation
        print("\n" + "="*50)
        print("VERIFYING DATA")
        print("="*50)
        
        # Get conversation with messages
        conv_query = (
            select(Conversation)
            .where(Conversation.id == conversation.id)
        )
        result = await db.execute(conv_query)
        conv = result.scalar_one()
        
        print(f"\nConversation: {conv.title}")
        print(f"Status: {conv.status}")
        print(f"Created: {conv.created_at}")
        
        # Get messages
        msg_query = (
            select(Message)
            .where(Message.conversation_id == conversation.id)
            .order_by(Message.created_at)
        )
        msg_result = await db.execute(msg_query)
        messages = msg_result.scalars().all()
        
        print(f"\nMessages ({len(messages)}):")
        for msg in messages:
            sender = "Unknown"
            if msg.user_id:
                sender = f"User ({user.username})"
            elif msg.agent_type:
                sender = f"Agent ({msg.agent_type})"
            elif msg.participant_id:
                sender = f"Participant ({participant.name})"
            else:
                sender = "System"
            
            print(f"  [{sender}] {msg.content[:50]}...")
        
        print("\n✅ All tests completed successfully!")
        print("\nYou can now:")
        print("1. Start the API server: uvicorn app.main:app --reload")
        print("2. View API docs at: http://localhost:8000/docs")
        print("3. Login with: test@example.com / password123")


if __name__ == "__main__":
    asyncio.run(test_database_setup())
