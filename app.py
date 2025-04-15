import streamlit as st
import pandas as pd
import pydeck as pdk
import time
import math
from datetime import datetime

# User Credentials
USER_CREDENTIALS = {
    "command": {"username": "command", "password": "123"},
    "ground": {"username": "ground", "password": "123"},
    "aircraft": {"username": "aircraft", "password": "123"},
}

# Constants
AIRCRAFT_ICON_URL = "https://cdn-icons-png.flaticon.com/512/287/287221.png"
BOMB_ICON_URL = "https://cdn-icons-png.flaticon.com/512/4389/4389779.png"
PROXIMITY_THRESHOLD = 4500  # meters

# Initialize all session state variables
def init_session_state():
    required_states = {
        'logged_in': False,
        'role': None,
        'fwg_messages': {"gun": "", "aircraft": ""},
        'message_status': {"gun": False, "aircraft": False},
        'priority_sent': False,
        'proximity_alert_shown': False,
        'in_proximity': False,
        'alert_frame': -1,
        'ground_position': (28.6139, 77.2090, 0.0),
        'alert_log': [],
        'acknowledged': {"gun": False, "aircraft": False},
        'unit_logs': {"gun": [], "aircraft": []}  # Separate logs for each unit
    }
    
    for key, value in required_states.items():
        if key not in st.session_state:
            st.session_state[key] = value

# Helper Functions
def calculate_3d_distance(ground, aircraft):
    lat1, lon1, elev1 = ground
    lat2, lon2, elev2 = aircraft
    # Convert degrees to meters (approx. 111,111 meters per degree)
    lat_dist = (lat2 - lat1) * 111111
    lon_dist = (lon2 - lon1) * 111111 * abs(math.cos(math.radians(lat1)))
    elev_dist = elev2 - elev1
    return (lat_dist**2 + lon_dist**2 + elev_dist**2) ** 0.5

def create_layers(ground, path, current_aircraft_pos):
    ground_pos = [ground[1], ground[0]]  # Note: PyDeck expects [lon, lat]
    return [
        pdk.Layer(
            "PathLayer",
            data=pd.DataFrame({"coordinates": [path]}),
            get_path="coordinates",
            get_color=[255, 0, 0],
            width_scale=20,
            width_min_pixels=5
        ),
        pdk.Layer(
            "ScatterplotLayer",
            data=pd.DataFrame({"position": [ground_pos]}),
            get_position="position",
            get_color=[0, 255, 0],
            get_radius=500,
            pickable=True
        ),
        pdk.Layer(
            "IconLayer",
            data=pd.DataFrame([
                {"coordinates": current_aircraft_pos, "icon": AIRCRAFT_ICON_URL},
                {"coordinates": ground_pos, "icon": BOMB_ICON_URL}
            ]),
            get_icon="icon",
            get_size=100,
            size_scale=1,
            get_position="coordinates",
            pickable=True
        )
    ]

