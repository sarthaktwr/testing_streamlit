import streamlit as st
from geopy.distance import geodesic
import math
import pandas as pd
import pydeck as pdk
import gspread
from datetime import datetime
from google.oauth2.service_account import Credentials
import json
import numpy as np

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
    current_time = datetime.utcnow().isoformat()
    sheet.append_row([current_time, 'True', unit_type])
    st.session_state['alert_sent'] = True
    st.write(f"Alert sent to {unit_type}!")

def calculate_3d_distance(loc1, loc2):
    surface_distance = geodesic((loc1[0], loc1[1]), (loc2[0], loc2[1])).meters
    elevation_difference = abs(loc1[2] - loc2[2])
    distance_3d = math.sqrt(surface_distance**2 + elevation_difference**2)
    return distance_3d

def check_aircraft_proximity(ground_unit_location, aircraft_location):
    distance_to_aircraft = calculate_3d_distance(ground_unit_location, aircraft_location)
    return distance_to_aircraft <= PROXIMITY_THRESHOLD

def create_alerts_sheet():
    sheet = client.create('Aircraft Proximity Alert System')
    sheet.share('aksh30990@gmail.com', perm_type='user', role='writer')
    worksheet = sheet.sheet1
    worksheet.append_row(['Time', 'Alert', 'Unit Type'])
    return worksheet

def check_for_alerts():
    sheet = client.open('Aircraft Proximity Alert System').sheet1
    alerts = sheet.get_all_records()
    if alerts:
        latest_alert = alerts[-1]
        if latest_alert['Alert'] == 'True':
            return latest_alert
    return None

def login_user(username, password):
    for role, credentials in USER_ROLES.items():
        if credentials['username'] == username and credentials['password'] == password:
            st.session_state['user_role'] = role
            st.success(f'Logged in as {role}')
            st.rerun()
            return
    st.error('Incorrect username or password')

# Generate a simulated flight path
def generate_flight_path(start_lat, start_lon, num_points=100):
    latitudes = np.linspace(start_lat, start_lat + 0.1, num_points)  # Simulate a slight northward flight
    longitudes = np.linspace(start_lon, start_lon + 0.1, num_points)  # Simulate a slight eastward flight
    elevations = np.linspace(1000, 5000, num_points)  # Simulate an ascent
    return list(zip(latitudes, longitudes, elevations))

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

        # Simulate flight path
        st.subheader('Simulate Flight Path')
        flight_path = generate_flight_path(ground_lat, ground_lon)

        # Create a DataFrame for the flight path
        flight_df = pd.DataFrame(flight_path, columns=['latitude', 'longitude', 'elevation'])

        # Define the initial view state of the map
        view_state = pdk.ViewState(
            latitude=flight_df['latitude'].mean(),
            longitude=flight_df['longitude'].mean(),
            zoom=11,
            pitch=50,
        )

        # Create the deck.gl map with the flight path
        path_layer = pdk.Layer(
            "PathLayer",
            data=flight_df,
            get_color=[255, 0, 0, 150],  # Red color for the path
            width_scale=20,
            width_min_pixels=2,
            get_path="path",
            get_width=5,
        )

        scatter_layer = pdk.Layer(
            "ScatterplotLayer",
            data=pd.DataFrame({'latitude': [ground_lat], 'longitude': [ground_lon]}),
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
        for index, row in flight_df.iterrows():
            aircraft_location = (row['latitude'], row['longitude'], row['elevation'])
            alert = check_aircraft_proximity(ground_unit_location, aircraft_location)
            distance_to_ground = calculate_3d_distance(ground_unit_location, aircraft_location)

            # Add an alert if the aircraft is within 4.5 km
            if distance_to_ground <= 4500:
                st.write(f"Alert: Aircraft is within firing range. Distance: {distance_to_ground:.2f} meters.")

                # Send alert to ground unit
                if st.button(f"Send Alert to Ground Unit for Aircraft at index {index}"):
                    send_alert_to_unit('ground_unit', sheet)

    elif st.session_state['user_role'] == 'ground_unit':
        st.title('Ground Unit Dashboard')
        system_alerts = check_for_alerts()
        if system_alerts:
            if system_alerts['Unit Type'] == 'ground_unit':
                st.error('Keep Firing.')
            else:
                st.error('Friendly aircraft approaching. Stop Firing!')

    elif st.session_state['user_role'] == 'aircraft':
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
