"""
Configuration Module for Dawson Project

This module serves as the central configuration hub for the application.
It imports and exposes all configuration-related classes and constants,
making them easily accessible throughout the application.
"""

import logging

# Configure application-wide logging with INFO level
# This ensures consistent logging behavior across the application
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

try:
    # Import configuration classes for different components
    from .database import DatabaseConfig  # Database connection settings
    from .services import SkyhawkConfig, EmailConfig  # External service configurations
    from .app_config import get_config, Config, DevelopmentConfig, ProductionConfig  # Environment-specific configs
    from .constants import (  # API endpoints and default settings
        DRM_BASE_URL_TRIP_INSPECTION,
        SUPERVISOR_API_URL,
        YARD_API_URL,
        DEFAULT_SETTINGS
    )

    logger.info("All configurations and constants imported successfully.")

except ImportError as e:
    # Log detailed error information if any configuration imports fail
    logger.error(f"Error importing configurations or constants: {e}")
    raise

# Define public API for the config package
# These are the only symbols that will be imported when using 'from config import *'
__all__ = [
    'DatabaseConfig',
    'SkyhawkConfig',
    'EmailConfig',
    'get_config',
    'Config',
    'DevelopmentConfig',
    'ProductionConfig',
    'DRM_BASE_URL_TRIP_INSPECTION',
    'SUPERVISOR_API_URL',
    'YARD_API_URL',
    'DEFAULT_SETTINGS'
]
