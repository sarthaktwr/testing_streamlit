import streamlit as st
from geopy.distance import geodesic
import math
import time
import pandas as pd
import pydeck as pdk
import gspread
from datetime import datetime, timedelta
from google.oauth2.service_account import Credentials
import json
import threading

# Constants
PROXIMITY_THRESHOLD = 4500  # in meters
ALERT_POLL_INTERVAL = 2  # seconds
ALERT_EXPIRY_SECONDS = 30

# Simulated user roles and credentials
USER_ROLES = {
    'command_center': {'username': 'command', 'password': 'center123'},
    'ground_unit': {'username': 'ground', 'password': 'unit123'},
    'aircraft': {'username': 'aircraft', 'password': 'flight123'}
}

# Google Sheets setup
scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
google_credentials = json.loads(st.secrets['google_credentials']['value'])
creds = Credentials.from_service_account_info(google_credentials, scopes=scope)
client = gspread.authorize(creds)

# Initialize session state
if 'user_role' not in st.session_state:
    st.session_state.user_role = None
if 'alert_sent' not in st.session_state:
    st.session_state.alert_sent = False
if 'last_alert_check' not in st.session_state:
    st.session_state.last_alert_check = datetime.min
if 'current_alert' not in st.session_state:
    st.session_state.current_alert = None

# Helper Functions
def calculate_3d_distance(loc1, loc2):
    surface_distance = geodesic((loc1[0], loc1[1]), (loc2[0], loc2[1])).meters
    elevation_difference = abs(loc1[2] - loc2[2])
    return math.sqrt(surface_distance**2 + elevation_difference**2)

def check_aircraft_proximity(ground_unit_location, aircraft_location):
    distance_to_aircraft = calculate_3d_distance(ground_unit_location, aircraft_location)
    return distance_to_aircraft <= PROXIMITY_THRESHOLD

def create_alerts_sheet():
    sheet = client.create('Aircraft Proximity Alert System')
    sheet.share('aksh30990@gmail.com', perm_type='user', role='writer')
    worksheet = sheet.sheet1
    worksheet.append_row(['Time', 'Alert', 'Unit Type'])
    return sheet

def send_alert_to_unit(unit_type, sheet):
    current_time = datetime.utcnow().isoformat()
    sheet.append_row([current_time, 'True', unit_type])
    st.session_state.alert_sent = True
    st.session_state.current_alert = {
        'Time': current_time,
        'Alert': 'True',
        'Unit Type': unit_type
    }

def check_for_alerts(force_check=False):
    now = datetime.utcnow()
    
    if not force_check and (now - st.session_state.last_alert_check).total_seconds() < ALERT_POLL_INTERVAL:
        return st.session_state.current_alert
    
    try:
        sheet = client.open('Aircraft Proximity Alert System').sheet1
        alerts = sheet.get_all_records()
        
        if alerts:
            latest_alert = alerts[-1]
            alert_time = datetime.fromisoformat(latest_alert['Time'])
            
            if (now - alert_time).total_seconds() <= ALERT_EXPIRY_SECONDS and latest_alert['Alert'] == 'True':
                st.session_state.current_alert = latest_alert
            else:
                st.session_state.current_alert = None
        else:
            st.session_state.current_alert = None
            
        st.session_state.last_alert_check = now
        return st.session_state.current_alert
        
    except Exception as e:
        st.error(f"Error checking alerts: {e}")
        return st.session_state.current_alert

def login_user(username, password):
    for role, credentials in USER_ROLES.items():
        if credentials['username'] == username and credentials['password'] == password:
            st.session_state.user_role = role
            st.success(f'Logged in as {role}')
            st.rerun()
            return
    st.error('Incorrect username or password')

# Real-Time Alert Display Components
def command_center_alerts():
    alert_placeholder = st.empty()
    
    while True:
        alert = check_for_alerts()
        with alert_placeholder.container():
            if alert:
                if alert['Unit Type'] == 'ground_unit':
                    st.error("🚨 PRIORITY ALERT: Ground Unit Engaged 🚨", icon="⚠️")
                elif alert['Unit Type'] == 'aircraft':
                    st.warning("⚠️ ALERT: Aircraft in Proximity ⚠️")
            else:
                st.success("✅ No Active Alerts", icon="✅")
        time.sleep(ALERT_POLL_INTERVAL)

def ground_unit_alerts():
    alert_placeholder = st.empty()
    
    while True:
        alert = check_for_alerts()
        with alert_placeholder.container():
            if alert:
                if alert['Unit Type'] == 'ground_unit':
                    st.error("## 🛡️ DEFENSIVE ALERT\n**You have firing priority**")
                elif alert['Unit Type'] == 'aircraft':
                    st.warning("## ✋ HOLD FIRE\n**Friendly aircraft in proximity**")
            else:
                st.success("## ✅ CLEAR\n**No active alerts**")
        time.sleep(ALERT_POLL_INTERVAL)

