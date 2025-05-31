from typing import Any, Callable, List, Optional, Union, Type, Dict, TypeVar, Generic
from agents import Agent, ModelSettings, AgentHooks
from agents.tool import Tool, FunctionTool
from agents.run_context import TContext, RunContextWrapper
import inspect
import logging
from app.core.config import settings

logger = logging.getLogger(__name__)

class BaseAgentHooks(AgentHooks):
    """Custom hooks for all agents to ensure context is properly initialized."""
    
    async def init_context(self, context: RunContextWrapper[Any]) -> None:
        """
        Initialize context for agents, ensuring conversation history is available.
        
        Args:
            context: The run context wrapper containing conversation data
        """
        # Call parent implementation
        await super().init_context(context)
        
        # Make sure the context has all expected attributes
        if hasattr(context, 'context'):
            agent_ctx = context.context
            logger.info(f"[CONTEXT_DEBUG] Initialized context, has buffer_context: {hasattr(agent_ctx, 'buffer_context')}")
            if hasattr(agent_ctx, 'buffer_context') and agent_ctx.buffer_context:
                logger.info(f"[CONTEXT_DEBUG] Buffer context length: {len(agent_ctx.buffer_context)} chars")
        else:
            logger.warning("[CONTEXT_DEBUG] Context initialized but no 'context' attribute found")

# Make BaseAgent generic over the context type
T = TypeVar('T')

