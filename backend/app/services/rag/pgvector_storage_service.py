from typing import List, Dict, Any, Optional, Union
from uuid import UUID, uuid4
import logging
from datetime import datetime
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, func, and_, or_, Float
from sqlalchemy.dialects.postgresql import insert
from langchain_openai import OpenAIEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
import numpy as np
from pgvector.sqlalchemy import Vector

from app.models.models import DocumentEmbedding
from app.core.config import settings
from app.db.database import get_db

logger = logging.getLogger(__name__)

class PgVectorStorageService:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(PgVectorStorageService, cls).__new__(cls)
        return cls._instance
        
    def __init__(self):
        if not hasattr(self, 'initialized'):
            self._initialize_components()
            self.initialized = True

    def _initialize_components(self):
        """Initialize components."""
        logger.info("Initializing pgvector storage service...")
        
        # Initialize embeddings
        self.embeddings = OpenAIEmbeddings(
            openai_api_key=settings.OPENAI_API_KEY,
            model="text-embedding-3-small"  # Using small model with 1536 dimensions instead of large with 3072
        )
        
        # Initialize text splitter
        chunk_size = int(getattr(settings, 'RAG_CHUNK_SIZE', 500))
        chunk_overlap = int(getattr(settings, 'RAG_CHUNK_OVERLAP', 75))
        
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", " ", ""]
        )
        
        logger.info(f"Initialized pgvector storage with chunk_size={chunk_size}, chunk_overlap={chunk_overlap}")

    async def add_texts(
        self,
        db: AsyncSession,
        owner_id: Union[UUID, str],
        texts: List[str],
        metadatas: Optional[List[Dict[str, Any]]] = None,
        conversation_id: Optional[UUID] = None,
        batch_size: int = 100
    ) -> List[str]:
        """Add texts with embeddings to PostgreSQL."""
        logger.info(f"Adding {len(texts)} texts for owner={owner_id}")
        
        try:
            # Ensure owner_id is UUID
            if isinstance(owner_id, str):
                owner_id = UUID(owner_id)
            
            metadatas = metadatas or [{}] * len(texts)
            all_ids = []
            
            # Process each text
            for i, (text, metadata) in enumerate(zip(texts, metadatas)):
                # Split text into chunks
                chunks = self.text_splitter.split_text(text)
                
                # Prepare base metadata
                base_metadata = {
                    k: str(v) if not isinstance(v, (str, int, float, bool, dict, list)) else v
                    for k, v in metadata.items()
                }
                
                # Process chunks in batches
                for batch_start in range(0, len(chunks), batch_size):
                    batch_chunks = chunks[batch_start:batch_start + batch_size]
                    
                    # Get embeddings for batch
                    embeddings = await asyncio.to_thread(
                        self.embeddings.embed_documents,
                        batch_chunks
                    )
                    
                    # Create embedding records
                    for idx, (chunk, embedding) in enumerate(zip(batch_chunks, embeddings)):
                        embedding_record = DocumentEmbedding(
                            id=uuid4(),
                            owner_id=owner_id,
                            conversation_id=conversation_id,
                            content=chunk,
                            embedding=embedding,
                            source_type=base_metadata.get('source_type', 'document'),
                            source=base_metadata.get('source', base_metadata.get('filename', 'unknown')),
                            chunk_index=batch_start + idx,
                            total_chunks=len(chunks),
                            metadata=base_metadata
                        )
                        db.add(embedding_record)
                        all_ids.append(str(embedding_record.id))
                    
                    # Commit batch
                    await db.commit()
                    logger.info(f"Added batch of {len(batch_chunks)} embeddings")
            
            logger.info(f"Successfully added {len(all_ids)} embeddings")
            return all_ids
            
        except Exception as e:
            logger.error(f"Error adding texts: {e}")
            await db.rollback()
            raise

    async def query_similar(
        self,
        db: AsyncSession,
        owner_id: UUID,
        query_text: str,
        k: int = 4,
        threshold: float = 0.7,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Query similar documents using pgvector."""
        try:
            # Get query embedding
            query_embedding = await asyncio.to_thread(
                self.embeddings.embed_query,
                query_text
            )
            
            # Build base query
            query = select(
                DocumentEmbedding,
                func.cast(
                    1 - (DocumentEmbedding.embedding.cosine_distance(query_embedding)),
                    Float
                ).label('similarity')
            ).where(
                DocumentEmbedding.owner_id == owner_id
            )
            
            # Apply filters
            if filters:
                if 'conversation_id' in filters:
                    query = query.where(DocumentEmbedding.conversation_id == filters['conversation_id'])
                if 'source_type' in filters:
                    query = query.where(DocumentEmbedding.source_type == filters['source_type'])
            
            # Apply similarity threshold and order
            query = query.where(
                func.cast(
                    1 - (DocumentEmbedding.embedding.cosine_distance(query_embedding)),
                    Float
                ) > threshold
            ).order_by(
                func.cast(
                    1 - (DocumentEmbedding.embedding.cosine_distance(query_embedding)),
                    Float
                ).desc()
            ).limit(k)
            
            # Execute query
            result = await db.execute(query)
            rows = result.all()
            
            # Format results
            results = []
            for row in rows:
                embedding_record = row[0]
                similarity = row[1]
                
                results.append({
                    'id': str(embedding_record.id),
                    'content': embedding_record.content,
                    'similarity': float(similarity),
                    'metadata': {
                        **(embedding_record.additional_data or {}),
                        'source_type': embedding_record.source_type,
                        'source': embedding_record.source,
                        'chunk_index': embedding_record.chunk_index,
                        'total_chunks': embedding_record.total_chunks
                    }
                })
            
            logger.info(f"Found {len(results)} similar documents")
            return results
            
        except Exception as e:
            logger.error(f"Error querying similar documents: {e}")
            raise

    async def delete_by_owner(self, db: AsyncSession, owner_id: UUID):
        """Delete all embeddings for an owner."""
        try:
            await db.execute(
                delete(DocumentEmbedding).where(DocumentEmbedding.owner_id == owner_id)
            )
            await db.commit()
            logger.info(f"Deleted all embeddings for owner {owner_id}")
        except Exception as e:
            logger.error(f"Error deleting embeddings: {e}")
            await db.rollback()
            raise

    async def get_stats(self, db: AsyncSession) -> Dict[str, Any]:
        """Get storage statistics."""
        try:
            # Total embeddings
            total_count = await db.execute(
                select(func.count(DocumentEmbedding.id))
            )
            total = total_count.scalar()
            
            # Unique owners
            owner_count = await db.execute(
                select(func.count(func.distinct(DocumentEmbedding.owner_id)))
            )
            owners = owner_count.scalar()
            
            # By source type
            type_counts = await db.execute(
                select(
                    DocumentEmbedding.source_type,
                    func.count(DocumentEmbedding.id)
                ).group_by(DocumentEmbedding.source_type)
            )
            
            source_types = {row[0]: row[1] for row in type_counts}
            
            return {
                "total_embeddings": total,
                "unique_owners": owners,
                "by_source_type": source_types
            }
            
        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            raise

# Create singleton instance
pgvector_storage_service = PgVectorStorageService()