def aircraft_alerts():
    alert_placeholder = st.empty()
    
    while True:
        alert = check_for_alerts()
        with alert_placeholder.container():
            if alert:
                if alert['Unit Type'] == 'ground_unit':
                    st.error("## 🚨 THREAT DETECTED\n**Ground unit is firing!**")
                elif alert['Unit Type'] == 'aircraft':
                    st.warning("## ⚠️ PROXIMITY WARNING\n**Another aircraft nearby**")
            else:
                st.success("## ✅ CLEAR SKIES\n**No threat detected**")
        time.sleep(ALERT_POLL_INTERVAL)

# Main App
def main():
    # Login form
    if st.session_state.user_role is None:
        st.subheader('Login')
        username = st.text_input('Username')
        password = st.text_input('Password', type='password')
        if st.button('Login'):
            login_user(username, password)
        return

    # Logout button
    if st.button('Logout'):
        st.session_state.user_role = None
        st.session_state.alert_sent = False
        st.rerun()

    # Command Center Interface
    if st.session_state.user_role == 'command_center':
        st.title('Command Center Dashboard')
        
        # Start alert monitoring thread
        if 'alert_thread' not in st.session_state:
            st.session_state.alert_thread = threading.Thread(target=command_center_alerts, daemon=True)
            st.session_state.alert_thread.start()
        
        st.subheader("Real-Time Alert Monitor")
        
        try:
            sheet = client.open('Aircraft Proximity Alert System').sheet1
        except gspread.SpreadsheetNotFound:
            sheet = create_alerts_sheet()

        # Ground Unit Location Input
        st.subheader('Ground Unit Location')
        ground_lat = st.number_input('Latitude (deg)', value=0.0, format='%f')
        ground_lon = st.number_input('Longitude (deg)', value=0.0, format='%f')
        ground_elev = st.number_input('Elevation (meters)', value=0.0, format='%f')
        ground_unit_location = (ground_lat, ground_lon, ground_elev)

        # Aircraft Path Upload
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

                map_placeholder = st.empty()
                ground_unit_df = pd.DataFrame({
                    'latitude': [ground_unit_location[0]],
                    'longitude': [ground_unit_location[1]],
                    'elevation': [ground_unit_location[2]],
                })

                previous_in_proximity = False
                
                for index, row in df.iterrows():
                    aircraft_location = (row['latitude_wgs84(deg)'], row['longitude_wgs84(deg)'], row['elevation_wgs84(m)'])
                    current_in_proximity = check_aircraft_proximity(ground_unit_location, aircraft_location)
                    distance_to_ground = calculate_3d_distance(ground_unit_location, aircraft_location)
                    
                    # Clear alert if aircraft exited proximity zone
                    if previous_in_proximity and not current_in_proximity:
                        current_time = datetime.utcnow().isoformat()
                        sheet.append_row([current_time, 'False', 'clear'])
                    
                    previous_in_proximity = current_in_proximity
                    
                    # Create map layers
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
                    
                    r = pdk.Deck(
                        layers=[path_layer, scatter_layer],
                        initial_view_state=view_state,
                        map_style="mapbox://styles/mapbox/light-v9",
                    )
                    
                    map_placeholder.pydeck_chart(r)
                    
                    if current_in_proximity:
                        col1, col2 = st.columns(2)
                        with col1:
                            if st.button("Priority to Ground Unit", key=f"ground_{index}"):
                                send_alert_to_unit('ground_unit', sheet)
                        with col2:
                            if st.button("Priority to Aircraft", key=f"aircraft_{index}"):
                                send_alert_to_unit('aircraft', sheet)
                    
                    time.sleep(0.1)

    # Ground Unit Interface
    elif st.session_state.user_role == 'ground_unit':
        st.title('Ground Unit Dashboard')
        
        if 'alert_thread' not in st.session_state:
            st.session_state.alert_thread = threading.Thread(target=ground_unit_alerts, daemon=True)
            st.session_state.alert_thread.start()
        
        col1, col2 = st.columns([3, 1])
        
        with col1:
            st.subheader("Alert Status")
            placeholder = st.empty()
            
        with col2:
            alert = check_for_alerts(force_check=True)
            st.metric("System Status", 
                     value="ALERT" if alert else "CLEAR",
                     delta="New alert!" if alert else None)

    # Aircraft Interface
    elif st.session_state.user_role == 'aircraft':
        st.title('Aircraft Dashboard')
        
        if 'alert_thread' not in st.session_state:
            st.session_state.alert_thread = threading.Thread(target=aircraft_alerts, daemon=True)
            st.session_state.alert_thread.start()
        
        st.subheader("Threat Status")
        alert = check_for_alerts(force_check=True)
        st.metric("Threat Level", 
                 value="DANGER" if alert and alert['Unit Type'] == 'ground_unit' else "WARNING" if alert else "CLEAR",
                 delta_color="inverse")

if __name__ == "__main__":
    main()
