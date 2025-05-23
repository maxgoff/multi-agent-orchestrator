from typing import Union, AsyncIterable, Optional, Any, TypeAlias
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from multi_agent_orchestrator.types import ConversationMessage
from multi_agent_orchestrator.utils import Logger

# Type aliases for complex types
AgentParamsType: TypeAlias = dict[str, Any]
AgentOutputType: TypeAlias = Union[str, "AgentStreamResponse", Any]  # Forward reference

@dataclass
class AgentProcessingResult:
    """
    Contains metadata about the result of an agent's processing.

    Attributes:
        user_input: The original input from the user
        agent_id: Unique identifier for the agent
        agent_name: Display name of the agent
        user_id: Identifier for the user
        session_id: Identifier for the current session
        additional_params: Optional additional parameters for the agent
    """
    user_input: str
    agent_id: str
    agent_name: str
    user_id: str
    session_id: str
    additional_params: AgentParamsType = field(default_factory=dict)


@dataclass
class AgentStreamResponse:
    """
    Represents a streaming response from an agent.

    Attributes:
        text: The current text in the stream
        final_message: The complete message when streaming is complete
    """
    text: str = ""
    final_message: Optional[ConversationMessage] = None


@dataclass
class AgentResponse:
    """
    Complete response from an agent, including metadata and output.

    Attributes:
        metadata: Processing metadata
        output: The actual output from the agent
        streaming: Whether this response is streaming
    """
    metadata: AgentProcessingResult
    output: AgentOutputType
    streaming: bool


class AgentCallbacks:
    """
    Defines callbacks that can be triggered during agent processing.
    Provides default implementations that can be overridden by subclasses.
    """
    def on_llm_new_token(self, token: str) -> None:
        """
        Called when a new token is generated by the LLM.

        Args:
            token: The new token generated
        """
        pass  # Default implementation does nothing


@dataclass
class AgentOptions:
    """
    Configuration options for an agent.

    Attributes:
        name: The display name of the agent
        description: A description of the agent's purpose and capabilities
        save_chat: Whether to save the chat history
        callbacks: Optional callbacks for agent events
        LOG_AGENT_DEBUG_TRACE: Whether to enable debug tracing for this agent
    """
    name: str
    description: str
    save_chat: bool = True
    callbacks: Optional[AgentCallbacks] = None
    # Optional: Flag to enable/disable agent debug trace logging
    # If true, the agent will log additional debug information
    LOG_AGENT_DEBUG_TRACE: Optional[bool] = False

class Agent(ABC):
    """
    Abstract base class for all agents in the system.

    Implements common functionality and defines the required interface
    for concrete agent implementations.
    """

    def __init__(self, options: AgentOptions):
        """
        Initialize a new agent with the given options.

        Args:
            options: Configuration options for this agent
        """
        self.name = options.name
        self.id = self.generate_key_from_name(options.name)
        self.description = options.description
        self.save_chat = options.save_chat
        self.callbacks = options.callbacks if options.callbacks is not None else AgentCallbacks()
        self.log_debug_trace = options.LOG_AGENT_DEBUG_TRACE

    def is_streaming_enabled(self) -> bool:
        """
        Whether this agent supports streaming responses.

        Returns:
            True if streaming is enabled, False otherwise
        """
        return False

    @staticmethod
    def generate_key_from_name(name: str) -> str:
        """
        Generate a standardized key from an agent name.

        Args:
            name: The display name to convert

        Returns:
            A lowercase, hyphenated key with special characters removed
        """
        # Remove special characters and replace spaces with hyphens
        key = re.sub(r"[^a-zA-Z0-9\s-]", "", name)
        key = re.sub(r"\s+", "-", key)
        return key.lower()

    @abstractmethod
    async def process_request(
        self,
        input_text: str,
        user_id: str,
        session_id: str,
        chat_history: list[ConversationMessage],
        additional_params: Optional[AgentParamsType] = None,
    ) -> Union[ConversationMessage, AsyncIterable[AgentOutputType]]:
        """
        Process a user request and generate a response.

        Args:
            input_text: The user's input text
            user_id: Identifier for the user
            session_id: Identifier for the current session
            chat_history: List of previous messages in the conversation
            additional_params: Optional additional parameters

        Returns:
            Either a complete message or an async iterable for streaming responses
        """
        pass

    def log_debug(self, class_name: str, message: str, data: Any = None) -> None:
        """
        Log a debug message if debug tracing is enabled.

        Args:
            class_name: Name of the class logging the message
            message: The message to log
            data: Optional data to include in the log
        """
        if self.log_debug_trace:
            prefix = f"> {class_name} \n> {self.name} \n>"
            if data:
                Logger.info(f"{prefix} {message} \n> {data}")
            else:
                Logger.info(f"{prefix} {message} \n>")