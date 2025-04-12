import streamlit as st
from geopy.distance import geodesic
import math
import time
import pandas as pd
import pydeck as pdk
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials
import json

# Constants
PROXIMITY_THRESHOLD = 4500  # in meters
REFRESH_INTERVAL = 30  # seconds for dashboard refresh
ANIMATION_DELAY = 10  # seconds between animation frames

# Military color scheme
COLORS = {
    "dark_green": "#0a5c36",
    "army_green": "#4b5320",
    "sand": "#c2b280",
    "red_alert": "#ff0000",
    "yellow_warning": "#ffff00",
    "white": "#ffffff"
}

# Simulated user roles and credentials
USER_ROLES = {
    'command_center': {'username': 'command', 'password': 'center123'},
    'ground_unit': {'username': 'ground', 'password': 'unit123'},
    'aircraft': {'username': 'aircraft', 'password': 'flight123'}
}

# Google Sheets credentials
scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
google_credentials = json.loads(st.secrets['google_credentials']['value'])
creds = Credentials.from_service_account_info(google_credentials, scopes=scope)
client = gspread.authorize(creds)

# Initialize session state
def init_session():
    if 'user_role' not in st.session_state:
        st.session_state.user_role = None
    if 'alerts' not in st.session_state:
        st.session_state.alerts = {'ground_unit': False, 'aircraft': False}
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False

def set_military_theme():
    st.markdown(f"""
    <style>
    .stApp {{ background-color: {COLORS["dark_green"]}; color: {COLORS["white"]}; }}
    .stTextInput>div>div>input, .stNumberInput>div>div>input {{
    background-color: {COLORS["sand"]};
    color: {COLORS["army_green"]};
    }}
    .stButton>button {{
    background-color: {COLORS["army_green"]};
    color: {COLORS["white"]};
    border: 2px solid {COLORS["sand"]};
    border-radius: 6px;
    font-weight: bold;
    }}
    .stButton>button:hover {{
    background-color: {COLORS["sand"]};
    color: {COLORS["army_green"]};
    }}
    h1, h2, h3 {{
    color: {COLORS["sand"]};
    text-shadow: 1px 1px 2px black;
    }}
    </style>
    """, unsafe_allow_html=True)

def login(username, password):
    for role, creds in USER_ROLES.items():
        if creds['username'] == username and creds['password'] == password:
            st.session_state.user_role = role
            st.session_state.logged_in = True
            st.session_state.login_message = f"ACCESS GRANTED: {role.replace('_', ' ').upper()} TERMINAL"
            return True
    st.error('ACCESS DENIED: INVALID CREDENTIALS', icon="🔒")
    return False

def calculate_3d_distance(loc1, loc2):
    surface = geodesic(loc1[:2], loc2[:2]).meters
    elev_diff = abs(loc1[2] - loc2[2])
    return math.sqrt(surface ** 2 + elev_diff ** 2)

def check_aircraft_proximity(g, a):
    return calculate_3d_distance(g, a) <= PROXIMITY_THRESHOLD

def send_alert(unit):
    st.session_state.alerts[unit] = True
    st.success(f"ALERT SENT TO {unit.replace('_', ' ').upper()}", icon="⚠️")

def get_active_alert():
    for unit, status in st.session_state.alerts.items():
        if status:
            st.session_state.alerts[unit] = False
            return unit
    return None

def create_layers(ground_loc, path):
    ground_df = pd.DataFrame({
        'latitude': [ground_loc[0]],
        'longitude': [ground_loc[1]],
        'elevation': [ground_loc[2]]
    })
    icon_df = pd.DataFrame({
        'coordinates': [[ground_loc[1], ground_loc[0]]],
    })
    return [
        pdk.Layer("PathLayer", pd.DataFrame({'path': [path]}), get_color=[255, 0, 0, 200], get_path="path", width_scale=20, get_width=5),
        pdk.Layer("ScatterplotLayer", ground_df, get_position=["longitude", "latitude"], get_fill_color=[0, 100, 0, 150], get_radius=PROXIMITY_THRESHOLD),
        pdk.Layer("IconLayer", icon_df, get_icon={"url": "https://img.icons8.com/ios-filled/50/000000/military-base.png", "width": 128, "height": 128, "anchorY": 128}, get_position="coordinates", size_scale=15)
    ]

