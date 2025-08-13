"""Human-readable logging configuration."""

import logging
import sys
from contextvars import ContextVar
from datetime import datetime
from uuid import uuid4

from .config import settings

# Context variable for correlation ID
correlation_id_var: ContextVar[str | None] = ContextVar("correlation_id", default=None)


class ColorFormatter(logging.Formatter):
    """Colored formatter for better readability."""

    # Color codes
    COLORS = {
        "DEBUG": "\033[36m",  # Cyan
        "INFO": "\033[32m",  # Green
        "WARNING": "\033[33m",  # Yellow
        "ERROR": "\033[31m",  # Red
        "CRITICAL": "\033[35m",  # Magenta
        "RESET": "\033[0m",  # Reset color
        "BOLD": "\033[1m",  # Bold
        "DIM": "\033[2m",  # Dim
    }

    def format(self, record: logging.LogRecord) -> str:
        """Format log record with colors and clear structure."""
        # Get correlation ID
        correlation_id = correlation_id_var.get()

        # Format timestamp
        timestamp = datetime.fromtimestamp(record.created).strftime("%H:%M:%S.%f")[:-3]

        # Color for level
        level_color = self.COLORS.get(record.levelname, "")
        reset = self.COLORS["RESET"]
        bold = self.COLORS["BOLD"]
        dim = self.COLORS["DIM"]

        # Format correlation ID part
        correlation_part = ""
        if correlation_id:
            short_id = correlation_id[:8]
            correlation_part = f" [{dim}{short_id}{reset}]"

        # Format module.function
        location = f"{record.module}.{record.funcName}"

        # Build the log message
        message = (
            f"{dim}{timestamp}{reset} "
            f"{level_color}{bold}{record.levelname:8}{reset}"
            f"{correlation_part} "
            f"{dim}{location:30}{reset} | "
            f"{record.getMessage()}"
        )

        # Add exception info if present
        if record.exc_info:
            message += f"\n{self.formatException(record.exc_info)}"

        return message


class SimpleFormatter(logging.Formatter):
    """Simple formatter without colors for production."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record without colors."""
        # Get correlation ID
        correlation_id = correlation_id_var.get()

        # Format timestamp
        timestamp = datetime.fromtimestamp(record.created).strftime("%H:%M:%S.%f")[:-3]

        # Format correlation ID part
        correlation_part = ""
        if correlation_id:
            short_id = correlation_id[:8]
            correlation_part = f" [{short_id}]"

        # Format module.function
        location = f"{record.module}.{record.funcName}"

        # Build the log message
        message = (
            f"{timestamp} "
            f"{record.levelname:8}"
            f"{correlation_part} "
            f"{location:30} | "
            f"{record.getMessage()}"
        )

        # Add exception info if present
        if record.exc_info:
            message += f"\n{self.formatException(record.exc_info)}"

        return message


def setup_logging() -> None:
    """Set up human-readable logging."""
    # Choose formatter based on environment
    if sys.stdout.isatty():
        # Terminal with color support
        formatter = ColorFormatter()
    else:
        # Production or file logging - no colors
        formatter = SimpleFormatter()

    # Set up handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.handlers = [handler]
    root_logger.setLevel(getattr(logging, settings.log_level.upper()))

    # Reduce noise from external libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("langchain").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance."""
    return logging.getLogger(name)


def generate_correlation_id() -> str:
    """Generate a new correlation ID."""
    return str(uuid4())


def set_correlation_id(correlation_id: str) -> None:
    """Set correlation ID in context."""
    correlation_id_var.set(correlation_id)


def get_correlation_id() -> str | None:
    """Get current correlation ID from context."""
    return correlation_id_var.get()
