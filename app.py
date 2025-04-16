import streamlit as st
from geopy.distance import geodesic
import math
import pandas as pd
import pydeck as pdk
import gspread
from datetime import datetime
from google.oauth2.service_account import Credentials
import json

# Constants
PROXIMITY_THRESHOLD = 4500  # in meters
# Simulated user roles and credentials
USER_ROLES = {
    'command_center': {'username': 'command', 'password': 'center123'},
    'ground_unit': {'username': 'ground', 'password': 'unit123'},
    'aircraft': {'username': 'aircraft', 'password': 'flight123'}
}
scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
google_credentials = json.loads(st.secrets['google_credentials']['value'])
creds = Credentials.from_service_account_info(google_credentials, scopes=scope)
client = gspread.authorize(creds)

# Initialize session state
if 'user_role' not in st.session_state:
    st.session_state['user_role'] = None
if 'alert_sent' not in st.session_state:
    st.session_state['alert_sent'] = False

def send_alert_to_unit(unit_type, sheet):
    """
    Sends an alert to a specific unit type.
    Args:
    unit_type (str): The type of unit to send the alert to.
    Returns:
    None
    """
    current_time = datetime.utcnow().isoformat()
    sheet.append_row([current_time, 'True', unit_type])
    st.session_state['alert_sent'] = True
    st.write(f"Alert sent to {unit_type}!")

def calculate_3d_distance(loc1, loc2):
    """
    Calculates the 3D distance between two locations.
    Args:
    loc1 (tuple): The 3D coordinates of the first location.
    loc2 (tuple): The 3D coordinates of the second location.
    Returns:
    float: The 3D distance between the two locations in meters.
    """
    surface_distance = geodesic((loc1[0], loc1[1]), (loc2[0], loc2[1])).meters
    elevation_difference = abs(loc1[2] - loc2[2])
    distance_3d = math.sqrt(surface_distance**2 + elevation_difference**2)
    return distance_3d

def check_aircraft_proximity(ground_unit_location, aircraft_location):
    """
    Checks if an aircraft is within a certain proximity to a ground unit.
    Args:
    ground_unit_location (tuple): The 3D coordinates of the ground unit.
    aircraft_location (tuple): The 3D coordinates of the aircraft.
    Returns:
    bool: True if the aircraft is within the proximity threshold, False otherwise.
    """
    distance_to_aircraft = calculate_3d_distance(ground_unit_location, aircraft_location)
    return distance_to_aircraft <= PROXIMITY_THRESHOLD

def create_alerts_sheet():
    """
    Creates a Google Sheet to store alerts.
    Returns:
    gspread.Spreadsheet: The created Google Sheet.
    """
    sheet = client.create('Aircraft Proximity Alert System')
    sheet.share('aksh30990@gmail.com', perm_type='user', role='writer')
    worksheet = sheet.sheet1
    worksheet.append_row(['Time', 'Alert', 'Unit Type'])
    return worksheet

def check_for_alerts():
    """
    Checks if there are any alerts in the Google Sheet.
    Returns:
    bool: True if there are alerts, False otherwise.
    """
    sheet = client.open('Aircraft Proximity Alert System').sheet1
    alerts = sheet.get_all_records()
    if alerts:
        latest_alert = alerts[-1]
        if latest_alert['Alert'] == 'True':
            return latest_alert
    return None

def login_user(username, password):
    """
    Logs in a user with the given username and password.
    Args:
    username (str): The username of the user to log in.
    password (str): The password of the user to log in.
    Returns:
    None
    """
    for role, credentials in USER_CREDENTIALS.items():
        if credentials['username'] == username and credentials['password'] == password:
            st.session_state['role'] = role
            st.session_state['logged_in'] = True
            st.success(f'Logged in as {role}')
            st.rerun()  # Rerun the app to reflect the new user role
            return
    st.error('Incorrect username or password')

# Login form
if st.session_state['user_role'] is None:
    st.subheader('Login')
    username = st.text_input('Username')
    password = st.text_input('Password', type='password')
    if st.button('Login'):
        login_user(username, password)

