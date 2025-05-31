# backend/app/api/rag.py
# Example updates to RAG API endpoints for pgvector

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
import uuid

from app.db.database import get_db
from app.auth.auth import get_current_user
from app.models.models import User
from app.services.rag.pgvector_storage_service import pgvector_storage_service
from app.services.rag.pgvector_query_service import pgvector_query_service
from app.services.rag.ingestion_service import DataIngestionManager

router = APIRouter(prefix="/api/rag", tags=["RAG"])

# Initialize ingestion manager with pgvector storage
ingestion_manager = DataIngestionManager(pgvector_storage_service)


@router.post("/documents/upload")
async def upload_document(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Upload and process a document for RAG."""
    try:
        # Pass db session to ingestion manager
        result = await ingestion_manager.ingest_document(
            db=db,
            owner_id=current_user.id,
            file=file
        )
        
        return {
            "success": True,
            "filename": result['filename'],
            "mime_type": result['mime_type'],
            "chunks_created": result['chunk_count']
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/documents/ingest-urls")
async def ingest_urls(
    urls: List[str],
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Ingest content from URLs."""
    try:
        result = await ingestion_manager.ingest_urls(
            db=db,
            owner_id=current_user.id,
            urls=urls
        )
        
        return {
            "success": True,
            "urls_processed": result['processed_urls'],
            "documents_created": result['document_count']
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/search")
async def search_knowledge(
    query: str,
    thread_id: Optional[uuid.UUID] = None,
    limit: int = 10,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Search the knowledge base."""
    try:
        results = await pgvector_query_service.query_knowledge(
            db=db,
            owner_id=current_user.id,
            query_text=query,
            thread_id=thread_id,
            k=limit
        )
        
        # Format results for API response
        formatted_results = []
        for doc, meta, dist in zip(
            results['documents'],
            results['metadatas'],
            results['distances']
        ):
            formatted_results.append({
                'content': doc,
                'metadata': meta,
                'relevance_score': 1 - dist  # Convert distance to similarity
            })
        
        return {
            "success": True,
            "query": query,
            "results": formatted_results,
            "count": len(formatted_results)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/documents")
async def clear_documents(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Clear all documents for the current user."""
    try:
        await pgvector_storage_service.delete_by_owner(
            db=db,
            owner_id=current_user.id
        )
        
        return {
            "success": True,
            "message": "All documents cleared successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_rag_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get RAG statistics for the current user."""
    try:
        # Get overall stats
        overall_stats = await pgvector_storage_service.get_stats(db)
        
        # Get user-specific count
        from sqlalchemy import select, func
        from app.models.models import DocumentEmbedding
        
        user_count_result = await db.execute(
            select(func.count(DocumentEmbedding.id))
            .where(DocumentEmbedding.owner_id == current_user.id)
        )
        user_count = user_count_result.scalar()
        
        return {
            "success": True,
            "user_documents": user_count,
            "overall_stats": overall_stats
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/threads/{thread_id}/ingest")
async def ingest_thread_history(
    thread_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Ingest conversation history from a thread."""
    try:
        # Verify thread ownership
        from sqlalchemy import select
        from app.models.models import Conversation as Thread
        
        thread_result = await db.execute(
            select(Thread).where(
                Thread.id == thread_id,
                Thread.owner_id == current_user.id
            )
        )
        thread = thread_result.scalars().first()
        
        if not thread:
            raise HTTPException(status_code=404, detail="Thread not found")
        
        # Ingest the conversation history
        await ingestion_manager.ingest_conversation_history(
            db=db,
            thread_id=thread_id
        )
        
        return {
            "success": True,
            "thread_id": str(thread_id),
            "message": "Conversation history ingested successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Update agent context preparation to use pgvector
async def prepare_agent_context_with_pgvector(
    db: AsyncSession,
    message: str,
    thread_id: Optional[str],
    owner_id: Optional[UUID]
):
    """Prepare context for agents using pgvector RAG."""
    context = {}
    
    if owner_id:
        # Query relevant documents
        rag_results = await pgvector_query_service.query_knowledge(
            db=db,
            owner_id=owner_id,
            query_text=message,
            thread_id=UUID(thread_id) if thread_id else None,
            k=10
        )
        
        # Add to context
        context['rag_results'] = rag_results
        context['rag_documents'] = rag_results['documents']
        
    return context


# Example WebSocket handler update
async def handle_message_with_pgvector(
    websocket,
    message: str,
    thread_id: str,
    user: User,
    db: AsyncSession
):
    """Handle incoming message with pgvector RAG support."""
    # Get RAG context
    rag_results = await pgvector_query_service.query_knowledge(
        db=db,
        owner_id=user.id,
        query_text=message,
        thread_id=UUID(thread_id),
        k=5
    )
    
    # Build context for agent
    context = {
        'rag_results': rag_results,
        'rag_documents': rag_results['documents'][:3]  # Top 3 most relevant
    }
    
    # Process with agent (existing code)
    # ...


# Migration endpoint (temporary, remove after migration)
@router.post("/migrate-from-chroma")
async def migrate_from_chroma(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Migrate data from ChromaDB to pgvector (admin only)."""
    if current_user.role != "super_admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    try:
        # Run migration script
        from scripts.migrate_chroma_to_pgvector import migrate_chroma_to_pgvector
        await migrate_chroma_to_pgvector()
        
        return {
            "success": True,
            "message": "Migration completed successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
