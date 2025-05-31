from typing import Dict, List, Tuple, Optional, Any, Callable, Awaitable
import asyncio
import logging
import os
import importlib
import inspect
import traceback
import json
from uuid import UUID
from datetime import datetime

from agents import Agent, Runner, RunConfig, ModelSettings, handoff, function_tool
from sqlalchemy import select
from app.core.config import settings
from app.core.buffer_manager import buffer_manager
from app.core.input_sanitizer import input_sanitizer
from app.services.rag.query_service import rag_query_service
from app.services.agents.agent_interface import agent_interface
from app.services.agents.collaboration_manager import collaboration_manager
from app.services.agents.common_context import CommonAgentContext
from app.services.agents.base_agent import BaseAgent
from app.models.domain.models import Message, ThreadAgent, ThreadParticipant
from app.services.agents.agent_calculator_tool import AgentCalculatorTool

logger = logging.getLogger(__name__)
MODEL = settings.DEFAULT_AGENT_MODEL
MAX_TURNS = settings.MAX_TURNS

class AgentManager:
    def __init__(self):
        # Initialize base agents - these are templates that will be copied for each conversation
        self._initialize_agents()

        # Initialize collaboration manager
        self.collaboration_manager = collaboration_manager
        self.collaboration_patterns = {}

        # Resource management configuration
        self.LLM_TIMEOUT = 120  # Timeout for LLM operations in seconds

    def _initialize_agents(self) -> None:
        """Dynamically discover and initialize all available base agents."""
        try:
            # Get the directory containing agent classes
            agents_dir = os.path.dirname(os.path.abspath(__file__))
            logger.info(f"Looking for agents in directory: {agents_dir}")

            # Track discovered agents
            discovered_agents = []

            # Iterate through all Python files in the agents directory
            for filename in os.listdir(agents_dir):
                if filename.endswith('_agent.py') and filename != 'base_agent.py':
                    module_name = filename[:-3]
                    try:
                        # Log every import attempt for debugging
                        logger.info(f"Attempting to import module: {module_name}")
                        
                        # Import the module using absolute import
                        full_module_name = f'app.services.agents.{module_name}'
                        module = importlib.import_module(full_module_name)
                        
                        # Log successful module import
                        logger.info(f"Successfully imported module: {full_module_name}")

                        # Look for singleton instance variables (like moderator_agent)
                        agent_var_name = module_name.replace('_agent', '_agent')
                        if hasattr(module, agent_var_name):
                            agent = getattr(module, agent_var_name)
                            if isinstance(agent, Agent):
                                agent_type = agent.name.replace('Agent', '').strip().upper()
                                
                                # Ensure tools is properly initialized
                                if not hasattr(agent, 'tools') or agent.tools is None:
                                    agent.tools = []
                                    logger.info(f"Initialized empty tools list for agent: {agent_type}")
                                
                                # Ensure input_guardrails is initialized
                                if not hasattr(agent, 'input_guardrails') or agent.input_guardrails is None:
                                    agent.input_guardrails = []
                                
                                # Ensure output_guardrails is initialized
                                if not hasattr(agent, 'output_guardrails') or agent.output_guardrails is None:
                                    agent.output_guardrails = []
                                
                                # Ensure handoffs is initialized
                                if not hasattr(agent, 'handoffs') or agent.handoffs is None:
                                    agent.handoffs = []
                                
                                # Register with agent interface as base agent
                                agent_interface.register_base_agent(agent_type, agent)
                                discovered_agents.append(agent_type)
                                logger.info(f"Successfully loaded agent: {agent_type}")
                        else:
                            # Find all classes in the module that inherit from Agent
                            for name, obj in inspect.getmembers(module):
                                if (inspect.isclass(obj) and name.endswith('Agent') and 
                                    name != 'BaseAgent' and name != 'Agent'):
                                    
                                    # Check inheritance
                                    is_agent = False
                                    for base in obj.__mro__:
                                        if base.__name__ == 'BaseAgent' or base.__name__ == 'Agent':
                                            is_agent = True
                                            break
                                    
                                    if is_agent:
                                        # Initialize the agent
                                        try:
                                            agent_instance = obj()
                                            agent_type = name.replace('Agent', '').strip().upper()
                                            
                                            # Ensure tools is properly initialized
                                            if not hasattr(agent_instance, 'tools') or agent_instance.tools is None:
                                                agent_instance.tools = []
                                                logger.info(f"Initialized empty tools list for agent: {agent_type}")
                                            
                                            # Ensure input_guardrails is initialized
                                            if not hasattr(agent_instance, 'input_guardrails') or agent_instance.input_guardrails is None:
                                                agent_instance.input_guardrails = []
                                            
                                            # Ensure output_guardrails is initialized
                                            if not hasattr(agent_instance, 'output_guardrails') or agent_instance.output_guardrails is None:
                                                agent_instance.output_guardrails = []
                                            
                                            # Ensure handoffs is initialized
                                            if not hasattr(agent_instance, 'handoffs') or agent_instance.handoffs is None:
                                                agent_instance.handoffs = []
                                            
                                            # Register with agent interface as base agent
                                            agent_interface.register_base_agent(agent_type, agent_instance)
                                            discovered_agents.append(agent_type)
                                            logger.info(f"Successfully initialized agent: {agent_type}")
                                        except Exception as init_error:
                                            logger.error(f"Error initializing agent {name}: {init_error}")
                                            logger.error(traceback.format_exc())
                    except ImportError as ie:
                        logger.error(f"Import error for module {module_name}: {ie}")
                        logger.error(traceback.format_exc())
                        continue
                    except Exception as e:
                        logger.error(f"Error loading agent module {module_name}: {e}")
                        logger.error(traceback.format_exc())
                        continue

            # Log the discovery results
            logger.info(f"Agent discovery complete, found {len(discovered_agents)} agents")
            logger.info(f"Agent types: {discovered_agents}")

            # Verify required agents are available - with more flexible error handling
            if not discovered_agents:
                logger.error("No agents were discovered!")
                raise RuntimeError("No agents were discovered")
                
            # Make the MODERATOR requirement conditional
            if 'MODERATOR' not in discovered_agents:
                logger.warning("MODERATOR agent is missing, some functionality may be limited")
                
            logger.info(f"Successfully initialized {len(discovered_agents)} base agents")

        except Exception as e:
            logger.error(f"Error initializing agents: {e}")
            logger.error(traceback.format_exc())
            # Let the original error propagate with more details
            raise RuntimeError(f"Failed to initialize agent system: {str(e)}")

    def get_agent_descriptions(self) -> Dict[str, str]:
        """Get descriptions for all available base agents."""
        return agent_interface.get_agent_descriptions()

    def get_available_agents(self) -> List[str]:
        """Get list of all available base agent types."""
        return agent_interface.get_agent_types()

    def _resolve_agent_name(self, requested_name: str, available_agents: List[str]) -> str:
        """
        Resolve a requested agent name to an available agent.
        
        Args:
            requested_name: The requested agent name
            available_agents: List of available agent names
            
        Returns:
            Resolved agent name from available agents
        """
        # Log available agents and requested agent for debugging
        logger.debug(f"Attempting to resolve '{requested_name}' from: {available_agents}")
        
        # Already an exact match
        if requested_name in available_agents:
            return requested_name
            
        # Try case-insensitive match
        normalized_request = requested_name.upper()
        for agent in available_agents:
            if agent.upper() == normalized_request:
                logger.debug(f"Found case-insensitive match: {agent}")
                return agent
                
        # Try prefix match
        for agent in available_agents:
            if agent.upper().startswith(normalized_request) or normalized_request.startswith(agent.upper()):
                logger.debug(f"Found prefix match: {agent}")
                return agent
                
        # Try substring match
        for agent in available_agents:
            if normalized_request in agent.upper() or agent.upper() in normalized_request:
                logger.debug(f"Found substring match: {agent}")
                return agent
                
        # No match, return MODERATOR or first agent
        if "MODERATOR" in available_agents:
            logger.warning(f"No match found for '{requested_name}', defaulting to MODERATOR")
            return "MODERATOR"
        elif available_agents:
            first_agent = available_agents[0]
            logger.warning(f"No match found for '{requested_name}', using first available: {first_agent}")
            return first_agent
        else:
            logger.error(f"No agents available for resolution")
            return requested_name  # Last resort, return original name

    async def _prepare_context(
        self,
        message: str,
        thread_id: Optional[str],
        owner_id: Optional[UUID],
        db: Optional[Any]
    ) -> CommonAgentContext:
        """Build context object with conversation history, buffer and RAG data."""
        context = CommonAgentContext(
            thread_id=thread_id,
            db=db,
            owner_id=owner_id
        )

        try:
            if not thread_id:
                return context

            # Get conversation history from buffer manager first
            if thread_id:
                try:
                    # Use the buffer manager to get formatted context
                    thread_uuid = UUID(thread_id) if not isinstance(thread_id, UUID) else thread_id
                    logger.info(f"[BUFFER_DEBUG] Retrieving context for thread: {thread_id} (converted to UUID: {thread_uuid}, type: {type(thread_uuid)})")
                    buffer_context = buffer_manager.get_context(thread_uuid)
                    
                    if buffer_context:
                        context.buffer_context = buffer_context
                        logger.info(f"[BUFFER_DEBUG] Retrieved conversation context from buffer for thread {thread_id}, length: {len(buffer_context)}")
                        
                        # Verify buffer context has content
                        if len(buffer_context.strip()) < 10:
                            logger.warning(f"[BUFFER_DEBUG] Buffer context is too short ({len(buffer_context)} chars), might be insufficient")
                    else:
                        logger.warning(f"[BUFFER_DEBUG] No buffer context found for thread {thread_id} (UUID: {thread_uuid})")
                except Exception as e:
                    logger.error(f"Error retrieving buffer context: {e}")
                    logger.error(traceback.format_exc())

            # If buffer didn't have context or had an error, fall back to DB
            if not context.buffer_context and db and thread_id:
                try:
                    # Convert thread_id to UUID if needed
                    thread_uuid = UUID(thread_id) if not isinstance(thread_id, UUID) else thread_id

                    # Query for recent messages in this thread (ordered by timestamp)
                    query = (
                        select(Message)
                        .where(Message.thread_id == thread_uuid)
                        .order_by(Message.created_at)
                        .limit(settings.MAX_CONTEXT_MESSAGES)  # Use a reasonable default if not defined
                    )

                    result = await db.execute(query)
                    messages = result.scalars().all()

                    # Format messages into a conversation history string
                    if messages:
                        history_parts = ["CONVERSATION HISTORY:"]

                        for msg in messages:
                            # Format depends on if it's an agent or user message
                            if msg.agent_id:
                                # Get the agent type
                                agent_query = select(ThreadAgent).where(ThreadAgent.id == msg.agent_id)
                                agent_result = await db.execute(agent_query)
                                agent = agent_result.scalar_one_or_none()
                                agent_type = agent.agent_type if agent else "AGENT"

                                sender = f"[{agent_type}]"
                            else:
                                # User/participant message
                                sender = "[USER]"
                                if msg.participant_id:
                                    participant_query = select(ThreadParticipant).where(
                                        ThreadParticipant.id == msg.participant_id
                                    )
                                    participant_result = await db.execute(participant_query)
                                    participant = participant_result.scalar_one_or_none()
                                    if participant:
                                        sender = f"[{participant.name or 'USER'}]"

                            # Add the formatted message
                            history_parts.append(f"{sender} {msg.content}")

                        # Set the formatted conversation history
                        context.buffer_context = "\n".join(history_parts)

                        logger.info(f"Added {len(messages)} messages to conversation context for thread {thread_id}")
                except Exception as e:
                    logger.error(f"Error retrieving conversation history: {e}")
                    logger.error(traceback.format_exc())

            # Get RAG context if available (keep this unchanged)
            if owner_id:
                try:
                    context.rag_results = await rag_query_service.query_knowledge(
                        owner_id=str(owner_id),
                        query_text=message,
                        k=10
                    )
                    logger.info(f"RAG query returned {len(context.rag_results['documents'])} documents")
                except Exception as e:
                    logger.error(f"Error retrieving RAG context: {e}")
                    logger.error(traceback.format_exc())

            # Add available agents to context (keep this unchanged)
            if thread_id:
                # Get agent types for this conversation
                agent_types = agent_interface.get_agent_types(thread_id)

                # Get descriptions for these agent types
                all_descriptions = self.get_agent_descriptions()
                context.available_agents = {
                    agent_type: all_descriptions.get(agent_type, f"{agent_type} agent")
                    for agent_type in agent_types
                }

            return context

        except Exception as e:
            logger.error(f"Error building context: {e}")
            logger.error(traceback.format_exc())
            return context

    async def _select_agent(
        self,
        message: str,
        context: CommonAgentContext,
        thread_id: str,
        mention: Optional[str] = None
    ) -> str:
        """
        Select the appropriate agent to handle the message.
        
        Args:
            message: The user's query message
            context: The conversation context
            thread_id: The thread identifier for this conversation
            mention: Optional mentioned agent
            
        Returns:
            The primary agent type for handling the query
        """
        try:
            # Get available agent types for this thread
            available_agents = agent_interface.get_agent_types(thread_id)
            
            # Handle empty agent list
            if not available_agents:
                logger.error("No agents available for selection")
                raise ValueError("No agents available for selection")
            
            # 1. If there's an explicit mention and it's valid, use that agent directly
            if mention:
                # Try exact match first
                normalized_mention = mention.upper()
                if normalized_mention in available_agents:
                    logger.info(f"Using explicitly mentioned agent: {normalized_mention}")
                    context.selected_agent = normalized_mention
                    return normalized_mention
                    
                # Try more flexible matching if not an exact match
                for agent_name in available_agents:
                    if agent_name.upper().startswith(normalized_mention) or normalized_mention in agent_name.upper():
                        logger.info(f"Using fuzzy-matched mentioned agent: {agent_name} (from '{mention}')")
                        context.selected_agent = agent_name
                        return agent_name
                        
                # If still no match, log warning and fall through to automated selection
                logger.warning(f"Mentioned agent '{mention}' not found in available agents: {available_agents}")
            
            # 2. Use the moderator to make a SINGLE agent selection attempt - with timeout protection
            if "MODERATOR" in available_agents:
                moderator = agent_interface.get_agent(thread_id, "MODERATOR")
                
                if moderator:
                    try:
                        # Use a direct tool call first with a strict timeout
                        select_tool = next((t for t in moderator.tools 
                                           if hasattr(t, 'name') and t.name == 'select_agent'), None)
                        
                        if select_tool and hasattr(select_tool, 'on_invoke_tool'):
                            try:
                                # Use asyncio.wait_for to add a timeout on the tool call
                                tool_input = json.dumps({
                                    "query": message,
                                    "available_agents": ",".join(available_agents)
                                })
                                
                                # Call with strict timeout to prevent hangs
                                result_str = await asyncio.wait_for(
                                    select_tool.on_invoke_tool(context, tool_input), 
                                    timeout=5.0  # 5 second timeout
                                )
                                
                                # Parse the result
                                try:
                                    selection_data = json.loads(result_str)
                                    primary_agent = selection_data.get("primary_agent", "")
                                    
                                    # Validate the selected agent
                                    if primary_agent in available_agents:
                                        # Get collaborators if available
                                        supporting_agents = [
                                            agent for agent in selection_data.get("supporting_agents", [])
                                            if agent in available_agents and agent != primary_agent
                                        ]
                                        
                                        # Store in context and return
                                        context.collaborators = supporting_agents
                                        context.is_agent_selection = True
                                        context.selected_agent = primary_agent
                                        
                                        logger.info(f"Selected primary agent: {primary_agent} with collaborators: {supporting_agents}")
                                        return primary_agent
                                except json.JSONDecodeError:
                                    logger.warning(f"Could not parse agent selection result: {result_str}")
                            except asyncio.TimeoutError:
                                logger.warning("Timeout using moderator's select_agent tool, falling back")
                            except Exception as tool_error:
                                logger.error(f"Error using moderator's select_agent tool: {tool_error}")
                    except Exception as e:
                        logger.error(f"Error using moderator for agent selection: {e}")
                        logger.error(traceback.format_exc())
            
            # 3. Fallback selection: if we couldn't use moderator's tool, make a simple selection
            # based on query keywords if possible
            query_keywords = message.lower().split()
            for agent in available_agents:
                # Skip MODERATOR for keyword matching
                if agent == "MODERATOR":
                    continue
                    
                # Check if agent type keywords appear in the query
                agent_name_keywords = agent.lower().split('_')
                if any(keyword in query_keywords for keyword in agent_name_keywords):
                    logger.info(f"Selected agent {agent} based on keyword match")
                    context.selected_agent = agent
                    return agent
            
            # 4. Fallback to MODERATOR if available
            if "MODERATOR" in available_agents:
                logger.info("Using fallback selection: MODERATOR")
                context.selected_agent = "MODERATOR"
                return "MODERATOR"
            
            # 5. Last resort: use first available agent
            first_agent = available_agents[0]
            logger.warning(f"Using first available agent as last resort: {first_agent}")
            context.selected_agent = first_agent
            return first_agent
            
        except Exception as e:
            logger.error(f"Error selecting agent: {e}")
            logger.error(traceback.format_exc())
            
            # Find a fallback agent
            available_agents = agent_interface.get_agent_types(thread_id)
            if "MODERATOR" in available_agents:
                return "MODERATOR"
            elif available_agents:
                return available_agents[0]
            else:
                raise ValueError("No agents available")

    async def process_conversation(
        self,
        message: str,
        conversation_agents: List[str],
        agents_config: Dict[str, Any],
        mention: Optional[str] = None,
        db: Optional[Any] = None,
        thread_id: Optional[str] = None,
        owner_id: Optional[UUID] = None,
        response_callback: Optional[Callable[[str], Awaitable[None]]] = None
    ) -> Tuple[str, str]:
        """
        Process a user message with the appropriate agent.

        This method uses the Agent SDK's built-in handoff mechanism to route
        queries to the appropriate specialist agent, with proper conversation isolation.

        Args:
            message: The user's message
            conversation_agents: List of available agent types for this conversation
            agents_config: Configuration for the agents
            mention: Optional mentioned agent
            db: Optional database session
            thread_id: Optional thread ID
            owner_id: Optional owner ID
            response_callback: Optional callback for streaming tokens

        Returns:
            Tuple of (agent_type, response)
        """
        logger.info(f"Processing conversation, message: '{message[:100]}...'")

        try:
            # Sanitize user input to prevent prompt injection attacks
            sanitized_message, is_suspicious, detected_patterns = input_sanitizer.sanitize_input(message)
            
            # If suspicious content was detected, log it for review
            if is_suspicious:
                logger.warning(f"Potential prompt injection detected in message from thread {thread_id}: {detected_patterns}")
                # If we detect highly suspicious patterns (optional security policy)
                if any(p in str(detected_patterns).lower() for p in ['ignore', 'system', 'jailbreak', 'dan mode']):
                    logger.error(f"High-risk prompt injection attempt detected: {detected_patterns}")
                    return "SYSTEM", "I'm unable to process this request due to security concerns. Please rephrase your message without instructions that attempt to override the system."
            
            # Wrap the sanitized message with tags to clearly delineate it from system instructions
            wrapped_message = input_sanitizer.wrap_user_input(sanitized_message)
            
            # Ensure we have a valid thread ID for proper isolation
            if not thread_id:
                thread_id = f"anonymous_{id(message)}"  # Generate a temporary ID if none provided
                logger.warning(f"No thread ID provided, using generated ID: {thread_id}")
                
            # Normalize agent types
            normalized_agents = [agent.upper() for agent in conversation_agents]
            
            # Set up conversation-specific agents
            agent_interface.setup_conversation(thread_id, normalized_agents)
           
            available_agents = agent_interface.get_agent_types(thread_id)

            # Prepare the context for processing - use original message for RAG retrieval
            context = await self._prepare_context(
                message=message,  # Using original message for RAG retrieval is fine
                thread_id=thread_id,
                owner_id=owner_id,
                db=db
            )
            
            # Store sanitization information in context
            context.is_sanitized = is_suspicious
            context.original_message = message
            
            # PHASE 1: AGENT SELECTION
            # -----------------------
            
            # Select the agent to handle this query (use original message for agent selection)
            primary_agent_type = await self._select_agent(
                message=message,  # Using original for agent selection is safe
                context=context,
                thread_id=thread_id,
                mention=mention
            )
            
            # Get the conversation-specific agent instance
            primary_agent = agent_interface.get_agent(thread_id, primary_agent_type)
            
            if not primary_agent:
                logger.error(f"Could not find agent {primary_agent_type} for conversation {thread_id}")
                return "MODERATOR", "I encountered an error processing your request: Agent not available"
                
            # PHASE 2: RESPONSE GENERATION
            # ---------------------------
            
            # Check if this is a collaboration scenario
            collaboration_needed = False
            collaborating_agents = []
            
            # Check for collaborators from the _select_agent result
            if hasattr(context, 'collaborators') and context.collaborators:
                collaborating_agents = context.collaborators
                collaboration_needed = len(collaborating_agents) > 0
                logger.info(f"Collaboration detected with agents: {collaborating_agents}")
            
            # Handle collaboration if needed
            if collaboration_needed and collaborating_agents:
                logger.info(f"Starting collaboration for message: {wrapped_message[:50]}...")
                response = await self._handle_collaboration(
                    message=wrapped_message,  # Use sanitized and wrapped message
                    thread_id=thread_id,
                    primary_agent_type=primary_agent_type,
                    collaborators=collaborating_agents,
                    context=context,
                    response_callback=response_callback
                )
                
                # Add message to conversation buffer AFTER processing
                if thread_id:
                    try:
                        thread_uuid = UUID(thread_id) if not isinstance(thread_id, UUID) else thread_id
                        # Store user message in buffer
                        await buffer_manager.add_message(
                            conversation_id=thread_uuid,
                            message=message,
                            sender_id="user",
                            sender_type="user",
                            owner_id=owner_id
                        )
                        logger.info(f"[BUFFER_DEBUG] Added user message to buffer for conversation {thread_id} (UUID: {thread_uuid})")
                        
                        # Store agent response in buffer
                        await buffer_manager.add_message(
                            conversation_id=thread_uuid,
                            message=response,
                            sender_id=primary_agent_type,
                            sender_type="agent",
                            owner_id=owner_id,
                            metadata={"agent_type": primary_agent_type}
                        )
                        logger.info(f"[BUFFER_DEBUG] Added agent response to buffer for conversation {thread_id} (UUID: {thread_uuid})")
                        
                        # Log buffer state after adding messages
                        logger.info(f"[BUFFER_DEBUG] Added both messages to buffer for conversation {thread_id}")
                    except Exception as buffer_error:
                        logger.error(f"Error adding messages to buffer: {buffer_error}")
                
                return primary_agent_type, response
            
            # Handle streaming vs non-streaming for single agent response
            if response_callback:
                # Streaming response
                try:
                    # Create a run config for the response generation
                    run_config = RunConfig(
                        workflow_name=f"{primary_agent_type} Conversation",
                        model=MODEL
                    )
                    
                    # Run the agent with streaming - first sanitize, then normalize calculator expressions
                    processed_message = AgentCalculatorTool.normalize_root_phrases_to_expressions(wrapped_message)
                    streamed_result = Runner.run_streamed(
                        starting_agent=primary_agent,
                        input=processed_message,  # Using sanitized, wrapped, and processed message
                        context=context,
                        run_config=run_config,
                        max_turns=MAX_TURNS
                    )

                    # Collect tokens for final response
                    tokens = []

                    # Use asyncio.wait_for to add a timeout
                    try:
                        async def process_stream():
                            async for event in streamed_result.stream_events():
                                # Look for text delta events in raw_response_event
                                if (hasattr(event, 'type') and 
                                    event.type == "raw_response_event" and
                                    hasattr(event.data, 'type') and
                                    event.data.type == "response.output_text.delta" and
                                    hasattr(event.data, 'delta')):
                                    token = event.data.delta
                                    if token:  # Only append non-empty tokens
                                        tokens.append(token)
                                        await response_callback(token)

                        # Wait for stream processing with timeout
                        await asyncio.wait_for(process_stream(), timeout=self.LLM_TIMEOUT)

                    except asyncio.TimeoutError:
                        await response_callback("\n\n[Response timed out, showing partial results]")
                        logger.warning(f"Streaming response timed out for {primary_agent_type}")

                    # Use the final output from the result if available, otherwise use collected tokens
                    final_response = streamed_result.final_output or "".join(tokens) or "I couldn't generate a proper response."
                    
                    # Add message to conversation buffer AFTER processing
                    if thread_id:
                        try:
                            thread_uuid = UUID(thread_id) if not isinstance(thread_id, UUID) else thread_id
                            # Store user message in buffer
                            await buffer_manager.add_message(
                                conversation_id=thread_uuid,
                                message=message,
                                sender_id="user",
                                sender_type="user",
                                owner_id=owner_id
                            )
                            logger.info(f"[BUFFER_DEBUG] Added user message (streaming) to buffer for conversation {thread_id} (UUID: {thread_uuid})")
                            
                            # Store agent response in buffer
                            await buffer_manager.add_message(
                                conversation_id=thread_uuid,
                                message=final_response,
                                sender_id=primary_agent_type,
                                sender_type="agent",
                                owner_id=owner_id,
                                metadata={"agent_type": primary_agent_type}
                            )
                            logger.info(f"[BUFFER_DEBUG] Added agent response (streaming) to buffer for conversation {thread_id} (UUID: {thread_uuid})")
                            
                            # Log the buffer state
                            logger.info(f"[BUFFER_DEBUG] Added both messages (streaming) to buffer for conversation {thread_id}")
                        except Exception as buffer_error:
                            logger.error(f"Error adding messages to buffer: {buffer_error}")
                    
                    return primary_agent_type, final_response
                    
                except Exception as e:
                    logger.error(f"Error in streaming response: {e}")
                    error_message = f"Error generating response: {str(e)}"
                    await response_callback(error_message)
                    return primary_agent_type, error_message
            
            # Non-streaming case
            try:
                # Create a run config for the response generation
                run_config = RunConfig(
                    workflow_name=f"{primary_agent_type} Conversation",
                    model=MODEL
                )

                # Run the selected agent - first sanitize, then normalize calculator expressions
                processed_message = AgentCalculatorTool.normalize_root_phrases_to_expressions(wrapped_message)
                result = await Runner.run(
                    starting_agent=primary_agent,
                    input=processed_message,  # Using sanitized, wrapped, and processed message
                    context=context,
                    run_config=run_config,
                    max_turns=MAX_TURNS
                )

                final_response = result.final_output
                
                # Add message to conversation buffer AFTER processing
                if thread_id:
                    try:
                        thread_uuid = UUID(thread_id) if not isinstance(thread_id, UUID) else thread_id
                        # Store user message in buffer
                        await buffer_manager.add_message(
                            conversation_id=thread_uuid,
                            message=message,
                            sender_id="user",
                            sender_type="user",
                            owner_id=owner_id
                        )
                        logger.info(f"[BUFFER_DEBUG] Added user message (non-streaming) to buffer for conversation {thread_id} (UUID: {thread_uuid})")
                        
                        # Store agent response in buffer
                        await buffer_manager.add_message(
                            conversation_id=thread_uuid,
                            message=final_response,
                            sender_id=primary_agent_type,
                            sender_type="agent",
                            owner_id=owner_id,
                            metadata={"agent_type": primary_agent_type}
                        )
                        logger.info(f"[BUFFER_DEBUG] Added agent response (non-streaming) to buffer for conversation {thread_id} (UUID: {thread_uuid})")
                        
                        # Log buffer state after adding both messages
                        logger.info(f"[BUFFER_DEBUG] Added both messages (non-streaming) to buffer for conversation {thread_id}")
                    except Exception as buffer_error:
                        logger.error(f"Error adding messages to buffer: {buffer_error}")
                
                return primary_agent_type, final_response
            except Exception as e:
                logger.error(f"Error running agent for response: {e}")
                return primary_agent_type, f"I encountered an error: {str(e)}"

        except Exception as e:
            logger.error(f"Error processing conversation: {e}")
            logger.error(traceback.format_exc())
            error_message = f"I encountered an error processing your request: {str(e)}"
            if response_callback:
                await response_callback(error_message)
            return "MODERATOR", error_message

    async def _handle_collaboration(
        self,
        message: str,  # This should now be the already-sanitized and wrapped message
        thread_id: str,
        primary_agent_type: str,
        collaborators: List[str],
        context: CommonAgentContext,
        response_callback: Optional[Callable[[str], Awaitable[None]]] = None
    ) -> str:
        """
        Handle multi-agent collaboration with streaming support.

        Args:
            message: Sanitized user query with safety wrapping
            thread_id: The conversation thread ID
            primary_agent_type: The type of the primary agent
            collaborators: List of agent types that should collaborate
            context: The context object
            response_callback: Optional callback for streaming tokens

        Returns:
            Synthesized response from the collaboration
        """
        try:
            # Ensure we have valid collaborators
            if not collaborators:
                logger.warning("Collaboration requested but no collaborators specified")
                # Fall back to standard agent response
                primary_agent = agent_interface.get_agent(thread_id, primary_agent_type)
                if not primary_agent:
                    raise ValueError(f"Primary agent {primary_agent_type} not found")
                # Apply calculator normalization to the already-sanitized message
                processed_message = AgentCalculatorTool.normalize_root_phrases_to_expressions(message)
                result = await Runner.run(
                    starting_agent=primary_agent,
                    input=processed_message,
                    context=context,
                    max_turns=MAX_TURNS,
                    run_config=RunConfig(
                        workflow_name=f"{primary_agent_type} Fallback",
                        model=MODEL
                    )
                )
                return result.final_output

            # Removed collaboration notification message

            # Initiate collaboration through the collaboration manager - using sanitized message
            collab_id = await self.collaboration_manager.initiate_collaboration(
                query=message,  # This is already the sanitized and wrapped message
                primary_agent_name=primary_agent_type,
                available_agents=agent_interface.get_agent_types(thread_id),
                collaborating_agents=collaborators,
                thread_id=thread_id,
                streaming_callback=response_callback
            )

            # Wait for the collaboration to complete and get the result
            result = await self.collaboration_manager.get_collaboration_result(collab_id)

            if not result:
                # If no result after timeout, provide a fallback
                logger.warning(f"Collaboration timeout for {collab_id}")
                return "I'm sorry, the collaborative response took too long to generate. Please try again with a more specific query."

            # Track collaboration for analysis - use context.original_message for tracking
            await self._track_collaboration(
                primary_agent=primary_agent_type,
                collaborators=collaborators,
                query=context.original_message if hasattr(context, 'original_message') else message,
                result=result
            )

            return result

        except Exception as e:
            logger.error(f"Error in collaboration: {e}")
            logger.error(traceback.format_exc())
            return f"Error coordinating collaboration: {str(e)}"

    async def _track_collaboration(
        self,
        primary_agent: str,
        collaborators: List[str],
        query: str,
        result: str
    ) -> None:
        """Track collaboration patterns for analysis."""
        pattern = frozenset([primary_agent] + collaborators)

        if pattern not in self.collaboration_patterns:
            self.collaboration_patterns[pattern] = {
                'count': 0,
                'queries': [],
                'success_rate': 0.0
            }

        self.collaboration_patterns[pattern]['count'] += 1
        self.collaboration_patterns[pattern]['queries'].append({
            'query': query,
            'timestamp': datetime.utcnow().isoformat()
        })

# Create singleton instance
agent_manager = AgentManager()

# For backward compatibility with existing code
try:
    AGENTS = {agent_type: agent_type for agent_type in agent_manager.get_available_agents()}
except Exception as e:
    logger.error(f"Error initializing AGENTS dictionary: {e}")
    AGENTS = {"MODERATOR": "MODERATOR"}