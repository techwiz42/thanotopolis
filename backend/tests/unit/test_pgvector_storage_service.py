# backend/tests/unit/test_pgvector_storage_service.py
import pytest
import uuid
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from datetime import datetime
import numpy as np
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.services.rag.pgvector_storage_service import PgVectorStorageService, pgvector_storage_service
from app.models.models import DocumentEmbedding

class TestPgVectorStorageService:
    """Test suite for pgvector Storage Service."""
    
    @pytest.fixture
    def service(self):
        """Create pgvector storage service with mocked dependencies."""
        with patch('app.services.rag.pgvector_storage_service.OpenAIEmbeddings') as mock_embeddings:
            service = PgVectorStorageService()
            service.embeddings = mock_embeddings
            return service
    
    @pytest.fixture
    def mock_embeddings(self):
        """Create mock embeddings."""
        mock = Mock()
        # Return consistent embeddings for testing
        mock.embed_documents.return_value = [[0.1] * 1536, [0.2] * 1536]
        mock.embed_query.return_value = [0.15] * 1536
        return mock
    
    @pytest.fixture
    async def test_owner(self, db_session: AsyncSession, test_user):
        """Use test user as owner."""
        return test_user
        
    @pytest.fixture
    def mock_db_session(self):
        """Create a mock db session."""
        session = MagicMock()
        session.add = MagicMock()
        session.execute = AsyncMock()
        session.commit = AsyncMock()
        return session
    
    def test_initialization(self, service):
        """Test service initialization."""
        assert hasattr(service, 'embeddings')
        assert hasattr(service, 'text_splitter')
        assert service.initialized is True
    
    def test_text_splitter_configuration(self):
        """Test text splitter is configured correctly."""
        with patch('app.services.rag.pgvector_storage_service.settings') as mock_settings:
            mock_settings.RAG_CHUNK_SIZE = '1000'
            mock_settings.RAG_CHUNK_OVERLAP = '200'
            mock_settings.OPENAI_API_KEY = 'test-key'
            
            service = PgVectorStorageService()
            # Recent versions of RecursiveCharacterTextSplitter use private attributes
            assert service.text_splitter._chunk_size == 1000
            assert service.text_splitter._chunk_overlap == 200
    
    async def test_add_texts_basic(self, service, db_session: AsyncSession, test_owner, mock_embeddings):
        """Test adding texts to pgvector."""
        service.embeddings = mock_embeddings
        texts = ["First document", "Second document"]
        metadatas = [{"source": "doc1"}, {"source": "doc2"}]
        
        # Mock text splitting
        service.text_splitter.split_text = Mock(side_effect=lambda x: [x])
        
        ids = await service.add_texts(
            db=db_session,
            owner_id=test_owner.id,
            texts=texts,
            metadatas=metadatas
        )
        
        assert len(ids) == 2
        
        # Verify records in database
        result = await db_session.execute(
            select(DocumentEmbedding).where(DocumentEmbedding.owner_id == test_owner.id)
        )
        embeddings = result.scalars().all()
        
        assert len(embeddings) == 2
        assert embeddings[0].content == "First document"
        assert embeddings[1].content == "Second document"
        assert embeddings[0].source == "doc1"
        assert embeddings[1].source == "doc2"
    
    async def test_add_texts_with_chunking(self, service, db_session: AsyncSession, test_owner, mock_embeddings):
        """Test adding texts that get split into chunks."""
        service.embeddings = mock_embeddings
        long_text = "This is a very long document that will be split into multiple chunks."
        
        # Mock text splitting to return 3 chunks
        chunks = ["Chunk 1", "Chunk 2", "Chunk 3"]
        service.text_splitter.split_text = Mock(return_value=chunks)
        
        # Mock embeddings for 3 chunks
        mock_embeddings.embed_documents.return_value = [[0.1] * 1536] * 3
        
        ids = await service.add_texts(
            db=db_session,
            owner_id=test_owner.id,
            texts=[long_text],
            metadatas=[{"source": "long_doc.txt"}]
        )
        
        assert len(ids) == 3
        
        # Verify chunks in database
        result = await db_session.execute(
            select(DocumentEmbedding)
            .where(DocumentEmbedding.owner_id == test_owner.id)
            .order_by(DocumentEmbedding.chunk_index)
        )
        chunks_in_db = result.scalars().all()
        
        assert len(chunks_in_db) == 3
        for i, chunk in enumerate(chunks_in_db):
            assert chunk.content == f"Chunk {i+1}"
            assert chunk.chunk_index == i
            assert chunk.total_chunks == 3
            assert chunk.source == "long_doc.txt"
    
    async def test_add_texts_with_conversation_id(self, service, mock_db_session, test_owner, mock_embeddings):
        """Test adding texts with conversation_id."""
        service.embeddings = mock_embeddings
        conversation_id = uuid.uuid4()
        
        service.text_splitter.split_text = Mock(side_effect=lambda x: [x])
        
        # Mock the document embedding
        mock_embedding = Mock()
        mock_db_session.add.side_effect = lambda obj: setattr(mock_embedding, 'id', uuid.uuid4())
        
        ids = await service.add_texts(
            db=mock_db_session,
            owner_id=test_owner.id,
            texts=["Conversation-specific content"],
            conversation_id=conversation_id
        )
        
        # Verify db operation was called with conversation_id
        call_kwargs = mock_embeddings.embed_documents.call_args[0][0]
        assert len(call_kwargs) == 1
        assert call_kwargs[0] == "Conversation-specific content"
        
        # Check that the mock_db_session.add was called
        assert mock_db_session.add.call_count >= 1
        assert mock_db_session.commit.called
        assert len(ids) == 1  # Should have 1 ID for 1 text
    
    async def test_add_texts_batch_processing(self, service, db_session: AsyncSession, test_owner, mock_embeddings):
        """Test batch processing of embeddings."""
        service.embeddings = mock_embeddings
        
        # Create many chunks to test batching
        num_chunks = 250
        chunks = [f"Chunk {i}" for i in range(num_chunks)]
        service.text_splitter.split_text = Mock(return_value=chunks)
        
        # Mock embeddings for all chunks
        mock_embeddings.embed_documents.return_value = [[0.1] * 1536] * 100  # Max batch size
        
        ids = await service.add_texts(
            db=db_session,
            owner_id=test_owner.id,
            texts=["Large document"],
            batch_size=100
        )
        
        # Should process in 3 batches (100 + 100 + 50)
        assert mock_embeddings.embed_documents.call_count == 3
        assert len(ids) == num_chunks
    
    async def test_query_similar_basic(self, service, mock_db_session, test_owner, mock_embeddings):
        """Test querying similar documents."""
        service.embeddings = mock_embeddings
        
        # Mock the execute result
        mock_row1 = MagicMock()
        mock_row1.__getitem__.side_effect = lambda idx: [MagicMock(id=uuid.uuid4(), 
                                                                   content="Document 1", 
                                                                   source_type="document",
                                                                   source="doc1.txt",
                                                                   chunk_index=0,
                                                                   total_chunks=1,
                                                                   additional_data={}), 0.95][idx]
        mock_row2 = MagicMock()
        mock_row2.__getitem__.side_effect = lambda idx: [MagicMock(id=uuid.uuid4(), 
                                                                   content="Document 2", 
                                                                   source_type="document",
                                                                   source="doc2.txt",
                                                                   chunk_index=0,
                                                                   total_chunks=1,
                                                                   additional_data={}), 0.85][idx]
        
        mock_result = MagicMock()
        mock_result.all.return_value = [mock_row1, mock_row2]
        mock_db_session.execute.return_value = mock_result
        
        # Query similar
        results = await service.query_similar(
            db=mock_db_session,
            owner_id=test_owner.id,
            query_text="test query",
            k=3
        )
        
        # Verify results
        assert len(results) == 2
        assert results[0]['content'] == "Document 1"
        assert results[1]['content'] == "Document 2"
        assert results[0]['similarity'] > results[1]['similarity']
        assert mock_db_session.execute.called
    
    async def test_query_similar_with_filters(self, service, mock_db_session, test_owner, mock_embeddings):
        """Test querying with filters."""
        service.embeddings = mock_embeddings
        thread_id = uuid.uuid4()
        
        # Mock the execute result for filtered query
        mock_row = MagicMock()
        mock_row.__getitem__.side_effect = lambda idx: [MagicMock(id=uuid.uuid4(), 
                                                              content="Doc 1", 
                                                              source_type="document",
                                                              source="test",
                                                              chunk_index=0,
                                                              total_chunks=1,
                                                              additional_data={}), 0.95][idx]
        
        mock_result = MagicMock()
        mock_result.all.return_value = [mock_row]
        mock_db_session.execute.return_value = mock_result
        
        # Query with filters
        results = await service.query_similar(
            db=mock_db_session,
            owner_id=test_owner.id,
            query_text="test",
            filters={
                "source_type": "document",
                "conversation_id": thread_id
            }
        )
        
        # Should return our mock result
        assert len(results) == 1
        assert results[0]['content'] == "Doc 1"
        assert mock_db_session.execute.called
    
    async def test_query_similar_threshold(self, service, mock_db_session, test_owner):
        """Test similarity threshold filtering."""
        with patch.object(service.embeddings, 'embed_query', return_value=[0.5] * 1536):
            # Mock the execute result with threshold applied
            # Empty result because the threshold is high
            mock_result = MagicMock()
            mock_result.all.return_value = []
            mock_db_session.execute.return_value = mock_result
            
            # Query with high threshold
            results = await service.query_similar(
                db=mock_db_session,
                owner_id=test_owner.id,
                query_text="test",
                threshold=0.8
            )
            
            # Should return empty result due to high threshold
            assert len(results) == 0
            assert mock_db_session.execute.called
    
    async def test_delete_by_owner(self, service, mock_db_session, test_owner):
        """Test deleting all embeddings for an owner."""
        # Mock execution response for the count query after deletion
        mock_result = MagicMock()
        mock_scalar = MagicMock(return_value=0)
        mock_result.scalar = mock_scalar
        mock_db_session.execute.return_value = mock_result
        
        # Delete all
        await service.delete_by_owner(mock_db_session, test_owner.id)
        
        # Verify delete was executed
        assert mock_db_session.execute.called
        assert mock_db_session.commit.called
    
    async def test_get_stats(self, service, mock_db_session):
        """Test getting storage statistics."""
        # Mock execute results for the three queries in get_stats
        total_mock = MagicMock()
        total_mock.scalar.return_value = 5
        
        owner_mock = MagicMock()
        owner_mock.scalar.return_value = 2
        
        type_mock = MagicMock()
        type_mock.__iter__.return_value = [("document", 4), ("message", 1)]
        
        # Set up the mock to return different results for each execute call
        mock_db_session.execute.side_effect = [total_mock, owner_mock, type_mock]
        
        # Get stats
        stats = await service.get_stats(mock_db_session)
        
        # Verify results
        assert stats["total_embeddings"] == 5
        assert stats["unique_owners"] == 2
        assert stats["by_source_type"]["document"] == 4
        assert stats["by_source_type"]["message"] == 1
        assert mock_db_session.execute.call_count == 3
    
    async def test_add_texts_error_handling(self, service, mock_db_session, test_owner):
        """Test error handling in add_texts."""
        # Replace asyncio.to_thread with a function that raises an exception directly
        async def mock_to_thread(*args, **kwargs):
            raise Exception("OpenAI API error")
            
        mock_db_session.rollback = AsyncMock()
        
        with patch('asyncio.to_thread', mock_to_thread):
            with pytest.raises(Exception):
                await service.add_texts(
                    db=mock_db_session,
                    owner_id=test_owner.id,
                    texts=["Test document"]
                )
            
            # Verify rollback was called
            assert mock_db_session.rollback.called
    
    async def test_metadata_handling(self, service, mock_db_session, test_owner, mock_embeddings):
        """Test metadata is properly stored and retrieved."""
        service.embeddings = mock_embeddings
        service.text_splitter.split_text = Mock(side_effect=lambda x: [x])
        
        complex_metadata = {
            "source": "complex_doc.pdf",
            "author": "John Doe",
            "created_date": "2024-01-01",
            "tags": ["important", "reference"],
            "page_count": 42
        }
        
        # Create a fresh mock for the query_similar call
        fresh_mock_db = MagicMock()
        
        # Mock for add_texts
        mock_db_session.add = MagicMock()
        mock_db_session.commit = AsyncMock()
        
        # Mock for query_similar
        mock_row = MagicMock()
        mock_doc = MagicMock()
        mock_doc.id = uuid.uuid4()
        mock_doc.content = "Document with complex metadata"
        mock_doc.source_type = "document"
        mock_doc.source = "complex_doc.pdf"
        mock_doc.chunk_index = 0
        mock_doc.total_chunks = 1
        # Set this based on what the actual service is expecting
        mock_doc.additional_data = complex_metadata
        
        mock_row.__getitem__.side_effect = lambda idx: [mock_doc, 0.95][idx]
        
        mock_result = MagicMock()
        mock_result.all.return_value = [mock_row]
        fresh_mock_db.execute = AsyncMock(return_value=mock_result)
        
        # Add the text
        await service.add_texts(
            db=mock_db_session,
            owner_id=test_owner.id,
            texts=["Document with complex metadata"],
            metadatas=[complex_metadata]
        )
        
        # Using a fresh mock for the query to avoid side effect issues
        results = await service.query_similar(
            db=fresh_mock_db,
            owner_id=test_owner.id,
            query_text="metadata",
            k=1
        )
        
        assert len(results) == 1
        metadata = results[0]['metadata']
        assert metadata['author'] == "John Doe"
        assert metadata['tags'] == ["important", "reference"]
        assert metadata['page_count'] == 42
