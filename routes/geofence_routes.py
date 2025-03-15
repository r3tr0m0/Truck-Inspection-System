"""
Geofence Routes Module

This module handles all routes related to geofence monitoring and alerts.
It provides endpoints for processing geofence alerts, checking vehicle movement,
and displaying historical alert data. The module integrates with Skyhawk API
for real-time vehicle tracking and implements email notifications for alerts.

Key Features:
- Geofence alert processing with movement tracking
- Real-time vehicle location monitoring
- Inspection status verification
- Email notifications to supervisors
- Historical alert data display
"""

from flask import Blueprint, request, jsonify, render_template, current_app
from datetime import datetime, timezone
from config import DatabaseConfig
from background_tasks import movement_checker
from utils.time_utils import format_pacific_time, determine_shift
from utils.inspection_utils import get_inspection_status, get_recent_trip_inspection
from utils.yard_utils import get_yard_coordinates, get_supervisor_for_yard
from utils.settings_utils import get_setting
from utils.alert_utils import calculate_distance, process_alert_tracking
import pytz
import logging
import time
from urllib.parse import quote

# Configure logging for the geofence module
logger = logging.getLogger(__name__)

# Create Blueprint for geofence-related routes
geofence_bp = Blueprint('geofence', __name__)

def get_services():
    """
    Helper function to retrieve service instances from app configuration.
    
    Returns:
        tuple: (SkyhawkService, EmailService) instances from current app config
    """
    return current_app.config['SKYHAWK_SERVICE'], current_app.config['EMAIL_SERVICE']

@geofence_bp.route('/geofence-alert', methods=['POST'])
def geofence_alert():
    """
    Process incoming geofence alerts and initiate movement tracking.
    
    This endpoint handles POST requests containing geofence alert data.
    It performs the following operations:
    1. Validates the alert data
    2. Retrieves vehicle and yard information
    3. Checks inspection status
    4. Initiates movement tracking
    5. Sends notifications if necessary
    
    Returns:
        json: Alert processing status and details
        int: HTTP status code (202 for accepted, 400/500 for errors)
    """
    skyhawk_service, email_service = get_services()
    logger.info("Received geofence alert request")
    
    data = request.json
    if not data:
        logger.error("No data received in geofence alert request")
        return jsonify({"error": "No data received"}), 400

    unit = data.get("Unit", "Unknown")
    yard = data.get("Yard", "Unknown")

    logger.info(f"Processing geofence alert for unit: {unit} at yard: {yard}")

    if yard == "Unknown":
        logger.error(f"Invalid yard information received: {yard}")
        return jsonify({"error": "Yard information is required"}), 400

    alert_time = datetime.now(timezone.utc)

    # Get yard coordinates for distance calculations
    yard_lat, yard_lon = get_yard_coordinates(yard)
    yard_coordinates = (yard_lat, yard_lon)
    logger.debug(f"Retrieved yard coordinates: lat={yard_lat}, lon={yard_lon}")

    # Get initial vehicle readings
    truck_lat, truck_lon, truck_location, initial_speed = skyhawk_service.get_truck_coordinates(unit)
    truck_details = (f"Latitude: {truck_lat}, Longitude: {truck_lon}, Location: {truck_location}" 
                    if truck_lat and truck_lon 
                    else "Geofence Alert Triggered - Could Not Fetch Skyhawk Data")
    yard_coordinates_text = f"Latitude: {yard_lat}, Longitude: {yard_lon}" if yard_lat and yard_lon else "Unavailable"

    # Gather additional context information
    supervisor = get_supervisor_for_yard(yard)
    completion_date = get_recent_trip_inspection(unit)
    inspection_status_text, is_valid = get_inspection_status(
        completion_date=completion_date,
        alert_time=alert_time
    )
    shift = determine_shift(alert_time)

    logger.info(f"Retrieved inspection details for unit {unit}: status={inspection_status_text}, recent={is_valid}")

    # Process alert tracking and determine if email notification is needed
    should_send_email = process_alert_tracking(
        unit=unit,
        current_inspection_time=completion_date,
        alert_time=alert_time,
        email_service=email_service,
        yard_name=yard,
        supervisors=supervisor
    )

    # Record alert in database
    try:
        with DatabaseConfig.get_cursor() as cursor:
            logger.debug("Inserting geofence alert into database")
            cursor.execute("""
                INSERT INTO geofence_alerts (
                    unit, yard, alert_time, inspection_date, inspection_status, shift,
                    truck_details, yard_coordinates, supervisors, movement_check_completed,
                    moving_status, email_sent, email_sent_time
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, FALSE, 
                          'Checking movement...', FALSE, NULL)
                RETURNING unit, alert_time;
            """, (unit, yard, alert_time, completion_date, inspection_status_text,
                  shift, truck_details, yard_coordinates_text, str(supervisor)))
            
            row = cursor.fetchone()
            logger.info(f"Successfully inserted geofence alert for unit {unit}")

    except Exception as e:
        logger.error(f"Database error while processing geofence alert: {e}")
        return jsonify({"error": "Database error"}), 500

    # Initiate asynchronous movement tracking
    logger.info(f"Initiating movement tracking for unit {unit}")
    task_id = movement_checker.add_check_request(
        unit=unit,
        yard_coordinates=yard_coordinates,
        alert_time=alert_time,
        get_truck_coordinates=skyhawk_service.get_truck_coordinates,
        calculate_distance=calculate_distance
    )

    return jsonify({
        "status": "Processing",
        "message": "Movement tracking initiated",
        "task_id": task_id,
        "alert_details": {
            "unit": unit,
            "yard": yard,
            "alert_time": alert_time.isoformat(),
            "completion_date": format_pacific_time(completion_date),
            "inspection_status": inspection_status_text,
            "shift": shift,
            "truck_details": truck_details,
            "yard_coordinates": yard_coordinates_text,
            "supervisors": supervisor,
            "movement_status": "Checking movement..."
        }
    }), 202  # 202 Accepted

