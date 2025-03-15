"""
Utility module for managing yard-related operations and data retrieval.

This module provides functionality for:
- Retrieving yard coordinates from the Yard API
- Fetching supervisor information for yards
- Handling API interactions with proper error handling
- URL encoding and parameter management

The module includes comprehensive error handling and logging
for debugging API interactions and data processing.
"""

import logging
import requests
from urllib.parse import quote
from config import SUPERVISOR_API_URL, YARD_API_URL

def get_yard_coordinates(yard_name):
    """
    Fetch the geographic coordinates (latitude, longitude) for a given yard.
    
    Args:
        yard_name (str): The name of the yard to look up
    
    Returns:
        tuple: A pair of (latitude, longitude) as floats,
               or (None, None) if coordinates cannot be retrieved
    
    Notes:
        - Makes HTTP request to yard API endpoint
        - URL encodes yard name for safe transmission
        - Handles network errors and JSON parsing
        - Returns None values if any error occurs
        - Includes detailed error logging
    """
    logging.info(f"Fetching coordinates for yard: {yard_name}")
    try:
        encoded_yard_name = quote(yard_name)
        url = f"{YARD_API_URL}?yard={encoded_yard_name}&api-version=2016-06-01&sp=%2Ftriggers%2Fmanual%2Frun&sv=1.0&sig=r1ZDbJJ9i-_jXig3NAetnHAqkcp2jz9MVHHZEeDS6oU"
        logging.debug(f"Making GET request to: {YARD_API_URL}")
        
        response = requests.get(url)
        logging.debug(f"API response status code: {response.status_code}")
        
        yard_data = response.json()
        logging.debug(f"Received yard data: {yard_data}")
        
        if yard_data and len(yard_data) > 0:
            latitude = yard_data[0].get("Latitude")
            longitude = yard_data[0].get("Longitude")
            logging.info(f"Found coordinates for {yard_name}: ({latitude}, {longitude})")
            return latitude, longitude
            
        logging.warning(f"No coordinates found for yard: {yard_name}")
        return None, None
    except requests.exceptions.RequestException as e:
        logging.error(f"Network error while fetching yard coordinates for {yard_name}: {e}", exc_info=True)
        return None, None
    except ValueError as e:
        logging.error(f"JSON parsing error for yard {yard_name}: {e}", exc_info=True)
        return None, None
    except Exception as e:
        logging.error(f"Unexpected error fetching yard coordinates for {yard_name}: {e}", exc_info=True)
        return None, None

def get_supervisor_for_yard(yard_name):
    """
    Retrieve the list of supervisors assigned to a specific yard.
    
    Args:
        yard_name (str): The name of the yard to get supervisors for
    
    Returns:
        list: List of supervisor data dictionaries from the API,
              or empty list if supervisors cannot be retrieved
    
    Notes:
        - Makes HTTP request to supervisor API endpoint
        - Includes API version and authentication parameters
        - Handles network errors and JSON parsing
        - Returns empty list for any error condition
        - Includes comprehensive error logging
    """
    logging.info(f"Fetching supervisor data for yard: {yard_name}")
    try:
        if not yard_name:
            logging.warning("Empty yard name provided, returning empty list")
            return []
            
        params = {
            "api-version": "2016-06-01",
            "sp": "/triggers/manual/run",
            "sv": "1.0",
            "sig": "r1ZDbJJ9i-_jXig3NAetnHAqkcp2jz9MVHHZEeDS6oU",
            "yard": yard_name
        }
        logging.debug(f"Making GET request to {SUPERVISOR_API_URL} with params: {params}")
        
        response = requests.get(SUPERVISOR_API_URL, params=params)
        logging.debug(f"API response status code: {response.status_code}")
        
        response.raise_for_status()
        supervisor_data = response.json()
        logging.info(f"Successfully retrieved supervisor data for yard {yard_name}")
        logging.debug(f"Supervisor data: {supervisor_data}")
        
        return supervisor_data
    except requests.exceptions.RequestException as e:
        logging.error(f"Network error while fetching supervisor data for {yard_name}: {e}", exc_info=True)
        return []
    except ValueError as e:
        logging.error(f"JSON parsing error for yard {yard_name}: {e}", exc_info=True)
        return []
    except Exception as e:
        logging.error(f"Unexpected error fetching supervisor data for {yard_name}: {e}", exc_info=True)
        return []
