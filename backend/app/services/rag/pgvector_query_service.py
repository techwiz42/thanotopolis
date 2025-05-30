# backend/app/services/rag/pgvector_query_service.py
from typing import List, Dict, Any, Optional
from uuid import UUID
import logging
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.rag.pgvector_storage_service import pgvector_storage_service

logger = logging.getLogger(__name__)

class PgVectorQueryService:
    def __init__(self):
        self.storage_service = pgvector_storage_service
    
    async def query_knowledge(
        self,
        db: AsyncSession,
        owner_id: UUID,
        query_text: str,
        conversation_id: Optional[UUID] = None,
        k: int = 10
    ) -> Dict[str, Any]:
        """Query knowledge base using pgvector."""
        try:
            # Build filters
            filters = {}
            if conversation_id:
                filters['conversation_id'] = conversation_id
            
            # Only search documents (not messages) by default
            filters['source_type'] = 'document'
            
            # Query similar documents
            results = await self.storage_service.query_similar(
                db=db,
                owner_id=owner_id,
                query_text=query_text,
                k=k,
                filters=filters
            )
            
            # Format for compatibility with existing code
            return {
                "documents": [r['content'] for r in results],
                "metadatas": [r['metadata'] for r in results],
                "distances": [1 - r['similarity'] for r in results]  # Convert similarity to distance
            }
            
        except Exception as e:
            logger.error(f"Error querying knowledge: {e}")
            return {
                "documents": [],
                "metadatas": [],
                "distances": []
            }

# Create singleton instance
pgvector_query_service = PgVectorQueryService()
