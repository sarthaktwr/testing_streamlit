import streamlit as st
from geopy.distance import geodesic
import math
import time
import pandas as pd
import pydeck as pdk
import gspread
from datetime import datetime
from shapely.geometry import Point, mapping
import geopandas as gpd
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
if 'sheet' not in st.session_state:
    try:
        st.session_state.sheet = client.open('Aircraft Proximity Alert System').sheet1
    except gspread.SpreadsheetNotFound:
        # Create the sheet if it doesn't exist
        new_sheet = client.create('Aircraft Proximity Alert System')
        new_sheet.share('aksh30990@gmail.com', perm_type='user', role='writer')
        st.session_state.sheet = new_sheet.sheet1
        st.session_state.sheet.append_row(['Time', 'Alert', 'Unit Type'])

def calculate_3d_distance(loc1, loc2):
    surface_distance = geodesic((loc1[0], loc1[1]), (loc2[0], loc2[1])).meters
    elevation_difference = abs(loc1[2] - loc2[2])
    distance_3d = math.sqrt(surface_distance**2 + elevation_difference**2)
    return distance_3d

def check_aircraft_proximity(ground_unit_location, aircraft_location):
    distance_to_aircraft = calculate_3d_distance(ground_unit_location, aircraft_location)
    return distance_to_aircraft <= PROXIMITY_THRESHOLD

def animate_path(df, view_state):
    map_placeholder = st.empty()
    for i in range(1, len(df) + 1):
        path_layer = pdk.Layer(
            "PathLayer",
            data=pd.DataFrame({'path': [df[['longitude_wgs84(deg)', 'latitude_wgs84(deg)']].values.tolist()[:i]]}),
            pickable=True,
            get_color=[255, 0, 0, 150],
            width_scale=20,
            width_min_pixels=2,
            get_path="path",
            get_width=5,
        )
        r = pdk.Deck(
            layers=[path_layer],
            initial_view_state=view_state,
            map_style="mapbox://styles/mapbox/light-v9",
        )
        map_placeholder.pydeck_chart(r)
        time.sleep(0.3)

def send_alert_to_unit(unit_type):
    """Send alert to Google Sheet"""
    try:
        current_time = datetime.utcnow().isoformat()
        st.session_state.sheet.append_row([current_time, 'True', unit_type])
        st.session_state['alert_sent'] = True
        st.success(f"Alert sent to {unit_type}!")
    except Exception as e:
        st.error(f"Failed to send alert: {str(e)}")

def check_for_alerts():
    """Check for new alerts with error handling"""
    try:
        records = st.session_state.sheet.get_all_records()
        if records:
            return records[-1]
        return None
    except Exception as e:
        st.error(f"Error checking alerts: {str(e)}")
        return None

def login_user(username, password):
    for role, credentials in USER_ROLES.items():
        if credentials['username'] == username and credentials['password'] == password:
            st.session_state['user_role'] = role
            st.success(f'Logged in as {role}')
            st.rerun()
            return
    st.error('Incorrect username or password')

# Login form
if st.session_state['user_role'] is None:
    st.subheader('Login')
    username = st.text_input('Username')
    password = st.text_input('Password', type='password')
    if st.button('Login'):
        login_user(username, password)
