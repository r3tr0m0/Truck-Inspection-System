"""
Skyhawk Service Module

This module provides integration with the Skyhawk API for vehicle tracking
and monitoring. It handles authentication, data retrieval, and GPS coordinate
tracking for fleet vehicles.

Key Features:
- Skyhawk API authentication management
- Real-time vehicle location tracking
- Speed monitoring
- Comprehensive logging system
- Error handling and retry logic

Dependencies:
- requests: For making HTTP requests to Skyhawk API
- logging: For detailed logging of API interactions
- datetime: For timestamp management
- os: For log file management
"""

import requests
import logging
from datetime import datetime, timezone, timedelta
from logging.handlers import RotatingFileHandler
import os

class SkyhawkService:
    def __init__(self, base_url, company_id, username, password):
        # Set up logging configuration
        if not os.path.exists('logs'):
            os.makedirs('logs')
            logging.debug(f"Created logs directory at {os.path.abspath('logs')}")
            
        self.logger = logging.getLogger('SkyhawkService')
        self.logger.setLevel(logging.DEBUG)
        
        # Create handlers with detailed formatting
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
        )
        console_formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        )
        
        # Configure rotating file handler for log management
        file_handler = RotatingFileHandler(
            'logs/skyhawk_service.log',
            maxBytes=10*1024*1024,  # 10MB file size
            backupCount=5
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(file_formatter)
        self.logger.debug("Configured rotating file handler with 10MB file size and 5 backups")
        
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(console_formatter)
        
        # Ensure clean logger setup
        if self.logger.handlers:
            self.logger.debug(f"Clearing {len(self.logger.handlers)} existing handlers")
            self.logger.handlers.clear()
            
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
        self.logger.debug("Added file and console handlers to logger")
        
        # Initialize service parameters
        self.base_url = base_url
        self.company_id = company_id
        self.username = username
        self.password = password
        self._auth_token = None
        self.logger.info(f"SkyhawkService initialized with base_url: {base_url}, company_id: {company_id}")
        self.logger.debug("Service initialization complete")

    def authenticate(self):
        """
        Authenticate with the Skyhawk API and obtain an access token.
        
        This method handles the authentication process with the Skyhawk API,
        storing the received token for subsequent requests. It includes
        comprehensive error handling and logging.
        
        Returns:
            str: Authentication token if successful, None otherwise
            
        Raises:
            requests.exceptions.RequestException: If the API request fails
            Exception: For unexpected errors during authentication
        """
        try:
            self.logger.info("Attempting to authenticate with SkyHawk API")
            auth_url = f"{self.base_url}/auth"
            
            headers = {
                "Content-Type": "application/json"
            }
            
            auth_data = {
                "username": self.username,
                "password": self.password
            }
            
            self.logger.debug(f"Authentication URL: {auth_url}")
            self.logger.debug("Sending authentication request with headers and data")
            self.logger.debug(f"Request headers: {headers}")
            
            response = requests.post(
                auth_url,
                headers=headers,
                json=auth_data
            )
            
            self.logger.debug(f"Auth response status code: {response.status_code}")
            self.logger.debug(f"Auth response headers: {response.headers}")
            response.raise_for_status()
            
            # Strip quotes from token if present
            token = response.text.strip('"')
            self._auth_token = token
            
            if self._auth_token:
                self.logger.info("Authentication successful")
                self.logger.debug(f"Token length: {len(self._auth_token)} characters")
                return self._auth_token
            else:
                self.logger.error("No token received in authentication response")
                self.logger.debug(f"Raw response content: {response.text}")
                return None
                
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Authentication request failed: {str(e)}", exc_info=True)
            self.logger.debug(f"Request URL: {auth_url}")
            return None
        except Exception as e:
            self.logger.error(f"Unexpected error during authentication: {str(e)}", exc_info=True)
            self.logger.debug("Full authentication attempt failed")
            return None

    def get_truck_coordinates(self, unit_name):
        """
        Retrieve current coordinates and speed for a specific truck.
        
        This method queries the Skyhawk API to get the latest location and
        speed data for a specified vehicle. It handles authentication,
        data retrieval, and error cases.
        
        Args:
            unit_name (str): Identifier of the truck to locate
            
        Returns:
            tuple: (latitude, longitude, location, speed) where:
                - latitude (float): Vehicle's latitude or None if unavailable
                - longitude (float): Vehicle's longitude or None if unavailable
                - location (str): Human-readable location or error message
                - speed (str): Vehicle speed with units or None if unavailable
                
        Note:
            The method includes a 45-second lookback window for message retrieval
            to ensure recent data availability.
        """
        try:
            self.logger.info(f"Attempting to get coordinates for truck: {unit_name}")
            
            # Get or refresh auth token
            auth_token = self._auth_token or self.authenticate()
            if not auth_token:
                self.logger.error("Failed to obtain authentication token")
                self.logger.debug("Returning early due to missing auth token")
                return None, None, "Geofence Alert Triggered - Could Not Fetch Skyhawk Data", None
                
            headers = {
                "Authorization": f"Bearer {auth_token}",
                "Content-Type": "application/json"
            }
            self.logger.debug("Authentication token obtained successfully")
            self.logger.debug(f"Using headers: {headers}")
            
            # Get asset list
            asset_list_url = f"{self.base_url}/companies/{self.company_id}/assets"
            self.logger.debug(f"Fetching asset list from: {asset_list_url}")
            
            response = requests.get(asset_list_url, headers=headers)
            self.logger.debug(f"Asset list response status code: {response.status_code}")
            self.logger.debug(f"Asset list response headers: {response.headers}")
            response.raise_for_status()
            
            assets = response.json()
            self.logger.debug(f"Retrieved {len(assets)} assets from API")
            self.logger.debug(f"Asset list response size: {len(str(assets))} bytes")
            
            # Find truck ID
            truck_id = next((asset.get("id") for asset in assets if asset.get("name") == unit_name), None)
            if not truck_id:
                self.logger.warning(f"Truck '{unit_name}' not found in asset list")
                self.logger.debug(f"Available asset names: {[asset.get('name') for asset in assets]}")
                return None, None, "Geofence Alert Triggered - Could Not Fetch Skyhawk Data", None
                
            self.logger.debug(f"Found truck ID: {truck_id} for unit: {unit_name}")
            
            # Get messages for the truck within a 45-second window
            current_time = datetime.now(timezone.utc)
            from_time = current_time - timedelta(seconds=45)

            from_time_str = from_time.strftime('%Y%m%dT%H%M%S.000Z')
            to_time_str = current_time.strftime('%Y%m%dT%H%M%S.000Z')
            
            messages_url = f"{self.base_url}/companies/{self.company_id}/assets/{truck_id}/messages"
            self.logger.debug(f"Fetching messages from: {messages_url}")
            self.logger.debug(f"Time range: {from_time_str} to {to_time_str}")
            self.logger.debug(f"Time window: {(current_time - from_time).total_seconds()} seconds")
            
            response = requests.get(
                messages_url, 
                headers=headers, 
                params={
                    "from": from_time_str,
                    "to": to_time_str
                }
            )
            
            if response.status_code != 200:
                self.logger.error(f"Failed to get messages for truck {unit_name}: {response.status_code}")
                return None, None, "Geofence Alert Triggered - Could Not Fetch Skyhawk Data", None
                
            messages = response.json().get(truck_id, [])
            if not messages:
                self.logger.warning(f"No messages found for truck {unit_name}")
                self.logger.debug(f"Empty messages response for truck ID: {truck_id}")
                return None, None, "Geofence Alert Triggered - Could Not Fetch Skyhawk Data", None
                
            # Extract GPS data from the most recent message
            message = messages[0]  # Take the first (most recent) message
            self.logger.debug(f"Message details for {unit_name}:")
            self.logger.debug(f"Message ID: {message.get('id', 'N/A')}")
            self.logger.debug(f"Timestamp: {message.get('timestamp', 'N/A')}")

            # Parse and validate GPS data
            gps_data = message.get("gps", {})
            latitude = gps_data.get("latitude")
            longitude = gps_data.get("longitude")
            location = gps_data.get("location", "Location data unavailable")
            speed = gps_data.get("speed", 0)

            self.logger.info(f"Successfully retrieved coordinates for {unit_name}: "
                          f"lat={latitude}, lon={longitude}, speed={speed}")
            self.logger.debug(f"Location: {location}")

            return latitude, longitude, location, f"{speed} km/h" if speed else "0 km/h"
            
        except (requests.exceptions.RequestException, Exception) as e:
            self.logger.error(f"Error fetching coordinates for {unit_name}: {str(e)}", exc_info=True)
            return None, None, "Geofence Alert Triggered - Error Fetching Data", None
