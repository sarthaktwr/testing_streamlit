import streamlit as st
import pandas as pd
import pydeck as pdk
import time
import math

# User Credentials
USER_CREDENTIALS = {
    "command": {"username": "command", "password": "123"},
    "ground": {"username": "ground", "password": "123"},
    "aircraft": {"username": "aircraft", "password": "123"},
}

# Constants
AIRCRAFT_ICON_URL = "https://cdn-icons-png.flaticon.com/512/287/287221.png"
BOMB_ICON_URL = "https://cdn-icons-png.flaticon.com/512/4389/4389779.png"
PROXIMITY_THRESHOLD = 500  # meters

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
    st.session_state.fwg_messages[unit.lower()] = message
    st.toast(f"PRIORITY message sent to {unit}: {message}")

# Dashboards
def command_center_dashboard():
    st.title("🛡️ COMMAND CENTER DASHBOARD")
    col1, col2 = st.columns(2)

    with col1:
        st.subheader('GROUND POSITION')
        ground = (
            st.number_input('LATITUDE', value=28.6139, format='%f', key='lat'),
            st.number_input('LONGITUDE', value=77.2090, format='%f', key='lon'),
            st.number_input('ELEVATION (m)', value=0.0, format='%f', key='elev')
        )

    with col2:
        st.subheader('AIRCRAFT PATH')
        csv = st.file_uploader("Upload Aircraft CSV", type="csv")

    if csv:
        df = pd.read_csv(csv)
        req = ['latitude_wgs84(deg)', 'longitude_wgs84(deg)', 'elevation_wgs84(m)']
        if not all(c in df.columns for c in req):
            st.error("CSV missing required columns.")
            return

        view = pdk.ViewState(
            latitude=ground[0],
            longitude=ground[1],
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
            distance = calculate_3d_distance(ground, aircraft)

            layers = create_layers(ground, path, aircraft_pos)
            map_placeholder.pydeck_chart(pdk.Deck(
                layers=layers,
                initial_view_state=view,
                map_style='mapbox://styles/mapbox/satellite-streets-v11'
            ))
            info_placeholder.info(f"Frame {idx+1}/{len(df)} | Distance: {distance:.2f}m")

            if distance <= PROXIMITY_THRESHOLD and not st.session_state.get('priority_sent', False):
                st.warning("⚠️ Aircraft in PRIORITY range")
                priority = st.radio("Send priority to:", ["Aircraft", "Gun"], key=f"priority_{idx}")
                if st.button("Send Priority", key=f"send_priority_{idx}"):
                    if priority == "Aircraft":
                        send_priority("gun", "Stop Firing")
                        send_priority("aircraft", "Clearance to continue flight")
                    else:
                        send_priority("gun", "Continue Firing")
                        send_priority("aircraft", "Danger Area Reroute immediately")
                    st.session_state.priority_sent = True
                    time.sleep(1)
                    st.rerun()
            time.sleep(0.5)

def unit_dashboard(unit_name):
    st.title(f"🎯 {unit_name.upper()} DASHBOARD")
    msg = st.session_state.fwg_messages.get(unit_name.lower(), "")
    
    if msg:
        st.warning(f"📨 PRIORITY Message: {msg}")
        if st.button("Acknowledge"):
            st.session_state.fwg_messages[unit_name.lower()] = ""
            st.session_state.priority_sent = False
            st.success("Acknowledged. Awaiting further instruction.")
            time.sleep(1)
            st.rerun()
    else:
        st.success("✅ No active messages.")

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
            st.session_state.logged_in = True
            st.session_state.role = role_key
            st.session_state.fwg_messages = st.session_state.get('fwg_messages', {})
            st.session_state.priority_sent = st.session_state.get('priority_sent', False)
            st.success(f"Logged in as {role}")
            time.sleep(1)
            st.rerun()
        else:
            st.error("Invalid credentials.")

# Main
def main():
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
    if 'role' not in st.session_state:
        st.session_state.role = None
    if 'fwg_messages' not in st.session_state:
        st.session_state.fwg_messages = {}
    if 'priority_sent' not in st.session_state:
        st.session_state.priority_sent = False

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
