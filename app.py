import streamlit as st
from geopy.distance import geodesic
import math
import time
import pandas as pd
import pydeck as pdk
from datetime import datetime

# Constants
PROXIMITY_THRESHOLD = 4500  # in meters
REFRESH_INTERVAL = 30  # seconds for dashboard refresh
ANIMATION_DELAY = 0.1  # seconds between animation frames
MAX_ALERTS_TO_DISPLAY = 5  # Maximum alerts to show in history

# Colors
COLORS = {
    "red_alert": "#ff0000",
    "yellow_warning": "#ffff00",
    "white": "#ffffff",
    "army_green": "#4B5320",
    "sand": "#C2B280",
    "status_background": "#eeeeee"
}

USER_ROLES = {
    'command_center': {'username': 'command', 'password': 'center123'},
    'ground_unit': {'username': 'ground', 'password': 'unit123'},
    'aircraft': {'username': 'aircraft', 'password': 'flight123'}
}

def init_session() -> None:
    """Initialize session state variables."""
    if 'user_role' not in st.session_state:
        st.session_state.user_role = None
    if 'alerts' not in st.session_state:
        st.session_state.alerts = {'ground_unit': [], 'aircraft': []}
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
    if 'last_refresh' not in st.session_state:
        st.session_state.last_refresh = datetime.now()
    if 'alert_acknowledged' not in st.session_state:
        st.session_state.alert_acknowledged = {'ground_unit': False, 'aircraft': False}
    if 'current_alert' not in st.session_state:
        st.session_state.current_alert = None

def login(username: str, password: str) -> bool:
    """Authenticate user credentials."""
    for role, creds in USER_ROLES.items():
        if creds['username'] == username and creds['password'] == password:
            st.session_state.user_role = role
            st.session_state.logged_in = True
            st.session_state.login_message = f"ACCESS GRANTED: {role.replace('_', ' ').upper()} TERMINAL"
            return True
    st.error('ACCESS DENIED: INVALID CREDENTIALS', icon="🔒")
    return False

def send_alert(unit: str, alert_message: str) -> None:
    """Send alert to the specified unit."""
    st.session_state.current_alert = alert_message
    st.session_state.alert_acknowledged[unit] = False
    st.session_state.alerts[unit].append(alert_message)
    st.success(f"ALERT SENT TO {unit.replace('_', ' ').upper()}: {alert_message}")

def acknowledge_alert(unit: str) -> None:
    """Acknowledge alert from the specified unit."""
    st.session_state.alert_acknowledged[unit] = True
    st.success(f"{unit.replace('_', ' ').upper()} HAS ACKNOWLEDGED THE ALERT")

def create_layers(ground_loc: Tuple[float, float, float], path: List[List[float]]) -> List[pdk.Layer]:
    """Create pydeck layers for visualization."""
    ground_df = pd.DataFrame({
        'latitude': [ground_loc[0]],
        'longitude': [ground_loc[1]],
        'elevation': [ground_loc[2]]
    })
    
    icon_df = pd.DataFrame({
        'coordinates': [[ground_loc[1], ground_loc[0]]],
    })
    
    return [
        pdk.Layer(
            "PathLayer", 
            pd.DataFrame({'path': [path]}), 
            get_color=[139, 0, 0, 255],  # Dark Red color
            get_path="path", 
            width_scale=20, 
            get_width=5
        ),
        pdk.Layer(
            "ScatterplotLayer", 
            ground_df, 
            get_position=["longitude", "latitude"], 
            get_fill_color=[0, 100, 0, 150], 
            get_radius=PROXIMITY_THRESHOLD
        ),
        pdk.Layer(
            "IconLayer", 
            icon_df, 
            get_icon={
                "url": "https://img.icons8.com/ios-filled/50/000000/military-base.png", 
                "width": 128, 
                "height": 128, 
                "anchorY": 128
            }, 
            get_position="coordinates", 
            size_scale=15
        )
    ]

