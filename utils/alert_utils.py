"""
Alert Utilities Module

This module provides functions for processing and managing geofence alerts,
including distance calculations, alert logging, and alert tracking logic.
It handles the core functionality of the geofence monitoring system.

Key Features:
- Distance calculation between geographic coordinates
- Geofence alert logging with duplicate detection
- Alert tracking with time-based reset logic
- Speed and movement status processing
- Comprehensive error handling and logging
"""

from config import DatabaseConfig
from geopy.distance import geodesic
import logging
from datetime import datetime, timedelta
import pytz
from utils.inspection_utils import get_inspection_status
from utils.settings_utils import get_setting

# Configure logging with detailed format
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('alert_utils')

def calculate_distance(coord1, coord2):
    logger.debug(f"Calculating distance between coordinates: {coord1} and {coord2}")
    if None in coord1 or None in coord2:
        logger.warning("Invalid coordinates detected (None values present)")
        return 0
    distance = geodesic(coord1, coord2).meters
    logger.debug(f"Calculated distance: {distance} meters")
    return distance

def log_geofence_alert(unit, yard, alert_time, inspection_date, inspection_status, shift, truck_details, yard_coordinates,
                       supervisors, initial_distance, distance_after_10s, distance_after_30s, 
                       speed_initial, speed_10s, speed_30s, moving_status):
    logger.info(f"Processing geofence alert for unit: {unit} in yard: {yard}")
    try:
        with DatabaseConfig.get_cursor() as cursor:
            # Clean and convert numeric values
            def safe_numeric(value):
                logger.debug(f"Converting value to numeric: {value}")
                if isinstance(value, (int, float)):
                    return value
                if value == "Modem Not Found" or value == "Unavailable":
                    logger.warning(f"Invalid value detected: {value}")
                    return None
                try:
                    return float(value)
                except (ValueError, TypeError):
                    logger.warning(f"Failed to convert value to float: {value}")
                    return None

            # Clean and convert the distance values
            clean_initial_distance = safe_numeric(initial_distance)
            clean_distance_10s = safe_numeric(distance_after_10s)
            clean_distance_30s = safe_numeric(distance_after_30s)

            logger.debug(f"Cleaned distances - Initial: {clean_initial_distance}, 10s: {clean_distance_10s}, 30s: {clean_distance_30s}")

            # Clean speed values - remove 'km/h' and convert to numeric
            def clean_speed(speed_value):
                logger.debug(f"Cleaning speed value: {speed_value}")
                if speed_value in ["Modem Not Found", "Unavailable"]:
                    logger.warning(f"Invalid speed value detected: {speed_value}")
                    return None
                try:
                    speed = float(speed_value.split()[0])  # Split "X km/h" and take X
                    logger.debug(f"Cleaned speed value: {speed}")
                    return speed
                except (ValueError, AttributeError, IndexError):
                    logger.warning(f"Failed to clean speed value: {speed_value}")
                    return None

            # Process speed measurements
            clean_speed_initial = clean_speed(speed_initial)
            clean_speed_10s = clean_speed(speed_10s)
            clean_speed_30s = clean_speed(speed_30s)

            logger.debug(f"Cleaned speeds - Initial: {clean_speed_initial}, 10s: {clean_speed_10s}, 30s: {clean_speed_30s}")

            # Store alert in database
            logger.info("Inserting alert into database")
            cursor.execute("""
                INSERT INTO geofence_alerts (
                    unit, yard, alert_time, inspection_date, inspection_status, shift, 
                    truck_details, yard_coordinates, supervisors, 
                    distance_at_alert, distance_after_10s, distance_after_30s, 
                    speed_at_alert, speed_after_10s, speed_after_30s, moving_status
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
            """, (
                unit, yard, alert_time, inspection_date, inspection_status, shift, 
                truck_details, yard_coordinates, str(supervisors), 
                clean_initial_distance, clean_distance_10s, clean_distance_30s, 
                clean_speed_initial, clean_speed_10s, clean_speed_30s, moving_status
            ))
            logger.info("Successfully inserted alert into database")
        return True
    except Exception as e:
        logger.error(f"Error logging geofence alert: {e}", exc_info=True)
        print(f"Error logging geofence alert: {e}")
        return False
    
