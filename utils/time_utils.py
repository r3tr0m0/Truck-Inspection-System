"""
Utility module for handling time-related operations and conversions.

This module provides functionality for:
- Converting UTC timestamps to Pacific time
- Determining work shifts based on time
- Formatting time differences for display
- Handling timezone conversions with pytz

The module includes comprehensive error handling and logging
for debugging time-related operations.
"""

import logging
import pytz
from datetime import datetime

def format_pacific_time(utc_time_str):
    """
    Convert a UTC ISO format time string to Pacific time with friendly formatting.
    
    Args:
        utc_time_str (str): UTC timestamp in ISO format (e.g., '2024-12-13T15:30:00Z')
    
    Returns:
        str: Formatted time string in Pacific time (e.g., 'December 13, 2024 - 07:30 AM PST')
             Returns 'N/A' if input is invalid or conversion fails
    
    Notes:
        - Handles ISO format strings with 'Z' timezone indicator
        - Converts to America/Los_Angeles timezone
        - Returns month, day, year, and 12-hour time with AM/PM
        - Includes comprehensive error handling
    """
    logging.info(f"Formatting UTC time string to Pacific time: {utc_time_str}")
    if not utc_time_str:
        logging.warning("Empty UTC time string provided, returning N/A")
        return "N/A"
    try:
        utc_time = datetime.fromisoformat(utc_time_str.replace("Z", "+00:00"))
        logging.debug(f"Parsed UTC time: {utc_time}")
        
        pacific = pytz.timezone("America/Los_Angeles")
        pacific_time = utc_time.astimezone(pacific)
        logging.debug(f"Converted to Pacific time: {pacific_time}")
        
        formatted_time = pacific_time.strftime("%B %d, %Y - %I:%M %p %Z")
        logging.info(f"Formatted result: {formatted_time}")
        return formatted_time
    except Exception as e:
        logging.error(f"Error formatting time {utc_time_str}: {e}")
        return "N/A"

def determine_shift(alert_time):
    """
    Determine the work shift based on the time in Pacific timezone.
    
    Args:
        alert_time (datetime): The time to determine shift for, 
                             can be in any timezone with tzinfo
    
    Returns:
        str: Shift description with time range:
            - "Morning Shift (6AM - 2PM)" for 6:00-13:59
            - "Afternoon Shift (2PM - 10PM)" for 14:00-21:59
            - "Night Shift (10PM - 6AM)" for 22:00-5:59
            Returns "Unknown Shift" if conversion fails
    
    Notes:
        - Automatically converts input time to Pacific timezone
        - Uses 24-hour format internally for calculations
        - Handles timezone-aware datetime objects
    """
    logging.info(f"Determining shift for time: {alert_time}")
    try:
        pacific_time = alert_time.astimezone(pytz.timezone("America/Los_Angeles"))
        logging.debug(f"Converted to Pacific time: {pacific_time}")
        
        hour = pacific_time.hour
        logging.debug(f"Hour in Pacific time: {hour}")
        
        if 6 <= hour < 14:
            shift = "Morning Shift (6AM - 2PM)"
        elif 14 <= hour < 22:
            shift = "Afternoon Shift (2PM - 10PM)"
        else:
            shift = "Night Shift (10PM - 6AM)"
            
        logging.info(f"Determined shift: {shift}")
        return shift
    except Exception as e:
        logging.error(f"Error determining shift for time {alert_time}: {e}")
        return "Unknown Shift"

def format_time_difference(time_diff_str):
    """
    Format a PostgreSQL time interval string into a human-readable duration.
    
    Args:
        time_diff_str (str): PostgreSQL interval string in format 'HH:MM:SS'
    
    Returns:
        str: Formatted duration string with appropriate units:
            - "Xh Ym" for durations >= 1 hour
            - "Xm Ys" for durations < 1 hour
            - "Xs" for durations < 1 minute
            Returns 'N/A' if input is empty or invalid
    
    Notes:
        - Designed to work with PostgreSQL age() function output
        - Intelligently selects most relevant time units
        - Handles floating point seconds
        - Returns original string if parsing fails
    """
    if not time_diff_str:
        return "N/A"
    try:
        # PostgreSQL age() function returns interval like '00:10:30'
        parts = time_diff_str.split(':')
        hours = int(parts[0])
        minutes = int(parts[1])
        seconds = int(float(parts[2]))
        
        if hours > 0:
            return f"{hours}h {minutes}m"
        elif minutes > 0:
            return f"{minutes}m {seconds}s"
        else:
            return f"{seconds}s"
    except Exception as e:
        logging.error(f"Error formatting time difference: {e}")
        return str(time_diff_str)
