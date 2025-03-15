"""
Flask application entry point for the vehicle tracking and monitoring system.

This module provides functionality for:
- Flask application initialization and configuration
- Blueprint registration for modular routing
- Service initialization (Skyhawk, Email)
- Database connection pool management
- Logging configuration and error handling

Key Components:
- Flask application factory pattern
- Blueprint-based route organization
- Service dependency injection
- Database connection pooling
- Comprehensive error logging

The module is designed to run on Heroku and includes
proper port configuration and production settings.
"""

import os
import requests
import psycopg2 
import logging
from datetime import datetime, timezone, timedelta
from flask import Flask, request, jsonify, render_template_string, redirect, url_for, flash, render_template, Blueprint
import sendgrid
from sendgrid.helpers.mail import Mail, Email, To, Content
import pytz
import time
from geopy.distance import geodesic
from urllib.parse import quote

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import routes
logger.info("Starting to import route blueprints")
try:
    from routes import (
        geofence_bp,
        settings_bp,
        home_bp,
        production_bp
    )
    from background_tasks import movement_checker
    from services import init_services
    logger.info("Successfully imported all route blueprints")
except ImportError as e:
    logger.error(f"Failed to import route blueprints: {e}")
    raise

try:
    logger.info("Attempting to import configuration")
    from config import (
        DatabaseConfig,
        SkyhawkConfig,
        EmailConfig,
        get_config,
        DRM_BASE_URL_TRIP_INSPECTION,
        SUPERVISOR_API_URL,
        YARD_API_URL,
        DEFAULT_SETTINGS
    )
except ImportError as e:
    logger.error(f"Failed to import configuration: {e}")
    logger.debug(f"Current PYTHONPATH: {os.environ.get('PYTHONPATH')}")
    logger.debug(f"Current directory: {os.getcwd()}")
    logger.debug(f"Directory contents: {os.listdir()}")
    if os.path.exists('config'):
        logger.debug(f"Config directory contents: {os.listdir('config')}")
    raise

# Initialize database pool
DatabaseConfig.init_pool()

def create_app():
    """
    Flask application factory function.
    
    Creates and configures a Flask application instance with:
    - Configuration loading from environment
    - Service initialization (Skyhawk and Email)
    - Blueprint registration for routes
    - Database pool initialization
    
    Returns:
        Flask: Configured Flask application instance
    
    Notes:
        - Uses factory pattern for flexible instantiation
        - Initializes services and makes them available in app context
        - Registers all route blueprints
        - Includes comprehensive error logging
        - Sets up database connection pooling
    """
    logger.info("Starting Flask application creation")
    app = Flask(__name__)
    app.config.from_object(get_config())
    logger.debug("Loaded configuration into Flask app")

    # Initialize services
    logger.info("Initializing services")
    skyhawk_service, email_service = init_services()

    # Make services available to the application context
    app.config['SKYHAWK_SERVICE'] = skyhawk_service
    app.config['EMAIL_SERVICE'] = email_service

    # Register blueprints
    logger.info("Registering blueprints")
    app.register_blueprint(geofence_bp)
    app.register_blueprint(settings_bp, url_prefix='/settings')
    app.register_blueprint(home_bp)
    app.register_blueprint(production_bp)
    logger.info("Application creation completed")
    return app

# Create the Flask application instance
app = create_app()

if __name__ == '__main__':
    # Get port from environment variable or use 5000 as default
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
