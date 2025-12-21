"""
Unified logging configuration for AI-DIY application.
All logs go to development/src/logs/app.jsonl with proper rotation and structured format.
"""
import os
import json
import logging
import logging.handlers
from datetime import datetime
from typing import Optional, Dict, Any
import uuid


class JSONLFormatter(logging.Formatter):
    """Custom formatter that outputs structured JSON lines."""
    
    def __init__(self, channel: str = "app"):
        super().__init__()
        self.channel = channel
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON line."""
        log_entry = {
            "time": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "channel": self.channel,
            "message": record.getMessage()
        }
        
        # Add optional fields if available
        if hasattr(record, 'request_id'):
            log_entry["request_id"] = record.request_id
        if hasattr(record, 'session_id'):
            log_entry["session_id"] = record.session_id
        if hasattr(record, 'user_id'):
            log_entry["user_id"] = record.user_id
        if hasattr(record, 'route'):
            log_entry["route"] = record.route
        if hasattr(record, 'latency_ms'):
            log_entry["latency_ms"] = record.latency_ms
        if hasattr(record, 'error'):
            log_entry["error"] = record.error
        if hasattr(record, 'raw_preview'):
            log_entry["raw_preview"] = record.raw_preview

        return json.dumps(log_entry, ensure_ascii=False)


class StructuredLogger:
    """Wrapper for structured logging with context."""
    
    def __init__(self, logger: logging.Logger, channel: str):
        self.logger = logger
        self.channel = channel
        self.context = {}
    
    def set_context(self, **kwargs):
        """Set context fields for subsequent log entries."""
        self.context.update(kwargs)
    
    def clear_context(self):
        """Clear all context fields.""" 
        self.context.clear()
    
    def _log_with_context(self, level: int, message: str, **kwargs):
        """Log message with context and additional fields."""
        # Reserve standard logging kwargs so they are not placed in `extra`
        exc_info = kwargs.pop("exc_info", None)
        stack_info = kwargs.pop("stack_info", None)
        
        extra = {**self.context, **kwargs}
        self.logger.log(level, message, extra=extra, exc_info=exc_info, stack_info=stack_info)
    
    def info(self, message: str, **kwargs):
        self._log_with_context(logging.INFO, message, **kwargs)
    
    def debug(self, message: str, **kwargs):
        self._log_with_context(logging.DEBUG, message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        self._log_with_context(logging.WARNING, message, **kwargs)
    
    def error(self, message: str, **kwargs):
        self._log_with_context(logging.ERROR, message, **kwargs)


def setup_logging():
    """Set up unified logging configuration."""
    
    # Create logs directory if it doesn't exist
    log_dir = os.path.join(os.path.dirname(__file__), '..', 'logs')
    os.makedirs(log_dir, exist_ok=True)
    
    # Main JSONL log file with rotation
    log_file = os.path.join(log_dir, 'app.jsonl')
    
    # Get log level from environment (default to INFO for production)
    log_level_str = os.getenv("LOG_LEVEL", "INFO").upper()
    log_level = getattr(logging, log_level_str, logging.INFO)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)  # Root always at DEBUG, handlers control output
    
    # Remove any existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Console handler - human-friendly format
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)  # Respect LOG_LEVEL
    console_format = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(console_format)
    root_logger.addHandler(console_handler)
    
    # File handler - structured JSONL format with rotation
    file_handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=5 * 1024 * 1024,  # 5MB
        backupCount=5
    )
    file_handler.setLevel(logging.DEBUG)  # File always gets everything for post-mortem debugging
    file_formatter = JSONLFormatter(channel="app")
    file_handler.setFormatter(file_formatter)
    root_logger.addHandler(file_handler)
    
    return root_logger


def get_structured_logger(channel: str) -> StructuredLogger:
    """Get a structured logger for a specific channel."""
    logger = logging.getLogger(f"ai_diy.{channel}")
    return StructuredLogger(logger, channel)


# Environment-based OpenRouter logging configuration
OPENROUTER_LOG_PAYLOADS = os.getenv("OPENROUTER_LOG_PAYLOADS", "false").lower() in ("1", "true", "yes")
OPENROUTER_LOG_SAMPLE = float(os.getenv("OPENROUTER_LOG_SAMPLE", "0.0"))
OPENROUTER_LOG_MAX_CHARS = int(os.getenv("OPENROUTER_LOG_MAX_CHARS", "2000"))

# User logging configuration
USER_LOG_ENABLED = os.getenv("USER_LOG_ENABLED", "false").lower() in ("1", "true", "yes")
USER_LOG_ID = os.getenv("USER_LOG_ID", "anonymous")
USER_LOG_LEVEL = getattr(logging, os.getenv("USER_LOG_LEVEL", "INFO").upper(), logging.INFO)


def log_openrouter_call(
    model: str,
    tokens_in: int,
    tokens_out: int,
    status: str,
    latency_ms: float,
    cost_estimate: float = 0.0,
    prompt_hash: Optional[str] = None,
    response_hash: Optional[str] = None,
    payload: Optional[Dict[str, Any]] = None,
    response: Optional[Dict[str, Any]] = None,
    error: Optional[str] = None
):
    """Log OpenRouter API call with proper redaction and sampling."""
    
    # Skip if sampling is enabled and we don't hit the sample rate
    if OPENROUTER_LOG_SAMPLE > 0.0:
        import random
        if random.random() > OPENROUTER_LOG_SAMPLE:
            return
    
    logger = get_structured_logger("openrouter")
    
    log_data = {
        "model": model,
        "tokens_in": tokens_in,
        "tokens_out": tokens_out,
        "status": status,
        "latency_ms": latency_ms,
        "cost_estimate": cost_estimate
    }
    
    if error:
        log_data["error"] = error
    
    # Add hashes for correlation when payloads are disabled
    if not OPENROUTER_LOG_PAYLOADS:
        if prompt_hash:
            log_data["prompt_hash"] = prompt_hash
        if response_hash:
            log_data["response_hash"] = response_hash
    else:
        # Include payloads if enabled (with truncation)
        if payload:
            payload_str = json.dumps(payload)
            if len(payload_str) > OPENROUTER_LOG_MAX_CHARS:
                payload_str = payload_str[:OPENROUTER_LOG_MAX_CHARS] + "..."
            log_data["payload"] = payload_str
        
        if response:
            response_str = json.dumps(response)
            if len(response_str) > OPENROUTER_LOG_MAX_CHARS:
                response_str = response_str[:OPENROUTER_LOG_MAX_CHARS] + "..."
            log_data["response"] = response_str
    
    logger.info("OpenRouter API call", **log_data)


def log_user_action(action: str, **kwargs):
    """Log user action if user logging is enabled."""
    if not USER_LOG_ENABLED:
        return
    
    logger = get_structured_logger("user")
    logger.set_context(user_id=USER_LOG_ID)
    
    if logger.logger.isEnabledFor(USER_LOG_LEVEL):
        logger._log_with_context(USER_LOG_LEVEL, f"User action: {action}", **kwargs)


# Initialize logging on import
setup_logging()
