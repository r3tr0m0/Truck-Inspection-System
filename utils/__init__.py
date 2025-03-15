"""
Utilities Package

This package provides a collection of utility functions used throughout the application
for common operations such as:
- Alert processing and distance calculations
- Inspection status management
- Application settings handling
- Time formatting and shift determination
- Yard and supervisor data management

Each module in this package focuses on a specific domain of functionality:

alert_utils:
    Functions for processing geofence alerts and calculating distances between
    coordinates.

inspection_utils:
    Functions for managing and querying vehicle inspection records and statuses.

settings_utils:
    Functions for managing application-wide settings and configurations.

time_utils:
    Functions for handling time zones, formatting timestamps, and determining
    work shifts.

yard_utils:
    Functions for managing yard locations and supervisor assignments.
"""

from .alert_utils import calculate_distance, log_geofence_alert
from .inspection_utils import get_inspection_status, get_recent_trip_inspection
from .settings_utils import get_setting, update_setting
from .time_utils import format_pacific_time, determine_shift
from .yard_utils import get_yard_coordinates, get_supervisor_for_yard

__all__ = [
    # Alert processing functions
    'calculate_distance',      # Calculate distance between two geographic points
    'log_geofence_alert',      # Log a geofence violation alert
    
    # Inspection management functions
    'get_inspection_status',   # Get current inspection status for a vehicle
    'get_recent_trip_inspection',  # Get most recent trip inspection record
    
    # Settings management functions
    'get_setting',            # Retrieve an application setting
    'update_setting',         # Update an application setting
    
    # Time handling functions
    'format_pacific_time',    # Format timestamp in Pacific timezone
    'determine_shift',        # Determine current work shift based on time
    
    # Yard management functions
    'get_yard_coordinates',   # Get geographic coordinates for a yard
    'get_supervisor_for_yard' # Get supervisor information for a yard
]
