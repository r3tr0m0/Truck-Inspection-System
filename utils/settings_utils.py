"""
Utility module for managing application settings stored in the database.

This module provides functionality for:
- Retrieving application settings with type conversion
- Updating setting values with validation
- Handling default values for missing settings

The module interacts with the app_settings table in the database and
includes comprehensive logging for debugging and monitoring.
"""

import logging
from config import DatabaseConfig

def get_setting(setting_name, default_value=None):
    logging.info(f"Attempting to retrieve setting: {setting_name}")
    try:
        with DatabaseConfig.get_cursor() as cursor:
            logging.debug(f"Executing SELECT query for setting: {setting_name}")
            cursor.execute(
                "SELECT setting_value, setting_type FROM app_settings WHERE setting_name = %s",
                (setting_name,)
            )
            result = cursor.fetchone()
            
        if result:
            value, setting_type = result
            logging.debug(f"Found setting {setting_name} with type {setting_type}")
            if setting_type == 'number':
                converted_value = float(value)
                logging.debug(f"Converted setting value to number: {converted_value}")
                return converted_value
            return value
        logging.info(f"Setting {setting_name} not found, returning default value: {default_value}")
        return default_value
    except Exception as e:
        logging.error(f"Error getting setting {setting_name}: {e}")
        return default_value

def update_setting(setting_name, value):
    logging.info(f"Attempting to update setting: {setting_name} to value: {value}")
    try:
        with DatabaseConfig.get_cursor() as cursor:
            logging.debug(f"Executing UPDATE query for setting: {setting_name}")
            cursor.execute(
                "UPDATE app_settings SET setting_value = %s WHERE setting_name = %s",
                (str(value), setting_name)
            )
            logging.info(f"Successfully updated setting: {setting_name}")
        return True
    except Exception as e:
        logging.error(f"Error updating setting {setting_name}: {e}")
        return False
