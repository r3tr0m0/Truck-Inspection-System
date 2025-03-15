"""
External Services Configuration Module

This module manages configuration settings for external services used by the application,
including Skyhawk integration and email notification services through SendGrid.
Sensitive credentials are loaded from environment variables for security.
"""

import os
from dotenv import load_dotenv

# Load service credentials from environment variables
load_dotenv()

class SkyhawkConfig:
    """
    Skyhawk API integration configuration.
    
    This class manages the configuration settings required to interact with
    the Skyhawk API service, including authentication credentials and base URL.
    All sensitive information is loaded from environment variables.
    
    Attributes:
        BASE_URL (str): Skyhawk API base URL
        COMPANY_ID (str): Company identifier for Skyhawk API
        USERNAME (str): Authentication username for API access
        PASSWORD (str): Authentication password for API access
    """
    BASE_URL = os.getenv('SKYHAWK_BASE_URL')
    COMPANY_ID = os.getenv('SKYHAWK_COMPANY_ID')
    USERNAME = os.getenv('SKYHAWK_USERNAME')
    PASSWORD = os.getenv('SKYHAWK_PASSWORD')

class EmailConfig:
    """
    Email notification service configuration.
    
    This class manages the configuration for sending email notifications
    through SendGrid's email service. It includes API authentication,
    sender details, and recipient information.
    
    Attributes:
        API_KEY (str): SendGrid API key for authentication
        SENDER_EMAIL (str): Default sender email address
        SENDER_NAME (str): Display name for the email sender
        RECIPIENT_EMAILS (list): List of primary recipient email addresses
        FALLBACK_EMAIL (str): Backup email address for critical notifications
    
    Note:
        The API key is loaded from environment variables for security,
        while other email settings are hardcoded for consistent notification routing.
    """
    API_KEY = os.getenv('SENDGRID_API_KEY')
    SENDER_EMAIL = 'dgcscanner@dawsongroup.ca'
    SENDER_NAME = 'Skyhawk Notifications'
    RECIPIENT_EMAILS = ['ymabbas112@gmail.com','t00640237@mytru.ca']
    FALLBACK_EMAIL = 'ymabbas11@gmail.com'
