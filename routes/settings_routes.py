"""
Settings Routes Module

This module handles all routes related to application settings management.
It provides endpoints for viewing, updating, and retrieving application
settings stored in the database. The module implements proper error handling
and logging for all operations.
"""

import logging
from flask import Blueprint, request, redirect, url_for, flash, render_template, jsonify
from config import DatabaseConfig

# Configure logger for settings module
logger = logging.getLogger(__name__)

# Create Blueprint for settings-related routes
settings_bp = Blueprint('settings', __name__)

def update_setting(setting_name, value):
    """
    Helper function to update a single setting in the database.
    
    Args:
        setting_name (str): Name of the setting to update
        value (str): New value for the setting
    
    Returns:
        bool: True if update was successful, False otherwise
        
    Note:
        Uses a database cursor context manager for automatic
        connection management and error handling.
    """
    try:
        with DatabaseConfig.get_cursor() as cursor:
            cursor.execute("""
                UPDATE app_settings 
                SET setting_value = %s 
                WHERE setting_name = %s
                """, 
                (value, setting_name)
            )
            return cursor.rowcount > 0
    except Exception as e:
        logger.error(f"Failed to update setting {setting_name}: {str(e)}")
        return False

@settings_bp.route('/', methods=['GET'])
def settings():
    """
    Route to display the settings management page.
    
    Retrieves all application settings from the database and renders
    them in the settings template. Settings are ordered by their ID
    for consistent display.
    
    Returns:
        rendered_template: Settings page with all current settings
        tuple: Error page with 500 status code if database operation fails
    """
    logger.info("Accessing settings page")
    try:
        with DatabaseConfig.get_cursor() as cursor:
            cursor.execute("""
                SELECT setting_name, setting_value, setting_type, display_name, description 
                FROM app_settings 
                ORDER BY setting_id
            """)
            settings = cursor.fetchall()
            
        logger.debug(f"Successfully retrieved {len(settings)} settings")
        return render_template('settings.html', settings=settings)
    except Exception as e:
        error_msg = f"Error loading settings: {str(e)}"
        logger.error(error_msg, exc_info=True)
        flash(error_msg, 'error')
        return render_template('error.html', error=error_msg), 500

@settings_bp.route('/save', methods=['POST'])
def save_settings():
    """
    Route to handle bulk settings updates from form submission.
    
    Processes form data and updates multiple settings at once.
    Handles checkbox inputs specially due to their hidden field behavior.
    Implements secure logging by redacting sensitive values.
    
    Returns:
        redirect: Redirects to settings page with success/error message
    """
    logger.info("Processing settings form submission")
    try:
        success = True
        form_data = request.form.to_dict(flat=False)
        
        # Log the received settings data (excluding sensitive values)
        safe_form_data = {k: v if 'password' not in k.lower() else '[REDACTED]' 
                         for k, v in form_data.items()}
        logger.debug(f"Received settings update: {safe_form_data}")
        
        # Handle each setting
        for setting_name, values in form_data.items():
            # For checkboxes, we'll get the last value (since hidden field comes first)
            value = values[-1] if isinstance(values, list) else values
            
            if not update_setting(setting_name, value):
                success = False
                logger.warning(f"Failed to update setting: {setting_name}")
                
        if success:
            logger.info("Successfully updated all settings")
            flash('Settings updated successfully', 'success')
        else:
            logger.warning("Some settings failed to update")
            flash('Error updating one or more settings', 'error')
            
        return redirect(url_for('settings.settings'))
    except Exception as e:
        error_msg = f"Error saving settings: {str(e)}"
        logger.error(error_msg, exc_info=True)
        flash(error_msg, 'error')
        return redirect(url_for('settings.settings'))

@settings_bp.route('/update', methods=['POST'])
def update_setting_value():
    """
    API route to update a single setting via AJAX request.
    
    Expects JSON payload with setting_name and value fields.
    Provides JSON response indicating success or failure.
    
    Returns:
        json: Success status or error message with appropriate HTTP status code
    """
    try:
        data = request.json
        setting_name = data.get('setting_name')
        value = data.get('value')
        
        if not setting_name or value is None:
            return jsonify({"error": "Missing required parameters"}), 400
            
        success = update_setting(setting_name, value)
        if success:
            return jsonify({"status": "success"})
        return jsonify({"error": "Failed to update setting"}), 500
            
    except Exception as e:
        logger.error(f"Error updating setting: {str(e)}")
        return jsonify({"error": str(e)}), 500

@settings_bp.route('/get/<setting_name>')
def get_setting_value(setting_name):
    """
    API route to retrieve a single setting value.
    
    Args:
        setting_name (str): Name of the setting to retrieve
    
    Returns:
        json: Setting value or error message with appropriate HTTP status code
    """
    try:
        with DatabaseConfig.get_cursor() as cursor:
            cursor.execute(
                "SELECT setting_value FROM app_settings WHERE setting_name = %s",
                (setting_name,)
            )
            result = cursor.fetchone()
            if result:
                return jsonify({"value": result[0]})
            return jsonify({"value": None}), 404
    except Exception as e:
        logger.error(f"Error getting setting {setting_name}: {str(e)}")
        return jsonify({"error": str(e)}), 500