def send_priority(unit, message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    st.session_state.fwg_messages[unit.lower()] = message
    st.session_state.message_status[unit.lower()] = True
    st.session_state.acknowledged[unit.lower()] = False
    
    # Add to main alert log
    log_entry = {
        "timestamp": timestamp,
        "unit": unit,
        "message": message,
        "status": "Sent",
        "ack_time": ""
    }
    st.session_state.alert_log.append(log_entry)
    
    # Add to unit-specific log
    st.session_state.unit_logs[unit.lower()].append({
        "timestamp": timestamp,
        "message": message,
        "status": "Sent",
        "ack_time": ""
    })
    
    st.toast(f"PRIORITY message sent to {unit}: {message}")

def log_acknowledgment(unit):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Update main alert log
    for log in reversed(st.session_state.alert_log):
        if log["unit"].lower() == unit.lower() and log["status"] == "Sent":
            log["status"] = "Acknowledged"
            log["ack_time"] = timestamp
            break
    
    # Update unit-specific log
    for log in reversed(st.session_state.unit_logs[unit.lower()]):
        if log["status"] == "Sent":
            log["status"] = "Acknowledged"
            log["ack_time"] = timestamp
            break

# Dashboards
def command_center_dashboard():
    st.title("🛡️ COMMAND CENTER DASHBOARD")
    
    # Layout columns
    col1, col2 = st.columns(2)

    with col1:
        st.subheader('GROUND POSITION')
        st.session_state.ground_position = (
            st.number_input('LATITUDE', value=28.6139, format='%f', key='lat'),
            st.number_input('LONGITUDE', value=77.2090, format='%f', key='lon'),
            st.number_input('ELEVATION (m)', value=0.0, format='%f', key='elev')
        )

    with col2:
        st.subheader('AIRCRAFT PATH')
        csv = st.file_uploader("Upload Aircraft CSV", type="csv")

    # Alert Log Section
    st.subheader("📜 FULL ALERT LOG")
    if st.session_state.alert_log:
        log_df = pd.DataFrame(st.session_state.alert_log)
        st.dataframe(
            log_df,
            column_config={
                "timestamp": "Time Sent",
                "unit": "Recipient",
                "message": "Priority Message",
                "status": "Status",
                "ack_time": "Ack Time"
            },
            use_container_width=True
        )
    else:
        st.info("No alerts sent yet")

    if csv:
        df = pd.read_csv(csv)
        req = ['latitude_wgs84(deg)', 'longitude_wgs84(deg)', 'elevation_wgs84(m)']
        if not all(c in df.columns for c in req):
            st.error("CSV missing required columns.")
            return

        view = pdk.ViewState(
            latitude=st.session_state.ground_position[0],
            longitude=st.session_state.ground_position[1],
            zoom=10,
            pitch=50
        )
        path = []
        map_placeholder = st.empty()
        info_placeholder = st.empty()

        for idx, row in df.iterrows():
            path.append([row['longitude_wgs84(deg)'], row['latitude_wgs84(deg)']])
            aircraft = (row['latitude_wgs84(deg)'], row['longitude_wgs84(deg)'], row['elevation_wgs84(m)'])
            aircraft_pos = [row['longitude_wgs84(deg)'], row['latitude_wgs84(deg)']]
            distance = calculate_3d_distance(st.session_state.ground_position, aircraft)

            layers = create_layers(st.session_state.ground_position, path, aircraft_pos)
            map_placeholder.pydeck_chart(pdk.Deck(
                layers=layers,
                initial_view_state=view,
                map_style='mapbox://styles/mapbox/satellite-streets-v11'
            ))
            info_placeholder.info(f"Frame {idx+1}/{len(df)} | Distance: {distance:.2f}m")

            # Proximity check
            if (distance <= PROXIMITY_THRESHOLD and 
                not st.session_state.proximity_alert_shown and
                st.session_state.alert_frame != idx):
                st.session_state.proximity_alert_shown = True
                st.session_state.alert_frame = idx
                st.session_state.in_proximity = True
                st.warning("⚠️ Aircraft in PRIORITY range (4500m)")
                
            # Priority sending
            if st.session_state.in_proximity and not st.session_state.priority_sent:
                priority = st.radio("Send priority to:", ["Aircraft", "Gun"], key=f"priority_{idx}")
                if st.button("Send Priority", key=f"send_priority_{idx}"):
                    if priority == "Aircraft":
                        send_priority("gun", "Stop Firing")
                        send_priority("aircraft", "Clearance to continue flight")
                    else:
                        send_priority("gun", "Continue Firing")
                        send_priority("aircraft", "Danger Area Reroute immediately")
                    st.session_state.priority_sent = True
                    st.session_state.in_proximity = False
                    time.sleep(1)
                    st.rerun()
            
            # Reset if aircraft moves out of proximity
            if distance > PROXIMITY_THRESHOLD:
                st.session_state.proximity_alert_shown = False
                st.session_state.in_proximity = False
                st.session_state.priority_sent = False
            
            time.sleep(0.5)

def unit_dashboard(unit_name):
    st.title(f"🎯 {unit_name.upper()} DASHBOARD")
    
    # Current Message Section
    current_msg = st.session_state.fwg_messages.get(unit_name.lower(), "")
    message_active = st.session_state.message_status.get(unit_name.lower(), False)
    
    st.subheader("✉️ CURRENT MESSAGE")
    if message_active and current_msg:
        with st.container(border=True):
            st.warning(f"📨 PRIORITY Message: {current_msg}")
            if st.button("Acknowledge", key=f"ack_{unit_name}"):
                st.session_state.message_status[unit_name.lower()] = False
                st.session_state.acknowledged[unit_name.lower()] = True
                log_acknowledgment(unit_name)
                st.success("✅ Acknowledged")
                time.sleep(1)
                st.rerun()
    else:
        st.success("✅ No active messages")
    
    # Message History Section
    st.subheader("📜 MESSAGE HISTORY")
    if st.session_state.unit_logs.get(unit_name.lower()):
        unit_log_df = pd.DataFrame(st.session_state.unit_logs[unit_name.lower()])
        st.dataframe(
            unit_log_df,
            column_config={
                "timestamp": "Time Sent",
                "message": "Priority Message",
                "status": "Status",
                "ack_time": "Acknowledged At"
            },
            use_container_width=True
        )
    else:
        st.info("No message history available")

# Login
def login():
    st.title("🔐 Secure Login")
    role = st.selectbox("Login As", ["Command Center", "Ground Unit", "Aircraft"])
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    
    if st.button("Login"):
        # Convert role to match USER_CREDENTIALS keys
        role_key = role.lower().replace(" center", "").replace(" unit", "").strip()
        
        cred = USER_CREDENTIALS.get(role_key)
        if cred and username == cred["username"] and password == cred["password"]:
            init_session_state()
            st.session_state.logged_in = True
            st.session_state.role = role_key
            st.success(f"Logged in as {role}")
            time.sleep(1)
            st.rerun()
        else:
            st.error("Invalid credentials.")

# Main
def main():
    init_session_state()

    if not st.session_state.logged_in:
        login()
    else:
        role = st.session_state.role
        st.sidebar.success(f"Logged in as {role.upper()}")
        if st.sidebar.button("Logout"):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()

        if role == "command":
            command_center_dashboard()
        elif role == "ground":
            unit_dashboard("gun")
        elif role == "aircraft":
            unit_dashboard("aircraft")

if __name__ == "__main__":
    main()
