from typing import Dict, List, Optional, Any, Union
import logging
import traceback
from uuid import UUID

from agents import Agent

logger = logging.getLogger(__name__)

class AgentInterface:
    """
    Unified interface for accessing agents across the application.
    Acts as a centralized access point for all agent operations.
    """
    
    def __init__(self):
        # Storage for base agent templates (copied for conversation instances)
        self.base_agents: Dict[str, Agent] = {}
        
        # Storage for conversation-specific agent instances
        # Format: {thread_id: {agent_type: agent_instance}}
        self.conversation_agents: Dict[str, Dict[str, Agent]] = {}
        
        # Agent descriptions
        self.agent_descriptions: Dict[str, str] = {}
        
    def register_base_agent(self, agent_type: str, agent: Agent) -> None:
        """
        Register a base agent template.
        
        Args:
            agent_type: The type identifier for the agent (e.g., "MODERATOR")
            agent: The agent instance to register as a template
        """
        agent_type = agent_type.upper()  # Normalize type to uppercase
        self.base_agents[agent_type] = agent
        
        # Store description if available
        if hasattr(agent, 'description') and agent.description:
            # Store the string description, not the attribute reference
            self.agent_descriptions[agent_type] = str(agent.description)
        else:
            self.agent_descriptions[agent_type] = f"{agent_type} agent"
            
        logger.info(f"Registered base agent: {agent_type}")
        
    def setup_conversation(self, thread_id: str, agent_types: List[str]) -> None:
        """
        Set up agents for a specific conversation.
        
        Args:
            thread_id: The conversation thread identifier
            agent_types: List of agent types to set up for this conversation
        """
        # Initialize conversation agents dict if not exists
        if thread_id not in self.conversation_agents:
            self.conversation_agents[thread_id] = {}
            
        # Create a deep copy of each requested agent type
        for agent_type in agent_types:
            agent_type = agent_type.upper()  # Normalize to uppercase
            
            # Skip if already set up
            if agent_type in self.conversation_agents[thread_id]:
                continue
                
            # Ensure base agent exists
            if agent_type not in self.base_agents:
                logger.warning(f"Base agent {agent_type} not found, skipping")
                continue
                
            try:
                # Clone the base agent for this conversation
                base_agent = self.base_agents[agent_type]
                
                # Most agents can be used directly from the base template
                # For agents that need conversation-specific state, implement 
                # a proper clone/copy mechanism
                self.conversation_agents[thread_id][agent_type] = base_agent
                
                logger.info(f"Set up agent {agent_type} for conversation {thread_id}")
            except Exception as e:
                logger.error(f"Failed to set up agent {agent_type}: {e}")
                logger.error(traceback.format_exc())
                
    def get_agent(self, thread_id: str, agent_type: str) -> Optional[Agent]:
        """
        Get a conversation-specific agent instance.
        
        Args:
            thread_id: The conversation thread identifier
            agent_type: The type of agent to retrieve
            
        Returns:
            The agent instance or None if not found
        """
        agent_type = agent_type.upper()  # Normalize to uppercase
        
        # First check conversation-specific agents
        if thread_id in self.conversation_agents:
            if agent_type in self.conversation_agents[thread_id]:
                return self.conversation_agents[thread_id][agent_type]
                
        # If not found in conversation agents, try to set it up
        if agent_type in self.base_agents:
            # Create conversation entry if it doesn't exist
            if thread_id not in self.conversation_agents:
                self.conversation_agents[thread_id] = {}
                
            # Add the agent to this conversation
            self.conversation_agents[thread_id][agent_type] = self.base_agents[agent_type]
            return self.conversation_agents[thread_id][agent_type]
        
        logger.warning(f"Agent {agent_type} not found for thread {thread_id}")
        return None
        
    def get_agent_types(self, thread_id: Optional[str] = None) -> List[str]:
        """
        Get available agent types.
        
        Args:
            thread_id: Optional thread ID to get agents for a specific conversation
            
        Returns:
            List of agent type identifiers
        """
        if thread_id and thread_id in self.conversation_agents:
            return list(self.conversation_agents[thread_id].keys())
        return list(self.base_agents.keys())
        
    def get_agent_descriptions(self) -> Dict[str, str]:
        """
        Get descriptions for all registered agents.
        
        Returns:
            Dictionary mapping agent types to their descriptions
        """
        return self.agent_descriptions
        
    def cleanup_conversation(self, thread_id: str) -> None:
        """
        Clean up resources for a conversation.
        
        Args:
            thread_id: The conversation thread identifier to clean up
        """
        if thread_id in self.conversation_agents:
            # Remove the conversation agents
            self.conversation_agents.pop(thread_id, None)
            logger.info(f"Cleaned up agents for conversation {thread_id}")

# Singleton instance
agent_interface = AgentInterface()
