"""
Application Configuration Module

This module manages different configuration settings for various environments
(development, production, testing). It uses environment variables loaded from
a .env file to configure the application settings securely.
"""

import os
import logging
from dotenv import load_dotenv

# Load environment variables from .env file if present
load_dotenv()

# Set up module-level logging
logger = logging.getLogger(__name__)

class Config:
    """
    Base configuration class that defines default settings.
    All environment-specific configurations inherit from this class.
    
    Attributes:
        SECRET_KEY (str): Application's secret key for security features
        DEBUG (bool): Flag to enable/disable debug mode
        TESTING (bool): Flag to enable/disable testing mode
    """
    SECRET_KEY = os.getenv('SECRET_KEY', 'default-dev-key')
    DEBUG = False
    TESTING = False

class DevelopmentConfig(Config):
    """
    Development environment configuration.
    Enables debug mode for detailed error messages and hot reloading.
    """
    DEBUG = True

class ProductionConfig(Config):
    """
    Production environment configuration.
    Ensures secure settings with debug mode disabled.
    """
    DEBUG = False

class TestingConfig(Config):
    """
    Testing environment configuration.
    Enables testing mode for unit tests and integration tests.
    """
    TESTING = True

def get_config():
    """
    Factory function to get the appropriate configuration based on FLASK_ENV.
    
    Returns:
        Config: An instance of the appropriate configuration class
        (DevelopmentConfig, ProductionConfig, or TestingConfig)
    
    Note:
        Defaults to DevelopmentConfig if FLASK_ENV is not set or invalid
    """
    env = os.getenv('FLASK_ENV', 'development')
    config_map = {
        'development': DevelopmentConfig,
        'production': ProductionConfig,
        'testing': TestingConfig
    }

    if env not in config_map:
        logger.warning(f"Unknown environment '{env}' specified. Defaulting to 'development'.")
    else:
        logger.info(f"Loading configuration for environment: {env}")
        
    return config_map.get(env, DevelopmentConfig)