@geofence_bp.route('/movement-status/<task_id>', methods=['GET'])
def get_movement_status(task_id):
    """
    Retrieve the status of a movement check request.
    
    Args:
        task_id (str): ID of the movement check task
    
    Returns:
        json: Current status of the movement check
    """
    status = movement_checker.get_status(task_id)
    return jsonify({
        "status": status
    })

@geofence_bp.route('/all-geofence-alerts')
def all_geofence_alerts():
    logger.info("Retrieving all geofence alerts")
    try:
        # Retrieve alert data from database
        alerts_data = None
        with DatabaseConfig.get_cursor() as cursor:
            logger.debug("Executing database query for all alerts")
            cursor.execute("""
                SELECT 
                    unit, yard, alert_time, inspection_date, inspection_status, 
                    shift, truck_details, yard_coordinates, supervisors,
                    distance_at_alert, distance_after_10s, distance_after_30s,
                    speed_at_alert, speed_after_10s, speed_after_30s,
                    moving_status, movement_check_completed, email_sent,
                    email_sent_time
                FROM geofence_alerts 
                ORDER BY alert_time DESC
                LIMIT 100;
            """)
            alerts_data = cursor.fetchall()

        if alerts_data is None:
            logger.warning("No alert data found in database")
            return "No data available", 500

        logger.info(f"Retrieved {len(alerts_data)} alerts from database")

        # Format alerts for display
        formatted_alerts = []
        for alert in alerts_data:
            # Helper function to format distance values
            def format_distance(distance):
                if isinstance(distance, (int, float)):
                    return f"{int(distance)} m"
                return str(distance) if distance else "Unavailable"

            # Helper function to format coordinates
            def format_coordinates(coord_str):
                if "Modem Not Found" in str(coord_str):
                    return "Modem Not Found"
                try:
                    parts = coord_str.split(', ')
                    formatted_parts = []
                    for part in parts:
                        if 'Latitude' in part or 'Longitude' in part:
                            label, value = part.split(': ')
                            try:
                                formatted_value = f"{float(value):.4f}"
                                formatted_parts.append(f"{label}: {formatted_value}")
                            except ValueError:
                                formatted_parts.append(part)
                        else:
                            formatted_parts.append(part)
                    return ', '.join(formatted_parts)
                except:
                    return str(coord_str)

            # Helper function to format speed values
            def format_speed(speed):
                if not speed or speed == "Checking...":
                    return "Checking..."
                try:
                    speed_val = float(speed.split()[0])
                    return f"{int(speed_val)} km/h"
                except:
                    return str(speed)

            # Helper function for supervisor list parsing
            def parse_supervisors(sup_str):
                if not sup_str or sup_str == "None":
                    return []
                try:
                    return eval(sup_str)
                except:
                    return []
                    
            # Format alert timestamp (UTC to PST conversion)
            alert_time = "N/A"
            if alert[2]:
                try:
                    utc_time = alert[2].replace(tzinfo=timezone.utc)
                    pacific = pytz.timezone("America/Los_Angeles")
                    pst_time = utc_time.astimezone(pacific)
                    alert_time = pst_time.strftime("%B %d, %Y - %I:%M %p %Z")
                except Exception as e:
                    logger.error(f"Error formatting alert time: {e}")
                    alert_time = str(alert[2])

            # Format inspection timestamp
            inspection_time = "N/A"
            if alert[3]:
                try:
                    if isinstance(alert[3], datetime):
                        dt = alert[3]
                    else:
                        cleaned_date = str(alert[3]).replace('Z', '')
                        dt = datetime.fromisoformat(cleaned_date)
                    inspection_time = dt.strftime("%B %d, %Y - %I:%M %p PST")
                except Exception as e:
                    logger.error(f"Error formatting inspection time: {e}")
                    inspection_time = str(alert[3])
                    
            def format_time_difference(time_diff_str):
                """Format PostgreSQL interval into human-readable duration"""
                if not time_diff_str:
                    return "N/A"
                try:
                    parts = time_diff_str.split(':')
                    if len(parts) != 3:
                        return time_diff_str
                        
                    hours = int(parts[0])
                    minutes = int(parts[1])
                    seconds = float(parts[2])
                    
                    total_seconds = hours * 3600 + minutes * 60 + seconds
                    
                    if total_seconds < 60:
                        return f"{int(total_seconds)} seconds"
                    elif total_seconds < 3600:
                        minutes = int(total_seconds // 60)
                        seconds = int(total_seconds % 60)
                        return f"{minutes}m {seconds}s"
                    else:
                        hours = int(total_seconds // 3600)
                        minutes = int((total_seconds % 3600) // 60)
                        return f"{hours}h {minutes}m"
                except Exception as e:
                    logger.error(f"Error formatting time difference: {e}")
                    return time_diff_str

            def format_email_sent_time(timestamp):
                if not timestamp:
                    return "Not Sent"
                try:
                    if isinstance(timestamp, str):
                        timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                    
                    pacific = pytz.timezone("America/Los_Angeles")
                    pst_time = timestamp.astimezone(pacific)
                    return pst_time.strftime("%B %d, %Y - %I:%M %p %Z")
                except Exception as e:
                    logger.error(f"Error formatting email sent time: {e}")
                    return str(timestamp)

            # Create formatted alert dictionary
            formatted_alert = {
                'unit': str(alert[0]) if alert[0] else "N/A",
                'yard': str(alert[1]) if alert[1] else "N/A",
                'alert_time': alert_time,
                'completion_date': inspection_time,
                'inspection_status': str(alert[4]) if alert[4] else "N/A",
                'shift': str(alert[5]) if alert[5] else "N/A",
                'truck_details': format_coordinates(alert[6]),
                'yard_coordinates': format_coordinates(alert[7]),
                'supervisors': parse_supervisors(alert[8]),
                'initial_distance': format_distance(alert[9]),
                'distance_after_10s': format_distance(alert[10]),
                'distance_after_30s': format_distance(alert[11]),
                'speed_initial': format_speed(str(alert[12])),
                'speed_10s': format_speed(str(alert[13])),
                'speed_30s': format_speed(str(alert[14])),
                'moving_status': str(alert[15]) if alert[15] else "Checking movement...",
                'is_checking': True if alert[16] is None else not bool(alert[16]),
                'email_sent': bool(alert[17]),
                'email_sent_time': format_email_sent_time(alert[18])
            }
            formatted_alerts.append(formatted_alert)

        logger.info(f"Successfully formatted {len(formatted_alerts)} alerts for display")
        return render_template('geofence_alerts.html', alerts=formatted_alerts)

    except Exception as e:
        import traceback
        logger.error(f"Error in all_geofence_alerts: {e}")
        logger.error(traceback.format_exc())
        return f"Error loading alerts: {str(e)}", 500
