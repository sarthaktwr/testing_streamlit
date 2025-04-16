import streamlit as st
from geopy.distance import geodesic
import math
import time
import pandas as pd
import pydeck as pdk
import gspread
from datetime import datetime
from google.oauth2.service_account import Credentials
import json

# Constants
PROXIMITY_THRESHOLD = 4500  # in meters
USER_ROLES = {
    'command_center': {'username': 'command', 'password': 'center123'},
    'ground_unit': {'username': 'ground', 'password': 'unit123'},
    'aircraft': {'username': 'aircraft', 'password': 'flight123'}
}

# Initialize Google Sheets connection
@st.cache_resource
def init_gsheet():
    scope = ['https://spreadsheets.google.com/feeds', 
             'https://www.googleapis.com/auth/drive']
    google_credentials = json.loads(st.secrets['google_credentials']['value'])
    creds = Credentials.from_service_account_info(google_credentials, scopes=scope)
    client = gspread.authorize(creds)
    
    try:
        sheet = client.open('Aircraft Proximity Alert System').sheet1
    except gspread.SpreadsheetNotFound:
        sheet = client.create('Aircraft Proximity Alert System')
        sheet.share('aksh30990@gmail.com', perm_type='user', role='writer')
        worksheet = sheet.sheet1
        worksheet.append_row(['Time', 'Alert', 'Unit Type'])
        return worksheet
    return sheet

# Initialize session state
if 'user_role' not in st.session_state:
    st.session_state.user_role = None
if 'sheet' not in st.session_state:
    st.session_state.sheet = init_gsheet()
if 'alert_sent' not in st.session_state:
    st.session_state.alert_sent = False
if 'last_alert_check' not in st.session_state:
    st.session_state.last_alert_check = datetime.min

# Utility functions
def calculate_3d_distance(loc1, loc2):
    surface_distance = geodesic((loc1[0], loc1[1]), (loc2[0], loc2[1])).meters
    elevation_difference = abs(loc1[2] - loc2[2])
    return math.sqrt(surface_distance**2 + elevation_difference**2)

def check_aircraft_proximity(ground_loc, aircraft_loc):
    return calculate_3d_distance(ground_loc, aircraft_loc) <= PROXIMITY_THRESHOLD

def send_alert(unit_type):
    try:
        current_time = datetime.utcnow().isoformat()
        st.session_state.sheet.append_row([current_time, 'True', unit_type])
        st.session_state.alert_sent = True
        return True
    except Exception as e:
        st.error(f"Failed to send alert: {str(e)}")
        return False

def check_for_alerts():
    try:
        records = st.session_state.sheet.get_all_records()
        if records:
            return records[-1]
    except Exception as e:
        st.error(f"Error checking alerts: {str(e)}")
    return None

# Login system
def login_user(username, password):
    for role, creds in USER_ROLES.items():
        if creds['username'] == username and creds['password'] == password:
            st.session_state.user_role = role
            st.success(f'Logged in as {role}')
            return True
    st.error('Incorrect username or password')
    return False

# Main app logic
def main():
    # Login form
    if st.session_state.user_role is None:
        st.subheader('Login')
        username = st.text_input('Username')
        password = st.text_input('Password', type='password')
        if st.button('Login'):
            login_user(username, password)
            st.rerun()
        return
    
    # Command Center Interface
    if st.session_state.user_role == 'command_center':
        st.title('Command Center Dashboard')
        
        # Ground unit location input
        st.subheader('Ground Unit Location')
        ground_lat = st.number_input('Latitude (deg)', value=0.0)
        ground_lon = st.number_input('Longitude (deg)', value=0.0)
        ground_elev = st.number_input('Elevation (m)', value=0.0)
        ground_loc = (ground_lat, ground_lon, ground_elev)
        
        # Aircraft data upload
        st.subheader('Aircraft Path Data')
        csv_file = st.file_uploader("Upload CSV", type="csv")
        
        if csv_file:
            df = pd.read_csv(csv_file)
            required_cols = ['latitude_wgs84(deg)', 'longitude_wgs84(deg)', 'elevation_wgs84(m)']
            
            if all(col in df.columns for col in required_cols):
                # Initialize map
                view_state = pdk.ViewState(
                    latitude=df['latitude_wgs84(deg)'].mean(),
                    longitude=df['longitude_wgs84(deg)'].mean(),
                    zoom=11,
                    pitch=50
                )
                
                map_placeholder = st.empty()
                alert_placeholder = st.empty()
                
                # Process each point in the flight path
                for i in range(len(df)):
                    aircraft_loc = (
                        df.iloc[i]['latitude_wgs84(deg)'],
                        df.iloc[i]['longitude_wgs84(deg)'],
                        df.iloc[i]['elevation_wgs84(m)']
                    )
                    
                    # Check proximity
                    if check_aircraft_proximity(ground_loc, aircraft_loc):
                        with alert_placeholder.container():
                            st.warning("Aircraft in proximity!")
                            col1, col2 = st.columns(2)
                            
                            # Use unique keys for buttons
                            if col1.button("Alert Ground Unit", key=f"ground_alert_{i}"):
                                if send_alert('ground_unit'):
                                    st.success("Alert sent to Ground Unit!")
                            
                            if col2.button("Alert Aircraft", key=f"aircraft_alert_{i}"):
                                if send_alert('aircraft'):
                                    st.success("Alert sent to Aircraft!")
                    
                    # Update map display
                    path_layer = pdk.Layer(
                        "PathLayer",
                        data=pd.DataFrame({'path': [df.iloc[:i+1][['longitude_wgs84(deg)', 'latitude_wgs84(deg)']].values.tolist()]}),
                        get_path="path",
                        get_color=[255, 0, 0],
                        width_scale=20,
                        width_min_pixels=2
                    )
                    
                    deck = pdk.Deck(
                        layers=[path_layer],
                        initial_view_state=view_state,
                        map_style="mapbox://styles/mapbox/light-v9"
                    )
                    
                    map_placeholder.pydeck_chart(deck)
                    time.sleep(0.1)
    
    # Ground Unit Interface
    elif st.session_state.user_role == 'ground_unit':
        st.title('Ground Unit Dashboard')
        
        # Check for alerts every 5 seconds
        if time.time() - st.session_state.last_alert_check > 5:
            alert = check_for_alerts()
            st.session_state.last_alert_check = time.time()
            
            if alert:
                if alert['Unit Type'] == 'ground_unit':
                    st.error("ALERT: Continue Firing")
                else:
                    st.error("ALERT: Stop Firing - Friendly Aircraft")
            else:
                st.success("No active alerts")
        
        st.button("Refresh Alerts")
    
    # Aircraft Interface
    elif st.session_state.user_role == 'aircraft':
        st.title('Aircraft Dashboard')
        
        # Check for alerts every 5 seconds
        if time.time() - st.session_state.last_alert_check > 5:
            alert = check_for_alerts()
            st.session_state.last_alert_check = time.time()
            
            if alert:
                if alert['Unit Type'] == 'ground_unit':
                    st.error("ALERT: Ground Unit Firing - Evasive Action")
                else:
                    st.error("ALERT: Flight Path Cleared")
            else:
                st.success("No active alerts")
        
        st.button("Refresh Alerts")
    
    # Logout button
    if st.button('Logout'):
        st.session_state.clear()
        st.rerun()

if __name__ == '__main__':
    main()
