"""
Application Constants Module

This module defines all the constant values used throughout the application,
including API endpoints and default application settings. Constants are loaded
from environment variables where appropriate for security and flexibility.
"""

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Base URL for the DRM (Driver Resource Management) API
# This should be set in the .env file for each environment
DRM_BASE_URL = os.getenv('DRM_BASE_URL')

# API endpoint URLs constructed from the base URL
# These endpoints are used for different aspects of the application
DRM_BASE_URL_TRIP_INSPECTION = f"{DRM_BASE_URL}/recentTripInspection"  # Endpoint for recent trip inspection data
SUPERVISOR_API_URL = f"{DRM_BASE_URL}/supervisors"  # Endpoint for supervisor-related operations
YARD_API_URL = f"{DRM_BASE_URL}/yards"  # Endpoint for yard management operations

# Default application settings
# These values are used as fallbacks if not specified in the configuration
DEFAULT_SETTINGS = {
    'inspection_period_hours': 24,      # Time period for inspection checks (in hours)
    'no_geofence_alert_period': 48,     # Time threshold for geofence alerts (in hours)
    'no_modem_alert_threshold': 3,      # Number of failed attempts before modem alert
    'send_no_modem_alerts': 'false',    # Toggle for modem alert notifications
    'send_no_geofence_alerts': 'false', # Toggle for geofence alert notifications
    'app_mode': 'development',          # Application running mode
    'check_movement_before_email': 'false'  # Toggle for movement verification before sending emails
}
