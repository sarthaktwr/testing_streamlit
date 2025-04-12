# Tactical Aircraft Threat Detection Dashboard (Indian Defence)
 
import streamlit as st

from geopy.distance import geodesic

import math

import time

import pandas as pd

import pydeck as pdk

from datetime import datetime
 
# Constants

PROXIMITY_THRESHOLD = 4500  # in meters

REFRESH_INTERVAL = 30       # seconds for dashboard refresh

ANIMATION_DELAY = 0.1       # seconds between animation frames
 
# Colors

COLORS = {

    "red_alert": "#ff4c4c",

    "yellow_warning": "#ffff00",

    "olive_drab": "#556B2F",

    "military_grey": "#1e1e1e",

    "white": "#ffffff"

}
 
USER_ROLES = {

    'command_center': {'username': 'command', 'password': 'center123'},

    'ground_unit': {'username': 'ground', 'password': 'unit123'},

    'aircraft': {'username': 'aircraft', 'password': 'flight123'}

}
 
def init_session():

    if 'user_role' not in st.session_state:

        st.session_state.user_role = None

    if 'alerts' not in st.session_state:

        st.session_state.alerts = {'ground_unit': [], 'aircraft': []}

    if 'logged_in' not in st.session_state:

        st.session_state.logged_in = False
 
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

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    st.session_state.alerts[unit].append(timestamp)

    st.success(f"ALERT SENT TO {unit.replace('_', ' ').upper()} @ {timestamp}", icon="⚠️")
 
def get_active_alert(unit):

    if st.session_state.alerts[unit]:

        return st.session_state.alerts[unit]

    return []
 
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

        pdk.Layer("PathLayer", pd.DataFrame({'path': [path]}), get_color=[255, 69, 0, 200], get_path="path", width_scale=20, get_width=8),

        pdk.Layer("ScatterplotLayer", ground_df, get_position=["longitude", "latitude"], get_fill_color=[85, 107, 47, 160], get_radius=PROXIMITY_THRESHOLD),

        pdk.Layer("IconLayer", icon_df, get_icon={"url": "https://img.icons8.com/ios-filled/50/000000/military-base.png", "width": 128, "height": 128, "anchorY": 128}, get_position="coordinates", size_scale=15)

    ]
 
def calculate_zoom(min_lat, max_lat, min_lon, max_lon):

    diff = max(abs(max_lat - min_lat), abs(max_lon - min_lon))

    for threshold, zoom in [(20, 4), (10, 5), (5, 6), (2, 7), (1, 8), (0.5, 9), (0.2, 10), (0.1, 11)]:

        if diff > threshold: return zoom

    return 12
 
def command_center():

    st.markdown(f"<h1 style='color:{COLORS['olive_drab']}'>🛡️ COMMAND CENTER</h1>", unsafe_allow_html=True)

    ground, csv = display_command_inputs()
 
    if csv:

        df = load_and_validate_csv(csv)

        if df is not None:

            execute_threat_detection(df, ground)
 
def display_command_inputs():

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

    return ground, csv
 
def load_and_validate_csv(csv):

    try:

        df = pd.read_csv(csv)

        required_columns = ['latitude_wgs84(deg)', 'longitude_wgs84(deg)', 'elevation_wgs84(m)']

        if not all(col in df.columns for col in required_columns):

            st.error(f"MISSING COLUMNS: {', '.join(required_columns)}")

            return None

        df['path'] = df[['longitude_wgs84(deg)', 'latitude_wgs84(deg)']].values.tolist()

        return df

    except Exception as e:

        st.error(f"CSV PARSING ERROR: {e}")

        return None
 
