"""
Services Module

This module provides centralized initialization and management of external services
used throughout the application. It handles the setup and configuration of:
- Email Service: For sending notifications and alerts
- Skyhawk Service: For interacting with the Skyhawk API for vehicle tracking

The module ensures proper initialization order and error handling for all services,
loading their configurations from environment variables through the config module.

Key Features:
- Centralized service initialization
- Configuration management
- Error handling and logging
- Circular import prevention
"""

import logging
from config import EmailConfig, SkyhawkConfig

logger = logging.getLogger(__name__)

# Import services after config to avoid circular imports
from .email import EmailService
from .skyhawk import SkyhawkService

__all__ = ['EmailService', 'SkyhawkService']

def init_services():
    """
    Initialize all application services with their respective configurations.
    
    This function handles the initialization of both the EmailService and 
    SkyhawkService, ensuring they are properly configured with their
    respective settings from the config module.
    
    Returns:
        tuple: A tuple containing (SkyhawkService, EmailService) instances
        
    Raises:
        Exception: If any service fails to initialize properly. The specific
                  exception details will be logged before being re-raised.
    
    Example:
        >>> skyhawk_service, email_service = init_services()
        >>> skyhawk_service.get_vehicle_status("VehicleID123")
        >>> email_service.send_alert("Alert message")
    """
    try:
        # Initialize email service with configuration
        email_service = EmailService(
            api_key=EmailConfig.API_KEY,
            sender_email=EmailConfig.SENDER_EMAIL,
            recipient_emails=EmailConfig.RECIPIENT_EMAILS,
            sender_name=EmailConfig.SENDER_NAME,
            fallback_email=EmailConfig.FALLBACK_EMAIL
        )
        logger.info("EmailService initialized successfully")

        # Initialize Skyhawk service with configuration
        skyhawk_service = SkyhawkService(
            base_url=SkyhawkConfig.BASE_URL,
            company_id=SkyhawkConfig.COMPANY_ID,
            username=SkyhawkConfig.USERNAME,
            password=SkyhawkConfig.PASSWORD
        )
        logger.info("SkyhawkService initialized successfully")

        return skyhawk_service, email_service
    except Exception as e:
        logger.error(f"Error initializing services: {e}", exc_info=True)
        raise
