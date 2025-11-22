import sys

from loguru import logger

from github_metrics.config.settings import get_settings

settings = get_settings()


def setup_logging() -> None:
    """
    Configure logging for the application.
    """

    # Remove default handler to avoid duplicate logs
    logger.remove()

    # Console handler - for development/debugging
    logger.add(
        sys.stderr,
        level=settings.logging_level,
        format=settings.logging_format,
        colorize=False,
        backtrace=True,
        diagnose=True,
        enqueue=True,
        catch=True,
    )

    # Configure common context (can be overridden per module)
    logger.configure(extra={"app": settings.app_name, "version": settings.app_version})

    # Log startup message
    logger.info(
        "Logging system initialized",
        log_level=settings.logging_level,
    )