class BaseAgent(Agent, Generic[T]):
    """
    BaseAgent is a wrapper around OpenAI's Agent SDK, providing compatibility with
    code originally written for the Swarm framework.
    
    This class inherits from Agent SDK's Agent class but provides additional methods
    and attributes to maintain compatibility with existing code.
    """
    
    def __init__(
        self,
        name: str = "Agent",
        model: str = settings.DEFAULT_AGENT_MODEL,
        instructions: Union[str, Callable[[RunContextWrapper[T], "Agent[T]"], str]] = "You are a helpful agent.",
        functions: List[Any] = None,
        tool_choice: Optional[str] = None,
        parallel_tool_calls: bool = True,
        max_tokens: Optional[int] = None,
        **kwargs
    ):
        """
        Initialize a BaseAgent with the given parameters.
        
        Args:
            name: The name of the agent.
            model: The model to use for this agent.
            instructions: The system prompt for the agent.
            functions: A list of functions to be used as tools by the agent.
            tool_choice: The tool choice strategy to use.
            parallel_tool_calls: Whether to allow the agent to call multiple tools in parallel.
            max_tokens: Maximum number of tokens to generate in the response.
            **kwargs: Additional arguments to pass to the Agent constructor.
        """
        # Convert functions to tools if provided
        tools = []
        if functions:
            tools = self._convert_functions_to_tools(functions)
        
        # Extract 'tools' from kwargs if it exists to avoid duplicate parameters
        if 'tools' in kwargs:
            del kwargs['tools']
            
        # Initialize the parent Agent class
        model_settings_params = {
            "tool_choice": tool_choice,
            "parallel_tool_calls": parallel_tool_calls
        }
        
        # Add max_tokens to ModelSettings if provided
        if max_tokens is not None:
            model_settings_params["max_tokens"] = max_tokens
        
        # If instructions is a string, we wrap it in a function that will include conversation history
        if isinstance(instructions, str):
            base_instructions = instructions
            instructions = lambda ctx, agent: self._build_instructions_with_context(ctx, base_instructions)
            
        super().__init__(
            name=name,
            model=model,
            instructions=instructions,
            tools=tools,
            model_settings=ModelSettings(**model_settings_params),
            **kwargs
        )
        
        # Store the original functions for compatibility
        self._functions = functions or []
        
        # Add standard hooks if not provided
        self.hooks = kwargs.get('hooks', None)
        if not self.hooks:
            from agents import AgentHooks
            self.hooks = BaseAgentHooks()
    
    def _build_instructions_with_context(self, ctx, base_instructions):
        """
        Build agent instructions with conversation context included
        
        Args:
            ctx: The RunContextWrapper with context data
            base_instructions: The base instructions string
            
        Returns:
            Combined instructions with conversation history
        """
        # Add conversation history if available
        if hasattr(ctx, 'context') and hasattr(ctx.context, 'buffer_context') and ctx.context.buffer_context:
            logger.info(f"[CONTEXT_DEBUG] Including conversation context in instructions for {self.name}. Context length: {len(ctx.context.buffer_context)} chars")
            return f"{base_instructions}\n\n## Conversation History:\n{ctx.context.buffer_context}"
        else:
            if not hasattr(ctx, 'context'):
                logger.warning(f"[CONTEXT_DEBUG] No 'context' attribute found in ctx for {self.name}")
            elif not hasattr(ctx.context, 'buffer_context'):
                logger.warning(f"[CONTEXT_DEBUG] No 'buffer_context' attribute found in ctx.context for {self.name}")
            elif not ctx.context.buffer_context:
                logger.warning(f"[CONTEXT_DEBUG] Empty buffer_context for {self.name}")
            return base_instructions
    
    def _convert_functions_to_tools(self, functions: List[Any]) -> List[Tool]:
        """
        Convert a list of functions to a list of tools, validating schemas along the way.
        
        Args:
            functions: List of functions to convert to tools.
            
        Returns:
            List of Tool objects.
        """
        tools = []
        for func in functions:
            if isinstance(func, Tool):
                tools.append(func)
            else:
                try:
                    # Check if the function is already wrapped in a function_tool decorator
                    if hasattr(func, 'schema'):  # Check for the schema attribute directly
                        # The function already has a schema, this is likely an SDK function_tool
                        tools.append(func)
                    else:
                        # We need to import function_tool here to avoid circular import
                        from agents import function_tool
                        # Attempt to convert to a function tool
                        tool = function_tool(func)
                        
                        # Validate the schema
                        self._validate_function_schema(func, tool)
                        
                        tools.append(tool)
                except Exception as e:
                    logger.error(f"Error converting function {getattr(func, '__name__', 'unknown')} to tool: {str(e)}")
                    # Create a sanitized version of the function
                    tools.append(self._create_sanitized_function_tool(func))
        return tools
    
    def _validate_function_schema(self, func: Callable, tool: FunctionTool) -> None:
        """
        Validate that the function tool's schema is correctly formed.
        
        Args:
            func: The original function.
            tool: The FunctionTool created from the function.
        """
        if not hasattr(tool, "schema") or not isinstance(tool.schema, dict):
            return
        
        schema = tool.schema
        if "parameters" not in schema:
            return
            
        parameters = schema["parameters"]
        if "properties" not in parameters or "required" not in parameters:
            return
            
        properties = parameters["properties"]
        required = parameters["required"]
        
        # Ensure all required fields are in properties
        invalid_required = [field for field in required if field not in properties]
        if invalid_required:
            logger.warning(f"Function {tool.name} has required fields that are not in properties: {invalid_required}")
            # Fix the required array
            parameters["required"] = [field for field in required if field in properties]
    
    def _create_sanitized_function_tool(self, func: Callable) -> FunctionTool:
        """
        Create a sanitized function tool that will pass schema validation.
        
        Args:
            func: The function to create a tool from.
            
        Returns:
            A valid FunctionTool.
        """
        func_name = getattr(func, "__name__", "unknown_function")
        
        # Get function signature to derive parameters
        try:
            sig = inspect.signature(func)
            params = sig.parameters
            
            # Create a valid schema based on the function's signature
            properties = {}
            required = []
            
            for name, param in params.items():
                properties[name] = {
                    "type": "string",  # Default to string as a safe type
                    "description": f"Parameter {name} for function {func_name}"
                }
                
                # If parameter has no default value, mark it as required
                if param.default == inspect.Parameter.empty:
                    required.append(name)
            
            schema = {
                "name": func_name,
                "description": getattr(func, "__doc__", f"Function {func_name}"),
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required
                }
            }
            
            # Create a wrapper function that logs calls and returns an error message
            def safe_wrapper(*args, **kwargs):
                logger.warning(f"Called sanitized function {func_name}")
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    error_msg = f"Error in function {func_name}: {str(e)}"
                    logger.error(error_msg)
                    return error_msg
            
            # Add schema attributes to the wrapper
            safe_wrapper.schema = schema
            # The wrapper function needs to be callable
            safe_wrapper.__call__ = safe_wrapper
            
            # Create the tool
            tool = FunctionTool(
                name=func_name,
                description=schema["description"],
                params_json_schema=schema["parameters"],
                on_invoke_tool=lambda ctx, args: safe_wrapper(ctx, args)
            )
            
            return tool
        
        except Exception as e:
            logger.error(f"Error creating sanitized function tool for {func_name}: {str(e)}")
            
            # Create a minimal valid schema as fallback
            schema = {
                "name": func_name,
                "description": f"Function {func_name} (sanitized)",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            }
            
            # Create a no-op function
            def no_op_function(*args, **kwargs):
                return f"Error: Function {func_name} is unavailable due to schema validation issues."
            
            # Add schema attributes to the no-op function
            no_op_function.schema = schema
            
            # Return a no-op function tool
            return FunctionTool(
                name=func_name,
                description=schema["description"],
                params_json_schema=schema["parameters"],
                on_invoke_tool=lambda ctx, args: no_op_function()
            )
    
    @property
    def functions(self) -> List[Any]:
        """
        Get the list of functions associated with this agent.
        
        Returns:
            The list of functions that can be called by this agent.
        """
        return self._functions
    
    @functions.setter
    def functions(self, value: List[Any]) -> None:
        """
        Set the list of functions for this agent and update the tools accordingly.
        
        Args:
            value: The new list of functions.
        """
        self._functions = value
        
        # Update the tools based on the new functions
        self.tools = self._convert_functions_to_tools(value)
    
    def add_function(self, func: Any) -> None:
        """
        Add a function to the agent's list of functions and tools.
        
        Args:
            func: The function to add.
        """
        self._functions.append(func)
        
        # Add the function as a tool
        if isinstance(func, Tool):
            self.tools.append(func)
        else:
            try:
                # Import at function level to avoid circular import
                from agents import function_tool
                tool = function_tool(func)
                self._validate_function_schema(func, tool)
                self.tools.append(tool)
            except Exception as e:
                logger.error(f"Error adding function {getattr(func, '__name__', 'unknown')}: {str(e)}")
                self.tools.append(self._create_sanitized_function_tool(func))
    
    def remove_function(self, func_name: str) -> None:
        """
        Remove a function from the agent's list of functions and tools.
        
        Args:
            func_name: The name of the function to remove.
        """
        # Remove from functions list
        self._functions = [f for f in self._functions if 
                          (hasattr(f, '__name__') and f.__name__ != func_name) or
                          (hasattr(f, 'name') and f.name != func_name)]
        
        # Remove from tools list
        self.tools = [t for t in self.tools if t.name != func_name]
    
    def get_function(self, func_name: str) -> Optional[Any]:
        """
        Get a function by name.
        
        Args:
            func_name: The name of the function to get.
            
        Returns:
            The function if found, otherwise None.
        """
        for func in self._functions:
            if hasattr(func, '__name__') and func.__name__ == func_name:
                return func
            elif hasattr(func, 'name') and func.name == func_name:
                return func
        return None
    
    def set_tool_choice(self, tool_choice: Optional[str]) -> None:
        """
        Set the tool choice strategy for this agent.
        
        Args:
            tool_choice: The tool choice strategy to use.
        """
        # Update the model settings with the new tool choice
        self.model_settings = ModelSettings(
            tool_choice=tool_choice,
            parallel_tool_calls=self.model_settings.parallel_tool_calls,
            temperature=self.model_settings.temperature,
            top_p=self.model_settings.top_p,
            frequency_penalty=self.model_settings.frequency_penalty,
            presence_penalty=self.model_settings.presence_penalty,
            max_tokens=self.model_settings.max_tokens,
            truncation=self.model_settings.truncation
        )
    
    def set_parallel_tool_calls(self, parallel_tool_calls: bool) -> None:
        """
        Set whether to allow the agent to call multiple tools in parallel.
        
        Args:
            parallel_tool_calls: Whether to allow the agent to call multiple tools in parallel.
        """
        # Update the model settings with the new parallel tool calls setting
        self.model_settings = ModelSettings(
            tool_choice=self.model_settings.tool_choice,
            parallel_tool_calls=parallel_tool_calls,
            temperature=self.model_settings.temperature,
            top_p=self.model_settings.top_p,
            frequency_penalty=self.model_settings.frequency_penalty,
            presence_penalty=self.model_settings.presence_penalty,
            max_tokens=self.model_settings.max_tokens,
            truncation=self.model_settings.truncation
        )
    
    def clone(self, **kwargs) -> "BaseAgent[T]":
        """
        Create a copy of this agent with the given overrides.
        
        Args:
            **kwargs: Attributes to override in the cloned agent.
            
        Returns:
            A new BaseAgent instance with the specified overrides.
        """
        # Get all current parameters that aren't None
        current_params = {
            "name": self.name,
            "model": self.model,
            "instructions": self.instructions,
            "functions": self._functions.copy() if self._functions else [],
            "tool_choice": self.model_settings.tool_choice,
            "parallel_tool_calls": self.model_settings.parallel_tool_calls,
        }
        
        # Include max_tokens if it's set
        if hasattr(self.model_settings, 'max_tokens') and self.model_settings.max_tokens is not None:
            current_params["max_tokens"] = self.model_settings.max_tokens
        
        # Update with any provided kwargs
        current_params.update(kwargs)
        
        # Create a new instance with the updated parameters
        return BaseAgent(**current_params)
