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

# Constants and setup (same as before)
PROXIMITY_THRESHOLD = 4500
USER_ROLES = {
    'command_center': {'username': 'command', 'password': 'center123'},
    'ground_unit': {'username': 'ground', 'password': 'unit123'},
    'aircraft': {'username': 'aircraft', 'password': 'flight123'}
}

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
if 'animation_frame' not in st.session_state:
    st.session_state.animation_frame = 0
if 'animation_running' not in st.session_state:
    st.session_state.animation_running = False
if 'df' not in st.session_state:
    st.session_state.df = None

# Utility functions (same as before)
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

def login_user(username, password):
    for role, creds in USER_ROLES.items():
        if creds['username'] == username and creds['password'] == password:
            st.session_state.user_role = role
            st.success(f'Logged in as {role}')
            return True
    st.error('Incorrect username or password')
    return False

def update_animation():
    if st.session_state.animation_running and st.session_state.df is not None:
        if st.session_state.animation_frame < len(st.session_state.df):
            st.session_state.animation_frame += 1
            time.sleep(0.3)  # Control animation speed
            st.rerun()

def main():
    if st.session_state.user_role is None:
        st.subheader('Login')
        username = st.text_input('Username')
        password = st.text_input('Password', type='password')
        if st.button('Login'):
            login_user(username, password)
        return
    
    if st.session_state.user_role == 'command_center':
        st.title('Command Center Dashboard')
        
        # Ground unit location
        st.subheader('Ground Unit Location')
        ground_lat = st.number_input('Latitude (deg)', value=0.0)
        ground_lon = st.number_input('Longitude (deg)', value=0.0)
        ground_elev = st.number_input('Elevation (m)', value=0.0)
        ground_loc = (ground_lat, ground_lon, ground_elev)
        
        # Aircraft data upload
        st.subheader('Aircraft Path Data')
        csv_file = st.file_uploader("Upload CSV", type="csv", key="csv_uploader")
        
        if csv_file:
            if st.session_state.df is None:
                st.session_state.df = pd.read_csv(csv_file)
                required_cols = ['latitude_wgs84(deg)', 'longitude_wgs84(deg)', 'elevation_wgs84(m)']
                
                if not all(col in st.session_state.df.columns for col in required_cols):
                    st.error("CSV missing required columns")
                    return
                
                st.session_state.animation_frame = 0
                st.session_state.animation_running = True
            
            # Start/stop animation controls
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Start Animation"):
                    st.session_state.animation_running = True
            with col2:
                if st.button("Stop Animation"):
                    st.session_state.animation_running = False
            
            # Display current frame
            current_frame = st.session_state.animation_frame
            st.write(f"Frame: {current_frame}/{len(st.session_state.df)}")
            
            # Get current aircraft position
            if current_frame < len(st.session_state.df):
                aircraft_loc = (
                    st.session_state.df.iloc[current_frame]['latitude_wgs84(deg)'],
                    st.session_state.df.iloc[current_frame]['longitude_wgs84(deg)'],
                    st.session_state.df.iloc[current_frame]['elevation_wgs84(m)']
                )
                
                # Check proximity
                if check_aircraft_proximity(ground_loc, aircraft_loc):
                    st.warning("Aircraft in proximity!")
                    col1, col2 = st.columns(2)
                    
                    if col1.button("Alert Ground Unit", key="ground_alert"):
                        if send_alert('ground_unit'):
                            st.success("Alert sent to Ground Unit!")
                    
                    if col2.button("Alert Aircraft", key="aircraft_alert"):
                        if send_alert('aircraft'):
                            st.success("Alert sent to Aircraft!")
                
                # Display map
                view_state = pdk.ViewState(
                    latitude=st.session_state.df['latitude_wgs84(deg)'].mean(),
                    longitude=st.session_state.df['longitude_wgs84(deg)'].mean(),
                    zoom=11,
                    pitch=50
                )
                
                path_layer = pdk.Layer(
                    "PathLayer",
                    data=pd.DataFrame({
                        'path': [st.session_state.df.iloc[:current_frame+1][
                            ['longitude_wgs84(deg)', 'latitude_wgs84(deg)']
                        ].values.tolist()]
                    }),
                    get_path="path",
                    get_color=[255, 0, 0],
                    width_scale=20,
                    width_min_pixels=2
                )
                
                st.pydeck_chart(pdk.Deck(
                    layers=[path_layer],
                    initial_view_state=view_state,
                    map_style="mapbox://styles/mapbox/light-v9"
                ))
            
            # Continue animation if running
            if st.session_state.animation_running:
                update_animation()
    
    elif st.session_state.user_role == 'ground_unit':
        st.title('Ground Unit Dashboard')
        alert = check_for_alerts()
        
        if alert:
            if alert['Unit Type'] == 'ground_unit':
                st.error("ALERT: Continue Firing")
            else:
                st.error("ALERT: Stop Firing - Friendly Aircraft")
        else:
            st.success("No active alerts")
        
        if st.button("Refresh"):
            st.rerun()
    
    elif st.session_state.user_role == 'aircraft':
        st.title('Aircraft Dashboard')
        alert = check_for_alerts()
        
        if alert:
            if alert['Unit Type'] == 'ground_unit':
                st.error("ALERT: Ground Unit Firing - Evasive Action")
            else:
                st.error("ALERT: Flight Path Cleared")
        else:
            st.success("No active alerts")
        
        if st.button("Refresh"):
            st.rerun()
    
    if st.button('Logout'):
        st.session_state.clear()
        st.rerun()

if __name__ == '__main__':
    main()
