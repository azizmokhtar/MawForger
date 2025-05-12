import logging
import os
from logging.handlers import RotatingFileHandler

# Create logs directory if it doesn't exist
os.makedirs("logs", exist_ok=True)

def get_logger(name=None):
    """
    Creates and returns a configured logger instance.
    
    Usage:
        logger = get_logger(__name__)
        logger.info("Bot started")
        logger.warning("Market volatility detected")
        logger.error("Order failed", exc_info=True)
    """
    # Create or get the logger
    logger = logging.getLogger(name or "default_logger")

    # Avoid duplicate handlers (important in reload/dev mode)
    if not logger.handlers:
        # Set default log level from environment or fallback to INFO
        log_level = os.getenv("LOG_LEVEL", "INFO").upper()
        logger.setLevel(getattr(logging, log_level, logging.INFO))

        # Define log format
        formatter = logging.Formatter(
            fmt='%(asctime)s - %(levelname)s - [%(module)s] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

        # File handler with rotation
        file_handler = RotatingFileHandler(
            filename=os.path.join("logs", "bot.log"),
            maxBytes=5 * 1024 * 1024,  # 5 MB
            backupCount=5,
            encoding="utf-8"
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger