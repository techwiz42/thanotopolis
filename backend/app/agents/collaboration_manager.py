from typing import Dict, List, Optional, Any, Callable, Awaitable, Tuple
import asyncio
import logging
import uuid
from uuid import UUID
import time
import traceback
from datetime import datetime

from openai import AsyncOpenAI

from agents import Agent, Runner, RunConfig, ModelSettings

from app.core.config import settings
# agent_manager will be imported dynamically to avoid circular imports

logger = logging.getLogger(__name__)

class CollaborationStatus:
    """Status of a collaboration between multiple agents."""
    
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"

class CollaborationSession:
    """A session tracking collaboration between multiple agents."""
    
    def __init__(
        self,
        collab_id: str,
        query: str,
        primary_agent_name: str,
        collaborating_agents: List[str],
        thread_id: Optional[str] = None
    ):
        self.collab_id = collab_id
        self.query = query
        self.primary_agent_name = primary_agent_name
        self.collaborating_agents = collaborating_agents
        self.thread_id = thread_id
        self.status = CollaborationStatus.PENDING
        self.start_time = time.time()
        self.end_time: Optional[float] = None
        self.result: Optional[str] = None
        self.response_parts: Dict[str, str] = {}
        self.error: Optional[str] = None
        self.future: Optional[asyncio.Future] = None

