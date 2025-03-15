"""
Routes Package Initialization

This module initializes the Flask Blueprint routing system for the application.
It imports and exposes all route blueprints, organizing the application's
URL endpoints into logical groups for better maintainability.

Blueprints:
    - production_bp: Routes for production-related operations
    - geofence_bp: Routes for geofence management and monitoring
    - settings_bp: Routes for application settings management
    - home_bp: Routes for the main landing pages
"""

from .production_routes import production_bp    # Production management endpoints
from .geofence_routes import geofence_bp       # Geofence monitoring endpoints
from .settings_routes import settings_bp       # Settings configuration endpoints
from .home_routes import home_bp              # Main application pages

# Define public API for the routes package
__all__ = [
    'production_bp',    # Blueprint for production operations
    'geofence_bp',     # Blueprint for geofence operations
    'settings_bp',     # Blueprint for settings management
    'home_bp'          # Blueprint for main pages
]
