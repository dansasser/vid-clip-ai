"""
Base Agent - Abstract class that all pipeline agents inherit from.

Provides:
- Common interface for all agents
- Logging infrastructure
- Error handling patterns
- User context propagation
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from datetime import datetime
import logging


class BaseAgent(ABC):
    """
    Abstract base class for all pipeline agents.

    All agents must implement the `execute` method and follow the
    structured input/output contract defined in their docstrings.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize agent with optional configuration.

        Args:
            config: Agent-specific configuration dictionary
        """
        self.config = config or {}
        self.logger = self._setup_logger()
        self.name = self.__class__.__name__

    def _setup_logger(self) -> logging.Logger:
        """Set up logger for this agent."""
        logger = logging.getLogger(self.__class__.__name__)
        logger.setLevel(logging.INFO)
        return logger

    @abstractmethod
    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the agent's primary function.

        Args:
            context: Execution context containing:
                - video_id: Unique video identifier
                - user_id: User identifier for scoping
                - base_path: User's base directory path
                - Additional agent-specific inputs

        Returns:
            Dictionary containing:
                - success: Boolean indicating success/failure
                - data: Agent-specific output data
                - errors: List of error messages if any
                - metadata: Additional metadata about execution
        """
        pass

    def log_start(self, context: Dict[str, Any]) -> None:
        """Log the start of agent execution."""
        self.logger.info(
            f"{self.name} started - video_id: {context.get('video_id')}, "
            f"user_id: {context.get('user_id')}"
        )

    def log_complete(self, context: Dict[str, Any], duration: float) -> None:
        """Log successful completion."""
        self.logger.info(
            f"{self.name} completed in {duration:.2f}s - "
            f"video_id: {context.get('video_id')}"
        )

    def log_error(self, context: Dict[str, Any], error: Exception) -> None:
        """Log execution error."""
        self.logger.error(
            f"{self.name} failed - video_id: {context.get('video_id')}, "
            f"error: {str(error)}"
        )

    def validate_context(self, context: Dict[str, Any], required_keys: list) -> None:
        """
        Validate that required keys are present in context.

        Args:
            context: Execution context to validate
            required_keys: List of required key names

        Raises:
            ValueError: If required keys are missing
        """
        missing = [key for key in required_keys if key not in context]
        if missing:
            raise ValueError(f"Missing required context keys: {missing}")