class CollaborationManager:
    """Manager for multi-agent collaborations."""
    
    def __init__(self):
        # Active collaborations
        self.active_collaborations: Dict[str, CollaborationSession] = {}
        
        # Collaboration history for analysis
        self.collaboration_history: List[CollaborationSession] = []
        
        # Collaboration timeout settings
        self.INDIVIDUAL_AGENT_TIMEOUT = 30.0  # seconds (increased for better completion)
        self.TOTAL_COLLABORATION_TIMEOUT = 90.0  # seconds (increased for complex queries)
        self.SYNTHESIS_TIMEOUT = 30.0  # seconds (increased for thorough synthesis)
        
        # Maximum collaborators to allow more diverse inputs
        self.MAX_COLLABORATORS = 3  # Increased limit for supporting agents
        
        # LLM client for synthesis
        self._client: Optional[AsyncOpenAI] = None
    
    def get_client(self) -> AsyncOpenAI:
        """Get or create LLM client."""
        if not self._client:
            self._client = AsyncOpenAI(
                api_key=settings.OPENAI_API_KEY,
                organization=getattr(settings, 'OPENAI_ORG_ID', None)
            )
        return self._client
    
    async def check_collaboration_needed(
        self,
        message: str,
        primary_agent_type: str,
        available_agents: List[str],
        llm_client: Optional[AsyncOpenAI] = None
    ) -> bool:
        """
        Determine if collaboration is needed for a query based on heuristics.
        
        Args:
            message: The user query
            primary_agent_type: The selected primary agent type
            available_agents: List of available agent types
            llm_client: Optional OpenAI client
            
        Returns:
            Boolean indicating if collaboration is needed
        """
        # Quick check for explicit collaboration request
        collaboration_keywords = [
            "collaborate", "multiple", "perspectives", "compare", "contrast", 
            "different views", "experts", "together"
        ]
        
        # Basic keyword check
        explicit_collab_request = any(keyword in message.lower() for keyword in collaboration_keywords)
        
        # Only check with LLM if there are keywords suggesting collaboration
        if explicit_collab_request:
            # Ensure we have at least one potential collaborator
            potential_collaborators = [a for a in available_agents if a != primary_agent_type]
            if not potential_collaborators:
                return False
                
            # We'll let the primary agent decide collaborators when processing through agent_manager
            return True
            
        return False
    
    async def initiate_collaboration(
        self,
        query: str,
        primary_agent_name: str,
        available_agents: List[str],
        collaborating_agents: List[str],
        thread_id: Optional[str] = None,
        streaming_callback: Optional[Callable[[str], Awaitable[None]]] = None
    ) -> str:
        """
        Initiate a collaboration between multiple agents.
        
        Args:
            query: The user query to collaborate on
            primary_agent_name: The primary agent's name
            available_agents: List of all available agents
            collaborating_agents: List of agent names that should collaborate
            thread_id: Optional thread ID for context
            streaming_callback: Optional callback for streaming tokens
            
        Returns:
            Collaboration ID for tracking
        """
        # Generate a unique collaboration ID
        collab_id = str(uuid.uuid4())
        
        # Limit number of collaborating agents to prevent excessive parallelism
        limited_collaborators = collaborating_agents[:self.MAX_COLLABORATORS] if collaborating_agents else []
        
        # Log collaboration start
        logger.info(f"Starting collaboration {collab_id} with primary: {primary_agent_name}, " 
                   f"collaborators: {limited_collaborators}")
        
        # Create a collaboration session
        session = CollaborationSession(
            collab_id=collab_id,
            query=query,
            primary_agent_name=primary_agent_name,
            collaborating_agents=limited_collaborators,
            thread_id=thread_id
        )
        
        # Store in active collaborations
        self.active_collaborations[collab_id] = session
        
        # Create a future for the result
        session.future = asyncio.Future()
        
        # Start the collaboration in the background with task name for debugging
        task = asyncio.create_task(
            self._run_collaboration(
                session=session,
                available_agents=available_agents,
                streaming_callback=streaming_callback
            ),
            name=f"collaboration-{collab_id}"
        )
        
        # Add done callback to clean up if task fails
        task.add_done_callback(lambda t: self._handle_task_done(t, collab_id))
        
        return collab_id
        
    def _handle_task_done(self, task, collab_id):
        """Handle completion or exception in collaboration task."""
        try:
            # Check if task raised an exception
            if task.done() and not task.cancelled():
                exc = task.exception()
                if exc:
                    logger.error(f"Collaboration {collab_id} failed with error: {exc}")
                    # Make sure we clean up session
                    if collab_id in self.active_collaborations:
                        session = self.active_collaborations[collab_id]
                        session.status = CollaborationStatus.FAILED
                        session.error = str(exc)
                        if session.future and not session.future.done():
                            session.future.set_exception(exc)
                        # Remove from active collaborations
                        self.active_collaborations.pop(collab_id, None)
        except Exception as e:
            logger.error(f"Error in task done callback: {e}")
    
    async def get_collaboration_result(
        self,
        collab_id: str,
        timeout: Optional[float] = None
    ) -> Optional[str]:
        """
        Get the result of a collaboration, waiting if necessary.
        
        Args:
            collab_id: The collaboration ID
            timeout: Optional timeout in seconds
            
        Returns:
            The collaboration result, or None if not complete/timeout/error
        """
        if collab_id not in self.active_collaborations:
            logger.error(f"Collaboration {collab_id} not found")
            return None
            
        session = self.active_collaborations[collab_id]
        
        if session.status == CollaborationStatus.COMPLETED and session.result:
            return session.result
            
        if not session.future:
            logger.error(f"Collaboration {collab_id} has no future")
            return None
            
        try:
            # Wait for the future to complete with timeout
            actual_timeout = timeout or self.TOTAL_COLLABORATION_TIMEOUT
            result = await asyncio.wait_for(asyncio.shield(session.future), timeout=actual_timeout)
            return result
        except asyncio.TimeoutError:
            logger.warning(f"Timeout waiting for collaboration {collab_id}")
            session.status = CollaborationStatus.TIMEOUT
            return None
        except Exception as e:
            logger.error(f"Error waiting for collaboration {collab_id}: {e}")
            session.status = CollaborationStatus.FAILED
            session.error = str(e)
            return None
    
    async def _run_collaboration(
        self,
        session: CollaborationSession,
        available_agents: List[str],
        streaming_callback: Optional[Callable[[str], Awaitable[None]]] = None
    ) -> None:
        """
        Run a collaboration session, getting responses from all agents.
        
        Args:
            session: The collaboration session
            available_agents: List of all available agent types
            streaming_callback: Optional callback for streaming tokens
        """
        session.status = CollaborationStatus.IN_PROGRESS
        
        try:
            # Verify thread_id exists
            if not session.thread_id:
                logger.error("Thread ID is required for collaboration")
                session.status = CollaborationStatus.FAILED
                session.error = "Thread ID is required for collaboration"
                if session.future and not session.future.done():
                    session.future.set_exception(ValueError("Thread ID is required"))
                # Make sure to remove from active collaborations
                self.active_collaborations.pop(session.collab_id, None)
                return

            # Get the primary agent instance
            # Import here to avoid circular imports
            from app.agents.agent_manager import agent_manager
            
            primary_agent = agent_manager.get_agent(session.primary_agent_name)
            if not primary_agent:
                logger.error(f"Primary agent {session.primary_agent_name} not found")
                session.status = CollaborationStatus.FAILED
                session.error = f"Primary agent {session.primary_agent_name} not found"
                if session.future and not session.future.done():
                    session.future.set_exception(ValueError(f"Primary agent {session.primary_agent_name} not found"))
                # Make sure to remove from active collaborations
                self.active_collaborations.pop(session.collab_id, None)
                return
            
            # Gather agent responses in parallel but with individual timeouts
            agent_response_tasks = []
            
            try:
                # Primary agent response (must have this)
                logger.info(f"Getting primary response from {session.primary_agent_name}")
                
                # Send a "starting response" token message to inform the client
                if streaming_callback and session.thread_id:
                    await streaming_callback(f"Starting collaboration with {session.primary_agent_name}...")
                
                primary_result = await asyncio.wait_for(
                    self._get_agent_response(
                        agent_name=session.primary_agent_name,
                        agent=primary_agent,
                        query=session.query,
                        is_primary=True,
                        thread_id=session.thread_id,
                        streaming_callback=streaming_callback
                    ),
                    timeout=self.INDIVIDUAL_AGENT_TIMEOUT
                )
                
                # Store primary result immediately
                agent_name, response = primary_result
                session.response_parts[agent_name] = response
                logger.info(f"Got primary response from {agent_name}")
                
                # Now gather supporting agent responses
                supporting_tasks = []
                
                # Limit to max number of collaborators (already enforced in initiate_collaboration)
                for collab_agent_name in session.collaborating_agents:
                    if collab_agent_name not in available_agents:
                        logger.warning(f"Collaborating agent {collab_agent_name} not available")
                        continue
                        
                    collab_agent = agent_manager.get_agent(collab_agent_name)
                    if not collab_agent:
                        logger.warning(f"Collaborating agent {collab_agent_name} not found")
                        continue
                        
                    logger.info(f"Starting supporting agent {collab_agent_name}")
                    collab_task = asyncio.create_task(
                        self._get_agent_response(
                            agent_name=collab_agent_name,
                            agent=collab_agent,
                            query=session.query,
                            is_primary=False,
                            thread_id=session.thread_id,
                            streaming_callback=streaming_callback
                        ),
                        name=f"supporting-{collab_agent_name}-{session.collab_id}"
                    )
                    supporting_tasks.append(collab_task)
                
                # Only wait for supporting agents if we have any
                if supporting_tasks:
                    # Use wait with a timeout - gather as many responses as possible within timeout
                    done, pending = await asyncio.wait(
                        supporting_tasks,
                        timeout=self.INDIVIDUAL_AGENT_TIMEOUT,
                        return_when=asyncio.ALL_COMPLETED  # Try to get all responses
                    )
                    
                    # Cancel any pending tasks
                    for task in pending:
                        # FIXED: Use safe get_name with fallback
                        task_name = getattr(task, 'get_name', lambda: 'unknown-task')()
                        logger.warning(f"Cancelling slow supporting agent: {task_name}")
                        task.cancel()
                        
                        # Extract agent_name from task name for timeout message
                        if task_name.startswith("supporting-"):
                            parts = task_name.split("-")
                            if len(parts) >= 2:
                                agent_name = parts[1]
                                session.response_parts[agent_name] = f"The {agent_name} agent took too long to respond."
                                logger.warning(f"Added timeout message for {agent_name}")
                    
                    # Get results from completed tasks
                    for task in done:
                        try:
                            agent_name, response = await task
                            session.response_parts[agent_name] = response
                            logger.info(f"Got supporting response from {agent_name}")
                        except Exception as e:
                            # FIXED: Use safe get_name with fallback
                            task_name = getattr(task, 'get_name', lambda: 'unknown-task')()
                            logger.error(f"Error getting agent response from task {task_name}: {e}")
                            
                            # Try to extract agent name from task name for error message
                            if task_name.startswith("supporting-"):
                                parts = task_name.split("-")
                                if len(parts) >= 2:
                                    agent_name = parts[1]
                                    session.response_parts[agent_name] = f"Error from {agent_name} agent: {str(e)}"
                
            except asyncio.TimeoutError:
                # This would happen if the primary agent times out
                logger.warning(f"Timeout waiting for primary agent response in {session.collab_id}")
                session.response_parts[session.primary_agent_name] = f"The {session.primary_agent_name} agent took too long to respond."
                
                # Send a specific timeout notification token to the client
                if streaming_callback and session.thread_id:
                    await streaming_callback(f"\n\n[TIMEOUT] The {session.primary_agent_name} agent took too long to respond.")
                    
            except Exception as e:
                logger.error(f"Error in collaboration sequence: {e}")
                logger.error(traceback.format_exc())
                session.response_parts[session.primary_agent_name] = f"Error: {str(e)}"
                
                # Send error notification to client
                if streaming_callback and session.thread_id:
                    await streaming_callback(f"\n\n[ERROR] An error occurred: {str(e)}")
            
            # Format responses for synthesis
            await self._synthesize_responses(
                session=session,
                streaming_callback=streaming_callback
            )
            
            # Mark as complete
            session.status = CollaborationStatus.COMPLETED
            session.end_time = time.time()
            
            # Store in history
            self.collaboration_history.append(session)
            
            # Set the future result
            if session.future and not session.future.done():
                session.future.set_result(session.result)
            
            # Clean up the active collaboration
            self.active_collaborations.pop(session.collab_id, None)
            
        except Exception as e:
            logger.error(f"Error running collaboration {session.collab_id}: {e}")
            logger.error(traceback.format_exc())
            session.status = CollaborationStatus.FAILED
            session.error = str(e)
            
            # Set the future to indicate failure
            if session.future and not session.future.done():
                session.future.set_exception(e)
            
            # Clean up
            self.active_collaborations.pop(session.collab_id, None)
    
    async def _get_agent_response(
        self,
        agent_name: str,
        agent: Agent,
        query: str,
        is_primary: bool,
        thread_id: Optional[str] = None,
        streaming_callback: Optional[Callable[[str], Awaitable[None]]] = None
    ) -> Tuple[str, str]:
        """
        Get response from a single agent for collaboration.
        
        Args:
            agent_name: The agent's name
            agent: The agent instance
            query: The query to respond to
            is_primary: Whether this is the primary agent
            thread_id: Optional thread ID for context
            
        Returns:
            Tuple of (agent_name, response)
        """
        role = "primary" if is_primary else "supporting"
        
        try:
            # Create a modified prompt for collaboration
            collab_prompt = f"""
            [COLLABORATIVE RESPONSE REQUEST]
            
            You are the {role} agent in a multi-agent collaboration to answer this query.
            
            QUERY: {query}
            
            Please provide your expert perspective on this query. Focus on areas where your expertise is most relevant.
            
            Your response will be combined with other specialist agents to create a comprehensive answer.
            """
            
            # Create run config
            run_config = RunConfig(
                workflow_name=f"{agent_name} Collaboration",
                model_settings=ModelSettings(
                    temperature=0.5  # Slightly higher for more diverse perspectives
                )
            )
            
            # Prefix message to identify agent in streaming output
            if streaming_callback:
                await streaming_callback(f"\n\n[{agent_name} is thinking...]\n")
                
            # Run the agent with streaming support
            streamed_result = Runner.run_streamed(
                starting_agent=agent,
                input=collab_prompt,
                context={"thread_id": thread_id, "is_collaboration": True},
                run_config=run_config
            )
            
            # Process streaming tokens
            tokens = []
            async for event in streamed_result.stream_events():
                # Look for text delta events
                if (hasattr(event, 'type') and 
                    event.type == "raw_response_event" and
                    hasattr(event.data, 'type') and
                    event.data.type == "response.output_text.delta" and
                    hasattr(event.data, 'delta')):
                    token = event.data.delta
                    if token:  # Only append non-empty tokens
                        tokens.append(token)
                        if streaming_callback:
                            await streaming_callback(token)
            
            # Get final output
            final_output = streamed_result.final_output or ''.join(tokens)
            
            # Agent completion message with explicit end token
            if streaming_callback:
                await streaming_callback(f"\n\n[{agent_name} has completed]\n[DONE]")
                
            return agent_name, str(final_output)
            
        except Exception as e:
            logger.error(f"Error getting response from {agent_name}: {e}")
            logger.error(traceback.format_exc())
            return agent_name, f"Error: Agent {agent_name} could not provide a response."
    
    async def _synthesize_responses(
        self,
        session: CollaborationSession,
        streaming_callback: Optional[Callable[[str], Awaitable[None]]] = None
    ) -> None:
        """
        Synthesize multiple agent responses into a cohesive response.
    
        Args:
            session: The collaboration session
            streaming_callback: Optional callback for streaming tokens
        """
        # Notify user that synthesis is starting
        if streaming_callback and session.thread_id:
            await streaming_callback("\n\n[Synthesizing collaborative response...]")
        try:
            # Get the primary response
            primary_response = session.response_parts.get(
                session.primary_agent_name,
                "Primary agent did not respond."
            )
        
            # Format supporting responses
            supporting_responses = []
            for agent_name, response in session.response_parts.items():
                if agent_name != session.primary_agent_name:
                    supporting_responses.append(f"--- {agent_name} RESPONSE ---\n{response}")
        
            # Handle case with no supporting responses
            if not supporting_responses:
                logger.warning(f"No supporting responses for {session.collab_id}")
                session.result = primary_response
                return
        
            supporting_text = "\n\n".join(supporting_responses)
        
            # Clear typing indicators for all agents involved in the collaboration
            if session.thread_id:
                try:
                    # Import here to avoid circular imports
                    from app.core.websocket_queue import connection_health
                    
                    # Clear typing indicator for primary agent (moderator)
                    primary_typing_end_message = {
                        "type": "typing_status",
                        "identifier": f"{session.primary_agent_name.lower()}@system.local",
                        "is_owner": False,
                        "is_typing": False,
                        "timestamp": datetime.utcnow().isoformat(),
                        "agent_type": session.primary_agent_name
                    }
                    
                    # Send to all clients in the conversation
                    await connection_health.broadcast(UUID(session.thread_id), primary_typing_end_message)
                    logger.info(f"Cleared {session.primary_agent_name} typing indicator for collaboration {session.collab_id}")
                    
                    # Clear typing indicators for all collaborating agents
                    for agent_name in session.collaborating_agents:
                        collab_typing_end_message = {
                            "type": "typing_status",
                            "identifier": f"{agent_name.lower()}@system.local",
                            "is_owner": False,
                            "is_typing": False,
                            "timestamp": datetime.utcnow().isoformat(),
                            "agent_type": agent_name
                        }
                        await connection_health.broadcast(UUID(session.thread_id), collab_typing_end_message)
                        logger.info(f"Cleared {agent_name} typing indicator for collaboration {session.collab_id}")
                    
                    # Also clear typing indicator for MODERATOR specifically if not already cleared
                    # This ensures the moderator's indicator is always cleared, even when dispatching
                    if session.primary_agent_name != "MODERATOR":
                        moderator_typing_end_message = {
                            "type": "typing_status",
                            "identifier": "moderator@system.local",
                            "is_owner": False,
                            "is_typing": False,
                            "timestamp": datetime.utcnow().isoformat(),
                            "agent_type": "MODERATOR"
                        }
                        await connection_health.broadcast(UUID(session.thread_id), moderator_typing_end_message)
                        logger.info(f"Cleared MODERATOR typing indicator for collaboration {session.collab_id}")
                except Exception as e:
                    logger.error(f"Error clearing typing indicators: {e}")
                    # Non-fatal error, continue with synthesis
            
            # Removed synthesis notification message
        
            # Direct synthesis with OpenAI client - skip the moderator agent entirely
            client = self.get_client()
            synthesis_prompt = f"""
            Synthesize these agent responses into a single cohesive answer:

            ORIGINAL QUERY:
            {session.query}

            PRIMARY AGENT ({session.primary_agent_name}) RESPONSE:
            {primary_response}

            SUPPORTING AGENT RESPONSES:
            {supporting_text}

            Your task is to:
            1. Combine the most relevant information from all responses
            2. Maintain consistent tone and style
            3. Attribute information to specific agents when appropriate
            4. Resolve any conflicts or contradictions
            5. Ensure all aspects of the query are addressed
            6. Present a logical flow of information
            7. Prioritize accuracy and clarity

            Create a comprehensive response that represents the collective expertise of the agents.
            """
        
            # Get synthesis response with streaming
            response_stream = await client.chat.completions.create(
                model=settings.DEFAULT_AGENT_MODEL,
                messages=[
                    {"role": "system", "content": "You are a synthesis specialist who combines multiple expert perspectives."},
                    {"role": "user", "content": synthesis_prompt}
                ],
                temperature=0.3,
                stream=True
            )
            
            # Collect the full response while streaming tokens
            full_content = []
            async for chunk in response_stream:
                if hasattr(chunk.choices[0], 'delta') and hasattr(chunk.choices[0].delta, 'content'):
                    content = chunk.choices[0].delta.content
                    if content:
                        full_content.append(content)
                        # Stream synthesis tokens in real-time if callback provided
                        if streaming_callback:
                            await streaming_callback(content)
            
            # Set and return the synthesized result
            synthesized_response = ''.join(full_content)
            session.result = synthesized_response
        
        except Exception as e:
            logger.error(f"Error synthesizing responses: {e}")
            logger.error(traceback.format_exc())
        
            # Fall back to primary response
            primary_response = session.response_parts.get(
                session.primary_agent_name,
                "No agent responses available."
            )
        
            # Simple concatenation as last resort
            parts = [f"Primary Agent ({session.primary_agent_name}):\n{primary_response}"]
            for agent_name, response in session.response_parts.items():
                if agent_name != session.primary_agent_name:
                    parts.append(f"Supporting Agent ({agent_name}):\n{response}")
        
            session.result = "\n\n".join(parts)

    def get_collaboration_stats(self) -> Dict[str, Any]:
        """Get statistics about collaborations."""
        if not self.collaboration_history:
            return {"total_collaborations": 0}
            
        total = len(self.collaboration_history)
        completed = sum(1 for s in self.collaboration_history if s.status == CollaborationStatus.COMPLETED)
        failed = sum(1 for s in self.collaboration_history if s.status in [CollaborationStatus.FAILED, CollaborationStatus.TIMEOUT])
        
        avg_duration = sum(
            (s.end_time or time.time()) - s.start_time 
            for s in self.collaboration_history if s.start_time
        ) / total if total > 0 else 0
        
        agent_participation = {}
        for session in self.collaboration_history:
            # Count primary agent
            agent_participation.setdefault(session.primary_agent_name, {"primary": 0, "supporting": 0})
            agent_participation[session.primary_agent_name]["primary"] += 1
            
            # Count supporting agents
            for agent in session.collaborating_agents:
                agent_participation.setdefault(agent, {"primary": 0, "supporting": 0})
                agent_participation[agent]["supporting"] += 1
        
        return {
            "total_collaborations": total,
            "completed": completed,
            "failed": failed,
            "completion_rate": (completed / total) if total > 0 else 0,
            "avg_duration_seconds": avg_duration,
            "agent_participation": agent_participation
        }

# Create singleton instance
collaboration_manager = CollaborationManager()
