"""
Background task processing module for vehicle movement monitoring and alerts.

This module provides functionality for:
- Asynchronous movement tracking of vehicles
- Email alert management based on movement patterns
- Database state management for alerts and tracking
- Sophisticated movement pattern detection

Key Components:
- MovementChecker: Main class handling background movement checks
- Database connection management
- Email service integration
- Movement status determination with pattern recognition

The module uses threading for non-blocking background operations
and includes comprehensive logging for monitoring and debugging.
"""

import threading
import time
import logging
from datetime import datetime
import psycopg2
from config.database import DatabaseConfig
from utils.settings_utils import get_setting
from services.email import EmailService  

DB_HOST = DatabaseConfig.DB_HOST
DB_NAME = DatabaseConfig.DB_NAME
DB_USER = DatabaseConfig.DB_USER
DB_PASSWORD = DatabaseConfig.DB_PASSWORD

def connect_db():
    """
    Establish a connection to the PostgreSQL database.
    
    Returns:
        psycopg2.connection: Active database connection object
    
    Raises:
        Exception: If connection fails, with error details
    
    Notes:
        - Uses connection parameters from DatabaseConfig
        - Prints success/failure messages to stdout
        - Raises exception on connection failure
    """
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )
        print("Database connection established successfully.")
        return conn
    except Exception as e:
        print(f"Error connecting to the database: {e}")
        raise