def execute_threat_detection(df, ground):

    min_lat, max_lat = df['latitude_wgs84(deg)'].min(), df['latitude_wgs84(deg)'].max()

    min_lon, max_lon = df['longitude_wgs84(deg)'].min(), df['longitude_wgs84(deg)'].max()

    min_lat, max_lat = min(min_lat, ground[0]), max(max_lat, ground[0])

    min_lon, max_lon = min(min_lon, ground[1]), max(max_lon, ground[1])
 
    view = pdk.ViewState(

        latitude=(min_lat + max_lat) / 2,

        longitude=(min_lon + max_lon) / 2,

        zoom=calculate_zoom(min_lat, max_lat, min_lon, max_lon),

        pitch=50

    )
 
    path = []

    map_area = st.empty()

    status_box = st.empty()
 
    for idx, row in df.iterrows():

        aircraft = (row['latitude_wgs84(deg)'], row['longitude_wgs84(deg)'], row['elevation_wgs84(m)'])

        path.append([aircraft[1], aircraft[0]])
 
        distance = calculate_3d_distance(ground, aircraft)

        view.latitude, view.longitude = aircraft[0], aircraft[1]
 
        render_map(map_area, ground, path, view)

        display_status(idx, len(df), distance, status_box)
 
        if distance <= PROXIMITY_THRESHOLD:

            show_alert_buttons(idx, distance)
 
        time.sleep(ANIMATION_DELAY)
 
def render_map(map_area, ground, path, view):

    map_area.pydeck_chart(

        pdk.Deck(

            layers=create_layers(ground, path),

            initial_view_state=view,

            map_style='mapbox://styles/mapbox/dark-v11'

        )

    )
 
def display_status(idx, total, distance, status_box):

    status = '⚠️ ENGAGEMENT RANGE' if distance <= PROXIMITY_THRESHOLD else '✅ CLEAR'

    color = COLORS['red_alert'] if distance <= PROXIMITY_THRESHOLD else COLORS['white']

    with status_box.container():

        st.markdown(f"""
<div style="padding:10px;border-radius:5px;background-color:{COLORS['military_grey']};color:{color};">
<h4>FRAME {idx+1}/{total}</h4>
<p><b>Distance:</b> {distance:.2f} m</p>
<p><b>Status:</b> {status}</p>
</div>

        """, unsafe_allow_html=True)
 
def show_alert_buttons(idx, distance):

    st.warning(f"⚠️ AIRCRAFT IN RANGE ({distance:.2f} m)")

    c1, c2 = st.columns(2)

    with c1:

        if st.button("🚀 ALERT GROUND UNIT", key=f"g{idx}"):

            send_alert('ground_unit')

    with c2:

        if st.button("✈️ ALERT AIRCRAFT", key=f"a{idx}"):

            send_alert('aircraft')
 
def unit_interface(unit):

    name = unit.replace("_", " ").upper()

    st.markdown(f"<h1 style='color:{COLORS['olive_drab']}'>🎯 {name} TERMINAL</h1>", unsafe_allow_html=True)

    st.markdown("---")
 
    alerts = get_active_alert(unit)
 
    if alerts:

        st.error(f"""

        ⚠️ HIGH ALERT

        **ORDERS:** ACTION REQUIRED  

        **ACTIVE THREATS:** {len(alerts)}  

        **TIMESTAMPS:** {', '.join(alerts)}

        """)

        if st.button("✅ ACKNOWLEDGE & CLEAR ALERTS"):

            st.session_state.alerts[unit] = []

            st.success("ALL ALERTS CLEARED")

    else:

        st.success("""

        ✅ NO THREAT

        **ORDERS:** MAINTAIN POSITION

        """)
 
    st.markdown(f"""
<div style="background-color:{COLORS['military_grey']};padding:10px;border-radius:5px;margin-top:20px;color:{COLORS['white']};">
<h4>SYSTEM STATUS</h4>
<p>Time: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
<p>Status: {'ALERT' if alerts else 'NORMAL'}</p>
</div>

    """, unsafe_allow_html=True)

    time.sleep(REFRESH_INTERVAL)

    st.rerun()
 
def main():

    init_session()
 
    if not st.session_state.logged_in:

        st.title("🔐 SECURE LOGIN")

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

 