def command_center() -> None:
    """Render command center dashboard."""
    st.title('🛡️ COMMAND CENTER DASHBOARD')
    
    with st.expander("CONFIGURATION", expanded=True):
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
            csv = st.file_uploader("UPLOAD CSV", type="csv", help="CSV with columns: latitude_wgs84(deg), longitude_wgs84(deg), elevation_wgs84(m)")

    if csv:
        try:
            df = pd.read_csv(csv)
            req_cols = ['latitude_wgs84(deg)', 'longitude_wgs84(deg)', 'elevation_wgs84(m)']
            
            if not all(col in df.columns for col in req_cols):
                st.error(f'MISSING COLUMNS: {", ".join(req_cols)}')
                return

            df['path'] = df[['longitude_wgs84(deg)', 'latitude_wgs84(deg)']].values.tolist()
            
            # Calculate view bounds
            min_lat, max_lat = df['latitude_wgs84(deg)'].min(), df['latitude_wgs84(deg)'].max()
            min_lon, max_lon = df['longitude_wgs84(deg)'].min(), df['longitude_wgs84(deg)'].max()
            min_lat, max_lat = min(min_lat, ground[0]), max(max_lat, ground[0])
            min_lon, max_lon = min(min_lon, ground[1]), max(max_lon, ground[1])

            view = pdk.ViewState(
                latitude=(min_lat + max_lat) / 2, 
                longitude=(min_lon + max_lon) / 2, 
                zoom=10, 
                pitch=50
            )

            path = []
            map_area = st.empty()
            status_box = st.empty()
            alert_sent = False

            progress_bar = st.progress(0)
            total_frames = len(df)

            for idx, row in df.iterrows():
                progress_bar.progress((idx + 1) / total_frames)
                path.append(row['path'])
                aircraft = (
                    row['latitude_wgs84(deg)'], 
                    row['longitude_wgs84(deg)'], 
                    row['elevation_wgs84(m)']
                )

                # Update view to follow aircraft
                view.latitude = aircraft[0]
                view.longitude = aircraft[1]

                # Update map
                map_area.pydeck_chart(pdk.Deck(
                    layers=create_layers(ground, path),
                    initial_view_state=view,
                    map_style='mapbox://styles/mapbox/satellite-streets-v11'
                ))

                # Update status
                status_text = f"""
                <div style="padding:10px;border-radius:5px;background-color:{COLORS['status_background']};">
                    <h4>STATUS</h4>
                    <p>Aircraft Frame: {idx+1}/{len(df)}</p>
                </div>
                """
                status_box.markdown(status_text, unsafe_allow_html=True)

                if st.session_state.alert_acknowledged['ground_unit'] == False and not alert_sent:
                    if st.button(f"🚀 ALERT GROUND UNIT @ {idx}", key=f"g{idx}"):
                        send_alert('ground_unit', f"ALERT: Aircraft in range at frame {idx+1}")
                        alert_sent = True
                if st.session_state.alert_acknowledged['aircraft'] == False and not alert_sent:
                    if st.button(f"✈️ ALERT AIRCRAFT @ {idx}", key=f"a{idx}"):
                        send_alert('aircraft', f"ALERT: Aircraft in range at frame {idx+1}")
                        alert_sent = True

                time.sleep(ANIMATION_DELAY)

            progress_bar.empty()
            st.success("Aircraft path simulation completed")

        except Exception as e:
            st.error(f"PROCESSING ERROR: {str(e)}")
            st.exception(e)

def unit_interface(unit: str) -> None:
    """Render interface for ground unit or aircraft."""
    name = unit.replace("_", " ").upper()
    st.title(f"🎯 {name} DASHBOARD")
    st.markdown("---")

    current_alert = st.session_state.current_alert
    alerts = st.session_state.alerts[unit]
    alert_acknowledged = st.session_state.alert_acknowledged[unit]
    
    if alerts:
        st.subheader("ACTIVE ALERTS")
        for alert in alerts:
            st.write(f"• {alert}")

        if current_alert and not alert_acknowledged:
            st.warning(f"⚠️ NEW ALERT: {current_alert}")

        if st.button("✅ ACKNOWLEDGE ALERT"):
            acknowledge_alert(unit)
            st.session_state.current_alert = None
            st.session_state.alert_acknowledged[unit] = True
            st.session_state.last_refresh = datetime.now()
            st.rerun()
    
    else:
        st.success("No active alerts")
    
    # System status panel
    st.markdown(f"""
        <div style="background-color:{COLORS['army_green']};padding:10px;border-radius:5px;margin-top:20px;">
            <h4 style="color:{COLORS['sand']};">SYSTEM STATUS</h4>
            <p>Status: {'🔴 ALERT' if current_alert and not alert_acknowledged else '🟢 NORMAL'}</p>
        </div>
    """, unsafe_allow_html=True)

def render_login() -> None:
    """Render login interface."""
    st.title("🔐 TACTICAL LOGIN")
    with st.form("auth"):
        username = st.text_input("OPERATOR ID")
        password = st.text_input("ACCESS CODE", type="password")
        if st.form_submit_button("LOGIN"):
            if login(username, password):
                st.rerun()

def main() -> None:
    """Main application function."""
    init_session()

    if not st.session_state.logged_in:
        render_login()
    else:
        # Show login success message if available
        if hasattr(st.session_state, 'login_message'):
            st.success(st.session_state.login_message)
            del st.session_state.login_message

        # Render appropriate interface based on role
        if st.session_state.user_role == 'command_center':
            command_center()
        elif st.session_state.user_role in ['ground_unit', 'aircraft']:
            unit_interface(st.session_state.user_role)

if __name__ == '__main__':
    main()
