"""
Home Routes Module

This module handles the main landing page routes of the application.
It provides the entry point for users accessing the application's
root URL, rendering the main dashboard or home page.
"""

from flask import Blueprint, render_template

# Create a Blueprint for home-related routes
home_bp = Blueprint('home', __name__)

@home_bp.route('/')
def home():
    """
    Render the application's main landing page.
    
    This route handles requests to the root URL ('/') and displays
    the main dashboard or home page of the application.
    
    Returns:
        rendered_template: The rendered HTML for the home page
    """
    return render_template('home.html')
