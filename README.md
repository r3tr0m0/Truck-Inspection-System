
# Trip Inspection and Geofence Alert System

## Overview

The **Trip Inspection and Geofence Alert System** is a real-time monitoring solution designed for Dawson Road Maintenance to track truck movements, compliance with trip inspections, and geofence alerts. The system integrates with **Skyhawk API**, **Geofence Alert API**, and **DRM Trip Inspection API** to provide a centralized platform for managing Dawson Road Construction operations efficiently. Key features include real-time alerts, movement status tracking, and automated notifications.

## File Structure

```
DawsonProject-Dummy-script2/
├── config/               # Application configurations (e.g., app_config.py)
├── routes/               # API route definitions
│   ├── geofence_routes.py # Handles geofence alert endpoints
│   ├── home_routes.py     # Main application routes
│   └── settings_routes.py # Settings-related endpoints
├── services/             # Business logic and backend services
│   ├── email.py           # Email notification logic (SendGrid integration)
│   ├── skyhawk.py         # Skyhawk API integration
│   └── inspection_utils.py# Trip inspection validation logic
├── static/               # Static files (CSS, JavaScript, images)
├── templates/            # HTML templates for rendering web pages
├── utils/                # Utility functions for reusable logic
│   ├── alert_utils.py     # Geofence alert processing
│   ├── time_utils.py      # Timezone and time calculations
│   ├── settings_utils.py  # Handles application settings logic
│   └── yard_utils.py      # Yard-related utility functions
├── background_tasks.py   # Scheduled background jobs
├── herokutest.py         # Application entry point
├── requirements.txt      # Python dependencies
├── Procfile              # Heroku deployment configuration
├── runtime.txt           # Python version for Heroku
├── .env                  # Environment variables (local setup)
└── README.md             # Project documentation (this file)
```

## APIs Used

1. **Skyhawk API**:  
   - Provides real-time truck telemetry (speed, coordinates).
   - Used for movement analysis (e.g., stationary, moving away).

2. **Geofence Alert API**:  
   - Triggers alerts when a truck exits a geofence.

3. **DRM Trip Inspection API**:  
   - Retrieves trip inspection details, yard data, and supervisor contact information.

4. **SendGrid API**:  
   - Sends automated email notifications for geofence alerts and inspection statuses.

## Technologies Used

- **Flask (v2.3.3)**: Python web framework.  
- **Werkzeug (v2.3.7)**: Internal Flask dependency for request handling.  
- **PostgreSQL**: Centralized database.  
- **psycopg2-binary (v2.9.9)**: PostgreSQL adapter for Flask.  
- **SendGrid (v6.10.0)**: Email notifications.  
- **Pytz (v2024.1)**: Timezone handling.  
- **Requests (v2.31.0)**: HTTP client library for making API calls.  
- **Geopy (v2.4.1)**: Geolocation and distance calculations.  
- **Gunicorn (v21.2.0)**: Production WSGI HTTP server.  
- **Python-Dotenv (v1.0.0)**: Manages environment variables.  
- **Python-Dateutil (v2.8.2)**: Advanced date/time manipulation.  
- **Urllib3 (v2.1.0)**: HTTP client for URL handling.  
- **Heroku**: Deployment platform.
- **Jinja2**: Template engine for rendering dynamic HTML content.
- **Logging**: Python's built-in module for creating and managing application logs.
- **Threading**: For managing background tasks and concurrent operations.
- **Datetime**: Standard Python library for handling date and time operations.

## Features

### 1. **Geofence Alerts**
- Detects when a truck leaves a geofence.
- Alerts are logged in the database and displayed on the `/all-geofence-alerts` page.

### 2. **Trip Inspection Compliance**
- Checks inspection status using the **DRM Trip Inspection API**.
- Notifies supervisors if inspections are overdue or incomplete.

### 3. **Truck Movement Status**
- Tracks movement using **Skyhawk API**.
- Determines if a truck is:
  - **Stationary**: No significant movement.
  - **Moving Away**: Distance from the geofence is increasing.
  - **Not Showing Alerts**: The API cannot establish a connection to the truck modem.

### 4. **Automated Email Alerts**
- Sends alerts for:
  - **Overdue Inspections**
- Development Mode: Emails are sent to testers.
- Production Mode: Emails are sent to supervisors.

