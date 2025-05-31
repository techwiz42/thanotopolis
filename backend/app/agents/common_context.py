from typing import Optional, Dict, List, Any
from uuid import UUID

class CommonAgentContext:
    """
    Shared context object for all agents.
    Extracted to a separate file to avoid circular imports.
    """
    
    def __init__(
        self, 
        thread_id: Optional[str] = None, 
        db: Optional[Any] = None,
        owner_id: Optional[UUID] = None
    ):
        self.thread_id = thread_id
        self.db = db
        self.owner_id = owner_id
        self.buffer_context: Optional[str] = None
        self.rag_results: Optional[Dict[str, Any]] = None
        self.message_history: List[Dict[str, str]] = []
        self.selected_agent: Optional[str] = None
        self.collaborators: List[str] = []
        self.is_agent_selection: bool = False
        self.available_agents: Dict[str, str] = {}
        
        # Fields related to prompt injection protection
        self.is_sanitized: bool = False
        self.original_message: Optional[str] = None
        self.detected_patterns: Optional[List[str]] = None