class MovementChecker:
    """
    Background task processor for checking vehicle movement patterns.
    
    This class manages a queue of movement check requests and processes them
    asynchronously in a background thread. It tracks vehicle positions over time,
    determines movement patterns, and triggers email alerts when necessary.
    
    Attributes:
        queue (list): Queue of pending movement check requests
        running (bool): Flag controlling background thread execution
        status_store (dict): Storage for task status tracking
        email_service (EmailService): Lazy-loaded email service instance
        thread (Thread): Background processing thread
    
    Notes:
        - Uses daemon thread for automatic cleanup on program exit
        - Implements lazy loading for email service
        - Provides task status tracking
        - Handles database updates and email notifications
    """
    
    def __init__(self):
        """Initialize the MovementChecker with required attributes and start background thread."""
        self.queue = []
        self.running = True
        self.status_store = {}
        self.email_service = None
        self.thread = threading.Thread(target=self._process_queue, daemon=True)
        self.thread.start()
        logging.info("MovementChecker initialized and background thread started.")

    def _get_email_service(self):
        """
        Lazy initialization of the email service.
        
        Returns:
            EmailService: Configured email service instance,
                         or None if initialization fails
        
        Notes:
            - Creates service only on first use
            - Caches instance for subsequent uses
            - Uses parameters from EmailConfig
            - Includes error handling and logging
        """
        if self.email_service is None:
            try:
                # Get email service parameters from config
                from config.services import EmailConfig
                
                # Create email service instance with required parameters
                self.email_service = EmailService(
                    api_key=EmailConfig.API_KEY,
                    sender_email=EmailConfig.SENDER_EMAIL,
                    recipient_emails=EmailConfig.RECIPIENT_EMAILS,
                    sender_name=EmailConfig.SENDER_NAME,
                    fallback_email=EmailConfig.FALLBACK_EMAIL
                )
                logging.info("Email service initialized successfully")
            except Exception as e:
                logging.error(f"Failed to initialize email service: {e}")
                return None
        return self.email_service

    def add_check_request(self, unit, yard_coordinates, alert_time, get_truck_coordinates, calculate_distance):
        """
        Add a new movement check request to the processing queue.
        
        Args:
            unit (str): Vehicle unit identifier
            yard_coordinates (tuple): (latitude, longitude) of the yard
            alert_time (datetime): Time when alert was triggered
            get_truck_coordinates (callable): Function to get truck coordinates
            calculate_distance (callable): Function to calculate distances
        
        Returns:
            str: Unique task identifier for status tracking
        
        Notes:
            - Generates unique task ID using unit and time
            - Adds request to processing queue
            - Initializes task status as 'pending'
        """
        task_id = f"{unit}_{alert_time.isoformat()}"
        self.status_store[task_id] = 'pending'
        self.queue.append({
            'task_id': task_id,
            'unit': unit,
            'yard_coordinates': yard_coordinates,
            'alert_time': alert_time,
            'get_truck_coordinates': get_truck_coordinates,
            'calculate_distance': calculate_distance
        })
        logging.info(f"Added movement check request for unit {unit}, task_id: {task_id}")
        return task_id

    def get_status(self, task_id):
        """
        Retrieve the current status of a movement check request.
        
        Args:
            task_id (str): Task identifier from add_check_request
        
        Returns:
            str: Current status of the task ('pending', 'completed', etc.)
        """
        return self.status_store.get(task_id, 'pending')


    def _process_queue(self):
        """
        Background thread function for processing movement check requests.
        
        Notes:
            - Runs continuously while self.running is True
            - Processes one request at a time from queue
            - Sleeps for 1 second when queue is empty
            - Handles each request via _check_movement
        """
        while self.running:
            if self.queue:
                request = self.queue.pop(0)
                task_id = request.pop('task_id')  # Remove task_id from request before unpacking
                logging.info(f"Processing movement check request for task: {task_id}")
                self._check_movement(task_id, **request)
            time.sleep(1)

    def _check_movement(self, task_id, unit, yard_coordinates, alert_time, get_truck_coordinates, calculate_distance):
        """
        Process a single movement check request.
        
        Args:
            task_id (str): Unique identifier for this check
            unit (str): Vehicle unit identifier
            yard_coordinates (tuple): (latitude, longitude) of yard
            alert_time (datetime): Time of alert
            get_truck_coordinates (callable): Function to get truck position
            calculate_distance (callable): Function to calculate distances
        
        Returns:
            bool: True if check completed (even with errors), False otherwise
        
        Notes:
            - Retrieves required data from database
            - Performs movement checks at 0s, 10s, and 30s intervals
            - Updates database with results
            - Handles email notifications based on settings
            - Includes comprehensive error handling
        """
        try:
            # Get email service and other required data from database
            with DatabaseConfig.get_cursor() as cursor:
                cursor.execute("""
                    SELECT ga.yard, ga.inspection_date, ga.inspection_status, ga.supervisors,
                           uat.alert_counter
                    FROM geofence_alerts ga
                    LEFT JOIN unit_alert_tracking uat ON ga.unit = uat.unit_id
                    WHERE ga.unit = %s AND ga.alert_time = %s
                """, (unit, alert_time))
                result = cursor.fetchone()
                if result:
                    yard, inspection_date, inspection_status, supervisors, alert_counter = result
                    
                    # Check if we should send email
                    should_send_email = alert_counter == 1  # Send email only on first alert
                    is_valid = "✅" in inspection_status  # Check if inspection is valid
                    
                    logging.info(f"Email conditions - should_send_email: {should_send_email}, is_valid: {is_valid}")
                    
                    check_movement = get_setting('check_movement_before_email', 'false').lower() == 'true'
                    email_success = False

                    if not check_movement:
                        # Send email before movement check if setting is false
                        if should_send_email and not is_valid:
                            try:
                                email_service = self._get_email_service()
                                if email_service:
                                    email_success = email_service.send_inspection_alert(
                                        asset_name=unit,
                                        yard_name=yard,
                                        inspection_date=inspection_date or "N/A",
                                        supervisors=supervisors
                                    )
                                    logging.info(f"Email sent successfully: {email_success}")
                                else:
                                    logging.error("Failed to initialize email service")
                            except Exception as e:
                                logging.error(f"Error sending email: {str(e)}", exc_info=True)
                                email_success = False

                    # Proceed with movement check
                    truck_lat, truck_lon, location_initial, speed_initial = get_truck_coordinates(unit)
                    initial_distance = calculate_distance(yard_coordinates, (truck_lat, truck_lon)) or 0
                    speed_initial = f"{speed_initial}" if speed_initial else "0 km/h"
                    
                    # Wait for 10 seconds and get new readings
                    time.sleep(10)
                    truck_lat_10, truck_lon_10, _, speed_10s = get_truck_coordinates(unit)
                    distance_after_10s = calculate_distance(yard_coordinates, (truck_lat_10, truck_lon_10)) or 0
                    speed_10s = f"{speed_10s}" if speed_10s else "0 km/h"
                    
                    # Wait for additional 20 seconds and get final readings
                    time.sleep(20)
                    truck_lat_30, truck_lon_30, _, speed_30s = get_truck_coordinates(unit)
                    distance_after_30s = calculate_distance(yard_coordinates, (truck_lat_30, truck_lon_30)) or 0
                    speed_30s = f"{speed_30s}" if speed_30s else "0 km/h"
                    
                    # Determine movement status
                    moving_status = self._determine_movement_status(
                        initial_distance, distance_after_10s, distance_after_30s,
                        speed_initial, speed_10s, speed_30s
                    )

                    # Always update database with available information
                    self._update_database(
                        unit, alert_time, moving_status, initial_distance, 
                        distance_after_10s, distance_after_30s,
                        speed_initial, speed_10s, speed_30s
                    )
                    
                    # Update task status
                    self.status_store[task_id] = moving_status
                    logging.info(f"Movement check completed for task {task_id}, status: {moving_status}")

                    # If check_movement is true, handle email after movement check
                    if check_movement and should_send_email and not is_valid:
                        if moving_status == "Moving Away":
                            try:
                                email_service = self._get_email_service()
                                if email_service:
                                    email_success = email_service.send_inspection_alert(
                                        asset_name=unit,
                                        yard_name=yard,
                                        inspection_date=inspection_date or "N/A",
                                        supervisors=supervisors
                                    )
                                    logging.info(f"Email sent successfully: {email_success}")
                                else:
                                    logging.error("Failed to initialize email service")
                            except Exception as e:
                                logging.error(f"Error sending email: {str(e)}", exc_info=True)
                                email_success = False
                        else:
                            logging.info(f"Skipping email for unit {unit} - Movement status: {moving_status}")

                    # Update email status in database
                    cursor.execute("""
                        UPDATE geofence_alerts 
                        SET email_sent = %s,
                            email_sent_time = CASE WHEN %s THEN NOW() AT TIME ZONE 'UTC' ELSE NULL END
                        WHERE unit = %s AND alert_time = %s
                    """, (email_success, email_success, unit, alert_time))

            return True

        except Exception as e:
            logging.error(f"Error checking movement for unit {unit}: {e}", exc_info=True)
            # Update database with error status but still mark as completed
            self._update_database(
                unit, alert_time, "Error checking movement", 
                0, 0, 0, "0 km/h", "0 km/h", "0 km/h"
            )
            self.status_store[task_id] = "Error checking movement"
            return True  # Return True even on error to prevent getting stuck

    def _determine_movement_status(self, initial_distance, distance_10s, distance_30s, 
                             speed_initial, speed_10s, speed_30s):
        """
        Enhanced movement status detection with sophisticated pattern recognition.
        
        Args:
            initial_distance (float): Initial distance measurement (meters)
            distance_10s (float): Distance after 10 seconds (meters)
            distance_30s (float): Distance after 30 seconds (meters)
            speed_initial (str): Initial speed measurement (km/h)
            speed_10s (str): Speed after 10 seconds (km/h)
            speed_30s (str): Speed after 30 seconds (km/h)
        
        Returns:
            str: Movement status:
                - "Moving Away": Vehicle is moving away from yard
                - "Stationary": Vehicle is not moving significantly
                - "No Data Found": Insufficient data for determination
        
        Notes:
            - Uses configurable thresholds for speed and distance
            - Implements sophisticated pattern recognition
            - Handles various data formats and missing values
            - Requires minimum valid readings for determination
        """
        # Constants
        SPEED_THRESHOLD_MOVING = 15.0  # km/h
        SPEED_THRESHOLD_STATIONARY = 5.0  # km/h
        DISTANCE_THRESHOLD = 10.0  # meters
        MIN_VALID_READINGS = 2
        
        def parse_speed(speed_str):
            """Parse speed values, handling various formats."""
            try:
                if isinstance(speed_str, (int, float)):
                    return float(speed_str)
                if isinstance(speed_str, str):
                    return float(speed_str.split()[0])
                return None
            except (ValueError, AttributeError, IndexError):
                return None
        
        def parse_distance(dist):
            """Parse distance values, handling various formats."""
            try:
                return float(dist) if dist not in (None, "", "0", 0) else None
            except (ValueError, TypeError):
                return None
        
        # Parse all values
        speeds = [parse_speed(s) for s in [speed_initial, speed_10s, speed_30s]]
        distances = [parse_distance(d) for d in [initial_distance, distance_10s, distance_30s]]
        
        # Check for No Data condition
        if all(s in (None, 0) for s in speeds) and all(d in (None, 0) for d in distances):
            return "No Data Found"
        
        # Filter out None values
        valid_speeds = [s for s in speeds if s is not None]
        valid_distances = [d for d in distances if d is not None]
        
        # Require minimum valid readings
        if len(valid_speeds) < MIN_VALID_READINGS and len(valid_distances) < MIN_VALID_READINGS:
            return "No Data Found"
        
        # Determine Stationary status
        def is_stationary():
            # Check if speeds are consistently low
            if valid_speeds and all(s <= SPEED_THRESHOLD_STATIONARY for s in valid_speeds):
                return True
            
            # Check if distances are nearly constant
            if len(valid_distances) >= 2:
                max_distance_change = max(valid_distances) - min(valid_distances)
                if max_distance_change < DISTANCE_THRESHOLD:
                    return True
            
            # Check for repeated distance values
            if len(valid_distances) >= 2:
                unique_distances = set(round(d, 2) for d in valid_distances)
                if len(unique_distances) == 1:
                    return True
            
            return False
        
        # Determine Moving Away status
        def is_moving_away():
            # Check for consistent speed above threshold
            if valid_speeds and any(s > SPEED_THRESHOLD_MOVING for s in valid_speeds):
                return True
            
            # Check for significant distance increase
            if len(valid_distances) >= 2:
                distance_change = valid_distances[-1] - valid_distances[0]
                if distance_change > DISTANCE_THRESHOLD:
                    return True
            
            # Check for increasing speed pattern
            if len(valid_speeds) >= 2:
                if valid_speeds[-1] > valid_speeds[0] and valid_speeds[-1] > SPEED_THRESHOLD_STATIONARY:
                    return True
            
            return False
        
        # Apply logic in order of precedence
        if is_moving_away():
            return "Moving Away"
        elif is_stationary():
            return "Stationary"
        else:
            # If we have some valid data but can't definitively categorize the movement
            if valid_speeds or valid_distances:
                return "Moving Away"  # Default to Moving Away if there's any valid data
            return "No Data Found"

    def _update_database(self, unit, alert_time, moving_status, initial_distance, 
                        distance_10s, distance_30s, speed_initial, speed_10s, speed_30s):
        """
        Update the database with movement check results.
        
        Args:
            unit (str): Vehicle unit identifier
            alert_time (datetime): Time of alert
            moving_status (str): Determined movement status
            initial_distance (float): Initial distance measurement
            distance_10s (float): Distance after 10 seconds
            distance_30s (float): Distance after 30 seconds
            speed_initial (str): Initial speed measurement
            speed_10s (str): Speed after 10 seconds
            speed_30s (str): Speed after 30 seconds
        
        Notes:
            - Updates geofence_alerts table
            - Marks movement check as completed
            - Includes error handling and logging
            - Returns True even on error to prevent processing loops
        """
        try:
            with DatabaseConfig.get_cursor() as cursor:
                cursor.execute("""
                UPDATE geofence_alerts 
                SET moving_status = %s,
                    distance_at_alert = %s,
                    distance_after_10s = %s,
                    distance_after_30s = %s,
                    speed_at_alert = %s,
                    speed_after_10s = %s,
                    speed_after_30s = %s,
                    movement_check_completed = TRUE
                WHERE unit = %s AND alert_time = %s
            """, (moving_status, initial_distance, distance_10s, distance_30s,
                  speed_initial, speed_10s, speed_30s, unit, alert_time))
            
        except Exception as e:
            logging.error(f"Error updating movement status in database: {e}", exc_info=True)
            # Even if database update fails, we don't want to get stuck
            return True

# Create global instance
movement_checker = MovementChecker()