else:
    if st.session_state['user_role'] == 'command_center':
        st.title('Command Center Dashboard')
        st.title('Aircraft Proximity Alert System')

        st.subheader('Ground Unit Location')
        ground_lat = st.number_input('Latitude (deg)', value=0.0, format='%f')
        ground_lon = st.number_input('Longitude (deg)', value=0.0, format='%f')
        ground_elev = st.number_input('Elevation (meters)', value=0.0, format='%f')
        ground_unit_location = (ground_lat, ground_lon, ground_elev)

        st.subheader('Upload Aircraft Location CSV')
        csv_file = st.file_uploader("Choose a CSV file", type="csv")

        if csv_file is not None:
            df = pd.read_csv(csv_file)
            required_columns = ['latitude_wgs84(deg)', 'longitude_wgs84(deg)', 'elevation_wgs84(m)']
            
            if all(col in df.columns for col in required_columns):
                df['path'] = df[['longitude_wgs84(deg)', 'latitude_wgs84(deg)']].values.tolist()
                view_state = pdk.ViewState(
                    latitude=df['latitude_wgs84(deg)'].mean(),
                    longitude=df['longitude_wgs84(deg)'].mean(),
                    zoom=11,
                    pitch=50,
                )

                ground_unit_df = pd.DataFrame({
                    'latitude': [ground_unit_location[0]],
                    'longitude': [ground_unit_location[1]],
                    'elevation': [ground_unit_location[2]],
                })

                icon_data = pd.DataFrame({
                    'coordinates': [[ground_unit_location[1], ground_unit_location[0]]],
                })

                map_placeholder = st.empty()
                button_placeholder = st.empty()
                alert_placeholder = st.empty()

                for index, row in df.iterrows():
                    aircraft_location = (
                        row['latitude_wgs84(deg)'],
                        row['longitude_wgs84(deg)'],
                        row['elevation_wgs84(m)']
                    )
                    
                    distance = calculate_3d_distance(ground_unit_location, aircraft_location)
                    
                    if distance <= PROXIMITY_THRESHOLD:
                        with button_placeholder.container():
                            col1, col2 = st.columns(2)
                            with col1:
                                if st.button("Priority to Ground Unit", key=f"ground_{index}"):
                                    send_alert_to_unit('ground_unit')
                            with col2:
                                if st.button("Priority to Aircraft", key=f"aircraft_{index}"):
                                    send_alert_to_unit('aircraft')
                    
                    # Update map visualization
                    path_layer = pdk.Layer(
                        "PathLayer",
                        data=pd.DataFrame({'path': [df[['longitude_wgs84(deg)', 'latitude_wgs84(deg)']].values.tolist()[:index+1]]}),
                        pickable=True,
                        get_color=[255, 0, 0, 150],
                        width_scale=20,
                        width_min_pixels=2,
                        get_path="path",
                        get_width=5,
                    )
                    
                    scatter_layer = pdk.Layer(
                        "ScatterplotLayer",
                        data=ground_unit_df,
                        get_position=["longitude", "latitude"],
                        get_fill_color=[0, 0, 255, 50],
                        get_radius=2500,
                        pickable=True,
                    )
                    
                    icon_layer = pdk.Layer(
                        "IconLayer",
                        data=icon_data,
                        get_icon={
                            "url": "https://img.icons8.com/windows/32/000000/square-full.png",
                            "width": 128,
                            "height": 128,
                            "anchorY": 128,
                        },
                        get_position="coordinates",
                        get_size=10,
                        size_scale=10,
                        pickable=True,
                    )
                    
                    r = pdk.Deck(
                        layers=[path_layer, scatter_layer, icon_layer],
                        initial_view_state=view_state,
                        map_style="mapbox://styles/mapbox/light-v9",
                    )
                    
                    map_placeholder.pydeck_chart(r)
                    time.sleep(0.1)

    elif st.session_state['user_role'] in ['ground_unit', 'aircraft']:
        st.title(f"{st.session_state['user_role'].replace('_', ' ').title()} Dashboard")
        
        # Add automatic refresh every 5 seconds
        st_autorefresh = st.empty()
        st_autorefresh.write("Auto-refresh in 5 seconds...")
        time.sleep(5)
        st.experimental_rerun()
        
        alert = check_for_alerts()
        if alert:
            if st.session_state['user_role'] == 'ground_unit':
                if alert['Unit Type'] == 'ground_unit':
                    st.error('Keep Firing.')
                else:
                    st.error('Friendly aircraft approaching. Stop Firing!')
            else:  # aircraft
                if alert['Unit Type'] == 'ground_unit':
                    st.error('Ground Unit Firing. Reroute the current path.')
                else:
                    st.error('Clearance to fly.')

# Logout button
if st.session_state['user_role'] is not None:
    if st.button('Logout'):
        st.session_state['user_role'] = None
        st.session_state['alert_sent'] = False
        st.rerun()
