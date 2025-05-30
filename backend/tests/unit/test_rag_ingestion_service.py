# backend/tests/unit/test_rag_ingestion_service.py
import pytest
import uuid
import json
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from datetime import datetime
from io import BytesIO
from fastapi import UploadFile

from app.services.rag.ingestion_service import DataIngestionManager, ingestion_manager
from app.models.models import Conversation, Message
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

class TestDataIngestionManager:
    """Test suite for Data Ingestion Manager."""
    
    @pytest.fixture
    def mock_rag_service(self):
        """Create a mock RAG service."""
        service = Mock()
        service.add_texts = AsyncMock(return_value=["id1", "id2"])
        return service
    
    @pytest.fixture
    def ingestion_service(self, mock_rag_service):
        """Create ingestion manager with mocked dependencies."""
        # Use the class directly instead of the singleton
        return DataIngestionManager(mock_rag_service)
    
    @pytest.fixture
    async def test_conversation(self, db_session: AsyncSession, test_user):
        """Create a test conversation."""
        conversation = Conversation(
            id=uuid.uuid4(),
            tenant_id=test_user.tenant_id,
            created_by_user_id=test_user.id,
            title="Test Conversation"
        )
        db_session.add(conversation)
        await db_session.commit()
        await db_session.refresh(conversation)
        return conversation
    
    @pytest.fixture
    async def test_messages(self, db_session: AsyncSession, test_conversation):
        """Create test messages."""
        messages = []
        for i in range(5):
            metadata = {
                "participant_name": "User" if i % 2 == 0 else "Agent",
                "agent_type": "ASSISTANT" if i % 2 == 1 else None
            }
            message = Message(
                id=uuid.uuid4(),
                conversation_id=test_conversation.id,
                content=f"Test message {i}",
                created_at=datetime.utcnow(),
                additional_data=json.dumps(metadata)
            )
            if i % 2 == 1:
                message.agent_type = "ASSISTANT"
            db_session.add(message)
            messages.append(message)
        
        await db_session.commit()
        return messages
    
    async def test_ingest_conversation_history(self, ingestion_service, mock_rag_service, db_session, test_conversation, test_messages):
        """Test ingesting conversation history."""
        await ingestion_service.ingest_conversation_history(
            db=db_session,
            conversation_id=test_conversation.id,
            batch_size=2
        )
        
        # Should have called add_texts for each batch
        expected_calls = 3  # 5 messages / batch_size 2 = 3 calls
        assert mock_rag_service.add_texts.call_count == expected_calls
        
        # Check the content of the calls
        first_call = mock_rag_service.add_texts.call_args_list[0]
        assert first_call[1]['owner_id'] == test_conversation.created_by_user_id
        assert first_call[1]['conversation_id'] == test_conversation.id
        
        # Check formatted texts
        texts = first_call[1]['texts']
        assert len(texts) == 2
        assert "[User]:" in texts[0] or "[USER]:" in texts[0]
        assert "[Agent]:" in texts[1] or "[ASSISTANT]:" in texts[1]
    
    async def test_ingest_conversation_history_no_messages(self, ingestion_service, mock_rag_service, db_session, test_conversation):
        """Test ingesting empty conversation history."""
        await ingestion_service.ingest_conversation_history(
            db=db_session,
            conversation_id=test_conversation.id
        )
        
        # Should not have called add_texts
        mock_rag_service.add_texts.assert_not_called()
    
    async def test_ingest_conversation_history_conversation_not_found(self, ingestion_service, mock_rag_service, db_session):
        """Test ingesting history for non-existent conversation."""
        non_existent_id = uuid.uuid4()
        
        await ingestion_service.ingest_conversation_history(
            db=db_session,
            conversation_id=non_existent_id
        )
        
        # Should not have called add_texts
        mock_rag_service.add_texts.assert_not_called()
    
    async def test_ingest_document_pdf(self, ingestion_service, mock_rag_service, db_session):
        """Test ingesting PDF document."""
        owner_id = uuid.uuid4()
        pdf_content = b"PDF content"
        
        # Create mock upload file
        file = Mock(spec=UploadFile)
        file.filename = "test.pdf"
        file.read = AsyncMock(return_value=pdf_content)
        
        with patch('magic.from_buffer', return_value='application/pdf'):
            with patch.object(ingestion_service, '_extract_text', return_value="Extracted PDF text"):
                result = await ingestion_service.ingest_document(
                    owner_id=owner_id,
                    file=file,
                    document_type='application/pdf',
                    db=db_session
                )
        
        assert result['filename'] == 'test.pdf'
        assert result['mime_type'] == 'application/pdf'
        assert result['chunk_count'] > 0
        
        mock_rag_service.add_texts.assert_called_once()
        call_args = mock_rag_service.add_texts.call_args
        assert call_args[1]['owner_id'] == owner_id
    
    async def test_ingest_document_docx(self, ingestion_service, mock_rag_service, db_session):
        """Test ingesting DOCX document."""
        owner_id = uuid.uuid4()
        docx_content = b"DOCX content"
        
        file = Mock(spec=UploadFile)
        file.filename = "test.docx"
        file.read = AsyncMock(return_value=docx_content)
        
        mime_type = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        
        with patch('magic.from_buffer', return_value=mime_type):
            with patch.object(ingestion_service, '_extract_text', return_value="Extracted DOCX text"):
                result = await ingestion_service.ingest_document(
                    owner_id=owner_id,
                    file=file,
                    db=db_session
                )
        
        assert result['filename'] == 'test.docx'
        assert result['mime_type'] == mime_type
    
    async def test_ingest_document_text(self, ingestion_service, mock_rag_service, db_session):
        """Test ingesting text document."""
        owner_id = uuid.uuid4()
        text_content = b"Plain text content"
        
        file = Mock(spec=UploadFile)
        file.filename = "test.txt"
        file.read = AsyncMock(return_value=text_content)
        
        with patch('magic.from_buffer', return_value='text/plain'):
            result = await ingestion_service.ingest_document(
                owner_id=owner_id,
                file=file,
                db=db_session
            )
        
        assert result['filename'] == 'test.txt'
        assert result['mime_type'] == 'text/plain'
    
    async def test_ingest_urls(self, ingestion_service, mock_rag_service, db_session):
        """Test ingesting content from URLs."""
        owner_id = uuid.uuid4()
        urls = ["https://example.com/page1", "https://example.com/page2"]
        
        # Use the mock implementation from the ingestion service instead of trying to patch a real loader
        result = await ingestion_service.ingest_urls(
            db=db_session,
            owner_id=owner_id,
            urls=urls
        )
        
        assert result['processed_urls'] == urls
        assert result['document_count'] == 2
        
        # Should have called add_texts for each document
        assert mock_rag_service.add_texts.call_count == 2
    
    async def test_extract_text_pdf(self, ingestion_service):
        """Test extracting text from PDF."""
        pdf_content = b"PDF bytes"
        
        mock_reader = Mock()
        mock_page = Mock()
        mock_page.extract_text.return_value = "Page text"
        mock_reader.pages = [mock_page, mock_page]
        
        with patch('PyPDF2.PdfReader', return_value=mock_reader):
            text = await ingestion_service._extract_text(
                content=pdf_content,
                mime_type='application/pdf',
                filename='test.pdf'
            )
        
        assert "Page text\nPage text" in text
    
    async def test_extract_text_docx(self, ingestion_service):
        """Test extracting text from DOCX."""
        docx_content = b"DOCX bytes"
        
        with patch('docx2txt.process', return_value="Extracted DOCX text"):
            text = await ingestion_service._extract_text(
                content=docx_content,
                mime_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                filename='test.docx'
            )
        
        assert text == "Extracted DOCX text"
    
    async def test_extract_text_plain(self, ingestion_service):
        """Test extracting text from plain text file."""
        text_content = b"Plain text content"
        
        text = await ingestion_service._extract_text(
            content=text_content,
            mime_type='text/plain',
            filename='test.txt'
        )
        
        assert text == "Plain text content"
    
    async def test_extract_text_unsupported(self, ingestion_service):
        """Test extracting text from unsupported file type."""
        content = b"Unknown content"
        
        with pytest.raises(ValueError) as exc_info:
            await ingestion_service._extract_text(
                content=content,
                mime_type='application/unknown',
                filename='test.unknown'
            )
        
        assert "Unsupported file type" in str(exc_info.value)
    
    async def test_process_pdf_error_handling(self, ingestion_service):
        """Test PDF processing error handling."""
        pdf_content = b"Invalid PDF"
        
        with patch('PyPDF2.PdfReader', side_effect=Exception("Invalid PDF")):
            with pytest.raises(Exception) as exc_info:
                await ingestion_service._process_pdf(pdf_content)
            
            assert "Invalid PDF" in str(exc_info.value)
    
    async def test_process_docx_error_handling(self, ingestion_service):
        """Test DOCX processing error handling."""
        docx_content = b"Invalid DOCX"
        
        with patch('docx2txt.process', side_effect=Exception("Invalid DOCX")):
            with pytest.raises(Exception) as exc_info:
                await ingestion_service._process_docx(docx_content)
            
            assert "Invalid DOCX" in str(exc_info.value)
    
    async def test_text_splitting(self, ingestion_service):
        """Test text splitting functionality."""
        long_text = "This is a long text. " * 100
        
        chunks = ingestion_service.text_splitter.split_text(long_text)
        
        # Should create multiple chunks
        assert len(chunks) > 1
        
        # Each chunk should be within size limits
        for chunk in chunks:
            assert len(chunk) <= 1000 + 200  # chunk_size + overlap
    
    async def test_ingest_document_with_metadata(self, ingestion_service, mock_rag_service, db_session):
        """Test document ingestion preserves metadata."""
        owner_id = uuid.uuid4()
        
        file = Mock(spec=UploadFile)
        file.filename = "important.txt"
        file.read = AsyncMock(return_value=b"Important content")
        
        with patch('magic.from_buffer', return_value='text/plain'):
            await ingestion_service.ingest_document(
                owner_id=owner_id,
                file=file,
                db=db_session
            )
        
        # Check metadata was included
        call_args = mock_rag_service.add_texts.call_args
        metadatas = call_args[1]['metadatas']
        
        assert all('source_type' in m for m in metadatas)
        assert all(m['source_type'] == 'document' for m in metadatas)
        assert all(m['source'] == 'important.txt' for m in metadatas)
