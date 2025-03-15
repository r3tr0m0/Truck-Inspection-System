"""
Utility module for handling vehicle inspection related operations.

This module provides functionality for:
- Retrieving and validating vehicle inspection status
- Calculating time differences between inspections
- Fetching recent trip inspection data from DRM API

The module handles timezone conversions, date parsing, and API interactions
while providing comprehensive logging for debugging and monitoring.
"""

import pytz
import requests
import logging
from datetime import datetime
from config import DRM_BASE_URL_TRIP_INSPECTION
from utils.settings_utils import get_setting

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('inspection_utils')

def get_inspection_status(completion_date, alert_time):
    logger.info(f"Getting inspection status for completion_date: {completion_date}, alert_time: {alert_time}")
    
    if not completion_date:
        logger.warning("No completion date provided")
        return "Inspection was not completed ✗", False
        
    pacific = pytz.timezone("America/Los_Angeles")
    
    try:
        # Convert alert_time to PST
        alert_time_pst = alert_time.astimezone(pacific)
        logger.debug(f"Alert time in PST: {alert_time_pst}")
        
        # Parse inspection time carefully
        logger.debug(f"Parsing inspection time from: {completion_date}")
        if isinstance(completion_date, datetime):
            inspection_time = completion_date
        else:
            cleaned_date = completion_date.rstrip('Z')
            logger.debug(f"Cleaned date string: {cleaned_date}")
            if '+' in cleaned_date or '-' in cleaned_date:
                inspection_time = datetime.fromisoformat(cleaned_date)
            else:
                inspection_time = datetime.fromisoformat(cleaned_date)
        
        if inspection_time.tzinfo is None:
            logger.debug("Localizing naive datetime to PST")
            inspection_time = pacific.localize(inspection_time)
        
        logger.debug(f"Final inspection time: {inspection_time}")
        
        time_difference = alert_time_pst - inspection_time
        total_seconds = abs(time_difference.total_seconds())
        logger.debug(f"Time difference in seconds: {total_seconds}")
        
        hours = int(total_seconds // 3600)
        minutes = int((total_seconds % 3600) // 60)
        seconds = int(total_seconds % 60)
        
        time_parts = []
        if hours > 0:
            time_parts.append(f"{hours} hour{'s' if hours != 1 else ''}")
        if minutes > 0:
            time_parts.append(f"{minutes} minute{'s' if minutes != 1 else ''}")
        if seconds > 0 or not time_parts:
            time_parts.append(f"{seconds} second{'s' if seconds != 1 else ''}")
            
        time_string = ", ".join(time_parts)
        logger.debug(f"Formatted time difference: {time_string}")
        
        inspection_period = get_setting('inspection_period_hours', 24)
        logger.debug(f"Inspection period setting: {inspection_period} hours")
        
        hours_difference = total_seconds / 3600
        logger.debug(f"Hours difference: {hours_difference}")
        
        if hours_difference <= inspection_period:
            logger.info("Inspection is within valid period")
            return f"Inspection done {time_string} ago ✅", True
        else:
            logger.warning(f"Inspection is older than {inspection_period} hours")
            return f"Inspection done but more than {int(inspection_period)} hours ago ❌", False
            
    except Exception as e:
        logger.error(f"Error in get_inspection_status with data: completion_date={completion_date}, alert_time={alert_time}")
        logger.error(f"Detailed error: {str(e)}", exc_info=True)
        print(f"Error in get_inspection_status with data: completion_date={completion_date}, alert_time={alert_time}")
        print(f"Detailed error: {str(e)}")
        return "Error calculating inspection time difference ", False

def get_recent_trip_inspection(unit_name):
    logger.info(f"Getting recent trip inspection for unit: {unit_name}")
    
    try:
        if not unit_name:
            logger.warning("No unit name provided")
            return None
            
        params = {
            "api-version": "2016-06-01",
            "sp": "/triggers/manual/run",
            "sv": "1.0",
            "sig": "r1ZDbJJ9i-_jXig3NAetnHAqkcp2jz9MVHHZEeDS6oU",
            "unit": unit_name
        }
        logger.debug(f"Making API request with params: {params}")
        
        response = requests.get(DRM_BASE_URL_TRIP_INSPECTION, params=params)
        response.raise_for_status()
        
        inspection_data = response.json()
        logger.debug(f"Received inspection data: {inspection_data}")
        
        if inspection_data and len(inspection_data) > 0:
            completion_date = inspection_data[0].get("Completion Date")
            logger.info(f"Found completion date: {completion_date}")
            return completion_date
            
        logger.warning("No inspection data found")
        return None
        
    except Exception as e:
        logger.error(f"Error fetching inspection data for unit {unit_name}: {e}", exc_info=True)
        print(f"Error fetching inspection data: {e}")
        return None