def process_alert_tracking(unit, current_inspection_time, alert_time, email_service, yard_name, supervisors):
    """
    Process alert tracking logic for a vehicle unit.
    
    This function manages the alert tracking system, which includes:
    - Tracking the number of alerts per inspection
    - Managing alert counters with time-based resets
    - Determining when to send notification emails
    
    The system implements the following rules:
    1. New units get immediate email notifications
    2. Existing units have an 8-hour cooldown between notifications
    3. Alert counters reset when a new inspection occurs
    
    Args:
        unit (str): Vehicle unit identifier
        current_inspection_time (datetime|str): Time of current inspection
        alert_time (datetime|str): Time of the alert
        email_service (EmailService): Email notification service instance
        yard_name (str): Name of the yard where alert occurred
        supervisors (list): List of supervisors to notify
        
    Returns:
        bool: True if email should be sent, False otherwise
        
    Note:
        All timestamps are normalized to UTC for consistent comparison.
        The function handles both datetime objects and ISO format strings.
    """
    logger.info(f"Processing alert tracking for unit: {unit}")
    utc = pytz.UTC  # Define UTC timezone for consistency

    try:
        # Normalize timestamps to UTC
        def normalize_to_utc(timestamp):
            """Ensure timestamp is a UTC datetime object"""
            if isinstance(timestamp, str):
                # Convert ISO format string to datetime
                timestamp = datetime.fromisoformat(timestamp)
            if timestamp.tzinfo is None:
                # If naive, assume it's in UTC
                timestamp = timestamp.replace(tzinfo=utc)
            else:
                # Convert to UTC
                timestamp = timestamp.astimezone(utc)
            return timestamp

        # Process timestamps
        current_inspection_time = normalize_to_utc(current_inspection_time)
        alert_time = normalize_to_utc(alert_time)

        with DatabaseConfig.get_cursor() as cursor:
            # Check existing tracking record
            cursor.execute("""
                SELECT current_inspection_time, first_alert_timestamp, alert_counter 
                FROM unit_alert_tracking 
                WHERE unit_id = %s
            """, (unit,))
            
            tracking_record = cursor.fetchone()
            should_send_email = False 

            if not tracking_record:
                # Case A: New unit - create tracking record
                logger.info(f"New unit {unit} - creating tracking record")
                cursor.execute("""
                    INSERT INTO unit_alert_tracking 
                    (unit_id, current_inspection_time, first_alert_timestamp, alert_counter)
                    VALUES (%s, %s, %s, 1)
                """, (unit, current_inspection_time, alert_time))
                should_send_email = True

            else:
                # Case B: Existing unit - process alert
                stored_inspection_time = tracking_record[0]
                first_alert_time = tracking_record[1]
                current_counter = tracking_record[2]

                # Normalize stored timestamps
                stored_inspection_time = normalize_to_utc(stored_inspection_time)
                first_alert_time = normalize_to_utc(first_alert_time)

                # Check if inspection time has changed
                if stored_inspection_time == current_inspection_time:
                    logger.debug("Stored and current inspection times match.")
                    # Check time since first alert
                    time_diff = alert_time - first_alert_time
                    hours_diff = time_diff.total_seconds() / 3600

                    if hours_diff > 8:
                        # Reset after 8-hour cooldown
                        logger.info(f"Unit {unit} - More than 8 hours since first alert. Resetting counter.")
                        cursor.execute("""
                            UPDATE unit_alert_tracking 
                            SET alert_counter = 1,
                                first_alert_timestamp = %s
                            WHERE unit_id = %s
                        """, (alert_time, unit))

                        should_send_email = True

                    else:
                        # Increment counter within cooldown period
                        new_counter = current_counter + 1
                        logger.info(f"Unit {unit} - Incrementing alert counter from {current_counter} to {new_counter}")
                        cursor.execute("""
                            UPDATE unit_alert_tracking 
                            SET alert_counter = %s
                            WHERE unit_id = %s
                        """, (new_counter, unit))
                        should_send_email = False
                        skip_reason = f"Multiple alerts within 8 hours - Email already sent (Alert #{new_counter})"
                else:
                    # New inspection detected - reset tracking
                    logger.info(f"Unit {unit} - New inspection time detected. Resetting counter.")
                    cursor.execute("""
                        UPDATE unit_alert_tracking 
                        SET current_inspection_time = %s,
                            first_alert_timestamp = %s,
                            alert_counter = 1
                        WHERE unit_id = %s
                    """, (current_inspection_time, alert_time, unit))
                    
                    should_send_email = True

            # Log final state
            cursor.execute("SELECT alert_counter FROM unit_alert_tracking WHERE unit_id = %s", (unit,))
            final_counter = cursor.fetchone()[0]
            logger.info(f"Unit {unit} - Final alert counter: {final_counter}")

            logger.info(f"""
            Alert Tracking Details:
            - Unit: {unit}
            - Current Inspection Time: {current_inspection_time}
            - Alert Time: {alert_time}
            - Yard Name: {yard_name}
            - Supervisors Count: {len(supervisors) if supervisors else 0}
            """)

            if tracking_record:
                logger.info(f"""
                Existing Tracking Record Found:
                - Stored Inspection Time: {tracking_record[0]}
                - First Alert Time: {tracking_record[1]}
                - Current Counter: {tracking_record[2]}
                """)

            return should_send_email

    except Exception as e:
        logger.error(f"Error processing alert tracking for unit {unit}: {e}", exc_info=True)
        # On error, return True to ensure notification is sent
        return True