### 5. **Settings Configuration**
- Manage thresholds, alert preferences, and other settings via the `/settings` page.

### 6. **Failsafes**
- **Duplicate Alert Prevention**: Implements cooldown logic.
- **Fallback Supervisors**: Sends alerts even if primary supervisor details are missing.

### 7. **Movement Validation Failsafe**
- Implements a 3-point check (at 0s, 10s, 30s intervals) to ensure accurate movement detection.

### 8. **Alert Cooldown Period**
- Prevents duplicate alerts by implementing a cooldown period for repeated geofence triggers.

### 9. **Web Interface Features**
- A dashboard to view geofence alerts, inspection statuses, and truck movements.
- Allows configuration of system settings through a user-friendly interface.

## Setup Guide

### Prerequisites
- Python 3.12
- PostgreSQL
- **pgAdmin 4** (for database management)
- A Heroku account with access to the Heroku Dashboard
- Your GitHub repository configured with the script in the `main` branch

---

### Installation and Deployment

1. **Log in to the Heroku Dashboard**:
   - Go to [Heroku Dashboard](https://dashboard.heroku.com/).
   - Log in with your Heroku credentials.

2. **Create a New Application**:
   - Click **New** → **Create New App**.
   - Enter a unique name for your application and select your region.
   - Click **Create App**.

3. **Connect the GitHub Repository**:
   - In the application’s dashboard, go to the **Deploy** tab.
   - Under **Deployment Method**, select **GitHub**.
   - Click **Connect to GitHub** and authorize access if prompted.
   - Search for your repository name (e.g., `DawsonProject-Dummy-script2`).
   - Click **Connect** to link the repository.

4. **Configure Environment Variables or Change the .env file on the Git itself**: 
   - Navigate to the **Settings** tab and click **Reveal Config Vars**.
   - Add the following environment variables:
     - `FLASK_ENV` = `production`
     - `DB_HOST` = `<your_postgres_host>` (found under the Heroku PostgreSQL add-on settings).
     - `DB_NAME` = `<your_database_name>` (same as above).
     - `DB_USER` = `<your_username>` (same as above).
     - `DB_PASSWORD` = `<your_password>` (same as above).
     - `SENDGRID_API_KEY` = `<your_sendgrid_key>` (from SendGrid).
     - `SENDER_EMAIL` = `<sender_email>` (the "from" email address for notifications).

5. **Deploy the Application**:
   - Under the **Deploy** tab, scroll to the **Manual Deploy** section.
   - Select the branch (e.g., `main`) and click **Deploy Branch**.
   - Wait for the deployment process to complete.
   - Once deployed, click **Open App** to access your application.

---

### Accessing PostgreSQL Database with pgAdmin 4

1. **Open pgAdmin 4**:
   - Launch **pgAdmin 4** on your system.

2. **Add a New Server**:
   - In the **pgAdmin 4** dashboard, click **Add New Server**.

3. **Enter Connection Details**:
   - Go to your Heroku dashboard, select your app, and find the **Heroku PostgreSQL** add-on under the **Resources** tab.
   - Click on the Heroku PostgreSQL add-on to access the database credentials.
   - Use these details in pgAdmin:
     - **Name**: Enter a custom name for the server (e.g., "Heroku PostgreSQL").
     - **Host**: Copy the `DB_HOST` from the Heroku PostgreSQL settings.
     - **Port**: Enter `5432`.
     - **Username**: Copy the `DB_USER`.
     - **Password**: Copy the `DB_PASSWORD`.

4. **Verify Connection**:
   - Click **Save** to connect.
   - If successful, your Heroku database will appear under the **Servers** section in pgAdmin.

5. **Explore the Database**:
   - Expand the database schema and tables to browse data.
   - Use the query tool to run SQL queries, such as:
     ```sql
     SELECT * FROM geofence_alerts ORDER BY alert_time DESC;
     ```
   - Inspect geofence alerts, truck statuses, and other system logs.

### Setting up Power BI

1. **Download the Power BI File**:
   - Go to the GitHub repository and download the pre-configured Power BI `.pbix` file.

2. **Open the Power BI File**:
   - Launch **Power BI Desktop**.
   - Open the downloaded `.pbix` file.

3. **Authenticate with the Database**:
   - If prompted for login credentials, retrieve the necessary database details from the Heroku dashboard:
     - **Host**: Copy the `DB_HOST`.
     - **Database Name**: Copy the `DB_NAME`.
     - **Username**: Copy the `DB_USER`.
     - **Password**: Copy the `DB_PASSWORD`.

4. **Resolve SSL Issues**:
   - If Power BI encounters SSL connection issues, download the necessary SSL certificates from the following link:  
     [Amazon RDS SSL Certificates](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/UsingWithRDS.SSL.html#UsingWithRDS.SSL.CertificatesAllRegions).
   - Save the certificates to your system and follow the Power BI instructions to import them.

5. **Verify and Refresh Data**:
   - After authentication and resolving any SSL issues, click **Refresh** in Power BI to pull the latest data from your Heroku PostgreSQL database.
   - Verify that dashboards are populated with the correct data (e.g., geofence alerts, truck statuses).


## Application Endpoints

1. **`/geofence-alert` (POST)**:
   - Logs geofence alerts.
   ```json
   {
    "Unit": "T2466",
    "GeoFence": "Williams Lake",
    "Service Area": "SA24",
    "Yard": "Williams Lake",
    "Timestamp": "2024-11-29T13:11:00.000Z"
   }
   ```

2. **`/all-geofence-alerts` (GET)**:
   - Displays all alerts.

3. **`/settings` (GET/POST)**:
   - View and update settings.

## Debugging

### Logs
- Access application logs directly on the Heroku website:
  1. Navigate to your app in the Heroku dashboard.
  2. Go to the **"More"** dropdown menu in the top right corner.
  3. Select **"View Logs"** to see real-time logs.
- Logs provide detailed insights into:
  - API request handling (e.g., `/geofence-alert` requests).
  - Background task execution via APScheduler.
  - Email delivery status using SendGrid.
  - Database query success or errors.

### Manual Testing with Postman
Postman is used to manually push geofence alerts and verify system behavior. Below are steps and examples:

1. **Testing Geofence Alerts**:
   - Use the **`/geofence-alert` (POST)** endpoint to simulate a geofence alert.
   - Example payload:
     ```json
     {
         "unit": "T2466",
         "geoFence": "Williams Lake",
         "serviceArea": "SA24",
         "yard": "Williams Lake",
         "timestamp": "2024-11-29T13:11:00.000Z"
     }
     ```
   - Ensure the `Body` tab in Postman is set to `raw` and `JSON` format.

2. **Verifying Responses**:
   - A successful response should look like:
     ```json
     {
         "alert_details": {
             "alert_time": "2024-12-06T09:57:02.868251+00:00",
             "completion_date": "December 05, 2024 - 09:57 AM PST",
             "inspection_status": "Inspection done but more than 8 hours ago ❌",
             "movement_status": "Checking movement...",
             "shift": "Night Shift (10PM - 6AM)",
             "supervisors": [
                 {
                     "Email": "example@example.ca",
                     "Employee Name": "Jane Smith",
                     "Yard Name": "Williams Lake"
                 }
             ],
             "truck_details": {
                 "latitude": 54.76778,
                 "longitude": -127.12581,
                 "location": "Yellowhead Highway, British Columbia"
             },
             "unit": "T2466",
             "yard": "Williams Lake",
             "yard_coordinates": {
                 "latitude": 52.168255,
                 "longitude": -122.162418"
             }
         },
         "message": "Movement tracking initiated",
         "status": "Processing",
         "task_id": "T2466_2024-12-06T09:57:02.868251+00:00"
     }
     ```

3. **Analyzing Movement Tracking**:
   - Logs and response data help verify whether the truck's movement (e.g., stationary, moving away) is being tracked correctly.
---

## Conclusion

The **Trip Inspection and Geofence Alert System** successfully addresses the challenges of monitoring truck movements and ensuring compliance with inspection requirements. By integrating real-time geofence alerts, movement tracking, and automated notifications, this system enhances operational efficiency and reduces the risk of non-compliance.

With over **1,078 Git commits** and **872 deployments**, we have built a solid solution deployed on Heroku and integrated with PostgreSQL for centralized data management. The system is also prepared for future enhancements, such as deeper analytics through Power BI.

We are proud to present this project and look forward to its potential contributions to Dawson Road Maintenance's operational goals.