def command_center():
    st.title('🛡️ COMMAND CENTER DASHBOARD')
    col1, col2 = st.columns(2)

    with col1:
        st.subheader('GROUND POSITION')
        ground = (
            st.number_input('LATITUDE', value=0.0, format='%f', key='lat'),
            st.number_input('LONGITUDE', value=0.0, format='%f', key='lon'),
            st.number_input('ELEVATION (m)', value=0.0, format='%f', key='elev')
        )

    with col2:
        st.subheader('AIRCRAFT PATH')
        csv = st.file_uploader("UPLOAD CSV", type="csv")

        if csv:
            try:
                df = pd.read_csv(csv)
                req_cols = ['latitude_wgs84(deg)', 'longitude_wgs84(deg)', 'elevation_wgs84(m)']
                if not all(col in df.columns for col in req_cols):
                    st.error(f'MISSING COLUMNS: {", ".join(req_cols)}')
                    return

                df['path'] = df[['longitude_wgs84(deg)', 'latitude_wgs84(deg)']].values.tolist()
                path = []
                map_area = st.empty()
                status_box = st.empty()

                for idx, row in df.iterrows():
                    path.append(row['path'])
                    aircraft = (row['latitude_wgs84(deg)'], row['longitude_wgs84(deg)'], row['elevation_wgs84(m)'])
                    distance = calculate_3d_distance(ground, aircraft)

                    map_area.pydeck_chart(pdk.Deck(layers=create_layers(ground, path), initial_view_state=pdk.ViewState(latitude=aircraft[0], longitude=aircraft[1], zoom=11, pitch=50), map_style='mapbox://styles/mapbox/satellite-v9'))

                    with status_box.container():
                        st.markdown(f"""
                        <div style="background-color:{COLORS['army_green']};padding:10px;border-radius:5px;">
                        <h4 style="color:{COLORS['sand']};">STATUS</h4>
                        <p>Aircraft Frame: {idx + 1}/{len(df)}</p>
                        <p>Distance: {distance:.2f}m</p>
                        <p>Status: {'⚠️ ENGAGEMENT RANGE' if distance <= PROXIMITY_THRESHOLD else '✅ CLEAR'}</p>
                        </div>
                        """, unsafe_allow_html=True)

                    if distance <= PROXIMITY_THRESHOLD:
                        st.warning(f"⚠️ AIRCRAFT IN RANGE ({distance:.2f}m)")
                        c1, c2 = st.columns(2)
                        with c1:
                            if st.button("🚀 ALERT GROUND UNIT", key=f"g{idx}"):
                                send_alert('ground_unit')
                        with c2:
                            if st.button("✈️ ALERT AIRCRAFT", key=f"a{idx}"):
                                send_alert('aircraft')
                        time.sleep(ANIMATION_DELAY)

            except Exception as e:
                st.error(f"PROCESSING ERROR: {str(e)}")

def unit_interface(unit):
    name = unit.replace("_", " ").upper()
    st.title(f"🎯 {name} DASHBOARD")
    st.markdown("---")

    alert = get_active_alert()

    if alert == unit:
        st.error("""
        ⚠️ HIGH ALERT
        **ORDERS:** ACTION REQUIRED
        """)
    elif alert:
        st.success("""
        ✅ NO THREAT
        **ORDERS:** MAINTAIN POSITION
        """)

    st.markdown(f"""
    <div style="background-color:{COLORS['army_green']};padding:10px;border-radius:5px;margin-top:20px;">
    <h4 style="color:{COLORS['sand']};">SYSTEM STATUS</h4>
    <p>Time: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
    <p>Status: {'ALERT' if alert else 'NORMAL'}</p>
    </div>
    """, unsafe_allow_html=True)
    time.sleep(REFRESH_INTERVAL)
    st.rerun()

def main():
    set_military_theme()
    init_session()

    if not st.session_state.logged_in:
        st.title("🔐 TACTICAL LOGIN")
        with st.form("auth"):
            username = st.text_input("OPERATOR ID")
            password = st.text_input("ACCESS CODE", type="password")
            if st.form_submit_button("LOGIN"):
                if login(username, password):
                    st.rerun()
                else:
                    if hasattr(st.session_state, 'login_message'):
                        st.success(st.session_state.login_message)
                        del st.session_state.login_message

    if st.session_state.user_role == 'command_center':
        command_center()
    else:
        unit_interface(st.session_state.user_role)

    if st.button("🔒 LOGOUT"):
        st.session_state.clear()
        st.success("LOGOUT SUCCESSFUL")
        time.sleep(1)
        st.rerun()

if __name__ == '__main__':
    main()
