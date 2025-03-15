"""
Production Routes Module

This module handles all routes related to production mode functionality,
including yard management, supervisor assignments, and alert monitoring.
It provides endpoints for retrieving and managing yard data, supervisor
assignments, and viewing production alerts.

Key Features:
- Yard list management and filtering
- Supervisor assignment and tracking
- Production alert monitoring
- Data formatting and timezone handling
"""

from flask import Blueprint, render_template, jsonify, request
from config import DatabaseConfig
from utils.yard_utils import get_supervisor_for_yard
import logging
import pytz
from datetime import datetime, timezone
import requests
from config.constants import YARD_API_URL, SUPERVISOR_API_URL
from utils.alert_utils import calculate_distance, process_alert_tracking

# Configure logging for the production module
logger = logging.getLogger(__name__)

# Create Blueprint for production-related routes
production_bp = Blueprint('production', __name__)

@production_bp.route('/production')
def production_view():
    """
    Render the main production mode view.
    
    Returns:
        rendered_template: The production mode dashboard
    """
    return render_template('production.html')

@production_bp.route('/production/yards')
def get_yards():
    """
    Retrieve and format the list of yards from DRM API.
    
    Makes a request to the DRM API to get all yard information,
    formats the yard names, and returns a deduplicated, sorted list.
    
    Returns:
        json: List of formatted yard names
        tuple: Error message and status code if request fails
    """
    logger.info("Received request for yards list")
    try:
        params = {
            "api-version": "2016-06-01",
            "sp": "/triggers/manual/run",
            "sv": "1.0",
            "sig": "r1ZDbJJ9i-_jXig3NAetnHAqkcp2jz9MVHHZEeDS6oU"
        }
        
        logger.info(f"Making request to YARD_API_URL: {YARD_API_URL}")
        logger.debug(f"Request parameters: {params}")
        
        response = requests.get(YARD_API_URL, params=params)
        logger.info(f"Received response from YARD_API_URL. Status code: {response.status_code}")
        
        if not response.ok:
            logger.error(f"API request failed. Status: {response.status_code}, Response: {response.text}")
            return jsonify({"error": "Failed to fetch yards", "yards": []}), response.status_code
            
        yards_data = response.json()
        logger.debug(f"Raw yards data received: {yards_data}")
        
        yards = []
        if yards_data:
            yards = [format_yard_name(yard.get("Yard Name")) 
                    for yard in yards_data if yard.get("Yard Name")]
            yards = sorted(list(set(yards)))
            logger.info(f"Processed {len(yards)} unique yards")
            logger.debug(f"Formatted yards list: {yards}")
        else:
            logger.warning("No yards data received from API")
            
        return jsonify({"yards": yards})
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Network error while fetching yards: {e}", exc_info=True)
        return jsonify({"error": "Network error", "yards": []}), 500
    except Exception as e:
        logger.error(f"Unexpected error in get_yards: {e}", exc_info=True)
        return jsonify({"error": str(e), "yards": []}), 500

@production_bp.route('/production/supervisors/<yard_name>')
def get_supervisors(yard_name):
    """
    Retrieve supervisors for a specific yard and their selection status.
    
    Args:
        yard_name (str): Name of the yard to get supervisors for
    
    Returns:
        json: List of supervisors with their details and selection status
        tuple: Error message and status code if request fails
    """
    try:
        # Get supervisors from DRM API
        params = {
            "api-version": "2016-06-01",
            "sp": "/triggers/manual/run",
            "sv": "1.0",
            "sig": "r1ZDbJJ9i-_jXig3NAetnHAqkcp2jz9MVHHZEeDS6oU",
            "yard": yard_name
        }
        
        response = requests.get(SUPERVISOR_API_URL, params=params)
        response.raise_for_status()
        supervisors = response.json()
        
        # Get current selections from database
        with DatabaseConfig.get_cursor() as cursor:
            cursor.execute("""
                SELECT supervisor_name 
                FROM yard_supervisors 
                WHERE yard_name = %s AND is_selected = TRUE
            """, (yard_name,))
            selected_supervisors = [row[0] for row in cursor.fetchall()]
        
        # Format supervisor data with selection status
        formatted_supervisors = []
        if supervisors:
            for supervisor in supervisors:
                formatted_supervisors.append({
                    "id": supervisor.get("Employee ID"),
                    "Employee Name": supervisor.get("Employee Name"),
                    "Email": supervisor.get("Email"),
                    "Phone": supervisor.get("Phone"),
                    "is_selected": supervisor.get("Employee Name") in selected_supervisors
                })
                
        return jsonify({"supervisors": formatted_supervisors})
    except Exception as e:
        logger.error(f"Error fetching supervisors for yard {yard_name} from DRM API: {e}")
        return jsonify({"error": str(e)}), 500

