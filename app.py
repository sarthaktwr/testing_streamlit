import streamlit as st
import pandas as pd
import pydeck as pdk
import time
import asyncio
import threading
import websockets

# WebSocket Client Class
class WSClient:
    def __init__(self, url):
        self.url = url
        self.message_callback = None
        self.connected = False
        self.websocket = None

    async def connect(self):
        async with websockets.connect(self.url) as websocket:
            self.connected = True
            self.websocket = websocket
            while True:
                message = await websocket.recv()
                if self.message_callback:
                    self.message_callback(message)

    def start(self):
        def run_loop():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self.connect())
        threading.Thread(target=run_loop, daemon=True).start()

    async def send(self, message):
        if self.connected and self.websocket:
            await self.websocket.send(message)

    def on_message(self, callback):
        self.message_callback = callback

# User Credentials
USER_CREDENTIALS = {
    "command": {"username": "command", "password": "123"},
    "ground": {"username": "ground", "password": "123"},
    "aircraft": {"username": "aircraft", "password": "123"},
}

# Constants
AIRCRAFT_ICON_URL = "https://cdn-icons-png.flaticon.com/512/287/287221.png"
BOMB_ICON_URL = "https://cdn-icons-png.flaticon.com/512/4389/4389779.png"
PROXIMITY_THRESHOLD = 500

# Helper Functions
def calculate_3d_distance(ground, aircraft):
    lat1, lon1, elev1 = ground
    lat2, lon2, elev2 = aircraft
    return ((lat2 - lat1)**2 + (lon2 - lon1)**2 + (elev2 - elev1)**2) ** 0.5

def create_layers(ground, path, current_aircraft_pos):
    return [
        pdk.Layer("PathLayer", data=[{"coordinates": path}], get_path="coordinates", get_color=[255, 0, 0], width_scale=20, get_width=5),
        pdk.Layer("ScatterplotLayer", data=[{"position": [ground[1], ground[0]]}], get_position="position", get_color=[0, 128, 0], get_radius=100),
        pdk.Layer("IconLayer", data=[
            {"position": current_aircraft_pos, "icon": {"url": AIRCRAFT_ICON_URL, "width": 128, "height": 128, "anchorY": 128}},
            {"position": [ground[1], ground[0]], "icon": {"url": BOMB_ICON_URL, "width": 128, "height": 128, "anchorY": 128}},
        ], get_icon="icon", get_size=4, size_scale=15, get_position="position")
    ]

def send_priority(unit, message):
    full_msg = f"{unit}:{message}"

    # Use async function to send the message
    async def async_send():
        await st.session_state.ws_client.send(full_msg)
    asyncio.create_task(async_send())
    
    st.toast(f"FWG message broadcast: {message}")

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

        df['path'] = df[['longitude_wgs84(deg)', 'latitude_wgs84(deg)']].values.tolist()
        view = pdk.ViewState(latitude=ground[0], longitude=ground[1], zoom=10, pitch=50)
        path = []
        map_placeholder = st.empty()
        info_placeholder = st.empty()

        for idx, row in df.iterrows():
            path.append(row['path'])
            aircraft = (row['latitude_wgs84(deg)'], row['longitude_wgs84(deg)'], row['elevation_wgs84(m)'])
            aircraft_pos = [row['longitude_wgs84(deg)'], row['latitude_wgs84(deg)']]
            distance = calculate_3d_distance(ground, aircraft)

            layers = create_layers(ground, path, aircraft_pos)
            map_placeholder.pydeck_chart(pdk.Deck(layers=layers, initial_view_state=view, map_style='mapbox://styles/mapbox/satellite-streets-v11'))
            info_placeholder.info(f"Frame {idx+1}/{len(df)} | Distance: {distance:.2f}m")

            if distance <= PROXIMITY_THRESHOLD and not st.session_state.priority_sent:
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
            time.sleep(0.1)

def unit_dashboard(unit_name):
    st.title(f"🎯 {unit_name.upper()} DASHBOARD")
    msg = st.session_state.fwg_messages.get(unit_name)
    if msg:
        st.warning(f"📨 FWG Message: {msg}")
        if st.button("Acknowledge"):
            st.session_state.fwg_messages[unit_name] = ""
            st.session_state.priority_sent = False
            st.success("Acknowledged. Awaiting further instruction.")
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
        key = role.lower().replace(" ", "")
        cred = USER_CREDENTIALS.get(key)
        if cred and username == cred["username"] and password == cred["password"]:
            st.session_state.logged_in = True
            st.session_state.role = key
            st.success(f"Logged in as {role}")
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
    if 'ws_client' not in st.session_state:
        ws = WSClient("ws://localhost:8000/ws")

        def handle_msg(msg):
            parts = msg.split(":")
            if len(parts) == 2:
                st.session_state.fwg_messages[parts[0]] = parts[1]
                st.session_state.priority_sent = False
                st.experimental_rerun()

        ws.on_message(handle_msg)
        ws.start()
        st.session_state.ws_client = ws

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
