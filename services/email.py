"""
Email Service Module

This module provides email notification functionality using the SendGrid API.
It handles sending inspection alerts to supervisors and managing email delivery
tracking in both development and production environments.

Key Features:
- SendGrid API integration for reliable email delivery
- Development and production mode support
- Supervisor notification management
- Email delivery tracking and logging
- Fallback email handling for unassigned yards
"""

import logging
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Email, To, Content
from config.database import DatabaseConfig
from utils.settings_utils import get_setting
from datetime import datetime, timezone

# Configure logging
logger = logging.getLogger('EmailService')

__all__ = ['EmailService']

class EmailService:
    def __init__(self, api_key, sender_email, recipient_emails, sender_name="Skyhawk Notifications", fallback_email=None):
        self.client = SendGridAPIClient(api_key)
        self.sender_email = sender_email
        self.recipient_emails = recipient_emails if isinstance(recipient_emails, list) else [recipient_emails]
        self.sender_name = sender_name
        self.fallback_email = fallback_email
        self.logger = logging.getLogger(__name__)

    def _get_current_mode(self):
        """
        Get the current application operating mode.
        
        Returns:
            str: Current mode ('development' or 'production')
        """
        return get_setting('app_mode', 'development')

    def send_inspection_alert(self, asset_name, yard_name, inspection_date, supervisors):
        """
        Send an email alert for an overdue inspection.
        
        Sends notification emails about missing pre-trip inspections to appropriate
        recipients based on the current operating mode. Updates the database with
        email delivery status and timing information.
        
        Args:
            asset_name (str): Name/ID of the asset requiring inspection
            yard_name (str): Name of the yard where the asset is located
            inspection_date (datetime): Date/time of the missed inspection
            supervisors (list): List of supervisors responsible for the yard
            
        Returns:
            bool: True if email was sent successfully, False otherwise
        """
        mode = self._get_current_mode()
        logger.info(f"Sending inspection alert in {mode} mode for asset: {asset_name}")

        if mode == 'development':
            success = self._send_development_inspection_alert(asset_name, yard_name, inspection_date, supervisors)
        else:
            success = self._send_production_inspection_alert(asset_name, yard_name, inspection_date, supervisors)

        # Update the email_sent and timing information in the database
        try:
            with DatabaseConfig.get_cursor() as cursor:
                email_sent_time = datetime.now(timezone.utc) if success else None
                
                cursor.execute("""
                    UPDATE geofence_alerts
                    SET email_sent = %s,
                        email_sent_time = %s,
                        alert_to_email_time_diff = CASE 
                            WHEN %s THEN age(%s, alert_time)::text
                            ELSE NULL 
                        END
                    WHERE unit = %s AND alert_time = %s
                """, (success, email_sent_time, success, email_sent_time, asset_name, inspection_date))
                logger.info(f"Updated email status and timing for asset: {asset_name}")
        except Exception as e:
            logger.error(f"Failed to update email status and timing for asset: {asset_name}: {str(e)}")

        return success

    def _send_development_inspection_alert(self, asset_name, yard_name, inspection_date, supervisors):
        """
        Send inspection alert in development mode.
        
        Development mode sends alerts to configured test recipients instead
        of actual supervisors.
        
        Args:
            asset_name (str): Name/ID of the asset
            yard_name (str): Name of the yard
            inspection_date (datetime): Date/time of missed inspection
            supervisors (list): List of supervisors (not used in dev mode)
            
        Returns:
            bool: True if all emails sent successfully, False otherwise
        """
        logger.info(f"Preparing development inspection alert email for asset: {asset_name}")
        
        try:
            from_email = Email(self.sender_email, self.sender_name)
            subject = f"{asset_name} - potential missing Pre-trip Inspection (development mode)"
            
            formatted_date = format_timestamp_for_email(inspection_date)
            body = f"""Warning: {asset_name} has left the {yard_name} yard with inspection time {formatted_date}, but there is no Pre-Trip inspection found in the system.

Please confirm with the operator if a Trip Inspection has been completed prior to them using the vehicle on their shift."""

            content = Content("text/plain", body)
            
            success = True
            for recipient_email in self.recipient_emails:
                try:
                    to_email = To(recipient_email)
                    mail = Mail(from_email, to_email, subject, content)
                    logger.debug(f"Attempting to send inspection alert email to {recipient_email}")
                    self.client.send(mail)
                    logger.info(f"Successfully sent inspection alert email to {recipient_email}")
                except Exception as e:
                    logger.error(f"Failed to send inspection alert email to {recipient_email}: {str(e)}")
                    success = False
            
            return success
        
        except Exception as e:
            logger.error(f"Failed to prepare inspection alert email for {asset_name}: {str(e)}")
            return False

    def _send_production_inspection_alert(self, asset_name, yard_name, inspection_date, supervisors):
        """
        Send inspection alert in production mode.
        
        Production mode sends alerts to actual yard supervisors, with fallback
        to a default recipient if no supervisors are assigned.
        
        Args:
            asset_name (str): Name/ID of the asset
            yard_name (str): Name of the yard
            inspection_date (datetime): Date/time of missed inspection
            supervisors (list): List of supervisors for the yard
            
        Returns:
            bool: True if all emails sent successfully, False otherwise
        """
        logger.info(f"Preparing production inspection alert email for asset: {asset_name}")
        
        supervisor_emails = self._get_supervisor_emails_for_yard(yard_name)
        fallback_message = ""
        if not supervisor_emails:
            logger.warning(f"No supervisor emails found for yard {yard_name}, using fallback email")
            supervisor_emails = [self.fallback_email] if self.fallback_email else []
            fallback_message = "\n\nNOTE: This email was sent to the fallback recipient because no supervisor email was found for this yard."
        
        from_email = Email(self.sender_email, self.sender_name)
        subject = f"{asset_name} - potential missing Pre-trip Inspection (production mode)"
        if fallback_message:
            subject = "Default Fallback Message: " + subject

        formatted_date = format_timestamp_for_email(inspection_date)
        body = f"""Warning: {asset_name} has left the {yard_name} yard with inspection time {formatted_date}, but there is no Pre-Trip inspection found in the system.

Please confirm with the operator if a Trip Inspection has been completed prior to them using the vehicle on their shift.{fallback_message}"""
        success = True
        for supervisor_email in supervisor_emails:
            try:
                to_email = To(supervisor_email)
                content = Content("text/plain", body)
                mail = Mail(from_email, to_email, subject, content)
                
                logger.debug(f"Attempting to send inspection alert email to {supervisor_email}")
                self.client.send(mail)
                logger.info(f"Successfully sent inspection alert email to {supervisor_email}")
            except Exception as e:
                logger.error(f"Failed to send inspection alert email to {supervisor_email}: {str(e)}")
                success = False
                
        return success

    def _get_supervisor_emails_for_yard(self, yard_name):
        """
        Retrieve email addresses for supervisors assigned to a yard.
        
        Args:
            yard_name (str): Name of the yard to get supervisors for
            
        Returns:
            list: List of supervisor email addresses for the yard
        """
        logger.info(f"Getting supervisor emails for yard: {yard_name}")
        try:
            with DatabaseConfig.get_cursor() as cursor:
                query = """
                    SELECT supervisor_email 
                    FROM yard_supervisors 
                    WHERE yard_name = %s 
                    AND is_selected = TRUE 
                    AND supervisor_email IS NOT NULL
                """
                logger.debug(f"Executing query: {query} with yard_name: {yard_name}")
                cursor.execute(query, (yard_name,))
                
                results = cursor.fetchall()
                logger.debug(f"Raw query results: {results}")
                
                supervisor_emails = [row[0] for row in results]
                logger.debug(f"Extracted supervisor emails: {supervisor_emails}")
                    
            if not supervisor_emails:
                logger.warning(f"No supervisor emails found for yard: {yard_name}")
                return []
                
            logger.info(f"Found {len(supervisor_emails)} supervisor emails for yard: {yard_name}")
            return supervisor_emails
        except Exception as e:
            logger.error(f"Error getting supervisor emails for yard {yard_name}: {e}")
            logger.exception(e)  # This will log the full stack trace
            return []


def format_timestamp_for_email(timestamp):
    """
    Format a timestamp for display in email messages.
    
    Args:
        timestamp (datetime|str): Timestamp to format
        
    Returns:
        str: Formatted timestamp string (e.g., "11 November 2024 at 2:30 PM PST")
    """
    if not timestamp:
        return 'N/A'
    try:
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        
        # Format as "11 November 2024 at 2:30 PM PST"
        return timestamp.strftime("%d %B %Y at %I:%M %p PST")
    except Exception as e:
        logger.error(f"Error formatting timestamp: {e}")
        return str(timestamp)