@production_bp.route('/production/save-filters', methods=['POST'])
def save_filters():
    """
    Save supervisor selections for a yard.
    
    Updates the database with the current supervisor selections for a yard,
    removing old selections and adding new ones.
    
    Returns:
        json: Success status or error message
    """
    try:
        data = request.json
        yard_name = data.get('yard')
        selections = data.get('selections', [])
        
        with DatabaseConfig.get_cursor() as cursor:
            # Remove old selections
            cursor.execute("""
                DELETE FROM yard_supervisors 
                WHERE yard_name = %s
            """, (yard_name,))
            
            # Add new selections
            for selection in selections:
                cursor.execute("""
                    INSERT INTO yard_supervisors 
                    (yard_name, supervisor_id, supervisor_name, supervisor_email, is_selected)
                    VALUES (%s, %s, %s, %s, TRUE)
                """, (
                    yard_name,
                    selection['supervisor_id'],
                    selection['supervisor_name'],
                    selection['supervisor_email']
                ))
            
        return jsonify({"status": "success"})
    except Exception as e:
        logger.error(f"Error saving filters: {e}")
        return jsonify({"error": str(e)}), 500

@production_bp.route('/production/alerts')
def get_alerts():
    """
    Retrieve filtered alerts based on yard and supervisor criteria.
    
    Returns:
        json: List of formatted alerts matching the filter criteria
        tuple: Error message and status code if request fails
    """
    try:
        yard = request.args.get('yard')
        supervisor_id = request.args.get('supervisor_id')
        
        with DatabaseConfig.get_cursor() as cursor:
            cursor.execute("""
                SELECT 
                    unit, yard, alert_time, inspection_date, inspection_status,
                    supervisors, email_sent, email_sent_time
                FROM geofence_alerts 
                WHERE (%s = '' OR yard = %s)
                    AND (%s = '' OR supervisors::text LIKE %s)
                ORDER BY alert_time DESC;
            """, (yard, yard, supervisor_id, f"%{supervisor_id}%"))
            alerts = cursor.fetchall()
            
            formatted_alerts = format_alerts(alerts)
            
        return jsonify({"alerts": formatted_alerts})
    except Exception as e:
        logger.error(f"Error fetching alerts: {e}")
        return jsonify({"error": str(e)}), 500 

def format_alerts(alerts_data):
    """
    Format alert data for display.
    
    Args:
        alerts_data (list): Raw alert data from database
    
    Returns:
        list: Formatted alerts with proper timezone and data formatting
    """
    formatted_alerts = []
    for alert in alerts_data:
        try:
            # Format alert timestamp (UTC to PST)
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

            def parse_supervisors(sup_str):
                if not sup_str or sup_str == "None":
                    return []
                try:
                    return eval(sup_str)
                except:
                    return []

            formatted_alert = {
                'unit': str(alert[0]) if alert[0] else "N/A",
                'yard': str(alert[1]) if alert[1] else "N/A",
                'alert_time': alert_time,
                'completion_date': inspection_time,
                'inspection_status': str(alert[4]) if alert[4] else "N/A",
                'supervisors': parse_supervisors(alert[5]),
                'email_sent': bool(alert[6]),
                'email_sent_time': format_email_sent_time(alert[7])
            }
            formatted_alerts.append(formatted_alert)
        except Exception as e:
            logger.error(f"Error formatting alert: {e}")
            continue
            
    return formatted_alerts

def format_yard_name(yard_name):
    """
    Format yard name by removing standard suffixes.
    
    Args:
        yard_name (str): Raw yard name from API
    
    Returns:
        str: Cleaned yard name without suffixes
    """
    logger.debug(f"Formatting yard name: {yard_name}")
    if not yard_name:
        logger.warning("Received empty yard name")
        return ""
        
    formatted_name = yard_name
    if yard_name.endswith(' DRM Yard'):
        formatted_name = yard_name[:-9]
        logger.debug(f"Removed 'DRM Yard' suffix: {formatted_name}")
    elif yard_name.endswith(' Yard'):
        formatted_name = yard_name[:-5]
        logger.debug(f"Removed 'Yard' suffix: {formatted_name}")
        
    logger.debug(f"Final formatted yard name: {formatted_name}")
    return formatted_name

def format_time_difference(time_diff_str):
    if not time_diff_str:
        return None
    try:
        # Parse duration components
        parts = time_diff_str.split(':')
        hours = int(parts[0])
        minutes = int(parts[1])
        seconds = int(parts[2])
        
        # Format based on duration magnitude
        if hours > 0:
            return f"{hours} hour{'s' if hours != 1 else ''}, {minutes} min"
        elif minutes > 0:
            return f"{minutes} minute{'s' if minutes != 1 else ''}, {seconds} sec"
        else:
            return f"{seconds} seconds"
    except:
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