# App functionality based on user role
else:
    if st.session_state['user_role'] == 'command_center':
        # Command center interface
        st.title('Command Center Dashboard')
        st.title('Aircraft Proximity Alert System')
        try:
            sheet = client.open('Aircraft Proximity Alert System').sheet1
        except gspread.SpreadsheetNotFound:
            sheet = create_alerts_sheet()

        # Input fields for the ground unit location
        st.subheader('Ground Unit Location')
        ground_lat = st.number_input('Latitude (deg)', value=0.0, format='%f')
        ground_lon = st.number_input('Longitude (deg)', value=0.0, format='%f')
        ground_elev = st.number_input('Elevation (meters)', value=0.0, format='%f')
        ground_unit_location = (ground_lat, ground_lon, ground_elev)

        # File uploader for the aircraft location CSV
        st.subheader('Upload Aircraft Location CSV')
        csv_file = st.file_uploader("Choose a CSV file", type="csv")

        if csv_file is not None:
            # Read the CSV file into a DataFrame
            df = pd.read_csv(csv_file)

            # Ensure the required columns are present
            required_columns = ['latitude_wgs84(deg)', 'longitude_wgs84(deg)', 'elevation_wgs84(m)']
            if all(col in df.columns for col in required_columns):
                # Create a new column for the path to match PyDeck's input format
                df['path'] = df[['longitude_wgs84(deg)', 'latitude_wgs84(deg)']].values.tolist()

                # Define the initial view state of the map
                view_state = pdk.ViewState(
                    latitude=df['latitude_wgs84(deg)'].mean(),
                    longitude=df['longitude_wgs84(deg)'].mean(),
                    zoom=11,
                    pitch=50,
                )

                # Create a DataFrame for the ground unit
                ground_unit_df = pd.DataFrame({
                    'latitude': [ground_unit_location[0]],
                    'longitude': [ground_unit_location[1]],
                    'elevation': [ground_unit_location[2]],
                })

                # Create the deck.gl map with all layers
                path_layer = pdk.Layer(
                    "PathLayer",
                    data=pd.DataFrame({'path': [df['path'].tolist()]}),
                    pickable=True,
                    get_color=[255, 0, 0, 150],  # Red color for the path
                    width_scale=20,
                    width_min_pixels=2,
                    get_path="path",
                    get_width=5,
                )

                scatter_layer = pdk.Layer(
                    "ScatterplotLayer",
                    data=ground_unit_df,
                    get_position=["longitude", "latitude"],
                    get_fill_color=[0, 0, 255, 50],  # Light blue color for the circle
                    get_radius=2500,  # 2.5km radius
                    pickable=True,
                )

                r = pdk.Deck(
                    layers=[path_layer, scatter_layer],
                    initial_view_state=view_state,
                    map_style="mapbox://styles/mapbox/light-v9",
                )

                # Render the updated map
                st.pydeck_chart(r)

                # Calculate proximity for the current aircraft position
                for index, row in df.iterrows():
                    aircraft_location = (
                        row['latitude_wgs84(deg)'],
                        row['longitude_wgs84(deg)'],
                        row['elevation_wgs84(m)']
                    )
                    alert = check_aircraft_proximity(ground_unit_location, aircraft_location)
                    distance_to_ground = calculate_3d_distance(ground_unit_location, aircraft_location)

                    # Add an alert if the aircraft is within 4.5 km
                    if distance_to_ground <= 4500:
                        st.write(f"Alert: Aircraft is within firing range. Distance: {distance_to_ground:.2f} meters.")

                        # Send alert to ground unit
                        if st.button(f"Send Alert to Ground Unit for Aircraft {index}"):
                            send_alert_to_unit('ground_unit', sheet)

            else:
                st.error('CSV file must contain latitude, longitude, and elevation columns.')

    elif st.session_state['user_role'] == 'ground_unit':
        # Ground unit interface
        st.title('Ground Unit Dashboard')
        system_alerts = check_for_alerts()
        if system_alerts:
            if system_alerts['Unit Type'] == 'ground_unit':
                st.error('Keep Firing.')
            else:
                st.error('Friendly aircraft approaching. Stop Firing!')

    elif st.session_state['user_role'] == 'aircraft':
        # Aircraft interface
        st.title('Aircraft Dashboard')
        system_alerts = check_for_alerts()
        if system_alerts:
            if system_alerts['Unit Type'] == 'ground_unit':
                st.error('Ground Unit Firing. Reroute the current path.')
            else:
                st.error('Clearance to fly.')

    # Logout button
    if st.session_state['user_role'] is not None:
        if st.button('Logout'):
            st.session_state['user_role'] = None
            st.session_state['alert_sent'] = False
            st.write("You have been logged out.")
